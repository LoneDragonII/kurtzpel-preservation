# SPDX-License-Identifier: AGPL-3.0-or-later
"""Opcodes and packet builders for the Dec 2019 story client (2019-12-27).

Opcode = index in the client's packet-name table (HEART_BEAT = 0). Struct layouts come from the client's
Deserialize functions; the RVA of each is given so the layout can be re-checked with tools/re/schema2019.py.
Only what is needed to get from the login screen to the square (lobby) is filled in; every container is sent
empty and every optional absent unless noted.
"""
import struct, time
from .wire import Writer

HEART_BEAT = 0x0000
CL_GS_VERIFY_ACCOUNT_REQ, GS_CL_VERIFY_ACCOUNT_ACK = 0x0001, 0x0002
CL_GS_CREATE_CHARACTER_REQ, GS_CL_CREATE_CHARACTER_ACK = 0x0003, 0x0004
CL_GS_DELETE_CHARACTER_REQ, GS_CL_DELETE_CHARACTER_ACK = 0x0009, 0x000a
CL_GS_CHARACTER_LIST_REQ, GS_CL_CHARACTER_LIST_ACK = 0x000b, 0x000c
CL_GS_USE_CHARACTER_REQ, GS_CL_USE_CHARACTER_ACK = 0x000d, 0x000e
CL_GS_ENTER_SQUARE_REQ, GS_CL_ENTER_SQUARE_ACK = 0x000f, 0x0010
GS_CL_JOINABLE_SQUARE_NOT = 0x0011
GS_CL_DISPLAY_MISSION_LIST_NOT = 0x0058
GS_CL_UPDATE_CHASER_RANK_INFO_NOT = 0x002b
GS_CL_PING_TEST_ADDRESS_LIST_NOT = 0x0050
GS_CL_END_GAME_NOT, GS_CL_GAME_REWARD_NOT = 0x001c, 0x001f
# The 2019 client hosting a mission locally still talks to its "relay" (RS) through the GS connection:
GAME_MODE_USER_JOIN_PROGRESS_INFO_NOT, JOINED_GAME_MODE_USER_NOT = 0x016c, 0x016d
DS_RS_END_GAME_NOT, DS_RS_UPDATE_GAME_PLAY_LOG_NOT = 0x00dc, 0x00de
UPDATE_CHARACTER_INFO_IN_GAME_ONLY_NOT = 0x016a
CL_GS_REQUEST_MATCH_REQ, GS_CL_REQUEST_MATCH_ACK = 0x0021, 0x0022
CL_GS_CREATE_ROOM_REQ, GS_CL_CREATE_ROOM_ACK = 0x0014, 0x0015
GS_CL_JOINABLE_ROOM_NOT = 0x0018
GS_CL_UPDATE_REQUESTED_MATCH_NOT, GS_CL_COMPLETED_MATCH_NOT = 0x0028, 0x0029
GS_CL_PROGRESS_INFO_OF_COMPLETED_MATCH_NOT = 0x002a
CL_GS_ANSWER_TO_COMPLETED_MATCH_NOT = 0x0049
CL_GS_CANCEL_MATCH_REQ, GS_CL_CANCEL_MATCH_ACK = 0x0023, 0x0024
CL_GS_EXIT_ROOM_REQ, GS_CL_EXIT_ROOM_ACK = 0x0019, 0x001a
CL_GS_DISUSE_CHARACTER_REQ, GS_CL_DISUSE_CHARACTER_ACK = 0x0044, 0x0045
CL_GS_CHANGE_GAME_STATE_NOT = 0x0059
CL_GS_SAVE_OPTION_REQ, GS_CL_SAVE_OPTION_ACK = 0x005b, 0x005c
CL_GS_UPDATE_PING_BY_REGION_NOT = 0x0070
CL_GS_QUIT_CLIENT_NOT = 0x0080
CL_GS_INITIAL_FLOW_STEP_NOT = 0x0086
CL_GS_ENTER_TRAINING_ROOM_REQ, GS_CL_ENTER_TRAINING_ROOM_ACK = 0x0092, 0x0093
CL_GS_GET_CUSTOM_MISSION_LIST_REQ, GS_CL_GET_CUSTOM_MISSION_LIST_ACK = 0x0068, 0x0069
CL_GS_SQUARE_FPS_LOG_NOT = 0x0085
CL_GS_COMPLETE_GUIDE_REQ, GS_CL_COMPLETE_GUIDE_ACK = 0x0089, 0x008a
CL_GS_EQUIP_ITEM_REQ, GS_CL_EQUIP_ITEM_ACK = 0x001d, 0x001e

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
    # Unknown counters. One of the account/character u32s is an inventory capacity: with all zero the client says
    # "you cannot accept new mission as your skill/equipment inventory is full". Trying 100 everywhere.
    w.u32(100).u8(1).u32(100)
    w.empty(1)          # TMap 0x2e18e0
    w.u32(100)
    w.empty(1)          # TMap 0x3519e0
    return w.bytes()


