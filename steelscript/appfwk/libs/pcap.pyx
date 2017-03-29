# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from struct import pack
import struct
from libc.stdint cimport uint32_t, uint16_t
import time
import sys


cdef class PcapHeader:

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

    cpdef double get_timestamp(self, uint16_t file_header_nano):
        cdef double rval
        if file_header_nano:
            rval = self.ts_sec + (self.ts_usec / 1000000000.0)
        else:
            rval = self.ts_sec + (self.ts_usec / 1000000.0)
        return rval


cdef class Reader:

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


