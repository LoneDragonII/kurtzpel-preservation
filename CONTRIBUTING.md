# Contributing

Thanks for helping keep KurtzPel alive. Anyone can help, whether or not you write code.

## Where help is needed

| Area | What it involves |
|---|---|
| **Live capture** (urgent, before 3 Feb 2027) | Playing the game while recording traffic and video. See [docs/capturing.md](docs/capturing.md) |
| **Reverse engineering** | Ghidra / x64dbg on `TheChase-Win64-Shipping.exe` (UE 4.19.1, KOG fork): packet ID table, framing, compression, encryption, send/recv functions |
| **Frida / hooking** | A hook that logs plaintext packets in our JSONL format (below) |
| **Server development** | Python prototype of the emulator: app-info bootstrap, login, lobby, missions; SQLite persistence |
| **Story research** | 2019 YouTube playthroughs, wiki archives, screenshots: story chapter order, dialogue, unlock conditions |
| **Asset research** | Comparing the Dec 2019 and Jan 2020 builds to find what was removed |

## Ground rules

- **Never commit game files**: no `.pak`/`.exe`/`.dll`, no extracted or decrypted assets, no encryption
  keys, no captures. Reference assets by their path inside the pak instead.
- **No personal data**: no account names, Steam IDs, tokens, or other players' names in issues, PRs or
  notes.
- **Our own code only**: the emulator is written from observed behaviour. Don't contribute KOG server
  code or binaries if any ever surface.
- **Observation only on live servers**: log your own client's traffic. Don't touch the anti-cheat,
  don't cheat, don't interfere with other players.
- Non-commercial: no paid features or donations tied to access.

## `notes/` conventions

`notes/` is the project's memory: one markdown file per topic.

| File | Topic |
|---|---|
| `notes/engine.md` | UE version, pak layout, encryption status |
| `notes/network.md` | Hosts, ports, transport, framing, crypto |
| `notes/opcodes.md` | Opcode table |
| `notes/story-diff.md` | Assets removed between Dec 2019 and Jan 2020 |
| `notes/pve-authority.md` | Is boss logic client- or server-side? |

### Cite your evidence

Every claim in `notes/` must cite where it came from:

- a capture folder + packet index (e.g. `2026-10-20_login-cold-start #142`), or
- an exe address / function name in Ghidra (and which build), or
- an asset path inside the pak.

Mark anything guessed with `?`. **Record failed approaches too**, briefly, so nobody retries them.

### Opcode table format (`notes/opcodes.md`)

```
| Opcode | Dir | Name (ours) | Seen in | Struct | Notes |
|--------|-----|-------------|---------|--------|-------|
| 0x0101 | c2s | LoginReq | captures/2026-10-20_login | u32 ver, str16 token | |
```

A field loses its `?` only after it has been matched in **at least two captures**.

### Packet log format (Frida hook output)

One JSON object per line:

```json
{"t": 1234, "dir": "c2s", "conn": "host:port", "len": 42, "opcode": "0x0101", "hex": "..."}
```

`t` is milliseconds since capture start; `dir` is `c2s` or `s2c`.

## Workflow

1. For anything bigger than a typo, open an issue first (use the templates: capture submission,
   RE finding, bug).
2. Fork, branch, keep PRs focused on one thing.
3. Keep the protocol definition (opcode → struct) in one place, shared by the server and the capture
   parser.
4. Python for prototyping; hot paths can move to C# or Rust later.

By contributing you agree your contributions are licensed under the [AGPL-3.0](LICENSE).