# EEquipSlot values (from the reflected enum table in the 2019 exe: FEnumeratorParam {name, int64 value}).
SLOT_NONE, SLOT_WEAPON, SLOT_WEAPON_SUB = 0, 1, 2
SLOT_TOP, SLOT_PANTS, SLOT_INNER, SLOT_HEAD, SLOT_HAIR = 10, 11, 12, 13, 14
SLOT_FOOT, SLOT_BACK, SLOT_WAIST, SLOT_HEADGEAR = 50, 51, 52, 53
SLOT_SKILL1, SLOT_SKILL2, SLOT_SKILL3, SLOT_RAGE = 101, 102, 103, 104

INV_NONE, INV_SKILL, INV_GENERAL = range(3)
INVENTORY_SLOTS = 100

# StatInfo = the client's UnitStatData row: UnitBaseStat {Strength, Agility, Inteligence, Spirit, Stamina}, Mass,
# GravityScale, MaxJumpHeight, MaxWalkSpeed, GroundFriction (field names and order from DataTable/CommonUnit/
# UnitStatTable; the last five match the unit constructor's defaults at 0x422ae0). Values = that table's row 0.
DEFAULT_STATS = (5.0, 5.0, 5.0, 5.0, 5.0, 100.0, 4.0, 300.0, 740.0, 0.02)


def stats(w: Writer, values=DEFAULT_STATS) -> Writer:
    """Optional 0x34a200 ("StatInfo"): 10 x **float32** (the setter at 0x485b2a loads them with movss and passes
    5 + 5 to 0x47fa40 / 0x43bfc0). Sent as ints they decode as ~0: no movement, empty stamina, one-shot deaths."""
    w.u8(1)
    for v in values: w.raw(struct.pack('<f', float(v)))
    return w


def item(w: Writer, it) -> Writer:
    """Item struct 0x34b510: u64 uid, u32 item id, u32, u32, u8, u8, u64, u64, 3 x u32, TSet<u32>.
    u8 +0x15 = EInventoryType (1 skill, 2 general; client logs "Fail FindItemInfo eInventoryType : 2"),
    u8 +0x16 = EEquipSlot the item is equipped in (0 = not equipped): with every equipped item at 1, the client took the
    last one (140070) as its weapon. The u32s are guessed as count and durability."""
    # second u32: durability? (100); for skill items guessed as the weapon-set (karma) index. With 1 on the bow item
    # the bow rendered pitch black, so weapons keep 100.
    b = it['set'] if ('set' in it and it.get('slot', 0) >= SLOT_SKILL1) else it.get('durability', 100)
    w.u64(it['uid']).u32(it['id']).u32(it.get('count', 1)).u32(b)
    w.u8(it.get('inv', INV_GENERAL)).u8(it.get('slot', SLOT_NONE))
    # u64 x2: live items carry an acquire time here (unix seconds); 0 may read as expired / not owned
    w.u64(it.get('acquired', now())).u64(0).u32(0).u32(0).u32(0)
    # trailing TSet<u32> (0x2e2090): guess = the skills socketed into a karma (weapon) item
    sk = it.get('skills', [])
    w.u32(len(sk))
    for x in sk: w.u32(x)
    return w


