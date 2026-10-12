# SPDX-License-Identifier: AGPL-3.0-or-later
"""Game server (the KOG "GS", TCP) for the Dec 2019 client: login -> character select -> square."""
import asyncio, json, logging, re, secrets, time
from . import packets2019 as P
from .framing import Codec
from .wire import Reader

log = logging.getLogger('gs')
NAMES = {v: k for k, v in vars(P).items() if k.isupper() and isinstance(v, int) and k != 'OK'}


class Session:
    def __init__(self, server, reader, writer):
        self.srv, self.r, self.w = server, reader, writer
        self.codec = Codec(server.key)
        self.peer = '%s:%d' % writer.get_extra_info('peername')[:2]
        self.account_uid = None
        self.steam_id = None
        self.char = None

    def name(self, op):
        return self.srv.names.get(op) or NAMES.get(op) or f'0x{op:04x}'

    def send(self, op, payload: bytes):
        self.w.write(self.codec.encode(op, payload))
        self.srv.trace(self, 's2c', op, payload)
        log.info('%s  s2c %-34s %d B', self.peer, self.name(op), len(payload))

    async def run(self):
        log.info('%s connected', self.peer)
        hb = asyncio.create_task(self.heartbeat())
        buf = bytearray()
        try:
            while data := await self.r.read(65536):
                buf += data
                for f in self.codec.split(buf):
                    seq, op, payload, hdr = self.codec.decode(f)
                    self.srv.trace(self, 'c2s', op, payload, seq=seq, hdr=hdr)
                    if op != P.HEART_BEAT:
                        log.info('%s  c2s %-34s %d B%s', self.peer, self.name(op), len(payload),
                                 '' if self.codec.encrypted else ' (plain)')
                    try:
                        self.dispatch(op, payload)
                    except Exception:
                        log.exception('%s handler for %s failed; payload %s', self.peer, self.name(op), payload.hex())
                await self.w.drain()
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        except Exception:
            log.exception('%s session error', self.peer)
        finally:
            hb.cancel()
            log.info('%s disconnected', self.peer)
            self.w.close()

    async def heartbeat(self):
        # the client drops the connection ("zombie!!") if it hears nothing for a while
        while True:
            await asyncio.sleep(10)
            if self.codec.encrypted is not None:
                self.w.write(self.codec.encode(P.HEART_BEAT, b''))

    # ---- handlers ----
    def dispatch(self, op, p):
        h = HANDLERS.get(op)
        if h:
            h(self, p)
        elif op != P.HEART_BEAT:
            log.warning('%s  unhandled %s: %s', self.peer, self.name(op), p[:64].hex())

    def on_verify_account(self, p):
        # payload: FString x2, u32, FString x6+ (serializer 0x3a80b0); one of the strings is the SteamID64
        strings, rd = [], Reader(p)
        while rd.left() >= 4:
            pos = rd.o
            try:
                strings.append(rd.fstr())
            except ValueError:
                rd.o = pos + 4
        sid = next((s for s in strings if re.fullmatch(r'7656\d{13}', s)), None) or 'local'
        self.steam_id = sid
        self.account_uid = self.srv.db.account(sid)
        log.info('%s  account %d', self.peer, self.account_uid)
        self.send(P.GS_CL_VERIFY_ACCOUNT_ACK, P.verify_account_ack(self.account_uid, sid))

    def chars(self):
        return [self.srv.db_char(c) for c in self.srv.db.characters(self.account_uid)]

    def on_character_list(self, p):
        self.send(P.GS_CL_CHARACTER_LIST_ACK, P.character_list_ack(self.chars()))

    def on_create_character(self, p):
        # Serializer (inline in send template 0x358650): FString name, u8, look struct (serializer 0x3a81b0, read back
        # by 0x349a00 inside FCharacterInfo), u32. The look bytes are stored as-is and echoed in FCharacterInfo.
        rd = Reader(p)
        name, kind = rd.fstr() or 'Chaser', rd.u8()
        look = p[rd.o:len(p) - 4]
        log.info('%s  CREATE_CHARACTER_REQ name=%r u8=%d look=%d B tail=%s', self.peer, name, kind, len(look), p[-4:].hex())
        ch = self.srv.db.create_character(self.account_uid, name[:24], look=look or None, create_req=p)
        self.send(P.GS_CL_CREATE_CHARACTER_ACK, P.create_character_ack(self.srv.db_char(ch)))

    def on_delete_character(self, p):
        uid = Reader(p).u64() if len(p) >= 8 else 0
        self.srv.db.delete_character(self.account_uid, uid)
        self.send(P.GS_CL_DELETE_CHARACTER_ACK, P.result_only() + p[:8])

    def on_use_character(self, p):
        uid = Reader(p).u64()
        ch = self.srv.db.character(self.account_uid, uid)
        if not ch:
            log.warning('%s  USE_CHARACTER for unknown uid %d', self.peer, uid)
            self.send(P.GS_CL_USE_CHARACTER_ACK, P.result_only(1))
            return
        self.char = self.srv.db_char(ch)
        self.send(P.GS_CL_USE_CHARACTER_ACK, P.use_character_ack(self.account_uid, self.char))

    def on_disuse_character(self, p):
        self.char = None
        self.send(P.GS_CL_DISUSE_CHARACTER_ACK, P.result_only())

    def on_enter_square(self, p):
        sq = self.srv.square
        self.send(P.GS_CL_ENTER_SQUARE_ACK, P.enter_square_ack(sq['id']))
        self.send(P.GS_CL_JOINABLE_SQUARE_NOT,
                  P.joinable_square_not(sq['id'], secrets.randbits(63), sq['host'], sq['port']))

    def on_training_room(self, p):
        self.send(P.GS_CL_ENTER_TRAINING_ROOM_ACK, P.result_only())

    def on_exit_room(self, p):
        self.send(P.GS_CL_EXIT_ROOM_ACK, P.result_only())

    def ignore(self, p):
        pass


