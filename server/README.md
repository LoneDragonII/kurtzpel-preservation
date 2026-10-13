# server/ — kzemu

Private-server emulator for KurtzPel. Current target: the **Dec 2019 story client** (build 2019-12-27, UE 4.19.1).
Python 3.11+, SQLite. Contains no KOG code, keys or assets: the packet key is read at startup from the player's own
client exe.

Status (2026-10-13): with a real 2019 client you can log in, create and select a character, walk around Eltheca,
open the Mission Map, request a story (Epic) mission, get matched and play it to the boss kill. Missions and the square
run inside your own client (it is its own host), loaded by `tools/frida/local_travel.js`.

## Run

```
pip install -r requirements.txt
python -m kzemu --client-exe "<KurtzPel>/TheChase/Binaries/Win64/TheChase-Win64-Shipping.exe"
```
Serves app info on `127.0.0.1:18080` and the game server on `127.0.0.1:11001`, and sends clients to a square at
`127.0.0.1:7777` (`--square host:port`). State goes to `kzemu.sqlite`; every decoded packet to `logs/trace.jsonl`.

With `--travel-file <path>` the server writes the map the client should open next; `tools/frida/local_travel.js`
(set its `TRAVEL_FILE` to the same path) opens it locally instead of connecting to a match server.
`--start-mission <id>` skips the Mission Map and opens that Epic straight after login (ids 1000-6020).

Client switches (the 2019 client reads these from its command line):
```
-GetOptionURL=http://127.0.0.1:18080/Service/GetOption
-LoginURL=http://127.0.0.1:18080/Service/Login
-UsingPrivatePublishCode=na        # needed when Steam is disabled
```
To join a square hosted by another client, both copies must run with Steam networking disabled (plain UDP).

## Layout
| File | What |
|---|---|
| `kzemu/appinfo.py` | HTTP bootstrap (`/Service/GetOption`, `/Service/Login`) |
| `kzemu/framing.py` | 54-byte frame header, AES-256-ECB body, zlib |
| `kzemu/wire.py` | untagged little-endian field encoding |
| `kzemu/packets2019.py` | opcodes and packet builders for the 2019 client (with the client RVAs they came from) |
| `kzemu/gameserver.py` | sessions and handlers |
| `kzemu/db.py` | SQLite accounts and characters |
| `tests/test_loopback.py` | fake client walks the whole flow with a random key |

## Known gaps
- No result screen after the boss (END_GAME is accepted; the client's reward widget class is never loaded).
- Starter skills are equipped (E/R/F/Q icons show) but don't fire yet.
- Equipping in Eltheca breaks movement until the next map load (gear is saved, so relog/mission applies it cleanly).
- Mission rewards (AP/CP/items) and story progress are not saved.
- Multiplayer square/missions: a listen host has no character data for joiners, so they can't move.
