# SPDX-License-Identifier: AGPL-3.0-or-later
"""Loading the game-server AES key from the player's own client.

The key is a string constant inside TheChase-Win64-Shipping.exe. We don't distribute it; the server reads it from
the exe the player already has (or from a key file they extracted themselves).
"""
import pathlib, pefile

# build -> RVA of the key string (first 32 bytes are the AES-256 key). Found via the encrypt call in the packet
# send path (see notes/network.md).
KEY_RVA = {
    '2019-12-27': 0x2ab02c0,  # manifest 8731260772729569992, PE timestamp 2019-12-27 07:40:39 UTC
}
PE_TIMESTAMPS = {0x5E05B577: '2019-12-27'}


def key_from_exe(exe: str, build: str | None = None) -> bytes:
    pe = pefile.PE(exe, fast_load=True)
    if build is None:
        build = PE_TIMESTAMPS.get(pe.FILE_HEADER.TimeDateStamp)
        if build is None:
            raise SystemExit(f'unknown client build (PE timestamp {pe.FILE_HEADER.TimeDateStamp:#x}); pass --key-file')
    key = pe.get_data(KEY_RVA[build], 32)
    if not all(0x20 < c < 0x7f for c in key):
        raise SystemExit('key string not found at the expected place; is this the right exe?')
    return key


def key_from_file(path: str) -> bytes:
    k = pathlib.Path(path).read_bytes()[:32]
    if len(k) != 32: raise SystemExit('key file must hold 32 bytes')
    return k
