# server/ — kzemu

Private-server emulator for KurtzPel. Current target: the **Dec 2019 story client** (build 2019-12-27, UE 4.19.1).
Python 3.11+, SQLite. Contains no KOG code, keys or assets: the packet key is read at startup from the player's own
client exe.

Status (2026-10-13): login → character creation → character select → Eltheca square works with a real client.
The new-character tutorial loads and the character spawns with the starter weapon. The square can be loaded locally
(single player, `tools/frida/square_local.js`, you can walk around) or hosted by a second copy of the client running
the map as a listen server (joins, but the joiner can't move yet).

## Run

```
pip install -r requirements.txt
python -m kzemu --client-exe "<KurtzPel>/TheChase/Binaries/Win64/TheChase-Win64-Shipping.exe"
```
Serves app info on `127.0.0.1:18080` and the game server on `127.0.0.1:11001`, and sends clients to a square at
`127.0.0.1:7777` (`--square host:port`). State goes to `kzemu.sqlite`; every decoded packet to `logs/trace.jsonl`.

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
- Equipping items (`CL_GS_EQUIP_ITEM_REQ`) has no handler yet, so the client waits forever.
- Starter skills are not equipped. The 10 stat values are placeholders.
- The world model may still use a placeholder body (the "worn look" set encoding is a guess).
- Multiplayer square: the listen host has no character data for joiners, so they can't move.
- Inventory capacity shows 0 ("equipment inventory is full"), probably from the placeholder stats.
- No story/mission flow yet.
