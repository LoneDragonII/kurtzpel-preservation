# SPDX-License-Identifier: AGPL-3.0-or-later
"""The "app info" bootstrap service (appinfo.playkog.com on the official servers).

The client asks it for the game-server address (GetOption) and for a login token (Login, keyed only by SteamID64).
Plain HTTP is fine: the 2019 client accepts -GetOptionURL= and -LoginURL= on its command line.
"""
import json, logging, secrets, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

log = logging.getLogger('appinfo')


def make_handler(gs_host: str, gs_port: int):
    class H(BaseHTTPRequestHandler):
        server_version = 'kzemu'

        def do_GET(self):
            u = urlsplit(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            path = u.path.rstrip('/').lower()
            if path.endswith('/service/getoption'):
                addr = json.dumps({'Domain': gs_host, 'Port': gs_port}, separators=(',', ':'))
                body = [{'Option': 'Address', 'Value': addr}]
            elif path.endswith('/service/login'):
                body = {'ZoneCode': q.get('ZoneCode') or 'live', 'State': 'OK', 'MarketLink': None, 'DelayTime': 0,
                        'MsgReserve': None, 'MsgReserveLocal': None, 'MsgOngoing': None, 'MsgOngoingLocal': None,
                        'MaStartTimeUTC': None, 'MaEndTimeUTC': None,
                        'Token': 'kz|' + secrets.token_hex(24), 'ClientCountryCode': 'US',
                        'ClientIP': self.client_address[0], 'BlockReason': None}
            else:
                log.warning('unknown path %s', self.path)
                self.send_error(404); return
            data = json.dumps(body, separators=(',', ':')).encode()
            log.info('GET %s -> %d bytes', u.path, len(data))
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_POST = do_GET

        def log_message(self, fmt, *args):
            log.debug(fmt, *args)

    return H


def start(bind: str, port: int, gs_host: str, gs_port: int):
    srv = ThreadingHTTPServer((bind, port), make_handler(gs_host, gs_port))
    threading.Thread(target=srv.serve_forever, daemon=True, name='appinfo').start()
    log.info('app info on http://%s:%d/Service/{GetOption,Login}', bind, port)
    return srv
