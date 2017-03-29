# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from datetime import datetime
from struct import pack
# from cpython cimport array
import struct

from libc.stdint cimport int64_t, uint64_t, \
    int32_t, uint32_t, uint16_t, intptr_t
from libc.string cimport memset
from libc.stdlib cimport malloc, free


import binascii
import socket
import time
import sys

import ctypes as c
_get_dict = c.pythonapi._PyObject_GetDictPtr
_get_dict.restype = c.POINTER(c.py_object)
_get_dict.argtypes = [c.py_object]


cdef uint16_t checksum(bytes pkt):
    cdef uint32_t s
    cdef uint16_t _s
    if len(pkt) % 2 == 1:
        pkt += b"\0"
    s = sum(struct.unpack("{0}H".format(len(pkt) / 2), pkt))
    s = (s >> 16) + (s & 0xffff)
    s += s >> 16
    _s = ~s
    return (((_s>>8)&0xff)|_s<<8) & 0xffff


cdef unsigned char is_ipv4(bytes ip):
    try:
        socket.inet_aton(ip)
        return 1
    except socket.error:
        return 0


cdef class PKT:
    cdef:
        public dict l7_ports
        public bytes pkt_name

    def __init__(self, *args, **kwargs):
        self.pkt_name = b'PKT'
        if 'l7_ports' in kwargs and isinstance(kwargs['l7_ports'], dict):
            self.l7_ports = kwargs['l7_ports']
        else:
            self.l7_ports = {445:  'NBSS',
                             2003: 'NetflowSimple',
                             2055: 'NetflowSimple'}

    cpdef get_layer(self, bytes name, int instance=1, int found=0):
        cdef int fnd
        fnd = found
        if hasattr(self, 'payload') and isinstance(self.payload, PKT):
            if self.payload.pkt_name == name:
                fnd += 1
            if fnd == instance:
                return self.payload
            else:
                return self.payload.get_layer(name,
                                              instance=instance,
                                              found=fnd)
        else:
            return None

    cpdef bytes pkt2net(self, dict kwargs):
        return b''

    cdef tuple from_buffer(self, tuple args, dict kwargs):
        cdef:
            bytes buff
            unsigned char use_buff
        buff = b''
        use_buff = 0

        if len(args) == 1 and isinstance(args[0], (bytes, str)):
            buff = args[0]
            use_buff = 1
        elif 'data' in kwargs and isinstance(kwargs['data'], (bytes, str)):
            buff = kwargs['data']
            use_buff = 1
        return use_buff, buff


cdef class ARP(PKT):
    '''
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |          Hardware Type        |         Protocol Type         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |  Hardware Len  |   Proto Len  |           Operation           |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |           Sender Hardware Addr (Hardware Len Bytes)           |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |            Sender Protocol Addr (Proto Len Bytes)             |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |           Target Hardware Addr (Hardware Len Bytes)           |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |            Target Protocol Addr (Proto Len Bytes)             |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    '''
    cdef:
        bytes _buffer
        public uint16_t hardware_type, proto_type,
        public unsigned char hardware_len, proto_len
        public bytes sender_hw_addr, sender_proto_addr, target_hw_addr, \
            target_proto_addr
        uint16_t ethernet, proto_ip, _operation
        unsigned char mac_len, ipv4_len

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.pkt_name = b'ARP'
        self.ethernet = 1
        self.proto_ip = 0x800
        self.mac_len = 6
        self.ipv4_len = 4

        cdef:
            unsigned char use_buffer
            unsigned int s_proto_start, t_hw_start, t_proto_start
            bytes h_u, p_u
        use_buffer, self._buffer = self.from_buffer(args, kwargs)
        if use_buffer:
            (self.hardware_type, self.proto_type, self.hardware_len,
             self.proto_len, self.operation) = \
                struct.unpack('!HHBBH', self._buffer[:8])
            if(self.hardware_type == self.ethernet and
                       self.proto_type == self.proto_ip and
                       self.proto_len == self.ipv4_len):
                self.sender_hw_addr = bytes(':'.join('%02x'%i for i in
                                struct.unpack("!6B",self._buffer[8:14])))
                self.sender_proto_addr = socket.inet_ntoa(self._buffer[14:18])
                self.target_hw_addr = bytes(':'.join('%02x'%i for i in
                                struct.unpack("!6B",self._buffer[18:24])))
                self.target_proto_addr = socket.inet_ntoa(self._buffer[24:28])
            else:
                s_proto_start = 8 + self.hardware_len
                t_hw_start = s_proto_start + self.proto_len
                t_proto_start = t_hw_start + self.hardware_len
                t_proto_end = t_proto_start + self.proto_len
                h_u = "!{0}B".format(self.hardware_len)
                p_u = "!{0}B".format(self.proto_len)
                self.sender_hw_addr = \
                    bytes(''.join('%02x'%i for i in struct.unpack(h_u,
                        self._buffer[8:s_proto_start])))
                self.sender_proto_addr = \
                    bytes(''.join('%02x'%i for i in struct.unpack(p_u,
                        self._buffer[s_proto_start:t_hw_start])))
                self.taget_hw_addr = \
                    bytes(''.join('%02x'%i for i in struct.unpack(h_u,
                        self._buffer[t_hw_start:t_proto_start])))
                self.taget_proto_addr = \
                    bytes(''.join('%02x'%i for i in struct.unpack(p_u,
                        self._buffer[t_proto_start:t_proto_end])))
        else:
            self.hardware_type = kwargs.get('hardware_type', self.ethernet)
            self.proto_type = kwargs.get('proto_type', self.proto_ip)
            self.hardware_len = kwargs.get('hardware_len', self.mac_len)
            self.proto_len = kwargs.get('proto_len', self.ipv4_len)
            self.operation = kwargs.get('operation', 1)
            self.sender_hw_addr = kwargs.get('sender_hw_addr',
                                             b'00:00:00:00:00:00')
            self.sender_proto_addr = kwargs.get('sender_proto_addr',
                                                b'0.0.0.0')
            self.target_hw_addr = kwargs.get('target_hw_addr',
                                            b'00:00:00:00:00:00')
            self.target_proto_addr = kwargs.get('target_proto_addr',
                                                b'0.0.0.0')
    property operation:
        def __get__(self):
            return self._operation
        def __set__(self, unsigned char val):
            if val in [1, 2]:
                self._operation = val
            else:
                raise ValueError("Valid operation codes are 1 for request and "
                                 "2 for reply.")


cdef class NullPkt(PKT):
    cdef:
        public bytes payload

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.pkt_name = b'NullPkt'

        if len(args) == 1 and isinstance(args[0], (bytes, str)):
            self.payload = args[0]
        elif 'data' in kwargs and isinstance(kwargs['data'], (bytes, str)):
            self.payload = kwargs['payload']
        else:
            self.payload = b''

    cpdef bytes pkt2net(self, dict kwargs):
        return bytes("{0}".format(self.payload))


cdef class ip4_ph:
    cdef:
        public bytes src, dst
        public unsigned char reserved, proto
        public uint16_t payload_len

    def __cinit__(self, **kwargs):
        self.src = kwargs.get('src', b'0.0.0.0')
        self.dst = kwargs.get('dst', b'0.0.0.0')
        self.reserved = kwargs.get('reserved', 0)
        self.proto = kwargs.get('proto', 0)
        self.payload_len = kwargs.get('payload_len', 0)

cdef class NetflowSimple(PKT):
    cdef:
        bytes _buffer
        public uint16_t version, count
        public uint32_t sys_uptime, unix_secs, unix_nano_seconds
        public bytes payload


    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.pkt_name = b'NetflowSimple'
        cdef:
            unsigned char use_buffer
        use_buffer, self._buffer = self.from_buffer(args, kwargs)

        if use_buffer:
            (self.version,
             self.count,
             self.sys_uptime,
             self.unix_secs,
             self.unix_nano_seconds) = \
                struct.unpack('!HHIII', self._buffer[:16])

            if len(self._buffer[16:]):
                self.payload = self._buffer[16:]
            else:
                self.payload = b''
        else:
            self.version = kwargs.get('version', 0)
            self.count = kwargs.get('count', 0)
            self.sys_uptime = kwargs.get('sys_uptime', 0)
            self.unix_secs = kwargs.get('unix_secs', 0)
            self.unix_nano_seconds = kwargs.get('unix_nano_seconds', 0)
            self.payload = kwargs.get('payload', b'')

    cpdef bytes pkt2net(self, dict kwargs):
        return bytes("{0}{1}".format(pack("!HHIII", self.version,
                                                    self.count,
                                                    self.sys_uptime,
                                                    self.unix_secs,
                                                    self.unix_nano_seconds),
                                     self.payload))


