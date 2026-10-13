# Emulator for the Dec 2019 story client

**Status 2026-10-13 (day 2):** a real 2019 client logs in, creates and selects a character (correct starter outfit,
karmas, emotes), walks around Eltheca, requests a story (Epic) mission from the Mission Map, gets matched, loads the
mission map locally and plays it to the boss kill. Open: skills don't fire, no result screen, equip in the square needs
a relog. Helper scripts referenced as `tools/run_offline.py`, `offline_guard.js`, `nosteam.js`, `boot_map.js` are local
and not published yet; `tools/frida/local_travel.js` is.

Code: `server/` (package `kzemu`, AGPL, no keys/assets).
Static evidence below is from `KurtzPel_2019-12-27_story/TheChase/Binaries/Win64/TheChase-Win64-Shipping.exe`
(PE timestamp 0x5E05B577); addresses are RVAs. Tools: `tools/re/schema2019.py`, `tools/re/handlers2019.py`,
`tools/re/sends2019.py`.

## Redirecting the client (no hosts edit, no certificate)
- The login state reads two command-line overrides with `FParse::Value(FCommandLine::Get(), ...)`:
  `GetOptionURL=` (0x36e994, string 0x2ae2b98) and `LoginURL=` (0x3733bb, string 0x2ae4a68). Plain `http://` works.
- Launch: `-GetOptionURL=http://127.0.0.1:18080/Service/GetOption -LoginURL=http://127.0.0.1:18080/Service/Login`
- GetOption JSON reads `Option`/`Value`, and Value is a JSON string with `Domain`/`Port` (same as live). The domain is
  resolved with gethostbyname ("Domain(%s) to IP(%s)"), so an IP literal is fine.
- Login JSON reads at least `ZoneCode` (must be non-empty: "Failed to start game(empty zone code)"), `State`, `Token`,
  `MsgReserve`. The emulator returns the full live-format object.
- Without Steam (`tools/nosteam.js`, needed for plain-UDP joins) the client has no region and fails with
  "Failed to start game(empty publish code)". Fix: `-UsingPrivatePublishCode=na`. The switch name is XOR-obfuscated on
  the stack (key byte = first byte of the 16 bytes at 0x2aee7b0), read with FParse::Value at 0x36ee0a.
- Other switches seen next to them: `ZoneCode=` (0x2ae2378), `BETA_SERVER` (0x2ae2458). Not needed so far.

## Game-server protocol differences vs live (2026)
| | 2019 | live |
|---|---|---|
| Header | 54 B: u32 len, u32 seq, 46-B packet header (u16 opcode at 0x08) | 62 B: len, seq, crc1, crc2, opcode at 0x10 |
| Checksums | none | crc1 = CRC32(frame[0:16] with crc1 zeroed), crc2 = CRC32(frame[0x10:0x3e]) (standard zlib CRC32, verified on capture frames) |
| Body cipher | AES-256-ECB, same key string (RVA 0x2ab02c0, first 32 bytes), body = u32 n + payload + random pad | same |
| Encryption on/off | per session flag `session+0xa8` (send, 0x2f2fdd) | `session+0x98` |
| Compression | zlib when payload > 0x1000; header+0x1a = uncompressed size | same idea |
| Field encoding | raw little-endian, **no tag bytes**; FString = u32 byte_len + UTF-16LE | every field prefixed with 0x01 |
| Opcodes | 370 (index into name table at RVA 0x3edbbd0+160*8; HEART_BEAT = 0) → `tools/capture/opnames_2019.json` | 632 |

- Read primitive 0x3e1610(reader, dst, n); FString reader 0x3c3940; write primitive 0x3f3ae0; FString writer 0x3e1580.
  Optional = u8 (1 = present) + struct; TArray/TMap/TSet = u32 count + elements.
- Receive loop: TCBaseSession, ReceiveBuffer around 0x3e1ad1 (body size = len - 0x36). SendBuffer 0x3e78b0 writes
  only the seq at frame+4. Client gives up with "Disconnected from server(Fatal)"/"zombie!!" if it hears nothing for
  a while, so the server sends HEART_BEAT (op 0, empty) every 10 s.

## Login → square flow (2019 structs, all confirmed against the client's Deserialize functions)
| Op | Name | Layout | Deserializer |
|---|---|---|---|
| 0x0002 | GS_CL_VERIFY_ACCOUNT_ACK | i32 result, u64 account, FString steam id, u64 x3, u32, u32, 3 containers, u64, 2 containers, u32, u8, u32, container, u32, container | 0x3a70a0 |
| 0x000c | GS_CL_CHARACTER_LIST_ACK | i32 result, TMap<u64, FCharacterInfo> | inline, map 0x352270 |
| 0x0004 | GS_CL_CREATE_CHARACTER_ACK | i32 result, FCharacterInfo | inline (0x3898dc) |
| 0x000e | GS_CL_USE_CHARACTER_ACK | i32 result, FCharacterFullInfo (0x34a0a0), 2 maps, 3 sets, u8, u32, 3 containers, set | 0x3a6f50 |
| 0x0010 | GS_CL_ENTER_SQUARE_ACK | i32 result, i32, u64 square id, i32, i32 | 0x34af20 |
| 0x0011 | GS_CL_JOINABLE_SQUARE_NOT | u64 square id, u64 auth key, FString public ip, FString private ip, u16 port, FString, u32 | 0x34b2f0 |
- FCharacterInfo (0x3a6900): u64 uid, FString name, opt<10 x u32> (0x34a200, appearance?), opt<0x349a00> (equipment
  look/stats, large), opt<inventory 0x30b600>, u64, u8.
