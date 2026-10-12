# KurtzPel Preservation

A non-commercial, fan-run effort to keep **KurtzPel** playable after the official servers shut down
on **3 February 2027**.

Goals:

- **Private server emulator** written from scratch from observed client behaviour.
- **PvE** missions and bosses playable offline / on private servers.
- **Private multiplayer lobbies** so friends can still play together.
- **Restore the 2019 story mode** that was removed from the game in January 2020.

> **We never distribute game files.** Players supply their own client from Steam (or download an
> archived build of their own with DepotDownloader, see [docs/getting-the-builds.md](docs/getting-the-builds.md)).
> This repo contains only our own code, tools and documentation.

---

## 🚨 Urgent: help capture live traffic before 3 February 2027

Once the official servers go dark, the server side of the game is gone for good. Every packet we
record from the live game now is a specification we can build the emulator from later. **We need
players to record their own client's traffic** while doing as many different things as possible:
logging in, every lobby menu, each PvE boss solo and in a party, PvP queues, custom lobbies.

You don't need to be a reverse engineer to help. See **[docs/capturing.md](docs/capturing.md)** for
what to record, how to name it, how to strip personal data, and how to submit it.

---

## Current status

| Area | Status |
|---|---|
| Archiving builds | Dec 2019 story build archived; Jan 2020 post-patch build in progress; final build pending |
| Engine | Identified: KOG fork of **Unreal Engine 4.19.1** (internal project name *TheChase*) |
| Pak files | Pak format v4, encrypted index; listing works for the Dec 2019 build |
| Networking | Bootstrap goes over HTTPS to an "app info" service under `appinfo.playkog.com`, which hands the client a game-server address. Lobby/game traffic is a custom KOG protocol; the client contains **355 packet names** (`CL_GS_*`, `GS_CL_*`, …). Opcode IDs and wire encryption not yet mapped |
| In-match | Missions appear to run on UE dedicated servers behind a relay. Whether boss logic is client- or server-authoritative is still open |
| Story mode | The 2019 client contains `Epic_<id>` story missions across six areas, with cinematics and NPC dialogue tables. Diff against the Jan 2020 build pending |
| Live captures | **Not started — this is where we need help most** |
| Server emulator | Not started |

## Roadmap

1. **Archive** — download and back up the Dec 2019 story build, the Jan 2020 post-patch build, and
   the final live build.
2. **Inspect the clients** — engine version, pak layout, story asset diff, networking layer (hosts,
   ports, framing, crypto, send/recv functions).
3. **Live traffic capture (before 3 Feb 2027)** — Wireshark for hosts/ports, a Frida hook that logs
   plaintext packets as JSONL, and a capture of every menu, mission and mode, paired with video.
4. **Server emulator (final build first)** — redirect the client to localhost, stub login, lobby
   (characters, inventory, currencies from SQLite), solo PvE, then multiplayer private lobbies.
5. **Story build** — point the Dec 2019 client at the emulator and reimplement story progression
   using the client data and 2019 playthrough videos as the spec.

See [CLAUDE.md](CLAUDE.md) for the full phase checklist and conventions.

## How to help

- **Play and capture** — the most valuable thing anyone can do before February 2027.
  [docs/capturing.md](docs/capturing.md)
- **Reverse engineering** — Ghidra / x64dbg on the client: packet IDs, framing, encryption.
- **Hooking** — Frida scripts that log plaintext packets.
- **Server development** — Python prototype of login/lobby/mission handlers.
- **Story research** — 2019 YouTube playthroughs, wiki archives, screenshots of story chapters.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR or issue.

## Repository layout

```
docs/            how to get builds, how to capture traffic
notes/           findings, one markdown file per topic (engine, network, opcodes, story, PvE)
tools/           our scripts: Frida hooks, parsers, diff tools
server/          the emulator
```

Game builds, captures, extracted assets and keys are **never** committed; see `.gitignore`.

## Legal and boundaries

- Non-commercial. No paid features, no donations tied to access.
- No KOG client files, extracted assets, or encryption keys are distributed here.
- The emulator is our own code written from observed behaviour; we don't use KOG server code or binaries.
- Live-server work is observation only: logging your own client's traffic. Don't touch anti-cheat or
  other players' sessions.

KurtzPel is a trademark of KOG. This project is not affiliated with or endorsed by KOG.

## License

Our code is licensed under the [GNU AGPL-3.0](LICENSE).
