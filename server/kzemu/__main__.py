# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run the emulator:  python -m kzemu --client-exe "<KurtzPel>/TheChase/Binaries/Win64/TheChase-Win64-Shipping.exe"

Then start the game with
    TheChase.exe -GetOptionURL=http://127.0.0.1:18080/Service/GetOption -LoginURL=http://127.0.0.1:18080/Service/Login
"""
import argparse, asyncio, json, logging, pathlib
from . import appinfo, keys
from .db import DB
from .gameserver import GameServer


def main():
    ap = argparse.ArgumentParser(prog='kzemu', description='KurtzPel private server (Dec 2019 story client)')
    k = ap.add_mutually_exclusive_group(required=True)
    k.add_argument('--client-exe', help="your own client's TheChase-Win64-Shipping.exe (the packet key is read from it)")
    k.add_argument('--key-file', help='32-byte packet key file you extracted yourself')
    ap.add_argument('--bind', default='127.0.0.1')
    ap.add_argument('--public-host', default='127.0.0.1', help='address the client is told to connect to')
    ap.add_argument('--http-port', type=int, default=18080)
    ap.add_argument('--gs-port', type=int, default=11001)
    ap.add_argument('--square', default='127.0.0.1:7777', help='host:port of the UE server hosting the square (lobby)')
    ap.add_argument('--db', default='kzemu.sqlite')
    ap.add_argument('--names', help='optional opcode-name table (JSON {"0x0001": "CL_GS_..."}) for nicer logs')
    ap.add_argument('--trace', default='logs/trace.jsonl', help='JSONL log of every decoded packet ("" to disable)')
    ap.add_argument('--travel-file', help='file read by tools/frida/local_travel.js: the map to open locally instead of '
                    'connecting to a match server (missions are then played single-player)')
    ap.add_argument('--start-mission', type=int, help='with --travel-file: entering the square opens this story mission '
                    'locally instead (e.g. 1000 = Abandoned Ruins Epic 1000)')
    ap.add_argument('-v', '--verbose', action='store_true')
    a = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format='%(asctime)s %(name)-7s %(message)s', datefmt='%H:%M:%S')
    key = keys.key_from_exe(a.client_exe) if a.client_exe else keys.key_from_file(a.key_file)
    if a.trace:
        pathlib.Path(a.trace).parent.mkdir(parents=True, exist_ok=True)
    sq_host, sq_port = a.square.rsplit(':', 1)
    names = json.loads(pathlib.Path(a.names).read_text(encoding='utf-8')) if a.names else None

    appinfo.start(a.bind, a.http_port, a.public_host, a.gs_port)
    gs = GameServer(DB(a.db), key, {'id': 1, 'host': sq_host, 'port': int(sq_port)}, names, a.trace or None, a.travel_file)
    gs.start_mission = a.start_mission
    try:
        asyncio.run(gs.serve(a.bind, a.gs_port))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
