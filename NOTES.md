# SJGAM M68 — firmware notes

Device string: `/etc/version` → `M68 / V1.0.0 / 2026-01-22 14:50`

## Platform

Not EmuELEC/Amlogic (the vendor page for the M66 is misleading). This is:

| | |
|---|---|
| SoC | Rockchip, Cortex-A7 32-bit (`/sys/bus/nvmem/devices/rockchip-efuse0`) |
| Userland | Buildroot 2018.02-rc3, busybox init |
| Binary ABI | ELF 32-bit LSB ARM EABI5 armhf, `/lib/ld-linux-armhf.so.3` |
| UI toolkit | **MiniGUI** (not EmulationStation — those dirs are empty mountpoints) |
| Launcher | `/usr/bin/game` (135 KB, stripped) |
| Emulator | RetroArch 1.x + libretro cores in `/usr/local/share/minigui/retro_lib/` |
| Display | DRM/KMS, `card0-HDMI-A-1`; also DSI/LVDS paths for handheld siblings |

Partition 4 = squashfs rootfs (read-only). `/sdcard` is a separate partition
mounted at boot; everything user-facing lives there.

## Boot path

`inittab` → `/etc/init.d/rcS` → `S50ui start`:

```sh
export XDG_CONFIG_HOME=/sdcard/
mount /dev/block/by-name/userdata /data
if [ -e "/sdcard/test" ]; then
        export LD_LIBRARY_PATH=LD_LIBRARY_PATH:/sdcard/test/lib
        export MG_CFG_PATH=/sdcard/test
        /sdcard/test/test.sh &            # ← dev escape hatch
else
        export MG_CFG_PATH=/usr/local/share/minigui/hdmicfg
        /usr/bin/game &
fi
swapon /sdcard/data/data4 &
```

**`/sdcard/test/test.sh` is the supported override.** Create that directory on the
SD card and the stock launcher never runs — you get to launch anything
(your own MiniGUI build, EmulationStation, a shell over the serial console,
RetroArch directly). It needs no rootfs modification, and deleting the folder
restores stock behaviour. This is the safest way to experiment.

Serial console is enabled: `console::respawn:/sbin/getty -L console 0 vt100`.
`adbd` is also present in `/usr/bin`.

## Launching a game

`game` shells out to `/usr/local/share/minigui/start_game.sh <game_type> "<appendcfg>" "<rompath>"`.

That script maps `game_type` → core:

```
$EMU_RA -c $GAME_CFG --appendconfig "$2" -L /usr/local/share/minigui/retro_lib/$GAME_LIB "$3"
```

Special cases: `88` → PPSSPP (`ppsspp/PPSSPPSDL`), `77` → nds (declared, no binary
shipped), `66` → `n2626` standalone, `99` → `/sdcard/gmtest/test.so` + `/sdcard/gmtest/test.cfg`
(second dev hook — you can side-load a core from the SD card).

**11 of the cores referenced by `start_game.sh` are not present in `retro_lib/`:**

| Missing `.so` | game_type |
|---|---|
| `daphne_libretro.so` | 2 |
| `mame2003_libretro.so` | 4 |
| `mupen64plus_libretro.so` | 8 |
| `desmume2015_libretro.so` | 12 |
| `atari800_libretro.so` | 16 |
| `snes9x_libretro_racing.so` | 19 |
| `atari800_libretro_other.so` | 22 |
| `prosystem_libretro_other.so` | 23 |
| `mame2003_libretro_other.so` | 26 |
| `fmsx_libretro.so` | 37 |
| `picodrive_libretro.so` | 38 |

Setting a `game_type` whose `.so` is absent gives a black screen, not an error.
(`pcsx_rearmed_libretro2.so` ships but no case references it.)

**N64 is the trap.** `game_type 8` → `mupen64plus_libretro.so`, which is missing.
The stock DB's 24 N64 titles all use **`game_type 66`**, the standalone `n2626`
emulator with its own config — and `scanf_game1()` classifies the `n64` folder as
**8**. So N64 ROMs added via the auto-scan path will not boot. Use 66.

