# KurtzPel Preservation Project

Non-commercial project to keep KurtzPel playable after official end of service:
an offline / private-server version with **PvE**, **private multiplayer lobbies**, and the
**2019 story mode** that was removed in January 2020.

This file is project context for contributors and for AI coding assistants (e.g. Claude Code)
working in this repo. Be concise and actionable. When unsure, inspect the files or run a tool
instead of guessing.

---

## Hard deadline

**Official servers shut down on 3 February 2027.**
Anything that requires the live servers (traffic capture, observing server responses) MUST be
done before then. Prioritise Phase 3 (live capture) over everything else that can wait.

---

## Background facts

- Developer/publisher: KOG (Korea) — same studio as GrandChase / Elsword.
- Steam App ID: `844870`
- Windows client depot: `844871`
- Engine: KOG fork of **Unreal Engine 4.19.1** (Dec 2019 build); internal project name **TheChase**.
- SDKs detected by SteamDB: EpicOnlineServices, Vivox (voice), CEF (embedded browser UI),
  BugTrap, PhysX/APEX/NvCloth. (EOS and Vivox not present in the Dec 2019 build.)
- Release: Early Access 30 April 2019.

### Content history (why we archive multiple builds)

| Date | Change |
|---|---|
| 2019 | Original release: story mode, original PvE structure, loot boxes, trust system |
| **15 Jan 2020** | Big update: Fallen Light karma, PvP mission overhaul, new group PvE missions, season pass. **Story mode removed.** Loot boxes / trust system / rebirth ticket removed |
| 20 Oct 2021 | Systems Revamp: PvE character levels, skill tree, Awakening, DP/CP removed |
| 29 Dec 2021 | Multiple PvP mission queues removed |
| 3 Feb 2027 | End of service |

---

## Builds

Downloaded with DepotDownloader (`-app 844870 -depot 844871`) using each contributor's own Steam
account. See `docs/getting-the-builds.md`.

| Folder | Manifest ID | Date (UTC) | Purpose |
|---|---|---|---|
| `KurtzPel_2019-12-27_story/` | `8731260772729569992` | 27 Dec 2019 08:42 | **Story build** — last build before story removal |
| `KurtzPel_2020-01-14_postpatch/` | `2917805514726316864` | 14 Jan 2020 22:15 | First build after story removal — used for diffing |
| `KurtzPel_final/` | (current) | latest | Live build — used for traffic capture and first emulator target |

**Build folders are read-only originals. Never modify, patch, or write into them.**
Copy a build to `work/<build>/` before patching anything. Builds are never committed.

---

## Folder layout

```
.
├── CLAUDE.md
├── KurtzPel_*/                     # local only, read-only originals (gitignored)
├── work/                           # local only, patched copies of clients (gitignored)
├── captures/                       # local only, raw + decrypted traffic logs (gitignored)
│   └── YYYY-MM-DD_<activity>/
│       ├── raw.pcapng
│       ├── decrypted.jsonl
│       ├── video.mp4 (or link)
│       └── README.md               # what was done in-game, in order, with timestamps
├── docs/                           # contributor guides
├── notes/                          # findings, one markdown file per topic
│   ├── engine.md                   # UE version, pak layout, encryption status
│   ├── network.md                  # hosts, ports, transport, framing, crypto
│   ├── opcodes.md                  # opcode table (see format below)
│   ├── story-diff.md               # assets removed between Dec 2019 and Jan 2020
│   └── pve-authority.md            # is boss logic client- or server-side?
├── tools/                          # our scripts: frida hooks, parsers, diff tools
└── server/                         # the emulator
```

Keep `notes/` up to date as findings come in — it is the project's memory.

---

## Phases

### Phase 1 — Archive
- [ ] Download all three builds (table above). Record the final build's manifest ID.
- [ ] Back up builds to a second drive.

### Phase 2 — Inspect the clients
- [x] Identify exact UE4 version → 4.19.1 (KOG fork).
- [ ] List all `.pak` files per build with sizes; check whether they're AES-encrypted.
- [ ] Diff the Dec 2019 vs Jan 2020 builds: file lists, pak contents, asset names. Look for
      story / episode / chapter / cinematic / quest assets that disappear. → `notes/story-diff.md`
- [ ] Find the networking layer:
  - Server hostnames/IPs/ports in config files, ini files, or exe strings.
    (Known: HTTPS "app info" bootstrap under `appinfo.playkog.com`; the client gets the game-server
    address from it.)
  - Custom KOG protocol for lobby (355 packet names in the client) and UE dedicated servers behind a
    relay for in-match — to confirm.
  - Identify the DLL/module and functions that send, receive, encrypt, decrypt.
  → `notes/network.md`

Encryption keys are never committed or posted publicly. Each contributor recovers or obtains them
locally.

