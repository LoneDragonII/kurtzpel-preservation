# SPDX-License-Identifier: AGPL-3.0-or-later
"""Loopback test: a fake 2019 client walks app-info -> verify -> create -> list -> use -> square.
Uses a random key, so no game files are needed:  python -m pytest tests  (or python tests/test_loopback.py)"""
import asyncio, json, os, struct, sys, tempfile, urllib.request, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from kzemu import appinfo, packets2019 as P
from kzemu.db import DB
from kzemu.framing import Codec, HDR
from kzemu.gameserver import GameServer
from kzemu.wire import Writer, Reader


async def flow(port, key):
    r, w = await asyncio.open_connection('127.0.0.1', port)
    cli = Codec(key); cli.encrypted = True
    srv_side = Codec(key); srv_side.encrypted = True
    buf = bytearray()

    async def call(op, payload, expect):
        w.write(cli.encode(op, payload)); await w.drain()
        got = []
        while len(got) < expect:
            buf.extend(await r.read(65536))
            for f in srv_side.split(buf):
                _, o, p, _ = srv_side.decode(f)
                if o != P.HEART_BEAT: got.append((o, p))
        return got

    v = await call(P.CL_GS_VERIFY_ACCOUNT_REQ, Writer().fstr('tok').fstr('76561190000000001').u32(1).bytes(), 1)
    assert v[0][0] == P.GS_CL_VERIFY_ACCOUNT_ACK and Reader(v[0][1]).i32() == 0
    lst = await call(P.CL_GS_CHARACTER_LIST_REQ, b'', 1)
    rd = Reader(lst[0][1]); assert rd.i32() == 0 and rd.u32() == 0
    c = await call(P.CL_GS_CREATE_CHARACTER_REQ, Writer().fstr('Tester').u8(1).raw(bytes(20)).u32(5).bytes(), 1)
    rd = Reader(c[0][1]); assert rd.i32() == 0; uid = rd.u64(); assert rd.fstr() == 'Tester'
    lst = await call(P.CL_GS_CHARACTER_LIST_REQ, b'', 1)
    rd = Reader(lst[0][1]); assert rd.i32() == 0 and rd.u32() == 1 and rd.u64() == uid
    u = await call(P.CL_GS_USE_CHARACTER_REQ, Writer().u64(uid).bytes(), 1)
    assert u[0][0] == P.GS_CL_USE_CHARACTER_ACK and Reader(u[0][1]).i32() == 0
    sq = await call(P.CL_GS_ENTER_SQUARE_REQ, b'', 2)
    assert [o for o, _ in sq] == [P.GS_CL_ENTER_SQUARE_ACK, P.GS_CL_JOINABLE_SQUARE_NOT]
    rd = Reader(sq[1][1]); rd.u64(); rd.u64(); assert rd.fstr() == '127.0.0.1'; rd.fstr(); assert rd.u16() == 7777
    w.close()


def test_loopback():
    key = os.urandom(32)
    if True:
        http = appinfo.start('127.0.0.1', 0, '127.0.0.1', 0)
        hp = http.server_address[1]
        opt = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{hp}/Service/GetOption?AppCode=kz&PublishCode=na&ZoneCode=live').read())
        assert opt[0]['Option'] == 'Address' and json.loads(opt[0]['Value'])['Domain'] == '127.0.0.1'
        login = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{hp}/Service/Login?AppCode=kz&DeviceID=1').read())
        assert login['State'] == 'OK' and login['ZoneCode']
        http.shutdown()
        gs = GameServer(DB(':memory:'), key, {'id': 1, 'host': '127.0.0.1', 'port': 7777})

        async def main():
            srv = await asyncio.start_server(lambda r, w: __import__('kzemu.gameserver', fromlist=['Session']).Session(gs, r, w).run(), '127.0.0.1', 0)
            port = srv.sockets[0].getsockname()[1]
            async with srv:
                await asyncio.wait_for(flow(port, key), 10)
        asyncio.run(main())


if __name__ == '__main__':
    test_loopback(); print('ok')