## Menu structure

### Categories (top level)

`game` builds the category row at startup by scanning the filesystem, **not** the DB:

1. Four priority slots, in fixed order, included only if the directory exists:
   `psp`, `n64`, `ps1`, `cps`
2. Then `readdir("/sdcard/game")` in directory order — every entry with
   `d_type == DT_DIR`, excluding `.`, `..` and the four above.
3. Hard cap: **50 categories.**

Paging: 4 tiles on page 1, 8 per page after → `pages = (n-4)/8 + 2`.

Icon per category: `/usr/local/share/minigui/res/images/class/<dirname>.png`.
A missing icon logs `"<path> is err"` and renders blank; it does not crash.

**43 icons ship, so 43 category names look native out of the box:**

```
atari2600 atari5200 atari7800 atarilynx cps cps1 cps2 cps3 dreamcast fbneo
fc fds gameandwatch gb gba gbah gbc genesis genh gg Gun mame md msx2 n64
naomi nds nesh ngp ngpc pce pokemini ps1 psp sega32x segacd sfc sg-1000
sgfx sms snes wonderswan wsc
```

`cps3`, `dreamcast`, `naomi`, `nds`, `Gun`, `fds`, `gbah`, `nesh`, `wonderswan`
have artwork but no corresponding core — the tile appears and games in it fail to launch.

So: **to expose more of the menu, create directories under `/sdcard/game/`.**
No binary patching required. The icon set is the limit on what looks stock; drop
your own PNGs into the squashfs `class/` dir (rootfs rebuild) for anything else.

### Settings menu

Four rows only (`hdmi_Setting-n0..n3`), strings from
`res/stringxbl/<LANG>-UTF8.bin`: key prompt sound, backlight, restore defaults,
language. 24 languages ship. There is no hidden deeper settings tree in this build —
`res/string/` (the fuller string set used by sibling models) is **empty** here.

### Dormant per-game features

`game` issues queries for columns that **do not exist** in the shipped schema:

```sql
SELECT hard, lives, vert, cointime, playerscoin, hidesavestat, delfspath
  FROM tbl_game WHERE fav = ?
UPDATE tbl_game SET fav = ?, hard = ?, lives = ? WHERE gameid = ?
```

Only `hard` exists. The others (`fav`, `lives`, `vert`, `cointime`, `playerscoin`,
`hidesavestat`, `delfspath`) are absent, so those `sqlite3_get_table` calls fail and
the features stay dark. Adding the columns is a one-line `ALTER TABLE` each and is
the most promising lead for unlocking arcade-style per-game options
(difficulty / lives / vertical rotate / coin timer / hide save-state).
Untested — needs a device to confirm the UI actually surfaces them.

## Databases — `/sdcard/game/`

Three SQLite files. Schema (identical for `games.db` and `games_scanf.db`):

```sql
CREATE TABLE tbl_game  (gameid INTEGER, game CHAR(50), suffix CHAR(4),
                        zh_id INTEGER, en_id INTEGER, ko_id INTEGER,
                        video_id INTEGER, class_type INTEGER,
                        game_type INTEGER, hard INTEGER, timer CHAR(50));
CREATE TABLE tbl_en    (en_id INTEGER, en_title CHAR(50));
CREATE TABLE tbl_zh    (zh_id INTEGER, zh_title CHAR(50));
CREATE TABLE tbl_ko    (ko_id,         ko_title);
CREATE TABLE tbl_tw    (tw_id INTEGER, tw_title CHAR(50));
CREATE TABLE tbl_match (ID INTEGER,    zh_match CHAR(50));
CREATE TABLE tbl_video (video_id TEXT, video TEXT, path_id TEXT);
CREATE TABLE tbl_path  (path_id TEXT,  path TEXT);
CREATE TABLE tbl_total (ID INTEGER PRIMARY KEY, total INTEGER);
```