cdef class NBSS(PKT):
    cdef:
        public unsigned char type
        uint32_t type_length, _length
        bytes _buffer
        bytes SMB2_PROTOCOLID
        public PKT payload

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.pkt_name = b'NBSS'
        self.SMB2_PROTOCOLID = b'{0}SMB'.format(chr(254))

        cdef:
            unsigned char use_buffer
        use_buffer, self._buffer = self.from_buffer(args, kwargs)
        if use_buffer:
            type_length = struct.unpack('!I', self._buffer[:4])[0]
            self.type = type_length >> 24
            self.length = type_length & 0xffffff
            if (self.type == 0 and
                        self.length == len(self._buffer[4:]) and
                        self._buffer[4:8] == self.SMB2_PROTOCOLID):
                self.payload = SMB2(self._buffer[4:])
            else:
                self.payload = UndecodedNBSS(self._buffer[4:])
        else:
            self.type = kwargs.get('type', 0)
            self.length = kwargs.get('length', 0)
            if kwargs.has_key('payload'):
                if isinstance(kwargs['payload'], PKT):
                    self.payload = kwargs['payload']
                elif isinstance(kwargs['payload'], bytes):
                    SMB2(kwargs['payload'])
                elif isinstance(kwargs['payload'], str):
                    SMB2(bytes(kwargs['payload']))
                else:
                    self.payload = PKT()
            else:
                self.payload = PKT()


    property length:
        def __get__(self):
            return self._length
        def __set__(self, uint32_t val):
            if 0 <= val <= 0xffffff:
                self._length = val
            else:
                raise ValueError("length valid values are "
                                 "0-{0}".format(0xffffff))


cdef class UndecodedNBSS(PKT):
    cdef:
        public bytes payload

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.pkt_name = b'UndecodedNBSS'
        if (args and len(args) == 1 and
                (type(args[0]) is bytes or type(args[0]) is str)):
            self.payload = args[0]
        elif (kwargs and kwargs.has_key('payload') and
                  (type(kwargs['payload']) is bytes or
                   type(kwargs['payload']) is str)):
            self.payload = bytes(kwargs['payload'])
        else:
            self.payload = b''

    cpdef bytes pkt2net(self, dict kwargs):
        return bytes("{0}".format(self.payload))


cdef class SMB2(PKT):
    cdef:
        bytes _buffer, _signature
        unsigned char _flag_response, _flag_async_command, \
            _flag_related_ops, _flag_signed, _flag_dfs_ops
        uint32_t _flags

        public bytes protocol_id, SMB2_PROTOCOLID
        public uint16_t header_len, credit_charge, command, credits_granted
        public uint32_t status, next_command, tree_id, NT_STATUS_NOERROR
        public uint64_t message_id, async_id, session_id
        public PKT payload
        # Header first 4 bytes for smb2
        public unsigned char SMB2_CREATE
        public unsigned char SMB2_READ

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.pkt_name = b'SMB2'
        self.SMB2_PROTOCOLID = b'{0}SMB'.format(chr(254))
        self.SMB2_CREATE = 0x05
        self.SMB2_READ = 0x08
        self.NT_STATUS_NOERROR = 0

        cdef:
            unsigned char use_buffer
        use_buffer, self._buffer = self.from_buffer(args, kwargs)

        if use_buffer:
            self.protocol_id = self._buffer[:4]
            (self.header_len, self.credit_charge, self.status, self.command,
             self.credits_granted, self._flags, self.next_command,
             self.message_id, self.async_id, self.session_id) = \
                struct.unpack('<HHIHHIIQQQ', self._buffer[4:48])
            self.response = self._flags & 1
            self.async_command = self._flags >> 1 & 1
            self.related_ops = self._flags >> 2 & 1
            self.signed = self._flags >> 3 & 1
            self.dfs_ops = self._flags >> 28 & 1
            self.signature = self._buffer[48:64]
            if not self.async_command:
                # sync request so change async_id into tree_id
                self.tree_id = self.async_id >> 32
                self.async_id = 0
            if (self.command == self.SMB2_CREATE and
                        self.status == self.NT_STATUS_NOERROR):
                if self.response:
                    self.payload = \
                        SMB2CreateResp(self._buffer[self.header_len:],
                                         smb_hdr_len=self.header_len)
                else:
                    self.payload = \
                        SMB2CreateReq(self._buffer[self.header_len:],
                                         smb_hdr_len=self.header_len)
            elif (self.command == self.SMB2_READ and
                        self.status == self.NT_STATUS_NOERROR):
                if self.response:
                    self.payload = \
                        SMB2ReadResp(self._buffer[self.header_len:],
                                         smb_hdr_len=self.header_len)
                else:
                    self.payload = \
                        SMB2ReadReq(self._buffer[self.header_len:],
                                         smb_hdr_len=self.header_len)
            else:
                self.payload = NullPkt(self._buffer[self.header_len:])

        else:
            self.protocol_id = kwargs.get('protocol_id', self.SMB2_PROTOCOLID)
            self.header_len = kwargs.get('header_len', 64)
            self.credit_charge = kwargs.get('credit_charge', 0)
            self.status = kwargs.get('status', 0)
            self.command = kwargs.get('command', 0)
            self.credits_granted = kwargs.get('credits_granted', 0)
            self.next_command = kwargs.get('next_command', 0)
            self.message_id = kwargs.get('message_id', 0)
            self.response = kwargs.get('response', 0)
            self.async_command = kwargs.get('async_command', 0)
            self.related_ops = kwargs.get('related_ops', 0)
            self.signed = kwargs.get('signed', 0)
            self.dfs_ops = kwargs.get('dfs_ops', 0)
            if self.async_command:
                # this is an async request
                self.async_id = kwargs.get('async_id', 0)
                self.tree_id = 0
            else:
                # sync request
                self.tree_id = kwargs.get('tree_id', 0)
                self.async_id = 0
            self.session_id = kwargs.get('session_id', 0)
            self.signature = kwargs.get('signature',
                                        b''.join('0' for i in range(16)))
            self.payload = kwargs.get('payload', PKT())

    property response:
        def __get__(self):
            return self._flag_response
        def __set__(self, unsigned char val):
            if val in [0,1]:
                self._flag_response = val
            else:
                raise ValueError("SMB response bit must be 0 or 1 "
                                 "got: {0}".format(val))

    property async_command:
        def __get__(self):
            return self._flag_async_command
        def __set__(self, unsigned char val):
            if val in [0,1]:
                self._flag_async_command = val
            else:
                raise ValueError("SMB Async bit must be 0 or 1 "
                                 "got: {0}".format(val))

    property related_ops:
        def __get__(self):
            return self._flag_related_ops
        def __set__(self, unsigned char val):
            if val in [0,1]:
                self._flag_related_ops = val
            else:
                raise ValueError("SMB related_ops bit must be 0 or 1 "
                                 "got: {0}".format(val))

    property signed:
        def __get__(self):
            return self._flag_signed
        def __set__(self, unsigned char val):
            if val in [0,1]:
                self._flag_signed = val
            else:
                raise ValueError("SMB signed bit must be 0 or 1 "
                                 "got: {0}".format(val))

    property dfs_ops:
        def __get__(self):
            return self._flag_dfs_ops
        def __set__(self, unsigned char val):
            if val in [0,1]:
                self._flag_dfs_ops = val
            else:
                raise ValueError("SMB dfs_ops bit must be 0 or 1 "
                                 "got: {0}".format(val))

    property signature:
        def __get__(self):
            return self._signature
        def __set__(self, bytes val):
            if len(val) == 16:
                self._signature = val
            else:
                raise ValueError("SMB2 signature must be 16 bytes.")


