# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from libc.stdint cimport int32_t, uint32_t, uint16_t


cdef class PcapHeader:
    cdef:
        bytes _buffer, _order
        int32_t _tz_offset
        uint16_t use_buffer
        public uint32_t magic, ts_accuracy, snap_len, net_layer
        public uint32_t PCAP_MAGIC_IDENT, PCAP_MAGIC_IDENT_NANO
        public uint32_t PCAP_MAGIC_SWAPPED_NANO, PCAP_MAGIC_SWAPPED
        public uint16_t nano, major_version, minor_version


cdef class PktHeader:
    cdef:
        bytes _buffer, _order
        uint16_t use_buffer
        public uint32_t ts_sec, ts_usec, incl_len, orig_len

    cpdef double get_timestamp(self, uint16_t file_header_nano)


cdef class Reader:
    cdef:
        object _f
        PcapHeader header
        object _iter
        uint16_t PCAP_HDR_LEN, PKT_HDR_LEN

    cpdef int tz_offset(self)

    cpdef list readpkts(self)

    cpdef next(self)


cdef class Writer:
    cdef:
        object _f
        PcapHeader _header
        PktHeader _p_header_c
        uint16_t EN10MB
        uint32_t PCAP_MAGIC_IDENT, PCAP_MAGIC_SWAPPED, _magic, _n
        double _ts

    cpdef writepkt(self, bytes pkt, double ts)


cpdef list pcap_info(object f)
