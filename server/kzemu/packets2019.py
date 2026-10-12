# SPDX-License-Identifier: AGPL-3.0-or-later
"""Opcodes and packet builders for the Dec 2019 story client (2019-12-27).

Opcode = index in the client's packet-name table (HEART_BEAT = 0). Struct layouts come from the client's
Deserialize functions; the RVA of each is given so the layout can be re-checked with tools/re/schema2019.py.
Only what is needed to get from the login screen to the square (lobby) is filled in; every container is sent
empty and every optional absent unless noted.
"""
import time
from .wire import Writer

HEART_BEAT = 0x0000
CL_GS_VERIFY_ACCOUNT_REQ, GS_CL_VERIFY_ACCOUNT_ACK = 0x0001, 0x0002
CL_GS_CREATE_CHARACTER_REQ, GS_CL_CREATE_CHARACTER_ACK = 0x0003, 0x0004
CL_GS_DELETE_CHARACTER_REQ, GS_CL_DELETE_CHARACTER_ACK = 0x0009, 0x000a
CL_GS_CHARACTER_LIST_REQ, GS_CL_CHARACTER_LIST_ACK = 0x000b, 0x000c
CL_GS_USE_CHARACTER_REQ, GS_CL_USE_CHARACTER_ACK = 0x000d, 0x000e
CL_GS_ENTER_SQUARE_REQ, GS_CL_ENTER_SQUARE_ACK = 0x000f, 0x0010
GS_CL_JOINABLE_SQUARE_NOT = 0x0011
CL_GS_EXIT_ROOM_REQ, GS_CL_EXIT_ROOM_ACK = 0x0019, 0x001a
CL_GS_DISUSE_CHARACTER_REQ, GS_CL_DISUSE_CHARACTER_ACK = 0x0044, 0x0045
CL_GS_CHANGE_GAME_STATE_NOT = 0x0059
CL_GS_SAVE_OPTION_REQ, GS_CL_SAVE_OPTION_ACK = 0x005b, 0x005c
CL_GS_UPDATE_PING_BY_REGION_NOT = 0x0070
CL_GS_QUIT_CLIENT_NOT = 0x0080
CL_GS_INITIAL_FLOW_STEP_NOT = 0x0086
CL_GS_ENTER_TRAINING_ROOM_REQ, GS_CL_ENTER_TRAINING_ROOM_ACK = 0x0092, 0x0093

OK = 0


def now(): return int(time.time())


def verify_account_ack(account_uid: int, steam_id: str) -> bytes:
    """Deserializer 0x3a70a0."""
    w = Writer()
    w.i32(OK).u64(account_uid).fstr(steam_id)
    w.u64(now()).u64(now()).u64(0)  # times (live: two unix times, then a small counter)
    w.u32(0).u32(1)
    w.empty(3)          # TMap<u32,u32> 0x2e0b90, TMap 0x351810, TSet<u32> 0x2e2090
    w.u64(0)
    w.empty(2)          # TSet<u8> 0x2e4510, TSet<u32> 0x2e2090
    w.u32(0).u8(0).u32(0)
    w.empty(1)          # TMap 0x2e18e0
    w.u32(0)
    w.empty(1)          # TMap 0x3519e0
    return w.bytes()


# EEquipSlot (reflected enum order in the 2019 exe)
SLOT_NONE, SLOT_WEAPON, SLOT_WEAPON_SUB, SLOT_TOP, SLOT_PANTS, SLOT_INNER, SLOT_HEAD, SLOT_HAIR, SLOT_FOOT = range(9)

INV_NONE, INV_SKILL, INV_GENERAL = range(3)

# Placeholder stats until the 10 fields are identified (values seen on a live character).
DEFAULT_STATS = (2713, 2152, 6679, 600, 6118, 2100, 600, 2100, 600, 600)


def stats(w: Writer, values=DEFAULT_STATS) -> Writer:
    """Optional 0x34a200 ("StatInfo"): 10 x u32."""
    w.u8(1)
    for v in values: w.u32(v)
    return w


def item(w: Writer, it) -> Writer:
    """Item struct 0x34b510: u64 uid, u32 item id, u32, u32, u8, u8, u64, u64, 3 x u32, TSet<u32>.
    u8 +0x15 = EInventoryType (1 skill, 2 general; client logs "Fail FindItemInfo eInventoryType : 2"),
    u8 +0x16 = EEquipSlot the item is equipped in (0 = not equipped): with every equipped item at 1, the client took the
    last one (140070) as its weapon. The u32s are guessed as count and durability."""
    w.u64(it['uid']).u32(it['id']).u32(it.get('count', 1)).u32(it.get('durability', 100))
    w.u8(it.get('inv', INV_GENERAL)).u8(it.get('slot', SLOT_NONE))
    w.u64(0).u64(0).u32(0).u32(0).u32(0).empty()
    return w