def inventory(w: Writer, items) -> Writer:
    """Optional 0x30b600 ("ItemInfo"): TMap<u64 uid, optional item> (0x2e5620), TSet<{u8, u32, u32}> (0x2e4110)."""
    w.u8(1).u32(len(items))
    for it in items:
        w.u64(it['uid']).u8(1)
        item(w, it)
    # TMap<u8 EInventoryType, {u32 used, u32 capacity}> (0x2e4110). Filled with (slot, item id, 0) the mission map
    # said "skill inventory is full (210,040 / 0)": entry 1 = skill inventory, 210040 used of 0.
    w.u32(2)
    for inv in (INV_SKILL, INV_GENERAL):
        w.u8(inv).u32(sum(1 for it in items if it.get('inv', INV_GENERAL) == inv)).u32(INVENTORY_SLOTS)
    return w


# Starting gear (client DefaultItemTable + ItemTable + SkillDataTable): outfit 30000/40000/20000 + boots 140070,
# emotes 160000-160090 (IT_Emotion -> slots 160-164), karmas 210040 (WT_GreateSword) / 220040 (WT_Bow) in the skill
# inventory, and the unsellable starter skills of those two karmas (SkillDataTable: 1100/1110/1120 normal + 1170 rage
# for the greatsword, 1220/1240/1250 + 1270 for the bow). (id, slot, inventory, weapon-set index)
SLOT_EMOTE = 160
DEFAULT_GEAR = [(210040, SLOT_WEAPON, INV_SKILL, 0), (220040, SLOT_WEAPON_SUB, INV_SKILL, 1),
                (30000, SLOT_TOP), (40000, SLOT_PANTS), (20000, SLOT_INNER), (140070, SLOT_FOOT),
                (160000, SLOT_EMOTE), (160010, SLOT_EMOTE + 1), (160020, SLOT_EMOTE + 2), (160030, SLOT_EMOTE + 3),
                (160040, SLOT_EMOTE + 4), (160090, SLOT_NONE),
                (1100, SLOT_SKILL1, INV_SKILL, 0), (1110, SLOT_SKILL2, INV_SKILL, 0), (1120, SLOT_SKILL3, INV_SKILL, 0),
                (1170, SLOT_RAGE, INV_SKILL, 0),
                (1220, SLOT_SKILL1, INV_SKILL, 1), (1240, SLOT_SKILL2, INV_SKILL, 1), (1250, SLOT_SKILL3, INV_SKILL, 1),
                (1270, SLOT_RAGE, INV_SKILL, 1)]


def default_items(char_uid: int):
    out = []
    karma_skills = {0: [1100, 1110, 1120, 1170], 1: [1220, 1240, 1250, 1270]}
    for i, g in enumerate(DEFAULT_GEAR):
        it = {'uid': char_uid * 1000 + i + 1, 'id': g[0], 'slot': g[1], 'inv': g[2] if len(g) > 2 else INV_GENERAL}
        if len(g) > 3: it['set'] = g[3]
        if g[1] in (SLOT_WEAPON, SLOT_WEAPON_SUB): it['skills'] = karma_skills[g[3]]
        out.append(it)
    return out


WT_GREATSWORD, WT_WAND, WT_BOW = 1, 2, 3   # EWeaponType
WEAPON_TYPE = {210040: WT_GREATSWORD, 220040: WT_BOW}