- c2s VERIFY_ACCOUNT_REQ serializer 0x3a80b0: FString, FString, u32, FString x6+.
- c2s CREATE_CHARACTER_REQ: serializer not found statically yet (send template not matched by sends2019.py). The
  emulator logs the payload and stores it in the DB (`character.create_req`) for decoding.

## Square (lobby)
- After JOINABLE_SQUARE_NOT the client travels to a UE server at `ip:port` (live: plain UE netcode on UDP, map
  `/Game/TheChase/Map/Eltheca/Square_Eltheca`, game mode `TcSquareGameModeBP`). The 2019 paks have the same map
  (`pakchunk32`).
- The emulator points the client at `--square 127.0.0.1:7777` by default. Something has to listen there:
  per the mission-hosting test, the 2019 client can run a map with `?listen` (a patched copy of the client). Hosting Square_Eltheca the
  same way is the next step; join URL options (`character_uid`, `auth_key`) still to be checked for 2019.
- From the mission-hosting test (2026-10-13, details in `notes/pve-authority.md`): a listen host on 7777 accepts a joiner
  with `?character_uid=<n>?auth_key=<n>` and does **not** validate them (junk values joined). A listen host **never
  dials a relay**: no RS_DS_* traffic, no host/port read, so there is nothing for the emulator to serve on that side
  yet. Both host and joiner must run with `tools/nosteam.js` (else SteamNetDriver P2P; `-nosteam` is ignored).
  All players spawn as spectators until character data exists; the host's own character should come from your GS
  login, so the useful combined test is emulator login → host OpenLevels a map with `?listen`.

## Status log
- 2026-10-13: emulator written; loopback test (`server/tests/test_loopback.py`) passes.
- 2026-10-13 real client (with Steam): login, character creation (new chars go to the tutorial map
  Abandoned_Ruins_Tutorial_10, standalone), character select, ENTER_SQUARE all work; client then browses to
  `127.0.0.1//Game/TheChase/Map/Branch/Branch_TheChase? character_uid=<n> auth_key=<n>` via SteamNetDriver.
- Starter gear (DefaultItemTable): weapons 210040 (WT_GreateSword) and 220040 (WT_Bow) are the WeaponDetailTable ids;
  160000-160090 are NOT weapons ("Weapon Data Is nullptr : 160000"). Outfit 30000/40000/20000/140070.
- Square host: second instance with `boot_map.js` (URL `/Game/TheChase/Map/Eltheca/Square_Eltheca?listen`) +
  `nosteam.js` binds UDP 7777 and loads the square.
- 2026-10-13 22:43Z: player client (nosteam + `-UsingPrivatePublishCode=na`) joined the square host: host log
  "Join succeeded", client "Welcomed by server (Level Square_Eltheca, Game TcSquareGameModeBP)". Character pawn spawns
  (tutorial and square) but body shimmers and "Weapon Data Is nullptr : 140070": weapon comes from the unit-property
  optional 0x30b690 = TMap<u8 weapon-set index, u32 weapon item id> (+ second TMap<u8,u32>), read by getter 0x46a9b0.
  Was sent absent; now filled {0: 210040, 1: 220040}. Untested yet.
- Unhandled c2s seen in the square: CL_GS_GET_ONLINE_CHARACTER_INFO_REQ, CL_GS_SQUARE_FPS_LOG_NOT.
- 2026-10-13 22:51Z: in the square the player sees their own character (weapon OK after item fix) but **cannot move**.
  Likely cause: movement is server-authoritative and the listen host has no character data for the joiner (host log:
  "GetUnitPropertyInfo Failed", "GetUnitItemInventoryInfo CharacterUID : 0"). The real DS gets character info from the
  relay (RS_DS_* / UPDATE_CHARACTER_INFO_IN_GAME_ONLY_NOT, UPDATE_ALLOWED_CHARACTER_LIST_REQ). Next: feed the host the
  joiner's character (host connects to kzemu as a DS/relay client, or a Frida injection), or have the host log in too.
- Equip in the inventory menu hangs: CL_GS_EQUIP_ITEM_REQ (0x001d: u32, u64 item uid, u8 slot, u8) has no ACK yet.
- 2026-10-13 22:55Z: **walking in Eltheca** with `tools/frida/square_local.js`. Inventory capacity shows 0 ("equipment inventory is full (220,040 / 0)"), probably a
  placeholder stat. 
