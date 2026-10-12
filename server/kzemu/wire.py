# SPDX-License-Identifier: AGPL-3.0-or-later
"""Payload encoding of the Dec 2019 client (build 2019-12-27, UE 4.19.1).

Fields are written back to back with no tags (the later live build added a 0x01 byte before every field):
    integers   little-endian, fixed width
    FString    u32 byte_length + UTF-16LE, no terminator (byte_length must be even)
    TArray/TMap/TSet   u32 count + elements
    optional   u8 (1 = present) + struct
"""
import struct


class Writer:
    def __init__(self):
        self.b = bytearray()

    def raw(self, data: bytes):
        self.b += data; return self

    def u8(self, v): self.b += struct.pack('<B', v & 0xff); return self
    def u16(self, v): self.b += struct.pack('<H', v & 0xffff); return self
    def i32(self, v): self.b += struct.pack('<i', v); return self
    def u32(self, v): self.b += struct.pack('<I', v & 0xffffffff); return self
    def u64(self, v): self.b += struct.pack('<Q', v & 0xffffffffffffffff); return self
    def i64(self, v): self.b += struct.pack('<q', v); return self

    def fstr(self, s: str):
        e = s.encode('utf-16-le')
        self.u32(len(e)); self.b += e; return self

    def empty(self, n=1):
        """n empty containers (u32 count 0 each)."""
        for _ in range(n): self.u32(0)
        return self

    def none(self, n=1):
        """n absent optionals (u8 0 each)."""
        for _ in range(n): self.u8(0)
        return self

    def bytes(self) -> bytes:
        return bytes(self.b)


class Reader:
    def __init__(self, data: bytes):
        self.d, self.o = data, 0

    def _take(self, n):
        if self.o + n > len(self.d):
            raise ValueError(f'read past end ({self.o}+{n} > {len(self.d)})')
        v = self.d[self.o:self.o + n]; self.o += n; return v

    def u8(self): return self._take(1)[0]
    def u16(self): return struct.unpack('<H', self._take(2))[0]
    def i32(self): return struct.unpack('<i', self._take(4))[0]
    def u32(self): return struct.unpack('<I', self._take(4))[0]
    def u64(self): return struct.unpack('<Q', self._take(8))[0]

    def fstr(self):
        n = self.u32()
        if n & 1 or n > 0x10000: raise ValueError(f'bad FString length {n}')
        return self._take(n).decode('utf-16-le', 'replace')

    def rest(self): return self.d[self.o:]
    def left(self): return len(self.d) - self.o