`games_fav.db` is separate and trivial: `Users(ID INTEGER PRIMARY KEY, Name TEXT)`.
Deleting it resets favourites (the UI does exactly that: `rm -rf /sdcard/game/games_fav.db`).

### Column meanings (from disassembly, not guesswork)

| Column | Meaning |
|---|---|
| `gameid` | 1-based, equals rowid |
| `game` | ROM filename **without** extension |
| `suffix` | extension **with** the dot, e.g. `.zip` |
| `timer` | **the ROM's directory** — e.g. `/sdcard/game/snes`. Badly named; it is the join key between filesystem and DB |
| `game_type` | the `start_game.sh` case number → selects the libretro core |
| `class_type` | legacy/vestigial. For `game_type >= 18` it mirrors `game_type`; below that it is inconsistent. Not used for menu grouping |
| `hard` | difficulty; read but never usefully written in this build |
| `*_id`, `video_id` | all equal `gameid` in the stock DB |

### The thing that will bite you

Titles are loaded with **no `WHERE` and no `ORDER BY`**:

```sql
SELECT en_title FROM tbl_en          -- and tbl_zh / tbl_ko / tbl_tw
```

into a flat array, and indexed **positionally** against the `tbl_game` array.
The `en_id` / `zh_id` / `ko_id` / `tw_id` columns are **never used in a join.**

> Every title table must have exactly the same number of rows as `tbl_game`,
> in the same rowid order. One missing row shifts every title after it.

Language → table: `0`=en, `1`=tw(**holds Korean**), `4`=ko(**holds Simplified Chinese**),
default=zh. `tbl_tw` and `tbl_ko` are swapped relative to their names in the stock DB.
Non-CJK languages all fall back to `tbl_en`.

`tbl_match` holds pinyin-initial search keys (`拳皇97` → `qh97QH97`) and is searched with
`LIKE '%<q>%'`; `tbl_en` is searched the same way. Keep it row-aligned too.

`tbl_video` / `tbl_path` drive preview videos (`<path><video>`); only the first 1099
gameids have entries, the rest have dangling `video_id`. Harmless.

`tbl_total` says 1329 while `tbl_game` holds 21520 rows — stale, and ignored by the UI.

### Category counts come from the DB, not the disk

```sql
SELECT rowid FROM tbl_game WHERE timer LIKE '<pattern>'
```

so a category tile shows a count even when the ROM files are gone. The file is only
touched at launch, which then logs `Game file not found: %s`. Conversely, a ROM on
disk with no DB row is invisible.

## Recreating the DB when you add content

**You mostly don't have to.** `game` regenerates it on every boot. Startup sequence
(`loadres()` at `0x16cd0`, run from a worker thread at `0x1bae8`):

```c
load_games ("/sdcard/game/games.db", lang);
load_titles("/sdcard/game/games.db", lang);
init_fav   ("/sdcard/game/games_fav.db");
load_fav   ("/sdcard/game/games_fav.db");
system("cp -a /sdcard/game/games.db /sdcard/game/games_scanf.db");   // ← every boot
```

then immediately `scanf_game1()` at `0x17760`:

```c
mkdir("/sdcard/game1");
for (i = 0; i <= 26; i++) {                 // 27 fixed subdirs
    mkdir("/sdcard/game1/<subdir[i]>");
    for (each dirent) {
        if (no '.' in name) continue;
        if (ext in {.png .jpg .bmp .srm .state .fs .cfg .mp4 .mkv .nv}) continue;
        split at last '.' -> base, suffix;
        type = classify(dirpath, suffix, base);
        INSERT INTO tbl_game(gameid, game, suffix, zh_id, game_type, timer)
             VALUES (n, base, suffix, 0, type, dirpath);     // into games_scanf.db
        INSERT INTO tbl_zh / tbl_tw / tbl_ko / tbl_en  (n, base);
    }
}
// then reload everything from games_scanf.db
```