- 2026-10-13 06:30Z: mission map. Needs GS_CL_DISPLAY_MISSION_LIST_NOT (0x58: u32, TMap<u32 mission id, u32>,
  TSet<u32>); 22 Epic ids = map suffixes (1000-1030 Abandoned Ruins ... 6000-6020 Karciel). Mission board asks
  CL_GS_GET_CUSTOM_MISSION_LIST_REQ (0x68) and spins until ACK 0x69 (i32, TArray, FString, i32, TMap<u8,u32>).
- Inventory TMap 0x2e4110 = TMap<u8 EInventoryType, {u32 used, u32 capacity}> (proved by the HUD warning
  "skill inventory is full (210,040 / 0)" when it held (1, 210040, 0)). Karmas (210040/220040) are skill inventory.
- Request Mission button sends nothing yet (client-side gate, unknown). Workaround: `--start-mission <id>` makes the
  next square travel open the Epic map locally via `local_travel.js` + `--travel-file`.
- Epic_1000 loads locally with the player's character; boss AI moves and attacks (client is the authority). Stats
  0x34a200 are 10 float32 (setter 0x485b2a → 0x47fa40 / 0x43bfc0); sent as ints they gave zero move speed/stamina/HP.
- 2026-10-13 07:18Z: **Epic 1000 fully playable** (hits both ways, dodges, karma switch, boss AI, intro). StatInfo
  = UnitStatTable UnitStatData: {Strength, Agility, Inteligence, Spirit, Stamina}, Mass, GravityScale, MaxJumpHeight,
  MaxWalkSpeed, GroundFriction (float32); row 0 = 5,5,5,5,5,100,4,300,740,0.02.
- Mission end: the local host sends DS_RS_END_GAME_NOT (0xdc: u8 result, u64 char uid, ...) on the GS socket.
  GS_CL_END_GAME_NOT (0x1c) handler TCStateRoom 0x37f7b0 needs the local player (u64 at controller+0x318) in the
  per-player TMap at struct+0x90, else no result screen (character stood still after the boss).
- 2026-10-13 07:55Z: **Request Mission works end to end.** RequestMatch (0x312280) sends one CL_GS_REQUEST_MATCH_REQ
  (u32 mission id, FString region) per ping-test region; regions come from GS_CL_PING_TEST_ADDRESS_LIST_NOT (0x50:
  TMap<FString, TArray<FString>>), so with none the button does nothing. Flow: REQUEST_MATCH_ACK (i32, u32, FString,
  u32) → UPDATE_REQUESTED_MATCH_NOT (u32, u64, u32, FString, TMap) → COMPLETED_MATCH_NOT (0x29: u32, FString, u32,
  u64, u32) → client ANSWER_TO_COMPLETED_MATCH_NOT → PROGRESS_INFO_OF_COMPLETED_MATCH_NOT (0x2a) + JOINABLE_ROOM_NOT
  → local_travel.js opens the Epic map. Caverns_of_Beast_Epic_3000 played to the boss kill.
- Result screen still missing: END_GAME handler needs GameInstance+0x2730 (reward widget class), null so far.
- 2026-10-13 11:20Z: **body fixed.** EEquipSlot real values (reflected FEnumeratorParam table): None 0, Weapon 1,
  Weapon_Sub 2, Costume Top 10 / Pants 11 / Iner 12 / Head 13 / Hair 14, Accessory Foot 50 ... LeftHand 60,
  NomalSkill1-3 101-103, RageSkill 104, Assist 150-153, Emotion 160-164. With the outfit in slots 3/4/5/8 nothing was
  worn and the in-world body showed the shimmering materialize effect. ECostumeType: Top 0, Pants 1, Iner 2, Head 3,
  Hair 4, OnePiece 100.
- EQUIP_ITEM_ACK (0x1e, handler 0x327356): i32 result, u32, TArray<{u32, u16, u16, optional item, u32}> (0x2e3170).
- 2026-10-13 12:00Z: starter gear from client tables: ItemTable says 160000-160090 are IT_Emotion (slots 160-164);
  starter skills (unsellable, SkillDataTable WeaponSetType): GS 1100/1110/1120 + rage 1170, Bow 1220/1240/1250 + 1270.
  Skills show on E/R/F/Q but do not fire yet (open). Unit-property map 1 = weapon-set index -> EWeaponType (1 GS, 3 Bow).
- Item second u32 behaves like durability: with 1 on the bow the bow rendered black.
- EQUIP_ITEM_REQ: u32 set, u64 uid, u8 (always 0 seen), u8 slot; equip and "Unequip" send the same request -> server
  toggles. Applying the ACK in the locally hosted square breaks movement until the next map load (client handler
  0x316970 has several branches; [ack+4] nonzero triggers 0x47e040/0x3c1f50). UPDATE_CHARACTER_INFO_IN_GAME_ONLY_NOT
  (0x16a: u32, TMap<u32, FCharacterFullInfo>) refreshes the look but also froze movement; not sent.