HANDLERS = {
    P.CL_GS_VERIFY_ACCOUNT_REQ: Session.on_verify_account,
    P.CL_GS_CHARACTER_LIST_REQ: Session.on_character_list,
    P.CL_GS_CREATE_CHARACTER_REQ: Session.on_create_character,
    P.CL_GS_DELETE_CHARACTER_REQ: Session.on_delete_character,
    P.CL_GS_USE_CHARACTER_REQ: Session.on_use_character,
    P.CL_GS_DISUSE_CHARACTER_REQ: Session.on_disuse_character,
    P.CL_GS_ENTER_SQUARE_REQ: Session.on_enter_square,
    P.CL_GS_ENTER_TRAINING_ROOM_REQ: Session.on_training_room,
    P.CL_GS_EXIT_ROOM_REQ: Session.on_exit_room,
    P.CL_GS_INITIAL_FLOW_STEP_NOT: Session.ignore,
    P.CL_GS_CHANGE_GAME_STATE_NOT: Session.ignore,
    P.CL_GS_UPDATE_PING_BY_REGION_NOT: Session.ignore,
    P.CL_GS_QUIT_CLIENT_NOT: Session.ignore,
}


class GameServer:
    def __init__(self, db, key, square, names=None, trace_path=None):
        self.db, self.key, self.square = db, key, square
        self.names = {int(k, 16): v for k, v in (names or {}).items()}
        self.trace_f = open(trace_path, 'a', encoding='utf-8') if trace_path else None

    @staticmethod
    def db_char(row):
        return {'uid': row['uid'], 'name': row['name'], 'look': row.get('look'), 'created': row.get('created', 0),
                'items': P.default_items(row['uid'])}

    def trace(self, s, d, op, payload, **kw):
        if not self.trace_f:
            return
        rec = {'t': round(time.time(), 3), 'peer': s.peer, 'dir': d, 'opcode': f'0x{op:04x}', 'name': s.name(op),
               'len': len(payload), 'hex': payload.hex()}
        if 'hdr' in kw:
            rec['hdr'], rec['seq'] = kw['hdr'].hex(), kw['seq']
        self.trace_f.write(json.dumps(rec) + '\n')
        self.trace_f.flush()

    async def serve(self, bind, port):
        srv = await asyncio.start_server(lambda r, w: Session(self, r, w).run(), bind, port)
        log.info('game server on %s:%d (square -> %s:%d)', bind, port, self.square['host'], self.square['port'])
        async with srv:
            await srv.serve_forever()