The 27 auto-created subdirs:

```
atari2600 atari5200 atari7800 cps cps1 cps2 fbneo fc gb gba gbc genesis gg
mame md n64 ngp ngpc pce ps1 psp sfc sg-1000 sgfx sms snes wsc
```

### So, the easy path

Drop ROMs into **`/sdcard/game1/<system>/`** (the folder is created for you on first
boot). On the next boot the launcher rebuilds `games_scanf.db` as
`games.db + your files` and uses that. `games.db` is never modified. To undo, delete
the files — `games_scanf.db` is overwritten from `games.db` every boot anyway.

Caveats of the easy path:
- The title shown is the bare filename. No Chinese/Korean titles, no search keys.
- `/sdcard/game1` is outside the 27-folder list for anything else — e.g. `atarilynx`,
  `gameandwatch`, `msx2`, `pokemini`, `sega32x`, `psx`, `pcengine`, `gamegear`,
  `megadrive`, `genh`, `segacd` are handled by `classify()` but never created or
  scanned. Create them by hand and they will be scanned.
- `game_type` is inferred, and the inference has bugs: `psx` → 43 (Atari Lynx!),
  `sega32x` → 39 (pcsx chd), `pokemini` → 45 (game & watch), `gb`/`gbc`/`gba` all → 7.

### Folder → game_type, as the firmware actually classifies

| Folder | Extension | → game_type | Core |
|---|---|---|---|
| `cps`, `fbneo`, `game` | `.zip` + name contains `olds` | 14 | fbalpha |
| `cps`, `fbneo`, `game` | `.zip` + name contains `kov*` | 3 | fbalpha2012_1 |
| `cps`, `fbneo`, `game` | `.zip` (otherwise) | 0 | fbalpha2012 |
| `md` | `.smd .gg .bin .gen` | 5 | genesisplusgx |
| `fc` | `.nes .fds` | 1 | nestopia |
| `sfc`, `snes` | `.smc .sfc` | 6 | snes9x |
| `gb`, `gbc`, `gba` | `.gb .gbc .gba` | 7 | mgba |
| `n64` | `.n64 .v64 .z64` | 8 | mupen64plus *(core missing)* |
| `ps1` | `.bin .ccd .img .sub .pbp .iso` | 9 | pcsx_rearmed |
| `pce`, `pcengine` | `.pce` | 10 | mednafen_pce_fast |
| — | `.wsc` | 11 | mednafen_wswan |
| — | `.nds` | 12 | desmume2015 *(missing)* |
| `gg`, `sms`, `sg-1000` | `.gg .sms` | 13 | genesis_plus_gx |
| `atari` | `.a26 .bin` | 15 | stella |
| `atari` | `.a52` | 16 | atari800 *(missing)* |
| `atari` | `.a78` | 17 | prosystem |
| `ngp`, `ngpc` | any | 32 | mednafen_ngp |
| `msx2` | any | 37 | fmsx *(missing)* |
| `sega32x` | `.chd` | 39 | pcsx_rearmed_chd ⚠ wrong |
| `atari5200` | any | 42 | a5200 |
| `atarilynx`, `psx` | any | 43 | handy ⚠ `psx` is wrong |
| `mame` | any | 44 | mame2003_plus |
| `gameandwatch`, `pokemini` | any | 45 | gw / pokemini ⚠ collision |
| `sgfx` | any | 46 | mednafen_supergrafx |
| `gamegear`, `genesis`, `genh`, `megadrive`, `segacd` | any | 5 | genesisplusgx |
| `psp` | any | 88 | PPSSPP |

### The controlled path

When you want real titles, correct cores, search keys and preview videos, build
`games.db` yourself — see `tools/build_gamesdb.py`. Put the result at
`/sdcard/game/games.db` and leave `/sdcard/game1` empty.

## Loose ends