cdef class SMB2CreateReq(PKT):
    cdef:
        bytes _buffer
        public bytes filename, create_context
        public uint16_t structure_size, name_offset, name_len, smb_hdr_len
        public uint32_t impersonation, access_mask, file_attrs, share_access
        public uint32_t disposition, create_options, create_con_offset
        public uint32_t create_con_len
        public uint64_t create_flags, reserved
        public unsigned char sec_flags, oplock

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.pkt_name = b'SMB2CreateReq'
        self.smb_hdr_len = kwargs.get('smb_hdr_len', 64)
        cdef:
            unsigned char use_buffer
            list fname_chars
            uint16_t name_start, name_end
            uint32_t con_start, con_end

        use_buffer, self._buffer = self.from_buffer(args, kwargs)

        if use_buffer:
            (self.structure_size, self.sec_flags, self.oplock,
             self.impersonation, self.create_flags, self.reserved,
             self.access_mask, self.file_attrs, self.share_access,
             self.disposition, self.create_options, self.name_offset,
             self.name_len, self.create_con_offset, self.create_con_len) = \
                struct.unpack('<HBBIQQIIIIIHHII', self._buffer[:56])

            fname_chars = list()
            if self.name_len and self.name_offset:
                name_start = self.name_offset - self.smb_hdr_len
                name_end = name_start + self.name_len
                # file name is bytes coming out of the unpack
                # unpack returns <char>0<char>0...
                # clean_name removes the 0 and changes any unprintables
                # to '?'
                fname_chars = self.clean_name(
                    struct.unpack('{0}B'.format(self.name_len),
                                  self._buffer[name_start:name_end]))
            self.filename = b''.join(fname_chars)

            if self.create_con_len and self.create_con_offset:
                con_start = self.create_con_offset - self.smb_hdr_len
                con_end = con_start + self.create_con_len
                self.create_context = self._buffer[con_start:con_end]
            else:
                self.create_context = b''
        else:
            self.structure_size = kwargs.get('structure_size', 0)
            self.sec_flags = kwargs.get('sec_flags', 0)
            self.oplock = kwargs.get('oplock', 0)
            self.impersonation = kwargs.get('impersonation', 0)
            self.create_flags = kwargs.get('create_flags', 0)
            self.reserved = kwargs.get('reserved', 0)
            self.access_mask = kwargs.get('access_mask', 0)
            self.file_attrs = kwargs.get('file_attrs', 0)
            self.share_access = kwargs.get('share_access', 0)
            self.disposition = kwargs.get('disposition', 0)
            self.create_options = kwargs.get('create_options', 0)
            self.name_offset = kwargs.get('name_offset', 0)
            self.name_len = kwargs.get('name_len', 0)
            self.create_con_offset = kwargs.get('create_con_offset', 0)
            self.create_con_len = kwargs.get('create_con_len', 0)
            self.filename = kwargs.get('filename', b'')
            self.create_context = kwargs.get('create_context', b'')

    cdef list clean_name(self, tuple input):
        # get rid of unprintable chars from file names
        cdef:
            list cleaned
        cleaned = list()
        for item in input:
            if item == 0:
                pass
            elif item >= 128:
                # insert '?'
                cleaned.append(chr(63))
            else:
                cleaned.append(chr(item))
        return cleaned


cdef class SMB2CreateResp(PKT):
    cdef:
        bytes _buffer
        public bytes create_context, fid
        public uint16_t structure_size, smb_hdr_len
        public uint32_t create_action, file_attrs, reserved
        public uint32_t create_con_offset, create_con_len
        public uint64_t create_time, last_access, last_write, change_time
        public uint64_t allocation_size, end_of_file,
        public unsigned char oplock, flags

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.pkt_name = b'SMB2CreateResp'
        self.smb_hdr_len = kwargs.get('smb_hdr_len', 64)
        cdef:
            unsigned char use_buffer
            uint32_t con_start, con_end
            bytes pars_buff
            bytes fid_bytes

        use_buffer, self._buffer = self.from_buffer(args, kwargs)
        fid_bytes = (b'{3}{2}{1}{0}-{5}{4}-{7}{6}-{8}{9}-'
                     b'{10}{11}{12}{13}{14}{15}')

        if use_buffer:
            pars_buff = '{0}{1}'.format(self._buffer[:64],
                                        self._buffer[80:88])
            (self.structure_size, self.oplock, self.flags, self.create_action,
             self.create_time, self.last_access, self.last_write,
             self.change_time, self.allocation_size, self.end_of_file,
             self.file_attrs, self.reserved, self.create_con_offset,
             self.create_con_len) = struct.unpack('<HBBIQQQQQQIIII', pars_buff)

            self.fid = \
                fid_bytes.format(*(b'{0:02x}'.format(a) for a in
                                   struct.unpack('16B', self._buffer[64:80])))

            if self.create_con_len and self.create_con_offset:
                con_start = self.create_con_offset - self.smb_hdr_len
                con_end = con_start + self.create_con_len
                self.create_context = self._buffer[con_start:con_end]
            else:
                self.create_context = b''
        else:
            self.structure_size = kwargs.get('structure_size', 0)
            self.oplock = kwargs.get('oplock', 0)
            self.flags = kwargs.get('flags', 0)
            self.create_action = kwargs.get('create_action', 0)
            self.create_time = kwargs.get('create_time', 0)
            self.last_access = kwargs.get('last_access', 0)
            self.last_write = kwargs.get('last_write', 0)
            self.change_time = kwargs.get('change_time', 0)
            self.allocation_size = kwargs.get('allocation_size', 0)
            self.end_of_file = kwargs.get('end_of_file', 0)
            self.file_attrs = kwargs.get('file_attrs', 0)
            self.reserved = kwargs.get('reserved', 0)
            self.fid = kwargs.get('fid', b'')
            self.create_con_offset = kwargs.get('create_con_offset', 0)
            self.create_con_len = kwargs.get('create_con_len', 0)
            self.create_context = kwargs.get('create_context', b'')


cdef class SMB2ReadReq(PKT):
    cdef:
        bytes _buffer
        public bytes fid, read_channel
        public uint16_t structure_size, read_channel_offset, read_channel_len
        public uint16_t smb_hdr_len
        public uint32_t length, min_count, channel, remaining_bytes
        public uint64_t offset
        public unsigned char padding, flags

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.pkt_name = b'SMB2ReadReq'
        self.smb_hdr_len = kwargs.get('smb_hdr_len', 64)
        cdef:
            unsigned char use_buffer
            uint32_t read_start, read_end
            bytes fid_bytes, pars_buff

        use_buffer, self._buffer = self.from_buffer(args, kwargs)
        fid_bytes = (b'{3}{2}{1}{0}-{5}{4}-{7}{6}-{8}{9}-'
                     b'{10}{11}{12}{13}{14}{15}')

        if use_buffer:
            pars_buff = '{0}{1}'.format(self._buffer[:16],
                                        self._buffer[32:48])
            (self.structure_size, self.padding, self.flags, self.length,
             self.offset, self.min_count, self.channel, self.remaining_bytes,
             self.read_channel_offset, self.read_channel_len) = \
                struct.unpack('<HBBIQIIIHH', pars_buff)
            self.fid = \
                fid_bytes.format(*(b'{0:02x}'.format(a) for a in
                                   struct.unpack('16B', self._buffer[16:32])))
            if self.read_channel_len and self.read_channel_offset:
                read_start = self.read_channel_offset - self.smb_hdr_len
                read_end = read_start + self.read_channel_len
                self.read_channel = self._buffer[read_start:read_end]
            else:
                self.read_channel = b''
        else:
            self.structure_size = kwargs.get('structure_size', 0)
            self.padding = kwargs.get('padding', 0)
            self.flags = kwargs.get('flags', 0)
            self.length = kwargs.get('length', 0)
            self.offset = kwargs.get('offset', 0)
            self.fid = kwargs.get('fid', b'')
            self.min_count = kwargs.get('min_count', 0)
            self.channel = kwargs.get('channel', 0)
            self.remaining_bytes = kwargs.get('remaining_bytes', 0)
            self.read_channel_offset = kwargs.get('read_channel_offset', 0)
            self.read_channel_len = kwargs.get('read_channel_len', 0)
            self.read_channel = kwargs.get('read_channel', b'')


cdef class SMB2ReadResp(PKT):
    cdef:
        bytes _buffer
        public bytes data
        public uint16_t structure_size, smb_hdr_len
        public uint32_t read_length, read_remaining, reserved2
        public unsigned char data_offset, reserved

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.pkt_name = b'SMB2ReadResp'
        self.smb_hdr_len = kwargs.get('smb_hdr_len', 64)
        cdef:
            unsigned char use_buffer
            uint32_t data_start, data_end

        use_buffer, self._buffer = self.from_buffer(args, kwargs)

        if use_buffer:
            (self.structure_size, self.data_offset, self.reserved,
             self.read_length, self.read_remaining, self.reserved2) = \
                struct.unpack('<HBBIII', self._buffer[:16])
            if self.read_length and self.data_offset:
                data_start = self.data_offset - self.smb_hdr_len
                data_end = data_start + self.read_length
                self.data = self._buffer[data_start:data_end]
            else:
                self.data = b''
        else:
            self.structure_size = kwargs.get('structure_size', 0)
            self.data_offset = kwargs.get('data_offset', 0)
            self.reserved = kwargs.get('reserved', 0)
            self.read_length = kwargs.get('read_length', 0)
            self.read_remaining = kwargs.get('read_remaining', 0)
            self.reserved2 = kwargs.get('reserved2', 0)
            self.data = kwargs.get('data', b'')


