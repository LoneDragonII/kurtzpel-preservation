# Emulator for the Dec 2019 story client

**Status 2026-10-13:** a real 2019 client logs in, creates and selects a character, plays into the new-character
tutorial, and walks around Eltheca (square loaded locally via `tools/frida/square_local.js`). Multiplayer square
(listen host) joins but the joiner can't move yet. Helper scripts referenced below as `tools/run_offline.py`,
`offline_guard.js`, `nosteam.js`, `boot_map.js` are local and not published yet.

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
- 2026-10-13 22:55Z: **walking in Eltheca** with `tools/frida/square_local.js` (OpenLevel with an IP as the level name →
  open `Square_Eltheca` locally). Character, weapon and NPC markers render; body still a placeholder mesh. HUD warns
  "equipment inventory is full (220,040 / 0)": the inventory capacity is 0, probably one of the 10 placeholder stats.