- `/proc/secic` — challenge/response against a security chip: writes 32 bytes,
  sleeps 15 ms, reads 32 back. Returns 0 if the node is absent, so it is probably
  not a hard gate, but check before rebuilding the rootfs.
- A custom base64 alphabet
  `abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ8923456701+/` sits in
  `.rodata`, unreferenced by anything found so far.
- `/usr/bin/lvui` (10 MB, LVGL) is a second, much larger UI that `S50ui` never
  launches. Unexamined — possibly the richer menu from a sibling model.
- `/sdcard/w20c/minigui/retroarch_hdmi.cfg` is written by the button-remap screen;
  that path does not exist in this firmware's layout.

## `site/`

A standalone, offline HTML guide to the M66/M68 aimed at buyers rather than at
this teardown. Everything about the M66 in it is transcribed from the
manufacturer listing; the "Inside the M68" section is the only first-hand part
and is derived from this repository.

The useful conclusion it records: **SJGAM's own site has no M68.** The page the
device is sold under describes the M66 — Amlogic-class, Mali-G52, EmuELEC 4.3 —
and the firmware here is none of those things. The two names are not two
revisions of one product.

## Overriding the launcher — `tools/make_test_launcher.sh`

Writes `/sdcard/test/` onto a mounted card so `S50ui` runs our script instead of
`/usr/bin/game`. Nothing in the read-only rootfs changes; deleting the directory
(or creating `/sdcard/test/DISABLE`) restores stock.

```
make_test_launcher.sh [-t lvui|game|retroarch|shell] [-n] /Volumes/SDCARD
```

The generated `test.sh` logs every boot to `/sdcard/test/test.log` (the only way
to see anything without a serial cable), and a watchdog hands back to
`/usr/bin/game` if the chosen target dies within 15s, so a failed experiment
cannot leave a black screen with no way in. `-n` disables that.

It also undoes two things `S50ui` sets wrongly for us:

- `LD_LIBRARY_PATH=LD_LIBRARY_PATH:/sdcard/test/lib` — missing the `$`, so the
  stock value is replaced by a literal string
- `MG_CFG_PATH=/sdcard/test` — no `MiniGUI.cfg` lives there, so any MiniGUI app
  started from `test.sh` must have it reset to `/usr/local/share/minigui/hdmicfg`

### On `lvui`

`/usr/bin/lvui` is a 10 MB LVGL (v7-era) binary that nothing in the firmware ever
launches. It links `libsqlite3 libasound libstdc++` — **no MiniGUI** — and draws to
`/dev/fb0` directly rather than through DRM/KMS like `game` does.

It is a leftover from a sibling handheld, not a hidden menu for this box:

- it reads `/proc/ov7251` (an OmniVision camera sensor the M68 does not have)
- its resources live in `/sdcard/minigui/res/...` and
  `/usr/local/share/lvgl/{picture,game,music,video}/` — of which this rootfs ships
  exactly one file, `picture/nosdbg.png`
- it has music, video, photo and camera apps alongside the game launcher
  (`/sdcard/music`, `/sdcard/video`, `/sdcard/pic`, `/sdcard/historical`,
  `/sdcard/collection`, `/data/qrcode.bmp`)
- it looks for `/sdcard/database.sqlite3` and `/sdcard/games.db` as well as the
  familiar `/sdcard/game/games.db`

So expect it to come up blank. The `lvui` target stages
`/usr/local/share/minigui/res` to `/sdcard/minigui/res` (where it looks) before
starting, which is the one piece we can supply; the LVGL artwork is simply absent
and would have to come from a sibling model's firmware.

## `/etc/webster` — decrypted

A 4986-byte encrypted blob. `game` decrypts it to `/tmp/webb.sh`, `chmod +x`'s it
and runs `/tmp/webb.sh <type> "<appendcfg>" "<rom>" "<arg4>"` — an alternative to
`start_game.sh`. `tools/webster.py` does the same offline; the plaintext is
committed as `webster-decrypted.sh`.