cdef class UDP(PKT):
    '''
     0      7 8     15 16    23 24    31
    +--------+--------+--------+--------+
    |     Source      |   Destination   |
    |      Port       |      Port       |
    +--------+--------+--------+--------+
    |                 |                 |
    |     Length      |    Checksum     |
    +--------+--------+--------+--------+
    |
    |          data octets ...
    +---------------- ...
    '''
    cdef:
        public uint16_t sport, dport, ulen, checksum
        public PKT payload
        bytes _buffer

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.pkt_name = b'UDP'
        cdef:
            unsigned char use_buffer
        use_buffer, self._buffer = self.from_buffer(args, kwargs)
        if use_buffer:
            self.sport, self.dport, self.ulen, self.checksum = \
                struct.unpack('!HHHH', self._buffer[:8])
            self.app_layer(self._buffer[8:])
        else:
            self.sport = kwargs.get('sport', 0)
            self.dport = kwargs.get('dport', 0)
            self.ulen = kwargs.get('ulen', 0)
            self.checksum = kwargs.get('checksum', 0)
            if kwargs.has_key('payload'):
                if isinstance(kwargs['payload'], PKT):
                   self.payload = kwargs['payload']
                elif isinstance(kwargs['payload'], (bytes)):
                    self.app_layer(kwargs['payload'])
                elif isinstance(kwargs['payload'], (str)):
                    self.app_layer(bytes(kwargs['payload']))
                else:
                    self.payload = PKT()
            else:
                self.payload = PKT()

    cpdef bytes pkt2net(self, dict kwargs):
        cdef:
            uint16_t _csum, _sum
            unsigned char _update
            ip4_ph _ipv4_pheader
            bytes _bytes, _pload_bytes, ip_ph
        _csum = 0
        _update = 0
        if kwargs.has_key('csum') and kwargs['csum']:
            _csum = 1
        if kwargs.has_key('update') and kwargs['update']:
            _update = 1
        if kwargs.has_key('ipv4_pheader') and kwargs['ipv4_pheader']:
            _ipv4_pheader = kwargs['ipv4_pheader']
        else:
            _ipv4_pheader = ip4_ph()

        if isinstance(self.payload, PKT):
            _pload_bytes = self.payload.pkt2net(kwargs)
        elif isinstance(self.payload, (bytes, str)):
            _pload_bytes = self.payload
        else:
            _pload_bytes = b''

        if _update:
            self.ulen = 8 + len(_pload_bytes)
    #
        if _csum and isinstance(_ipv4_pheader, ip4_ph):
            ip_ph = bytes("{0}{1}{2}".format(_ipv4_pheader.src,
                                             _ipv4_pheader.dst,
                                             pack('!HHHHH',
                                                  _ipv4_pheader.proto,
                                                  self.ulen,
                                                  self.sport,
                                                  self.dport,
                                                  self.ulen)))
            _sum = checksum("{0}\000\000{1}".format(ip_ph, _pload_bytes))
        else:
            _sum = self.checksum
        return bytes("{0}{1}".format(pack('!HHHH', self.sport, self.dport,
                                                   self.ulen, _sum),
                                    _pload_bytes))

    cdef app_layer(self, bytes plbuffer):
        cdef type pkt_cls
        if len(plbuffer):
            if self.dport in self.l7_ports:
                pkt_cls = globals()[self.l7_ports[self.dport]]
            elif self.sport in self.l7_ports:
                pkt_cls = globals()[self.l7_ports[self.sport]]
            elif 0 in self.l7_ports and len(self.l7_ports) == 1:
                pkt_cls = globals()[self.l7_ports[0]]
            else:
                pkt_cls = NullPkt
            self.payload = pkt_cls(plbuffer)
        else:
            self.payload = PKT()


cdef class TCP(PKT):
    '''
     0                  1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |          Source Port          |       Destination Port        |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                        Sequence Number                        |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                    Acknowledgment Number                      |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |  Data |           |U|A|P|R|S|F|                               |
    | Offset| Reserved  |R|C|S|S|Y|I|            Window             |
    |       |           |G|K|H|T|N|N|                               |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |           Checksum            |         Urgent Pointer        |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                    Options                    |    Padding    |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                             data                              |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

    '''

    cdef:
        public uint16_t sport, dport, window, checksum, urg_ptr
        uint16_t _off_flags
        public uint32_t sequence, acknowledgment
        unsigned char _data_offset, _flag_urg, _flag_ack, _flag_psh
        unsigned char _flag_fin, _flag_rst, _flag_syn
        public bytes options
        bytes _buffer
        public PKT payload

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.pkt_name = b'TCP'
        cdef:
            unsigned char use_buffer
            tuple _unpacked
        use_buffer, self._buffer = self.from_buffer(args, kwargs)

        if use_buffer:
            (self.sport, self.dport, self.sequence, self.acknowledgment,
            self._off_flags, self.window, self.checksum, self.urg_ptr) = \
                struct.unpack('!HHIIHHHH', self._buffer[:20])
            self.data_offset = self._off_flags >> 12
            self.flag_urg = (self._off_flags >> 5) & 1
            self.flag_ack = (self._off_flags >> 4) & 1
            self.flag_psh = (self._off_flags >> 3) & 1
            self.flag_rst = (self._off_flags >> 2) & 1
            self.flag_syn = (self._off_flags >> 1) & 1
            self.flag_fin = self._off_flags & 1

            if self.data_offset > 5:
                self.options = self._buffer[20:(self.data_offset * 4)]
            else:
                self.options = b''

            self.app_layer(self._buffer[(self.data_offset * 4):])

        else:
            self.sport = kwargs.get('sport', 0)
            self.dport = kwargs.get('dport', 0)
            self.sequence = kwargs.get('sequence', 0)
            self.acknowledgment = kwargs.get('acknowledgment', 0)
            self.data_offset = kwargs.get('data_offset', 5)
            self.flag_urg = kwargs.get('flag_urg', 0)
            self.flag_ack = kwargs.get('flag_ack', 0)
            self.flag_psh = kwargs.get('flag_psh', 0)
            self.flag_rst = kwargs.get('flag_rst', 0)
            self.flag_syn = kwargs.get('flag_syn', 0)
            self.flag_syn = kwargs.get('flag_syn', 0)
            self.options = kwargs.get('options', b'')
            if kwargs.has_key('payload'):
                if isinstance(kwargs['payload'], PKT):
                   self.payload = kwargs['payload']
                elif isinstance(kwargs['payload'], (bytes)):
                    self.app_layer(kwargs['payload'])
                elif isinstance(kwargs['payload'], (str)):
                    self.app_layer(bytes(kwargs['payload']))
                else:
                    self.payload = PKT()
            else:
                self.payload = PKT()

    property data_offset:
        # 4 bits
        def __get__(self):
            return self._data_offset
        def __set__(self, unsigned char val):
            if 0 <= val <= 15:
                self._data_offset = val
            else:
                raise ValueError("data_offset valid values are 0-15")

    property flag_urg:
        def __get__(self):
            return self._flag_urg
        def __set__(self, unsigned char val):
            if val in [0,1]:
                self._flag_urg = val
            else:
                raise ValueError("TCP URG bit must be 0 or 1 "
                                 "got: {0}".format(val))

    property flag_ack:
        def __get__(self):
            return self._flag_ack
        def __set__(self, unsigned char val):
            if val in [0,1]:
                self._flag_ack = val
            else:
                raise ValueError("TCP ACK bit must be 0 or 1 "
                                 "got: {0}".format(val))

    property flag_psh:
        def __get__(self):
            return self._flag_psh
        def __set__(self, unsigned char val):
            if val in [0,1]:
                self._flag_psh = val
            else:
                raise ValueError("TCP PSH bit must be 0 or 1 "
                                 "got: {0}".format(val))

    property flag_rst:
        def __get__(self):
            return self._flag_rst
        def __set__(self, unsigned char val):
            if val in [0,1]:
                self._flag_rst = val
            else:
                raise ValueError("TCP RST bit must be 0 or 1 "
                                 "got: {0}".format(val))

    property flag_syn:
        def __get__(self):
            return self._flag_syn
        def __set__(self, unsigned char val):
            if val in [0,1]:
                self._flag_syn = val
            else:
                raise ValueError("TCP SYN bit must be 0 or 1 "
                                 "got: {0}".format(val))

    property flag_fin:
        def __get__(self):
            return self._flag_fin
        def __set__(self, unsigned char val):
            if val in [0,1]:
                self._flag_fin = val
            else:
                raise ValueError("TCP FIN bit must be 0 or 1 "
                                 "got: {0}".format(val))

    cdef app_layer(self, bytes plbuffer):
        cdef type pkt_cls
        if len(plbuffer):
            if self.dport in self.l7_ports:
                pkt_cls = globals()[self.l7_ports[self.dport]]
            elif self.sport in self.l7_ports:
                pkt_cls = globals()[self.l7_ports[self.sport]]
            elif 0 in self.l7_ports and len(self.l7_ports) == 1:
                pkt_cls = globals()[self.l7_ports[0]]
            else:
                pkt_cls = NullPkt
            self.payload = pkt_cls(plbuffer)
        else:
            self.payload = PKT()


