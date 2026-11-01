# M68 mini retro console

Notes and tooling from reading the SD card of a retro TV game stick sold as an
**M68** (build `M68 V1.0.0`, 22 January 2026) — a clone of the SJGAM M66.


---

## Notes


- **The menu is a directory listing.** Categories come from `readdir("/sdcard/game")`,
  capped at 50. `mkdir` is the whole procedure for adding a system.
- **`/sdcard/game1` is a dead end.** The launcher scans it every boot, but tags the
  rows with a path no category tile matches. Put ROMs in `/sdcard/game/<system>/` and
  build `games.db` for them (below).
- **720p50 is a script's choice, not a hardware limit.** `drm-hotplug.sh` prefers
  1280x720 over 1920x1080, and the mode is matched on size alone, so the refresh rate
  is whichever the TV lists first. 1080p can be forced from `test.sh`; on our unit it
  worked but flickered and looked no better, so stock stays.
- **`/sdcard/test/test.sh` replaces the launcher**, checked for by `S50ui` at boot.
  No firmware modification, fully reversible.
- **`/etc/webster` is decrypted.** It turned out to be an older `start_game.sh`. The
  cipher keys off a window of the init script XORed with the kernel builder's
  `user@host` — a tamper check rather than a secret. It is stale, and the code that
  reads it is unreachable, along with a Rockchip eFuse anti-clone check.
- **Nine menu icons have no emulator behind them** (`dreamcast`, `naomi`, `cps3`,
  `nds`, …).

## Layout

```
NOTES.md                      the full teardown: boot path, menu, schema, crypto, addresses
webster-decrypted.sh          plaintext of /etc/webster
tools/                        see below
assets/                       product photograph from the M66 listing
```

## Tools

### `tools/build_gamesdb.py` — build or extend `games.db`

```sh
tools/build_gamesdb.py scan   ROMDIR                        # dry run, flags missing cores
tools/build_gamesdb.py build  ROMDIR -o games.db --base games.db
tools/build_gamesdb.py titles games.db -o titles.csv        # edit, feed back with --titles
```

#### Starting from scratch with your own ROMs

A category tile is a directory in `/sdcard/game`, and it lists exactly the rows whose
`timer` is `/sdcard/game/<that directory>`. So the ROMs and `games.db` must both live
under `/sdcard/game`:

1. Lay out `roms/<system>/<file>` on the PC, using the firmware's folder names
   (`snes`, `md`, `cps`, `gba`, … — see NOTES.md).
2. `tools/build_gamesdb.py scan roms` — check every folder maps to a core that ships.
3. `tools/build_gamesdb.py build roms -o games.db` — no `--base`, so no stock rows.
4. Back up the card's `/sdcard/game`, then delete its system folders and `.db` files.
5. Copy `roms/*` into `/sdcard/game/`, plus the `games.db` from step 3 — check
   `sqlite3 games.db "select count(*) from tbl_game"` isn't 0 first. Don't copy
   `games_fav.db` or `games_scanf.db`; the launcher creates both at boot.
6. Leave `/sdcard/game1/*` empty.

**What `game1` is:** every boot the launcher copies `games.db` to `games_scanf.db`
and appends a row for each file under `/sdcard/game1/<system>/`, with
`timer = /sdcard/game1/<system>`. No tile ever matches that path, so from the code
those games are not listed under any category. Earlier versions of this README
recommended `game1`; that was wrong. Leave its folders empty (the launcher recreates
them at boot).

### `tools/make_blank_dbs.py` — empty databases

```sh
tools/make_blank_dbs.py OUTDIR      # OUTDIR/games.db, OUTDIR/games_fav.db; --force to overwrite
```

Same schema as stock, no rows. Not needed for setting up a card — the launcher
creates `games_fav.db` itself — and its `games.db` is **empty**: copied to a card,
every tile shows nothing.

### `tools/make_test_launcher.sh` — replace the launcher

```sh
tools/make_test_launcher.sh [-t lvui|game|retroarch|shell] [-m WxH] [-n] /Volumes/SDCARD
```

Writes the `/sdcard/test/` override. Logs each boot to the card, and falls back to the
stock launcher if the target dies within 15 s, so a failed experiment can't leave a
black screen with no way back in. Run `-t game` first to prove the hook fires.

`-m 1920x1080` forces the HDMI mode (see below) and logs the TV's mode list to
`test.log`.

### `tools/webster.py` — the encrypted blob

```sh
tools/webster.py params                                     # what a rootfs derives
tools/webster.py decrypt squash/etc/webster -o webb.sh
tools/webster.py crack   squash/etc/webster --model squash/usr/local/share/minigui/start_game.sh
```

`crack` recovers size, offset and key from scratch without `/proc/version`.

## HDMI mode

`S50ui` runs `/usr/bin/drm-hotplug.sh`, whose preference list is
`1280x720 1024x 1280x1024 800x600 1920x1080`. It writes the winner as a bare `WxH` to
`/tmp/drm_mode.cfg`, which MiniGUI and the vendor RetroArch both read, taking the
first TV mode of that size. 720p50 and 720p60 share a pixel clock, so the TV's EDID
order decides the refresh rate — hence 50 Hz on some sets.

`tools/make_test_launcher.sh -t game -m 1920x1080 CARD` overrides it without touching
the rootfs (the UI still draws at 720p and is scaled). Tried on one unit: 1080p came
up, with some flicker and no visible gain, since everything on screen is upscaled
anyway. Delete `/sdcard/test` to go back.


## Licence

The work in this repository is [MIT licensed](LICENSE) — `tools/`, `NOTES.md`
and `README.md`.

The MIT grant does **not** extend to the material that came off the device or from
the SJGAM listing, which is included for reference and remains its rights holders':

No reuse licence was established for any of those. Attribution does not grant
permission for redistribution.
