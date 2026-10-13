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
        self.send(P.GS_CL_PING_TEST_ADDRESS_LIST_NOT,
                  P.ping_test_address_list_not({'local': [self.srv.square['host']]}))
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
        # after the ACK: before it the client has no current character ("SetUnitChaserRankInfo CharacterUID : 0")
        self.send(P.GS_CL_UPDATE_CHASER_RANK_INFO_NOT, P.chaser_rank_info_not(self.char['name']))

    def on_disuse_character(self, p):
        self.char = None
        self.send(P.GS_CL_DISUSE_CHARACTER_ACK, P.result_only())

    def on_enter_square(self, p):
        # back to the square, unless --start-mission asked to go straight into a story mission
        mid, self.srv.start_mission = self.srv.start_mission, None  # only once
        self.srv.current_mission = mid
        self.srv.set_travel(P.mission_map(mid) if mid else '')
        sq = self.srv.square
        self.send(P.GS_CL_ENTER_SQUARE_ACK, P.enter_square_ack(sq['id']))
        self.send(P.GS_CL_DISPLAY_MISSION_LIST_NOT, P.display_mission_list_not(sorted(P.EPIC_MISSIONS)))
        self.send(P.GS_CL_JOINABLE_SQUARE_NOT,
                  P.joinable_square_not(sq['id'], secrets.randbits(63), sq['host'], sq['port']))

    def on_training_room(self, p):
        self.send(P.GS_CL_ENTER_TRAINING_ROOM_ACK, P.result_only())

    def on_exit_room(self, p):
        self.send(P.GS_CL_EXIT_ROOM_ACK, P.result_only())

    def on_custom_mission_list(self, p):
        self.send(P.GS_CL_GET_CUSTOM_MISSION_LIST_ACK, P.custom_mission_list_ack())

    def on_complete_guide(self, p):
        self.guides = getattr(self, 'guides', set()) | {p[0]} if p else getattr(self, 'guides', set())
        self.send(P.GS_CL_COMPLETE_GUIDE_ACK, P.complete_guide_ack(sorted(self.guides)))

    def on_request_match(self, p):
        # CL_GS_REQUEST_MATCH_REQ (sender 0x312280, one per selected mission): u32 mission id?, FString.
        rd = Reader(p)
        mid = rd.u32() if rd.left() >= 4 else 0
        log.info('%s  mission request %s: payload %s', self.peer, mid, p.hex())
        self.srv.current_mission = mid if P.mission_map(mid) else 1000
        self.send(P.GS_CL_REQUEST_MATCH_ACK, P.request_match_ack(value=mid))
        self.send(P.GS_CL_UPDATE_REQUESTED_MATCH_NOT, P.update_requested_match_not(mid))
        # solo: the match is "found" at once; the client answers with ANSWER_TO_COMPLETED_MATCH_NOT
        region = rd.fstr() if rd.left() >= 4 else 'local'
        self.send(P.GS_CL_COMPLETED_MATCH_NOT, P.completed_match_not(mid, region))

    def on_answer_completed_match(self, p):
        log.info('%s  answer to completed match: %s', self.peer, p.hex())
        self.srv.set_travel(P.mission_map(self.srv.current_mission or 1000))
        ch = self.char or {'uid': 0}
        self.send(P.GS_CL_PROGRESS_INFO_OF_COMPLETED_MATCH_NOT,
                  P.progress_info_of_completed_match_not(self.srv.current_mission or 0, ch['uid']))
        sq = self.srv.square
        self.send(P.GS_CL_JOINABLE_ROOM_NOT, P.joinable_room_not(1, secrets.randbits(63), sq['host'], sq['port']))

    def on_cancel_match(self, p):
        self.send(P.GS_CL_CANCEL_MATCH_ACK, P.result_only())

    def on_ds_end_game(self, p):
        # The client is its own mission host and reports the end like a DS would (u8 first: 1 = cleared?).
        won = bool(p and p[0] == 1)
        log.info('%s  mission ended (won=%s): %s', self.peer, won, p[:32].hex())
        ch = self.char or {'uid': 0, 'name': ''}
        self.send(P.GS_CL_END_GAME_NOT, P.end_game_not(self.srv.current_mission or 0, won, ch['uid'], ch['name'], self.account_uid or 0))
        self.send(P.GS_CL_GAME_REWARD_NOT, P.game_reward_not())

    def on_equip_item(self, p):
        # CL_GS_EQUIP_ITEM_REQ (template 0x2ed8e0): u32 weapon-set index, u64 item uid, u8, u8 slot (0 = unequip)
        rd = Reader(p)
        idx, uid, flag, slot = rd.u32(), rd.u64(), rd.u8(), rd.u8()
        items = self.char['items'] if self.char else []
        target = next((it for it in items if it['uid'] == uid), None)
        log.info('%s  equip uid=%d slot=%d flag=%d (%s)', self.peer, uid, slot, flag, target and target['id'])
        if not target:
            self.send(P.GS_CL_EQUIP_ITEM_ACK, P.equip_item_ack(idx, [], result=1)); return
        changed = []
        # the client sends the same request for "equip" and "Unequip" (flag 0 both times): toggle
        if target.get('slot') == slot:
            slot = P.SLOT_NONE
        if slot:
            for it in items:  # whatever was in that slot comes off
                if it is not target and it.get('slot') == slot and it.get('set') == target.get('set'):
                    it['slot'] = P.SLOT_NONE; changed.append(it)
        target['slot'] = slot
        changed.append(target)
        self.send(P.GS_CL_EQUIP_ITEM_ACK, P.equip_item_ack(idx, changed))
        self.srv.db.save_slots(self.char['uid'], {it['uid']: it.get('slot', 0) for it in items})
        # (UPDATE_CHARACTER_INFO_IN_GAME_ONLY_NOT here froze movement in the square: not sent)

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
    P.CL_GS_EQUIP_ITEM_REQ: Session.on_equip_item,
    P.DS_RS_END_GAME_NOT: Session.on_ds_end_game,
    P.DS_RS_UPDATE_GAME_PLAY_LOG_NOT: Session.ignore,
    P.GAME_MODE_USER_JOIN_PROGRESS_INFO_NOT: Session.ignore,
    P.JOINED_GAME_MODE_USER_NOT: Session.ignore,
    P.CL_GS_REQUEST_MATCH_REQ: Session.on_request_match,
    P.CL_GS_ANSWER_TO_COMPLETED_MATCH_NOT: Session.on_answer_completed_match,
    P.CL_GS_CANCEL_MATCH_REQ: Session.on_cancel_match,
    P.CL_GS_SQUARE_FPS_LOG_NOT: Session.ignore,
    P.CL_GS_GET_CUSTOM_MISSION_LIST_REQ: Session.on_custom_mission_list,
    P.CL_GS_COMPLETE_GUIDE_REQ: Session.on_complete_guide,
}


class GameServer:
    def __init__(self, db, key, square, names=None, trace_path=None, travel_file=None):
        self.db, self.key, self.square = db, key, square
        self.travel_file = travel_file
        self.start_mission = None
        self.current_mission = None
        self.names = {int(k, 16): v for k, v in (names or {}).items()}
        self.trace_f = open(trace_path, 'a', encoding='utf-8') if trace_path else None

    def set_travel(self, path):
        """Tell tools/frida/local_travel.js which map to open locally on the next server travel."""
        if self.travel_file:
            with open(self.travel_file, 'w', encoding='utf-8') as f:
                f.write(path or '')
            log.info('local travel -> %s', path)

    @staticmethod
    def db_char(row):
        items = P.default_items(row['uid'])
        if row.get('slots'):
            over = {int(k): v for k, v in json.loads(row['slots']).items()}
            for it in items:
                if it['uid'] in over: it['slot'] = over[it['uid']]
        return {'uid': row['uid'], 'name': row['name'], 'look': row.get('look'), 'created': row.get('created', 0),
                'items': items}

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