cdef class IP(PKT):
    '''
     0                   1                   2                   3
     0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |Version|  IHL  |Type of Service|          Total Length         |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |         Identification        |Flags|      Fragment Offset    |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |  Time to Live |    Protocol   |         Header Checksum       |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                       Source Address                          |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                    Destination Address                        |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                    Options                    |    Padding    |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    '''
    cdef:
        unsigned char _version, _iphl
        public unsigned char ttl, _proto, tos
        unsigned char _flag_d, _flag_m, _flag_x
        uint16_t _frag_offset
        public uint16_t checksum, total_len, ident,
        bytes _src, _dst, _buffer
        public PKT payload
        ip4_ph ipv4_pheader

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.pkt_name = b'IP'
        cdef:
            unsigned char use_buffer
            tuple _unpacked
        self.ipv4_pheader = ip4_ph()
        use_buffer, self._buffer = self.from_buffer(args, kwargs)

        if use_buffer:
            _unpacked = struct.unpack('!HHHHBBH', self._buffer[:12])
            self.version = _unpacked[0] >> 12
            self.iphl = (_unpacked[0] & 0x0f00) >> 8
            self.tos = _unpacked[0] & 0x00ff
            self.total_len = _unpacked[1]
            self.ident = _unpacked[2]
            self.flag_x = _unpacked[3] >> 15
            self.flag_d = (_unpacked[3] & 0b0100000000000000) >> 14
            self.flag_m = (_unpacked[3] & 0b0010000000000000) >> 13
            self.frag_offset= _unpacked[3] & 0b00000000000000000001111111111111
            self.ttl = _unpacked[4]
            self.proto = _unpacked[5]
            self.checksum = _unpacked[6]
            self.src = socket.inet_ntoa(self._buffer[12:16])
            self.dst = socket.inet_ntoa(self._buffer[16:20])
            if len(self._buffer[(self.iphl * 4):]):
                if self.proto == 17:
                    self.payload = UDP(self._buffer[(self.iphl * 4):],
                                       l7_ports = self.l7_ports)
                elif self.proto == 6:
                    self.payload = TCP(self._buffer[(self.iphl * 4):],
                                       l7_ports = self.l7_ports)
                else:
                    self.payload = NullPkt(self._buffer[(self.iphl * 4):],
                                           l7_ports = self.l7_ports)
            else:
                self.payload = PKT()
        else:
            self.version = kwargs.get('version', 4)
            self.iphl = kwargs.get('iphl', 5)
            self.tos = kwargs.get('tos', 0)
            self.total_len = kwargs.get('total_len', 0)
            self.ident = kwargs.get('ident', 0)
            self.flag_x = kwargs.get('flag_x', 0)
            self.flag_d = kwargs.get('flag_d', 0)
            self.flag_m = kwargs.get('flag_m', 0)
            self.frag_offset = kwargs.get('frag_offset', 0)
            self.ttl = kwargs.get('ttl', 64)
            self.proto = kwargs.get('proto', 0)
            self.checksum = kwargs.get('checksum', 0)
            self.src = kwargs.get('src', b'0.0.0.0')
            self.dst = kwargs.get('dst', b'0.0.0.0')
            if (kwargs.has_key('payload') and
                    isinstance(kwargs['payload'], PKT)):
                self.payload = kwargs['payload']
            elif (kwargs.has_key('payload') and
                      isinstance(kwargs['payload'], (str, bytes))):
                if self.proto == 17:
                    self.payload = UDP(kwargs['payload'],
                                       l7_ports = self.l7_ports)
                elif self.proto == 6:
                    self.payload = UDP(kwargs['payload'],
                                       l7_ports = self.l7_ports)
                else:
                    self.payload = NullPkt(kwargs['payload'],
                                           l7_ports = self.l7_ports)
            else:
                self.payload = PKT()

    cpdef bytes pkt2net(self, dict kwargs):
        cdef:
            unsigned char _csum
            bytes _pload_bytes, ip_ph

            uint16_t _sum
        _csum = 0
        _update = 0
        _pload_bytes = b''
        ip_ph = b''

        _csum = kwargs.get('csum', 0)
        _update = kwargs.get('update', 0)
        if isinstance(self.payload, (TCP, UDP)):
            kwargs['ipv4_pheader'] = self.ipv4_pheader
        if isinstance(self.payload, PKT):
            _pload_bytes = self.payload.pkt2net(kwargs)
        else:
            _pload_bytes = b''

        if _update:
            self.total_len = self.iphl * 4 + len(_pload_bytes)

        ip_ph = pack('!HHHHH',
                     (self.version << 12) + (self.iphl << 8) + self.tos,
                     self.total_len,
                     self.ident,
                     ((self.flag_x << 15) +
                        (self.flag_d << 14) +
                        (self.flag_m << 13) +
                        self.frag_offset),
                     (self.ttl << 8) + self.proto)

        if _csum:
            _sum = checksum(bytes("{0}\000\000"
                                  "{1}{2}".format(ip_ph,
                                                  self.ipv4_pheader.src,
                                                  self.ipv4_pheader.dst)))
        else:
            _sum = self.checksum

        return bytes("{0}{1}{2}{3}{4}".format(ip_ph,
                                              pack('!H', _sum),
                                              self.ipv4_pheader.src,
                                              self.ipv4_pheader.dst,
                                              _pload_bytes))

    property version:
        """ The IP version defined by this packet. """
        def __get__(self):
            """ Return the IP Version. """
            return self._version
        def __set__(self, unsigned char val):
            """ Set the IP Version. """
            if val in [4,6]:
                self._version = val
            else:
                raise ValueError("Only IP versions 4 and 6 supported")

    property iphl:
        """ Number of 32 bit words in the header. Max is 15 (60 bytes). """
        def __get__(self):
            """ Return the number of 32 bit words in the header. """
            return self._iphl
        def __set__(self, unsigned char val):
            """ Set the IP header length in 32 bit words. """
            if 0 <= val <= 0xf:
                self._iphl = val
            else:
                raise ValueError("IP iphl valid values are 0-15")

    property flag_x:
        """ Set or get the so called evil bit. See RFC 3514. Implemented
        here for fun. """
        def __get__(self):
            """ Return the Evil Bit. """
            return self._flag_x
        def __set__(self, unsigned char val):
            """ Set the Evil Bit. """
            if val in [0,1]:
                self._flag_x = val
            else:
                raise ValueError("IP Evil bit must be 0 or 1")

    property flag_d:
        """ Set or get the do not fragment bit. """
        def __get__(self):
            """ Return the do not fragment bit. """
            return self._flag_d
        def __set__(self, unsigned char val):
            """ Set the do not fragment bit. """
            if val in [0,1]:
                self._flag_d = val
            else:
                raise ValueError("IP do not fragment bit must be 0 or 1")

    property flag_m:
        """ Set or get the more fragments bit. """
        def __get__(self):
            """ Return the more fragments bit. """
            return self._flag_m
        def __set__(self, unsigned char val):
            """ Set the more fragments bit. """
            if val in [0,1]:
                self._flag_m = val
            else:
                raise ValueError("IP more fragments bit must be 0 or 1")

    property frag_offset:
        """ Get and set the frag_offset of the datagram. """
        def __get__(self):
            """ Return the frag_offset. """
            return self._frag_offset
        def __set__(self, uint16_t val):
            """ Set the datagram frag_offset value. """
            if 0 <= val <= 0x1fff:
                self._frag_offset = val
            else:
                raise ValueError("IP frag offset valid values are 0-8191")

    property proto:
        """ Get and set the proto. """
        def __get__(self):
            """ Return the proto. """
            return self._proto
        def __set__(self, unsigned char val):
            """ Set the datagram proto value. """
            self._proto = val
            self.ipv4_pheader.proto = val

    property src:
        def __get__(self):
            return self._src
        def __set__(self, bytes val):
            if is_ipv4(val):
                self._src = val
                self.ipv4_pheader.src = socket.inet_aton(val)
            else:
                raise ValueError("src must be a dot notation "
                                 "IPv4 string. (1.1.1.1)")

    property dst:
        def __get__(self):
            return self._dst
        def __set__(self, bytes val):
            if is_ipv4(val):
                self._dst = val
                self.ipv4_pheader.dst = socket.inet_aton(val)
            else:
                raise ValueError("dst must be a dot notation "
                                 "IPv4 string. (1.1.1.1)")


