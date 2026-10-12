# Getting the game builds

This project never distributes KurtzPel files. You need your own copy of the client. You can play
the current build from Steam as normal; for older builds (needed for the story mode work) use
[DepotDownloader](https://github.com/SteamRE/DepotDownloader), which downloads specific historical
builds from Steam using your own account. KurtzPel is free to play, so any Steam account that has
added it to its library should work.

| | ID |
|---|---|
| App | `844870` |
| Windows client depot | `844871` |

## Known builds

| Build | Manifest ID | Date (UTC) | Why |
|---|---|---|---|
| Dec 2019 story build | `8731260772729569992` | 27 Dec 2019 | Last build before story mode was removed |
| Jan 2020 post-patch | `2917805514726316864` | 14 Jan 2020 | First build after story removal, used for diffing |
| Final / live | (current Steam build) | — | Traffic capture and first emulator target |

## Download

1. Get the latest DepotDownloader release for your OS and unzip it.
2. Run one of the commands below from that folder. Replace `<your_steam_username>` with your own
   Steam login, and pick an output folder with ~25 GB free.

Dec 2019 story build:

```bash
DepotDownloader -app 844870 -depot 844871 -manifest 8731260772729569992 -username <your_steam_username> -remember-password -dir KurtzPel_2019-12-27_story
```

Jan 2020 post-patch build:

```bash
DepotDownloader -app 844870 -depot 844871 -manifest 2917805514726316864 -username <your_steam_username> -remember-password -dir KurtzPel_2020-01-14_postpatch
```

Latest build (no `-manifest`):

```bash
DepotDownloader -app 844870 -depot 844871 -username <your_steam_username> -remember-password -dir KurtzPel_final
```

### Logging in with a QR code

Instead of typing your password, you can use `-qr`: DepotDownloader prints a QR code that you scan
with the Steam mobile app.

```bash
DepotDownloader -app 844870 -depot 844871 -manifest 8731260772729569992 -qr -dir KurtzPel_2019-12-27_story
```

## Notes

- Record the manifest ID of any build you download (DepotDownloader prints it). If you find other
  historical manifests that matter, open an issue.
- Treat downloaded builds as read-only originals. Copy a build to a separate `work/` folder before
  patching or modifying anything.
- Don't upload builds or extracted files anywhere public, including issues and PRs in this repo.
