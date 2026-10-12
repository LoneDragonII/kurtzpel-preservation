# SPDX-License-Identifier: AGPL-3.0-or-later
"""Game-server (TCP) framing of the Dec 2019 client.

    0x00 u32 total frame length (header + body)
    0x04 u32 sequence number, per direction, starting at 1
    0x08 46-byte packet header:
         +0x00 u16 opcode
         +0x1a u32 uncompressed payload size when the payload is zlib-compressed, else 0
         other bytes: client context, zero from the server
    0x36 body. When the session is encrypted: AES-256-ECB( u32 n | n payload bytes | random pad to 16 ).
         When not: the payload as is.

The live (2026) build uses a 62-byte header with two CRC32s instead; see notes/network.md.
The AES key is a constant in the player's own client exe. It is never shipped with this server: see keys.py.
"""
import os, struct, zlib
from Crypto.Cipher import AES

HDR = 0x36
OP_OFF = 0x08
UNCOMP_OFF = 0x08 + 0x1a


class Codec:
    def __init__(self, key: bytes | None):
        self.aes = AES.new(key, AES.MODE_ECB) if key else None
        self.encrypted = None  # decided from the first client frame with a body
        self.tx_seq = 0

    # ---- decode client frames ----
    def split(self, buf: bytearray):
        """Yield complete raw frames from buf (consumed in place)."""
        while len(buf) >= 4:
            n = struct.unpack_from('<I', buf, 0)[0]
            if n < HDR or n > 16 << 20:
                raise ValueError(f'bad frame length {n}')
            if len(buf) < n: return
            f = bytes(buf[:n]); del buf[:n]
            yield f

    def decode(self, f: bytes):
        """-> (seq, opcode, payload bytes, header bytes)."""
        seq = struct.unpack_from('<I', f, 4)[0]
        op = struct.unpack_from('<H', f, OP_OFF)[0]
        uncomp = struct.unpack_from('<I', f, UNCOMP_OFF)[0]
        body = f[HDR:]
        payload = body
        if body:
            if self.encrypted is None:
                self.encrypted = self._looks_encrypted(body)
            if self.encrypted:
                pt = self.aes.decrypt(body[:len(body) // 16 * 16])
                n = struct.unpack_from('<I', pt, 0)[0]
                payload = pt[4:4 + n]
        if uncomp and payload[:1] == b'\x78':
            payload = zlib.decompress(payload)
        return seq, op, payload, f[8:HDR]

    def _looks_encrypted(self, body):
        if not self.aes or len(body) % 16: return False
        pt = self.aes.decrypt(body)
        n = struct.unpack_from('<I', pt, 0)[0]
        return n <= len(pt) - 4 and len(pt) - 4 - n < 16

    # ---- encode server frames ----
    def encode(self, op: int, payload: bytes) -> bytes:
        if self.encrypted and payload is not None:
            inner = struct.pack('<I', len(payload)) + payload
            inner += os.urandom(-len(inner) % 16)
            body = self.aes.encrypt(inner)
        else:
            body = payload
        self.tx_seq += 1
        hdr = bytearray(HDR)
        struct.pack_into('<IIH', hdr, 0, HDR + len(body), self.tx_seq, op)
        return bytes(hdr) + body