cdef class MPLS(PKT):
    cdef:
        unsigned char _tc, _bs
        public unsigned char _ttl
        uint32_t _label
        public PKT payload

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.pkt_name = b'MPLS'
        self.label = kwargs.get('label', 0)
        self.tc = kwargs.get('tc', 0)
        self.s = kwargs.get('s', 0)
        self.ttl = kwargs.get('ttl', 0)
        if kwargs.has_key('payload') and isinstance(kwargs['payload'], PKT):
            self.payload = kwargs['payload']
        elif (kwargs.has_key('payload') and
                  isinstance(kwargs['payload'], (str, bytes))):
            self.payload = NullPkt(kwargs['payload'],
                                   l7_ports = self.l7_ports)
        else:
            self.payload = NullPkt(b'')

    property label:
        """ The label value. """
        def __get__(self):
            """ Return the label value. """
            return self._label
        def __set__(self, uint32_t val):
            """ Set the label value. """
            if 0 <= val <= '0xfffff':
                self._label = val
            else:
                raise ValueError("label valid values are 0-1048575")

    property tc:
        """ The Traffic Class. """
        def __get__(self):
            """ Return the traffic class value. """
            return self._tc
        def __set__(self, unsigned char val):
            """ Set the traffic class value. """
            if 0 <= val <= 0b111:
                self._tc = val
            else:
                raise ValueError("IP ttl valid values are 0-255")

    property s:
        """ Set or get the stack bit. """
        def __get__(self):
            """ Return the do not fragment bit. """
            return self._bs
        def __set__(self, unsigned char val):
            """ Set the do not fragment bit. """
            if val in [0,1]:
                self._bs = val
            else:
                raise ValueError("Bottom of stack bit must be 0 or 1")

    cpdef bytes pkt2net(self, dict kwargs):
        cdef:
            bytes _pload_bytes

        _pload_bytes = b''

        if isinstance(self.payload, PKT):
            _pload_bytes = self.payload.pkt2net(kwargs)
        else:
            _pload_bytes = b''

        return bytes("{0}{1}".format(pack('!I', (self.label << 12) +
                                                (self.tc << 9) +
                                                (self.s << 8) +
                                                self.ttl),
                                                _pload_bytes))


cdef class Ethernet(PKT):

    cdef:
        bytes _buffer
        public bytes src_mac, dst_mac
        public uint16_t type, ETH_TYPE_IP, ETH_TYPE_ARP
        public PKT payload
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.pkt_name = b'Ethernet'
        cdef unsigned char use_buffer
        self.ETH_TYPE_IP = 0x0800  # IP protocol
        self.ETH_TYPE_ARP = 0x0806 # ARP
        use_buffer, self._buffer = self.from_buffer(args, kwargs)

        if use_buffer:
            self.dst_mac = bytes(':'.join('%02x'%i for i in
                                struct.unpack("!6B",self._buffer[:6])))
            self.src_mac = bytes(':'.join('%02x'%i for i in
                                struct.unpack("!6B",self._buffer[6:12])))
            self.type = struct.unpack('!H', self._buffer[12:14])[0]
            if self.type == self.ETH_TYPE_IP:
                self.payload = IP(self._buffer[14:],
                                  l7_ports = self.l7_ports)
            elif self.type == self.ETH_TYPE_ARP:
                self.payload = ARP(self._buffer[14:])
            else:
                self.payload = NullPkt(self._buffer[14:])
        else:
            self.src_mac = kwargs.get('src_mac', b'00:00:00:00:00:00')
            self.dst_mac = kwargs.get('dst_mac', b'00:00:00:00:00:00')
            self.type = kwargs.get('type', self.ETH_TYPE_IP)
            self.payload = kwargs.get('payload', PKT())

    cpdef bytes pkt2net(self, dict kwargs):
        cdef:
            bytes _pload_bytes
            str src, dst
        src = ''
        dst = ''
        _pload_bytes = b''

        if isinstance(self.payload, PKT):
            _pload_bytes = self.payload.pkt2net(kwargs)
        for pair in str(self.src_mac).split(':'):
            src += binascii.unhexlify(pair)
        for pair in str(self.dst_mac).split(':'):
            dst += binascii.unhexlify(pair)
        return bytes("{0}{1}{2}{3}".format(dst,
                                           src,
                                           pack('!H', self.type),
                                           _pload_bytes))


cdef class PcapHeader:
    cdef:
        bytes _buffer, _order
        int32_t _tz_offset
        uint16_t use_buffer
        public uint32_t magic, ts_accuracy, snap_len, net_layer
        public uint32_t PCAP_MAGIC_IDENT, PCAP_MAGIC_IDENT_NANO
        public uint32_t PCAP_MAGIC_SWAPPED_NANO, PCAP_MAGIC_SWAPPED
        public uint16_t nano, major_version, minor_version

    def __init__(self, *args, **kwargs):
        self.PCAP_MAGIC_IDENT = 0xa1b2c3d4
        self.PCAP_MAGIC_IDENT_NANO = 0xa1b23c4d
        self.PCAP_MAGIC_SWAPPED = 0xd4c3b2a1
        self.PCAP_MAGIC_SWAPPED_NANO= 0x4d3cb2a1
        self.use_buffer = 0
        self._buffer = b''
        if (args and
                len(args) == 1 and
                (type(args[0]) is str or type(args[0]) is bytes)):
            self._buffer = args[0]
            self.use_buffer = 1
        elif (kwargs and kwargs.has_key('data') and
                type(kwargs['data']) is bytes):
            self._buffer = kwargs['data']
            self.use_buffer = 1

        if self.use_buffer:
            self.magic = struct.unpack('I', self._buffer[:4])[0]
            if self.magic == self.PCAP_MAGIC_IDENT:
                self.order = '<'
                self.nano = 0
            elif self.magic == self.PCAP_MAGIC_IDENT_NANO:
                self.order = '<'
                self.nano = 1
            elif self.magic == self.PCAP_MAGIC_SWAPPED:
                self.order = '>'
                self.nano = 0
            elif self.magic == self.PCAP_MAGIC_SWAPPED_NANO:
                self.order = '>'
                self.nano = 1
            else:
                raise ValueError('PCAP header magic number is invalid. Was '
                                 '{0} vs {1}'.format(self.magic,
                                                     self.PCAP_MAGIC_IDENT))
            (self.major_version,
            self.minor_version,
            self.tz_offset,
            self.ts_accuracy,
            self.snap_len,
            self.net_layer) = struct.unpack('{0}HHiIII'.format(self.order),
                                                        self._buffer[4:])
            if self.net_layer != 1:
                raise ValueError('PCAP does not contain Ethernet packets. '
                                 'Type not supported.')
        else:
            self.magic = kwargs.get('magic', self.PCAP_MAGIC_IDENT)
            if self.magic == self.PCAP_MAGIC_IDENT:
                self.order = '<'
                self.nano = 0
            elif self.magic == self.PCAP_MAGIC_IDENT_NANO:
                self.order = '<'
                self.nano = 1
            elif self.magic == self.PCAP_MAGIC_SWAPPED:
                self.order = '>'
                self.nano = 0
            elif self.magic == self.PCAP_MAGIC_SWAPPED_NANO:
                self.order = '>'
                self.nano = 1
            else:
                raise ValueError('PCAP header magic number is invalid. Was '
                                 '{0} vs {1}'.format(self.magic,
                                                     self.PCAP_MAGIC_IDENT))
            self.major_version = kwargs.get('major_version', 2)
            self.minor_version = kwargs.get('minor_version', 4)
            self.tz_offset = kwargs.get('tz_offset', 0)
            self.ts_accuracy = kwargs.get('ts_accuracy', 0)
            self.snap_len = kwargs.get('snap_len', 1500)
            self.net_layer = kwargs.get('net_layer', 1)
    property order:
        def __get__(self):
            return self._order
        def __set__(self, bytes val):
            if val in ['<', '>']:
                self._order = val
            else:
                raise ValueError("order must '>' or '<'")

    property tz_offset:
        def __get__(self):
            return self._tz_offset
        def __set__(self, int val):
            if -0x80000000 <= val <= 0x7fffffff:
                self._tz_offset = val
                if val != 0:
                    print("Warning: Non-Zero time zone offset "
                          "({0}).".format(val))
            else:
                raise ValueError("Valid tz_offset number values are "
                                 "{0}-{1}".format(-0x80000000, 0x7fffffff))

    def __str__(self):
        return bytes(pack('{0}IHHIIII'.format(self.order),
                          self.magic,
                          self.major_version,
                          self.minor_version,
                          self.tz_offset,
                          self.ts_accuracy,
                          self.snap_len,
                          self.net_layer))


