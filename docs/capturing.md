# Capturing live traffic

**Deadline: the official servers shut down on 3 February 2027.** After that, nothing in this guide
is possible. Every capture you make before then helps us rebuild the server side of the game.

Only capture **your own client's traffic on your own account**. This is observation only: don't
modify the game, don't touch the anti-cheat, don't interfere with other players.

## What you need

- KurtzPel installed from Steam (the live build).
- [Wireshark](https://www.wireshark.org/) (raw capture).
- A screen recorder (OBS or similar). Video lets us match packets to what happened on screen.
- Optional, for advanced contributors: [Frida](https://frida.re/) with the hook script from
  `tools/` once it exists, which logs decrypted packets. Raw Wireshark captures are still useful
  without it.

## What to capture

Each activity is its own capture. Start Wireshark and the video recorder, do the activity, stop both.

**Priority 1**
- [ ] Cold start: launch the game → login → character select → lobby
- [ ] Every lobby menu: inventory, equip/unequip, karma change, shop browsing (don't buy anything you
      don't want), mail, quests, collection, settings
- [ ] Each PvE boss / mission **solo**

**Priority 2**
- [ ] Each PvE boss / mission **in a party** (2+ players)
- [ ] Death, revive, mission fail, abandoning a mission midway
- [ ] Character creation and deletion
- [ ] PvP queues (1v1, 2v2, ranked) and custom / private lobbies
- [ ] Abyss and any other mode that's still live

**Repeat key actions 2–3 times** (separate captures). Comparing repeats tells us which packet fields
are fixed and which change.

## Folder naming

One folder per activity:

```
YYYY-MM-DD_<activity>/
    raw.pcapng        Wireshark capture
    decrypted.jsonl   only if you used the Frida hook
    video.mp4         or a link to an unlisted video in README.md
    README.md         what you did, in order, with timestamps
```

Examples: `2026-10-20_login-cold-start`, `2026-10-21_pve-<boss-name>-solo`,
`2026-10-21_lobby-inventory-equip`.

## The capture README

Write down every action with the time it happened (video timestamp or wall-clock), so we can line it
up with the packets:

```markdown
# PvE boss <name>, solo

- Date: 2026-10-21, client build: current Steam build
- Region / server: EU
- Party: solo
- Wireshark started 20:14:05, video started 20:14:07

| Time  | Action |
|-------|--------|
| 00:00 | In lobby, opened mission board |
| 00:12 | Selected the boss mission, clicked Start |
| 00:31 | Loading screen ended, in mission |
| 03:40 | Died once, revived with item |
| 06:02 | Boss killed, results screen |
| 06:20 | Back in lobby |
```

## Strip personal data before sharing

Before you upload anything, remove or redact:

- Your account name, Steam display name, **Steam ID** (the 17-digit number starting with `7656…`)
- Login tokens, session tickets, cookies, auth headers
- **Other players' names** and IDs (party members, PvP opponents, chat)
- Your local and public IP addresses, if you care about that

In Wireshark you can limit the export to the game's connections only (File → Export Specified
Packets with a display filter for the game's server IP). If you're unsure whether something is
sensitive, say so in the issue and we'll help, but **don't post it publicly first**.

The Frida JSONL output is easier to redact than a raw pcap. If you can only share a pcap and it
contains other players' data, mention it and we'll arrange a private hand-off.

## How to submit

**Don't commit captures to this repository.** Captures stay out of git (see `.gitignore`).

1. Zip the capture folder.
2. Upload it somewhere you control (Google Drive, Mega, etc.) with a shareable link.
3. Open a **Capture submission** issue on this repo with the link, the activity, the date, and
   confirmation that you've stripped personal data.

We keep raw captures unmodified; anything we derive from them goes into `notes/`.