def unit_property(w: Writer, items) -> Writer:
    """Optional 0x30b690 ("UnitPropertyInfo"): two TMap<u8, u32> (0x2e4360). Map 1 is read as "WeaponSetTypeInfo"
    (host log: "InitializeWeaponSetTypeInfo GetUnitPropertyInfo Failed"): weapon-set index -> EWeaponType. Skills are
    tied to a weapon type (SkillDataTable WeaponSetType), so with item ids here the skills showed but never fired.
    Map 2 is probably passive skills ("InitializePassiveSkills")."""
    sets = sorted((it['set'], WEAPON_TYPE.get(it['id'], 0)) for it in items
                  if it.get('slot') in (SLOT_WEAPON, SLOT_WEAPON_SUB) and 'set' in it)
    w.u8(1).u32(len(sets))
    for idx, wt in sets:
        w.u8(idx).u32(wt)
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


def full_info(w: Writer, account_uid: int, ch) -> Writer:
    """FCharacterFullInfo, deserializer 0x34a0a0."""
    w.u64(account_uid).u64(ch['uid']).fstr(ch['name'])
    unit_property(w, ch.get('items', []))  # optional 0x30b690
    w.none()                          # optional 0x2e2970 (wraps another optional chaser-rank struct)
    stats(w)                          # optional 0x34a200
    _opt(w, ch.get('look'))           # optional 0x349a00
    inventory(w, ch.get('items', []))  # optional 0x30b600
    return w


def use_character_ack(account_uid: int, ch) -> bytes:
    """Deserializer 0x3a6f50: i32 result + FCharacterFullInfo (0x34a0a0) + inventory/progress containers."""
    w = Writer().i32(OK)
    full_info(w, account_uid, ch)
    # rest of 0x3a6f50
    w.empty(2)                        # TMap 0x2e10e0, TMap 0x2e0f20
    w.empty(3)                        # TSet<u32> 0x2e0a30 x3
    w.u8(1).u32(100)                  # unknown (capacity? see verify_account_ack)
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


def custom_mission_list_ack() -> bytes:
    """Handler 0x38ae05: i32 result, TArray<room 0x3a6ac0>, FString, i32, TMap<u8, u32>. Empty list."""
    return Writer().i32(OK).empty().fstr('').i32(0).empty().bytes()


def complete_guide_ack(guides) -> bytes:
    """Handler 0x32ade0: i32 result, TSet<u8> completed guides."""
    w = Writer().i32(OK).u32(len(guides))
    for g in guides: w.u8(g)
    return w.bytes()


# 2019 story ("Epic") missions: id -> map. Ids are the map-name suffixes (Abandoned_Ruins_Epic_1000 ...).
EPIC_MISSIONS = {
    1000: 'KillMonster/Abandoned_Ruins/Abandoned_Ruins_Epic_1000', 1010: 'KillMonster/Abandoned_Ruins/Abandoned_Ruins_Epic_1010',
    1020: 'KillMonster/Abandoned_Ruins/Abandoned_Ruins_Epic_1020', 1030: 'KillMonster/Abandoned_Ruins/Abandoned_Ruins_Epic_1030',
    2000: 'KillMonster/Delasa/Delasa_Epic_2000', 2010: 'KillMonster/Delasa/Delasa_Epic_2010',
    2020: 'KillMonster/Delasa/Delasa_Epic_2020', 2030: 'KillMonster/Delasa/Delasa_Epic_2030',
    3000: 'KillMonster/Caverns_of_Beast/Caverns_of_Beast_Epic_3000', 3010: 'KillMonster/Caverns_of_Beast/Caverns_of_Beast_Epic_3010',
    3020: 'KillMonster/Caverns_of_Beast/Caverns_of_Beast_Epic_3020', 3030: 'KillMonster/Caverns_of_Beast/Caverns_of_Beast_Epic_3030',
    4000: 'KillMonster/Secret_Gate/Twisted_Ruins_Epic_4000', 4010: 'KillMonster/Secret_Gate/Twisted_Ruins_Epic_4010',
    4020: 'KillMonster/Secret_Gate/Secret_Gate_Epic_4020', 4030: 'KillMonster/Secret_Gate/Secret_Gate_Epic_4030',
    5000: 'KillMonster/Regenier_Monastery/Regenier_Epic_5000', 5010: 'KillMonster/Regenier_Monastery/Regenier_Epic_5010',
    5020: 'KillMonster/Regenier_Monastery/Regenier_Epic_5020',
    6000: 'KillMonster/Karciel/Karciel_Epic_6000', 6010: 'KillMonster/Karciel/Karciel_Epic_6010',
    6020: 'KillMonster/Karciel/Karciel_Epic_6020',
}