cdef class PktHeader:
    cdef:
        bytes _buffer, _order
        uint16_t use_buffer
        public uint32_t ts_sec, ts_usec, incl_len, orig_len

    def __init__(self, *args, **kwargs):
        self.order = kwargs.get('order', b'<')
        self.use_buffer = 0
        self._buffer = b''
        if (args and len(args) == 1 and
                (type(args[0]) is str or type(args[0]) is bytes)):
            self._buffer = args[0]
            self.use_buffer = 1
        elif (kwargs and kwargs.has_key('data') and
                    type(kwargs['data']) is bytes):
            self._buffer = kwargs['data']
            self.use_buffer = 1

        if self.use_buffer:
            (self.ts_sec,
             self.ts_usec,
             self.incl_len,
             self.orig_len) = struct.unpack('{0}IIII'.format(self.order),
                                            self._buffer)
        else:
            self.ts_sec = kwargs.get('ts_sec', 0)
            self.ts_usec = kwargs.get('ts_usec', 0)
            self.incl_len = kwargs.get('incl_len', 0)
            self.orig_len = kwargs.get('orig_len', 0)
    def __str__(self):
        return bytes(pack('{0}IIII'.format(self.order),
                          self.ts_sec,
                          self.ts_usec,
                          self.incl_len,
                          self.orig_len))

    property order:
        def __get__(self):
            return self._order
        def __set__(self, bytes val):
            if val in ['<', '>']:
                self._order = val
            else:
                raise ValueError("order must '>' or '<'")

    cpdef double get_timestamp(self, file_header_nano):
        cdef double rval
        if file_header_nano:
            rval = self.ts_sec + (self.ts_usec / 1000000000.0)
        else:
            rval = self.ts_sec + (self.ts_usec / 1000000.0)
        return rval


cdef class Reader:
    cdef:
        object _f
        PcapHeader header
        object _iter
        uint16_t PCAP_HDR_LEN, PKT_HDR_LEN

    def __init__(self, file_handle):
        self.PCAP_HDR_LEN = 24
        self.PKT_HDR_LEN = 16

        self._f = file_handle
        self.header =  PcapHeader(self._f.read(self.PCAP_HDR_LEN))
        self._iter = iter(self)

    cpdef int tz_offset(self):
        return self.header.tz_offset

    cpdef list readpkts(self):
        return list(self)

    cpdef next(self):
        return self._iter.next()

    def __iter__(self):
        cdef:
            bytes data, pkt
            PktHeader hdr

        while 1:
            data = self._f.read(self.PKT_HDR_LEN)
            if not len(data):
                break
            hdr = PktHeader(data, order=self.header.order)
            pkt = self._f.read(hdr.incl_len)
            yield (hdr.get_timestamp(self.header.nano), pkt)


cdef class Writer:
    cdef:
        object _f
        PcapHeader _header
        PktHeader _p_header_c
        uint16_t EN10MB
        uint32_t PCAP_MAGIC_IDENT, PCAP_MAGIC_SWAPPED, _magic, _n
        double _ts
        # bytes _s

    def __init__(self, file_handle, snap_len=1500, net_layer=1):
        self.PCAP_MAGIC_IDENT = 0xa1b2c3d4
        self.PCAP_MAGIC_SWAPPED = 0xd4c3b2a1
        self._magic = self.PCAP_MAGIC_SWAPPED
        if sys.byteorder == 'little':
            self._magic = self.PCAP_MAGIC_IDENT
        self.EN10MB = 1
        self._f = file_handle
        self._header = PcapHeader(magic=self._magic, snap_len=snap_len,
                                  net_layer=net_layer)
        self._f.write(str(self._header))

    cpdef writepkt(self, bytes pkt, double ts):
        if ts ==0.00:
            _ts = time.time()
        else:
            _ts = ts
        # _s = pkt
        _n = len(pkt)
        _p_header_c = PktHeader(ts_sec=int(_ts),
                                ts_usec=int(round(_ts % 1, 6) * 10 ** 6),
                                incl_len=_n, orig_len=_n,
                                order = self._header.order)
        self._f.write(str(_p_header_c))
        self._f.write(pkt)

    def close(self):
        self._f.close()

cpdef list pcap_info(object f):
    cdef:
        Reader rdr
        uint32_t pkts
        double first_ts, last_ts
        bytes pkt
        list rval

    rdr = Reader(f)
    first_ts, pkt = rdr.next()
    pkts = 1
    for last_ts, pkt in rdr:
        pkts += 1
    rval = list([first_ts, last_ts, pkts])
    return rval

cpdef long cidx(list columns, str name):
    if columns.count(name):
        return columns.index(name)
    else:
        return -1

cpdef bytes get_name_from_fid(dict name_map, bytes fid, frozenset session):
    if session in name_map and fid in name_map[session]:
        return bytes(name_map[session][fid])
    else:
        return fid

cpdef dict smb_analysis_get_file_map(list packet_data):
    cdef:
        list c
        tuple record
        dict rval_id_name, msg_map, messages, msg_data
        frozenset session_hash, session
        uint16_t SMB_SUCCESS
        uint64_t msg_id

    SMB_SUCCESS = 0x00
    # columns this analysis function expects in data
    c = ['pkt.ts', 'ip.src', 'tcp.srcport', 'ip.dst', 'tcp.dstport',
         'smb2.msg_id', 'smb2.fid', 'smb2.filename', 'smb2.nt_status',
         'smb2.cmd', 'smb2.file_offset', 'smb2.read_length', 'ip.len',
         'ip.hdr_len', 'tcp.seq', 'tcp.ack']
    record = tuple()
    rval_id_name = dict()
    msg_map = dict()
    for record in packet_data:
            session_hash = frozenset([(record[cidx(c, 'ip.src')],
                                       record[cidx(c, 'tcp.srcport')]),
                                      (record[cidx(c, 'ip.dst')],
                                       record[cidx(c, 'tcp.dstport')])])
            if record[cidx(c, 'smb2.cmd')] == 5:
                if session_hash not in msg_map:
                    msg_map[session_hash] = dict()
                if record[cidx(c, 'smb2.msg_id')] not in msg_map[session_hash]:
                    msg_map[session_hash][record[cidx(c, 'smb2.msg_id')]] = \
                        {'cli_data': {'name': None},
                         'srv_data': {'fid': None, 'stat': None}}

                if (record[cidx(c, 'tcp.srcport')] >
                        record[cidx(c, 'tcp.dstport')]):
                    # This is a client record
                    msg_map[session_hash][record[cidx(c,
                        'smb2.msg_id')]]['cli_data']['name'] = \
                        record[cidx(c, 'smb2.filename')]
                else:
                    # Srv record
                    msg_map[session_hash][record[cidx(c,
                        'smb2.msg_id')]]['srv_data']['fid'] = \
                        record[cidx(c, 'smb2.fid')]
                    msg_map[session_hash][record[cidx(c,
                        'smb2.msg_id')]]['srv_data']['stat'] = \
                        record[cidx(c, 'smb2.nt_status')]

    for session, messages in msg_map.iteritems():
        if session not in rval_id_name:
            # new session in the data.
            rval_id_name[session] =  dict()
        for msg_id, msg_data in messages.iteritems():
            if msg_data['srv_data']['stat'] == SMB_SUCCESS:
                # This request worked. We should have a good FID to name match.
                if msg_data['cli_data']['name'] in rval_id_name[session]:
                    print('WARNING: Name collision while building name_map '
                          'for file ID - '
                          '{0}.'.format(msg_data['cli_data']['name']))
                else:
                    if msg_data['cli_data']['name'] is not None:
                        rval_id_name[session][msg_data['srv_data']['fid']] = \
                            msg_data['cli_data']['name']
    return rval_id_name

