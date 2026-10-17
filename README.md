# SJGAM M68 — firmware teardown

Notes and tooling from reading the SD card of an **SJGAM M68** retro TV game stick
(build `M68 V1.0.0`, 22 January 2026).

<img src="site/assets/product-2.jpg" alt="The SJGAM M68 game stick with its red and blue wireless controllers" width="520">

📖 **Write-up: [simonccc.github.io/m68](https://simonccc.github.io/m68/)** — the same
material as a readable page.

---

## The short version

The device is sold under SJGAM's **M66** product page, which specifies an
Amlogic-class SoC with Mali-G52 graphics running **EmuELEC 4.3**. The card contains
none of that. SJGAM's site lists no M68 at all.

| | Listed (M66) | Actually on the card (M68) |
|---|---|---|
| CPU | Amlogic-class, Mali-G52 MC2 | **Rockchip, 32-bit ARM Cortex-A7** |
| OS | EmuELEC 4.3 | **Buildroot 2018.02-rc3**, BusyBox init |
| Interface | (EmulationStation) | **MiniGUI**, `/usr/bin/game` |
| Emulation | "30+ emulators" | RetroArch, **26 of 37** referenced cores present |

The `emuelec/` and `emulationstation/` directories in the root filesystem are empty
mount points.

Other findings:

- **The menu is a directory listing.** Categories come from `readdir("/sdcard/game")`,
  capped at 50. `mkdir` is the whole procedure for adding a system.
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
games.db, games_scanf.db      the shipped SQLite databases (21,520 rows)
games_fav.db                  favourites
tools/                        see below
site/                         the write-up, deployed to GitHub Pages
squash/                       extracted root filesystem (gitignored — ~460 MB)
```

`squash/` is not committed. Extract partition 4 of the card into it; the tools expect
it at that path (or pass `--root`).

## Tools

### `tools/build_gamesdb.py` — build or extend `games.db`

```sh
tools/build_gamesdb.py scan   ROMDIR                        # dry run, flags missing cores
tools/build_gamesdb.py build  ROMDIR -o games.db --base games.db
tools/build_gamesdb.py titles games.db -o titles.csv        # edit, feed back with --titles
```

`ROMDIR` holds one directory per system (`ROMDIR/snes/Foo.zip`). Rebuilding with
`--base` reproduces all 21,520 stock rows byte-identically before appending.

> [!WARNING]
> The launcher loads titles with a bare `SELECT en_title FROM tbl_en` — no `WHERE`,
> no `ORDER BY` — and indexes the result **positionally** against `tbl_game`. The
> `en_id`/`zh_id`/`ko_id`/`tw_id` columns are never joined on. Every title table must
> have the same row count as `tbl_game`, in the same order, or every title after the
> gap shifts onto the wrong game. The script asserts this before writing.

You often don't need this at all: drop ROMs into `/sdcard/game1/<system>/` and the
firmware rebuilds `games_scanf.db` from `games.db` plus your files on every boot. The
catch is bare filenames for titles, and a core-inference bug that sends N64 ROMs to a
core that isn't on the card — use `game_type 66`, not 8.

### `tools/make_test_launcher.sh` — replace the launcher

```sh
tools/make_test_launcher.sh [-t lvui|game|retroarch|shell] [-n] /Volumes/SDCARD
```

Writes the `/sdcard/test/` override. Logs each boot to the card, and falls back to the
stock launcher if the target dies within 15 s, so a failed experiment can't leave a
black screen with no way back in. Run `-t game` first to prove the hook fires.

### `tools/webster.py` — the encrypted blob

```sh
tools/webster.py params                                     # what a rootfs derives
tools/webster.py decrypt squash/etc/webster -o webb.sh
tools/webster.py crack   squash/etc/webster --model squash/usr/local/share/minigui/start_game.sh
```

`crack` recovers size, offset and key from scratch without `/proc/version`.

## Scope

One unit, one firmware build. Everything here was read from that card or disassembled
from its launcher binary; any M66 specification and the product photographs are
manufacturer-published and not independently verified. Other M68 batches may differ —
corrections welcome.

Independent research, not affiliated with or endorsed by SJGAM. Product images and
trademarks belong to their owners; no reuse licence was established. No ROMs,
copyrighted game data or firmware images are distributed here.