### Phase 3 — Live traffic capture (BEFORE 3 Feb 2027)
- [ ] Wireshark: record which hosts/ports the client contacts at login, lobby, matchmaking,
      in-mission.
- [ ] Locate encrypt/decrypt (or send/recv-after-decrypt) functions via Ghidra + x64dbg.
- [ ] Frida hook (`tools/frida_hook.js`) that logs plaintext packets as JSONL:
      `{"t": <ms>, "dir": "c2s"|"s2c", "conn": "<host:port>", "len": N, "opcode": "0x....", "hex": "..."}`
- [ ] Capture checklist — each as its own folder in `captures/`, with a README of actions:
  - [ ] Login → character select → lobby (cold start)
  - [ ] Character creation and deletion
  - [ ] Every lobby menu: inventory, equip/unequip, karma change, shop browse, mail, quests,
        collection, settings
  - [ ] Every PvE boss/mission: solo, and in a party (2+ players) if possible
  - [ ] Death, revive, fail, abandon mid-mission
  - [ ] PvP queues (1v1, 2v2, ranked) and custom/private lobby
  - [ ] Abyss / any other mode still live
  - [ ] Repeat key actions 2–3 times to separate static vs dynamic fields
- [ ] Record video alongside captures so packets can be matched to on-screen events.

**Never edit files in `captures/`.** Derived/parsed output goes in `notes/` or a sibling file.
See `docs/capturing.md`.

### Phase 4 — Server emulator (final build first)
Order of work — each step should get the client one screen further:
1. Redirect the client to localhost (hosts file, config edit, or patched copy in `work/`).
2. Login server stub — accept any credentials; stub out Steam/EOS ticket validation.
3. Lobby server — character list, inventory, currencies, karmas from SQLite.
4. Enter a PvE mission solo.
5. Answer `notes/pve-authority.md`: if boss AI runs on the client/host, just relay; if it's
   server-authoritative, reimplement per-boss logic from captures + video.
6. Multiplayer: private lobbies, party join, relay in-match traffic.

Language: Python for prototyping packet handlers; move hot paths to C# or Rust if needed.
Keep the protocol definition (opcode → struct) in one place, shared by the server and the capture
parser.

### Phase 5 — Story build (Dec 2019 client)
- Point the Dec 2019 client at the emulator; adapt for opcode/struct differences from final.
- Reimplement story progression (chapter unlocks, quest state, cutscene triggers) using the
  client code and 2019 YouTube playthroughs as the spec. No live captures exist for this.

---

## Conventions

### Opcode table format (`notes/opcodes.md`)
```
| Opcode | Dir | Name (ours) | Seen in | Struct | Notes |
|--------|-----|-------------|---------|--------|-------|
| 0x0101 | c2s | LoginReq | captures/2026-10-20_login | u32 ver, str16 token | |
```
Mark anything guessed with `?`. Confirmed fields lose the `?` only after matching ≥2 captures.

### Findings
- Every claim in `notes/` should cite its evidence: capture folder + packet index, or
  exe address / function name in Ghidra, or asset path.
- Record failed approaches too, briefly, so they aren't retried.

### Working with a contributor
- The contributor plays the game and runs GUI tools (x64dbg, FModel, Wireshark capture start/stop).
  The assistant does file inspection, static analysis, scripting, log parsing, and server code.
- When a step needs someone in-game, say exactly what to do and what to capture, in a short
  numbered list.
- Prefer command-line tools: Ghidra headless (`analyzeHeadless`), radare2/rizin, `strings`,
  Python (`pefile`, `capstone`, `scapy`/`pyshark`), Frida CLI, repak/UnrealPak or CUE4Parse for paks.

---

## Tooling

| Tool | Use |
|---|---|
| DepotDownloader | Archive builds (`-qr` or `-username <your_steam_username> -remember-password`) |
| FModel | Browse/extract UE4 paks (GUI) |
| repak / CUE4Parse | Scriptable pak listing/extraction |
| Ghidra (+ headless) | Static analysis of `TheChase-Win64-Shipping.exe` and DLLs |
| x64dbg | Dynamic debugging, finding crypto at runtime |
| Frida | Hook send/recv/crypto to log plaintext packets |
| Wireshark | Raw capture, host/port discovery |
| Python | Parsers, diff tools, emulator prototype |
| SQLite | Emulator persistence |

---

## Boundaries

- Non-commercial. No paid features, no donations tied to access.
- Do not redistribute KOG's client files, extracted assets, or encryption keys. Players supply their
  own client (from Steam/DepotDownloader); we distribute only our own server code and tools.
- The emulator is our own code written from observed behaviour — don't copy KOG server code
  or binaries if any are ever found.
- Use only your own account for captures; don't capture or log other players' data
  beyond what's unavoidable in party/PvP sessions, and strip it from anything shared.
- Don't touch anti-cheat or other players' sessions on the live servers. Live-server work is
  observation only (logging your own client's traffic).