cpdef list smb_analysis_normalize_to_shark(list packet_data, dict map):
    """
    Analyze the data and normalize it into NetShark data. Each item in the
    list represents a second and contains a list of data showing all packets
    in that second matching:
        [Key('tcp.client_ip'),
         Key('tcp.server_ip'),
         Key('cifs.file_path'),
         Value('tcp.window'),
         Value('cifs.requests'),
         Value('generic.bytes')]

    [
        {u'vals':
             [[u'10.38.25.27', u'10.16.128.24', u'wkssvc', 65536, 1, 171],
              [u'10.38.25.27', u'10.16.128.24', u'srvsvc', 66048, 1, 171],
              ...],
         u'p': 64,
         u't': datetime.datetime(2016,
                                 8,
                                 8,
                                 12,
                                 35,
                                 55,
                                 324104,
                                 tzinfo=tzutc()
                                 )
         },
        ...
    ]
    """
    cdef:
        list c
        tuple record
        frozenset session_hash
        uint16_t SMB_SUCCESS, first_pkt
        uint64_t msg_id, second_index
        double first_ts, cur_ts, pkt_ts
        list sec_data, f_record
        dict cur_sec_data, last_sec_data
        bytes f_name, f_hash

    SMB_SUCCESS = 0x00
    # columns this analysis function expects in data
    c = ['pkt.ts', 'ip.src', 'tcp.srcport', 'ip.dst', 'tcp.dstport',
         'smb2.msg_id', 'smb2.fid', 'smb2.filename', 'smb2.nt_status',
         'smb2.cmd', 'smb2.file_offset', 'smb2.read_length', 'ip.len',
         'ip.hdr_len', 'tcp.seq', 'tcp.ack']
    sc = ['tcp.client_ip', 'tcp.server_ip', 'cifs.file_path',
          'tcp.window', 'cifs.requests', 'generic.bytes']

    record = tuple()
    sec_data = list([{u'vals': list(), u'p': 0, u't': None}])
    cur_sec_data = dict()
    first_pkt = 1
    second_index = 0
    for record in packet_data:
            session_hash = frozenset([(record[cidx(c, 'ip.src')],
                                       record[cidx(c, 'tcp.srcport')]),
                                      (record[cidx(c, 'ip.dst')],
                                       record[cidx(c, 'tcp.dstport')])])
            if record[cidx(c, 'smb2.cmd')] == 8:
                if first_pkt:
                    first_ts = record[cidx(c, 'pkt.ts')]
                    cur_ts = record[cidx(c, 'pkt.ts')]
                    sec_data[second_index]['t'] = \
                        datetime.utcfromtimestamp(record[cidx(c, 'pkt.ts')])
                    first_pkt = 0
                if (record[cidx(c, 'tcp.srcport')] >
                        record[cidx(c, 'tcp.dstport')]):
                    # only want client records for now
                    f_name = get_name_from_fid(map,
                                               record[cidx(c, 'smb2.fid')],
                                               session_hash)
                    f_hash = '{0}-{1}-{2}'.format(record[cidx(c, 'ip.dst')],
                                                  record[cidx(c, 'ip.src')],
                                                  f_name)
                    if cur_ts <= record[cidx(c, 'pkt.ts')] < (cur_ts + 1):
                        # This record is in the current second.
                        if f_hash in cur_sec_data:
                            cur_sec_data[f_hash][cidx(sc,
                                                      'cifs.requests')] += 1
                            cur_sec_data[f_hash][cidx(sc,
                                                      'generic.bytes')] += \
                                record[cidx(c, 'smb2.read_length')]
                        else:
                            cur_sec_data[f_hash] = \
                            list([record[cidx(c, 'ip.dst')],
                                  record[cidx(c, 'ip.src')],
                                  f_name,
                                  None,
                                  1,
                                  record[cidx(c, 'smb2.read_length')]])
                        sec_data[second_index]['p'] += 1

                    elif (cur_ts + 1) <= record[cidx(c,'pkt.ts')]:
                        # packet is past current second
                        # flush the current second to the sec_data
                        if len(cur_sec_data.keys()):
                            for _, f_record in cur_sec_data.iteritems():
                                sec_data[second_index]['vals'].append(f_record)
                        else:
                            del sec_data[second_index]

                        cur_ts += 1
                        while record[cidx(c,'pkt.ts')] >= (cur_ts + 1):
                            cur_ts += 1
                        cur_sec_data = dict()
                        sec_data.append({u'vals': list(),
                                         u'p': 0,
                                         u't': datetime.utcfromtimestamp(
                                             cur_ts)})
                        second_index += 1
                        cur_sec_data[f_hash] = list([record[cidx(c, 'ip.dst')],
                                                     record[cidx(c, 'ip.src')],
                                                    f_name,
                                                    None,
                                                    1,
                                                    record[cidx(c,
                                                        'smb2.read_length')]])
                        sec_data[second_index]['p'] += 1
                    else:
                        # out of order for some reason
                        pass
    return sec_data


cpdef list smb_analyze(unicode pcap_file):
    cdef:
        Reader rdr
        Ethernet pk
        IP ip
        TCP tcp
        SMB2 smb2
        SMB2CreateResp cresp
        SMB2CreateReq creq
        SMB2ReadReq rreq
        list raw_pkt_data
        dict name_map

    f = open(pcap_file, 'rb')
    rdr = Reader(f)
    raw_pkt_data = list()
    # first go over the raw packet data and ret info for each packet
    # we care about.
    for ts, pkt in rdr:
        pk = Ethernet(pkt)
        if pk.type == 0x0800:
            ip = pk.payload
            if ip.proto == 6:
                tcp = ip.payload
                if tcp.dport == 445 or tcp.sport == 445:
                    smb2 = tcp.get_layer(b'SMB2')
                    if smb2:
                        if smb2.response and smb2.command == 5:
                            cresp = smb2.get_layer(b'SMB2CreateResp')
                            if cresp:
                                raw_pkt_data.append((ts, ip.src, tcp.sport,
                                                     ip.dst, tcp.dport,
                                                     smb2.message_id,
                                                     cresp.fid,
                                                     None, smb2.status,
                                                     smb2.command, None, None,
                                                     ip.total_len, ip.iphl,
                                                     tcp.sequence,
                                                     tcp.acknowledgment))
                        elif (not smb2.response) and smb2.command == 5:
                            creq = smb2.get_layer(b'SMB2CreateReq')
                            if creq:
                                raw_pkt_data.append((ts, ip.src, tcp.sport,
                                                     ip.dst, tcp.dport,
                                                     smb2.message_id, None,
                                                     creq.filename,
                                                     smb2.status,
                                                     smb2.command, None, None,
                                                     ip.total_len, ip.iphl,
                                                     tcp.sequence,
                                                     tcp.acknowledgment))
                        elif smb2.response and smb2.command == 8:
                            raw_pkt_data.append((ts, ip.src, tcp.sport,
                                                 ip.dst, tcp.dport,
                                                 smb2.message_id, None,
                                                 None, smb2.status,
                                                 smb2.command,
                                                 None, None, ip.total_len,
                                                 ip.iphl, tcp.sequence,
                                                 tcp.acknowledgment))
                        elif (not smb2.response) and smb2.command == 8:
                            rreq = smb2.get_layer(b'SMB2ReadReq')
                            if rreq:
                                raw_pkt_data.append((ts, ip.src, tcp.sport,
                                                     ip.dst, tcp.dport,
                                                     smb2.message_id, rreq.fid,
                                                     None, smb2.status,
                                                     smb2.command, rreq.offset,
                                                     rreq.length,
                                                     ip.total_len,
                                                     ip.iphl, tcp.sequence,
                                                     tcp.acknowledgment))

    # Get a list of fid to name for each session observed
    name_map = smb_analysis_get_file_map(raw_pkt_data)
    return smb_analysis_normalize_to_shark(raw_pkt_data, name_map)