def mission_map(mid: int) -> str | None:
    m = EPIC_MISSIONS.get(mid)
    return f'/Game/TheChase/Map/Room/{m}' if m else None


def display_mission_list_not(mission_ids) -> bytes:
    """0x2e0440: u32, TMap<u32 mission id, u32> (0x2e2300), TSet<u32> (0x2e0a30). Live sends value 0 for every id."""
    w = Writer().u32(0).u32(len(mission_ids))
    for m in mission_ids: w.u32(m).u32(0)
    return w.empty().bytes()


def request_match_ack(result=OK, value=0) -> bytes:
    """Handler window 0x3274ac: i32 result, u32, FString, u32."""
    return Writer().i32(result).u32(value).fstr('').u32(0).bytes()


def joinable_room_not(room_id: int, auth_key: int, ip: str, port: int) -> bytes:
    """0x34b1d0: u64 room id, FString public ip, FString private ip, u16 port, u8, u32 x4, u64 auth key?, FString."""
    return (Writer().u64(room_id).fstr(ip).fstr(ip).u16(port).u8(0)
            .u32(0).u32(0).u32(0).u32(0).u64(auth_key).fstr('').bytes())


def chaser_rank_info_not(name: str) -> bytes:
    """Handler window 0x328597: optional<0x349830: u32 x4, FString name, u32 x6, u8, u64, u32, u32, u8, u32>.
    Without it the client logs "Fail TCGameUserManager::GetUnitChaserRankInfo" over and over. Values copied from the
    shape of the live packet (4, 4, 1001, 1001, name, zeros); meanings unknown."""
    w = Writer().u8(1).u32(4).u32(4).u32(1001).u32(1001).fstr(name)
    for _ in range(6): w.u32(0)
    return w.u8(0).u64(0).u32(0).u32(0).u8(0).u32(0).bytes()


def end_game_not(mission_id: int, won: bool, char_uid: int = 0, name: str = '', account_uid: int = 0) -> bytes:
    """Handler window 0x38a1c0 -> TCStateRoom 0x37f7b0. The handler looks the local player (u64 at controller+0x318,
    the character uid: DS_RS_END_GAME_NOT carries it too) up in the per-player result map at +0x90 and skips the
    result screen if it isn't there. Layout from the deserializers; scalars mostly unknown:
    {u32, u32, u8, u8, {u32, TMap<u32,{u32,u32}>, 12 x u32}},
    TMap<u64 uid, {0x3a7380 result, 0x3a7750, TArray<{u8,u8,u32}>, u8}> (0x352630), TSet<u64> (0x2e4820),
    {u32, FString}, u32, u8, u8, {u64, u64}, u8, u32, u32."""
    w = Writer().u32(mission_id).u32(0).u8(1 if won else 0).u8(0)
    w.u32(0).empty()
    for _ in range(12): w.u32(0)
    # per-player results. The lookup key (controller+0x318) isn't confirmed: send the same entry under the character
    # uid, the account uid and 0.
    keys = list(dict.fromkeys([char_uid, account_uid, 0]))
    w.u32(len(keys))
    for key in keys:
        w.u64(key)
        w.u64(char_uid).fstr(name).u64(account_uid).u64(0).u32(0).u32(0)  # 0x3a7380 head
        w.empty(2)                                                         # two TMap<u8,u32>
        for _ in range(7): w.u32(0)
        w.u8(1 if won else 0)
        for _ in range(5 + 6): w.u32(0)
        w.u8(0)
        for _ in range(4): w.u32(0)
        w.raw(bytes(9))                                                    # 0x3a7940: 9 x u8
        for _ in range(14): w.u32(0)                                       # 2 x 0x3a72b0: 7 x u32
        w.u8(0).fstr(name).u64(char_uid).u32(0).u32(0)                    # 0x3a7750
        w.empty()                                                          # TArray<{u8,u8,u32}>
        w.u8(0)
    w.empty()                                                          # TSet<u64>
    w.u32(0).fstr('')
    w.u32(0).u8(0).u8(0).u64(0).u64(0).u8(0).u32(0).u32(0)
    return w.bytes()