def inventory(w: Writer, items) -> Writer:
    """Optional 0x30b600 ("ItemInfo"): TMap<u64 uid, optional item> (0x2e5620), TSet<{u8, u32, u32}> (0x2e4110)."""
    w.u8(1).u32(len(items))
    for it in items:
        w.u64(it['uid']).u8(1)
        item(w, it)
    # TSet<{u8, u32, u32}> (0x2e4110). Guess: equipped look per slot = (EEquipSlot, item id, dye/0). With the two
    # weapons only, the weapon showed but the body stayed a placeholder mesh in the world (fine in the inventory menu).
    worn = [it for it in items if it.get('slot')]
    w.u32(len(worn))
    for it in worn:
        w.u8(it['slot']).u32(it['id']).u32(0)
    return w


# Starting gear from the client's DefaultItemTable (same for HumanMan and HumanWoman): BasicItemList holds the outfit
# (30000 top, 40000 pants, 140070 foot; slots inferred from icon names) and 160000-160090 (skills, ids not in
# WeaponDetailTable); DefaultUnderwearList = 20000; the two weapons 210040 (WT_GreateSword) and 220040 (WT_Bow) are in
# WeaponDetailTable. Equipping the skills is left for later.
DEFAULT_GEAR = [(210040, SLOT_WEAPON), (220040, SLOT_WEAPON_SUB), (30000, SLOT_TOP), (40000, SLOT_PANTS),
                (20000, SLOT_INNER), (140070, SLOT_FOOT),
                (160000, SLOT_NONE), (160010, SLOT_NONE), (160020, SLOT_NONE), (160030, SLOT_NONE),
                (160040, SLOT_NONE), (160090, SLOT_NONE)]


def default_items(char_uid: int):
    return [{'uid': char_uid * 1000 + i + 1, 'id': iid, 'slot': slot} for i, (iid, slot) in enumerate(DEFAULT_GEAR)]


def unit_property(w: Writer, items) -> Writer:
    """Optional 0x30b690 ("UnitPropertyInfo"): two TMap<u8, u32> (0x2e4360). The first is read by the weapon getter
    0x46a9b0 (key = current weapon-set index, value = weapon item id); the host logs
    "InitializeWeaponSetTypeInfo GetUnitPropertyInfo Failed" without it. The second is probably passive skills."""
    weapons = [it['id'] for it in items if it.get('slot') in (SLOT_WEAPON, SLOT_WEAPON_SUB)]
    w.u8(1).u32(len(weapons))
    for i, iid in enumerate(weapons):
        w.u8(i).u32(iid)
    return w.empty()


def char_info(w: Writer, ch) -> Writer:
    """FCharacterInfo, deserializer 0x3a6900."""
    w.u64(ch['uid']).fstr(ch['name'])
    stats(w)                          # optional 0x34a200
    _opt(w, ch.get('look'))           # optional 0x349a00: customization from CREATE_CHARACTER_REQ
    inventory(w, ch.get('items', []))  # optional 0x30b600
    w.u64(ch.get('created', 0)).u8(0)
    return w


def _opt(w: Writer, blob: bytes | None):
    if blob:
        w.u8(1).raw(blob)
    else:
        w.u8(0)


def character_list_ack(chars) -> bytes:
    """i32 result + TMap<u64 uid, FCharacterInfo> (0x352270)."""
    w = Writer().i32(OK).u32(len(chars))
    for ch in chars:
        w.u64(ch['uid']); char_info(w, ch)
    return w.bytes()


def create_character_ack(ch, result=OK) -> bytes:
    """i32 result + FCharacterInfo (handler near 0x3898dc)."""
    w = Writer().i32(result)
    return char_info(w, ch).bytes() if ch else w.bytes()


def use_character_ack(account_uid: int, ch) -> bytes:
    """Deserializer 0x3a6f50: i32 result + FCharacterFullInfo (0x34a0a0) + inventory/progress containers."""
    w = Writer().i32(OK)
    # 0x34a0a0
    w.u64(account_uid).u64(ch['uid']).fstr(ch['name'])
    unit_property(w, ch.get('items', []))  # optional 0x30b690
    w.none()                          # optional 0x2e2970
    stats(w)                          # optional 0x34a200
    _opt(w, ch.get('look'))           # optional 0x349a00
    inventory(w, ch.get('items', []))  # optional 0x30b600
    # rest of 0x3a6f50
    w.empty(2)                        # TMap 0x2e10e0, TMap 0x2e0f20
    w.empty(3)                        # TSet<u32> 0x2e0a30 x3
    w.u8(0).u32(0)
    w.empty(3)                        # TMap 0x352130, TSet<u8> 0x2e4050, TMap 0x351b90
    w.empty(1)                        # TSet<u32> 0x2e0a30
    return w.bytes()


def enter_square_ack(square_id: int, channel: int = 1) -> bytes:
    """Deserializer 0x34af20: i32 result, i32, u64 square id, i32, i32."""
    return Writer().i32(OK).i32(0).u64(square_id).i32(channel).i32(0).bytes()


def joinable_square_not(square_id: int, auth_key: int, ip: str, port: int) -> bytes:
    """Deserializer 0x34b2f0: u64 square id, u64 auth key, FString public ip, FString private ip, u16 port,
    FString (unknown, empty), u32."""
    return Writer().u64(square_id).u64(auth_key).fstr(ip).fstr(ip).u16(port).fstr('').u32(0).bytes()


def result_only(result=OK) -> bytes:
    return Writer().i32(result).bytes()