**It is an older copy of `start_game.sh` that loads its configs and cores from
the SD card instead of the rootfs** (`GAME_CFG=//sdcard/minigui/gbx66.cfg`,
`-L //sdcard/minigui/retro_lib/$GAME_LIB`). It stops at `game_type 36`, so it
predates the `fmsx`/`picodrive`/`a5200`/`handy`/`pokemini`/`supergrafx` entries
(37–46). Note the doubled slash: it expects `XDG_CONFIG_HOME=/sdcard` to be
prefixed. Nothing else in the firmware references `/sdcard/minigui/retro_lib`.

### The cipher

Keyed off three things that are all meant to be untouched on a genuine unit:

```
sum    = sum of every byte of the first two lines of /etc/version
a-b-c/d = the third line, parsed as "%d-%d-%d/%d"   (date / hour)
klen   = (sum % 64) + d
size   = klen + 512
offset = (b*c*d + a) % (len(/etc/init.d/S50ui) - klen - 512)
key    = the text between the first '(' and the next ')' in /proc/version

block[j] = S50ui[offset + j] ^ key[j % len(key)]        for j < size
plain[i] = ((cipher[i] - klen) & 0xff) ^ block[i % size]
```

So the keystream is **a window of the S50ui shell script itself**, XORed with the
kernel builder's `user@host`. Editing `S50ui`, editing `/etc/version`, or booting
a kernel built elsewhere all silently corrupt the output. That is the point — it
is a tamper check, not a secret.

It is also why the `/sdcard/test` override in `tools/make_test_launcher.sh` is the
safe way in: it changes nothing that this derivation reads.

### Recovered parameters

| | |
|---|---|
| size | 582 |
| subtracted byte (`klen`) | 70 |
| S50ui offset | 2215 |
| `/proc/version` key | `Percival@dell-build-sz-35` (25 bytes) |

Re-encrypting the decrypted script with these reproduces `/etc/webster` byte for
byte, and the recovered keystream repeats with a clean period of 25 across all
582 bytes — which also proves the `S50ui` in this rootfs is byte-identical to the
one on the vendor's build machine.

### …but this firmware cannot decrypt it

The shipped `/etc/version` is `M68\nV1.0.0\n2026-01-22/14:50\n`: sum 530,
`sum % 64` = 18, `d` = 14. That gives `klen` 32, `size` 544, `offset` 11 — not the
582/2215 the blob actually needs. `tools/webster.py params` prints the mismatch.

`klen = 70` needs `(sum % 64) + d == 70`, so the blob was built against a
different `/etc/version` (a different model string, version string or build
timestamp). **`/etc/webster` is stale**: on this unit it would decrypt to noise,
get `chmod +x`'d, and fail to run.

### Dead code anyway

Three functions are involved and **none of them is reachable** — no `bl` targets
them and their addresses appear nowhere as data:

| Address | What it does |
|---|---|
| `0x2a898` | the decryption above, writes `/tmp/webb.sh` |
| `0x2aca0` | calls it, then `system("/tmp/webb.sh %d \"%s\" \"%s\" \"%s\"")` |
| `0x2abcc` | the eFuse check below |

The live launcher path is `enterGame` at `0x18d40`, which calls
`/usr/local/share/minigui/start_game.sh` with three arguments.

### The eFuse check (`0x2abcc`, also dead)

```c
fd = open("/sys/bus/nvmem/devices/rockchip-efuse0/nvmem", O_RDONLY);
if (fd < 0)                 system("poweroff");
if (lseek(fd, 7, SEEK_SET) < 0) system("poweroff");
read(fd, buf, 2);
if (buf[0] != 'C' && buf[1] != 'X') system("poweroff");
```

Two bytes at offset 7 of the Rockchip eFuse must contain `'C'` or `'X'` — note it
is an OR, and `system("poweroff")` does not abort, so control falls through
either way. An anti-clone measure that was wired up and then disconnected.