def game_reward_not() -> bytes:
    """Deserializer 0x34b070: 3 x TMap<u8,u32>, TMap<u32,{u32,u32}>, TMap 0x2e3170 (items), TSet<u32>, u32.
    Empty reward for now."""
    return Writer().empty(6).u32(0).bytes()


def update_requested_match_not(mission_id: int) -> bytes:
    """Handler window 0x32777d: u32, u64, u32, FString, TMap 0x2e5870. Meanings guessed (mission id first)."""
    return Writer().u32(mission_id).u64(0).u32(0).fstr('').empty().bytes()


def completed_match_not(mission_id: int, region: str = 'local', match_id: int = 1) -> bytes:
    """Handler window 0x327a53 (before its log at 0x327b02): u32, FString, u32, u64, u32.
    Guess: mission id, region, ?, match id, accept timeout (s)."""
    return Writer().u32(mission_id).fstr(region).u32(0).u64(match_id).u32(30).bytes()


def progress_info_of_completed_match_not(mission_id: int, char_uid: int) -> bytes:
    """Handler window 0x327ba9: u32, u32, TMap<u64,u32> (0x2e4980) x2, container 0x2e6050 (u32 count + ...).
    Guess: mission id, ?, accepted {uid: 1}, declined {}, ..."""
    return Writer().u32(mission_id).u32(0).u32(1).u64(char_uid).u32(1).empty(2).bytes()


def ping_test_address_list_not(regions) -> bytes:
    """Deserializer 0x2e3ca0: TMap<FString region, TArray<FString address>>. The client pings each region
    (CL_GS_UPDATE_PING_BY_REGION_NOT) and RequestMatch (0x312280) sends one CL_GS_REQUEST_MATCH_REQ per known
    region: with no regions the Request Mission button silently does nothing."""
    w = Writer().u32(len(regions))
    for name, addrs in regions.items():
        w.fstr(name).u32(len(addrs))
        for a in addrs: w.fstr(a)
    return w.bytes()


def equip_item_ack(set_index: int, changed_items, op: int = 1, result=OK) -> bytes:
    """Handler at 0x327356: i32 result, u32, TArray<{u32 op?, u16, u16, optional item, u32}> (0x2e3170).
    The element fields besides the item are guesses (operation, inventory type, slot)."""
    w = Writer().i32(result).u32(set_index).u32(len(changed_items))
    for it in changed_items:
        w.u32(op).u16(it.get('inv', INV_GENERAL)).u16(it.get('slot', SLOT_NONE)).u8(1)
        item(w, it)
        w.u32(0)
    return w.bytes()


def update_character_info_in_game_not(account_uid: int, ch) -> bytes:
    """Handler 0x32c5c7 (relay -> host): u32, TMap<u32, FCharacterFullInfo> (0x2e2720). Sent after an equip so the
    locally hosted square/mission refreshes the character. Key guessed as the character uid (low 32 bits)."""
    w = Writer().u32(0).u32(1).u32(ch['uid'] & 0xffffffff)
    return full_info(w, account_uid, ch).bytes()
