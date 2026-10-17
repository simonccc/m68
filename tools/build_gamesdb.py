#!/usr/bin/env python3
"""Build an SJGAM M68 games.db from a ROM tree.

The launcher loads titles with a bare `SELECT <x>_title FROM tbl_<x>` and indexes
the result positionally against tbl_game, so every title table must hold exactly
as many rows as tbl_game, in the same order. This script guarantees that.

Usage
-----
  # inspect what a tree would produce, change nothing
  build_gamesdb.py scan ROMDIR

  # build from scratch
  build_gamesdb.py build ROMDIR -o games.db

  # keep the stock 21520 titles and append a tree on top
  build_gamesdb.py build ROMDIR -o games.db --base stock-games.db

  # dump an existing db to a titles CSV, edit it, feed it back with --titles
  build_gamesdb.py titles games.db -o titles.csv

ROMDIR is laid out one directory per system, matching the names the firmware
knows:  ROMDIR/snes/Foo.zip -> timer '/sdcard/game/snes'.
"""

from __future__ import annotations

import argparse
import csv
import os
import sqlite3
import sys

# Where the card is mounted on the device. tbl_game.timer must use this prefix.
DEVICE_GAME_DIR = "/sdcard/game"

# Extensions scanf_game1() skips: artwork, saves, configs, preview video.
SKIP_EXT = {
    ".png", ".jpg", ".bmp", ".srm", ".state", ".fs", ".cfg", ".mp4", ".mkv", ".nv"
}

# game_type -> core, from start_game.sh. False = referenced but not shipped.
CORES = {
    0: ("fbalpha2012", True), 1: ("nestopia", True), 2: ("daphne", False),
    3: ("fbalpha2012_1", True), 4: ("mame2003", False), 5: ("genesisplusgx", True),
    6: ("snes9x", True), 7: ("mgba", True), 8: ("mupen64plus", False),
    9: ("pcsx_rearmed", True), 10: ("mednafen_pce_fast", True),
    11: ("mednafen_wswan", True), 12: ("desmume2015", False),
    13: ("genesis_plus_gx", True), 14: ("fbalpha", True), 15: ("stella", True),
    16: ("atari800", False), 17: ("prosystem", True), 18: ("mame2016", True),
    19: ("snes9x_racing", False), 20: ("fbalpha_other", True),
    21: ("stella_other", True), 22: ("atari800_other", False),
    23: ("prosystem_other", False), 24: ("mame2016_other", True),
    25: ("pcsx_rearmed_1 (25_ra.cfg)", True), 26: ("mame2003_other", False),
    27: ("pcsx_rearmed_1 (28_ra.cfg)", True), 28: ("pcsx_rearmed (28_ra.cfg)", True),
    29: ("pcsx_rearmed (29_ra.cfg)", True), 31: ("genesis_plus_gx", True),
    32: ("mednafen_ngp", True), 33: ("mednafen_pce_fast", True),
    34: ("genesis_plus_gx", True), 35: ("mednafen_wswan", True),
    36: ("genesis_plus_gx", True), 37: ("fmsx", False), 38: ("picodrive", False),
    39: ("pcsx_rearmed_chd", True), 40: ("stella_other", True),
    41: ("genesisplusgx", True), 42: ("a5200", True), 43: ("handy", True),
    44: ("mame2003_plus", True), 45: ("pokemini", True),
    46: ("mednafen_supergrafx", True), 66: ("n2626 (standalone)", True),
    88: ("PPSSPP", True),
}

# folder -> game_type. Corrected where scanf_game1()'s own inference is wrong;
# values marked FIXED differ from what the firmware would guess.
FOLDER_TYPE = {
    "cps": 0, "fbneo": 0, "game": 0, "cps1": 3, "cps2": 14,
    "fc": 1, "nesh": 1, "fds": 1,
    "md": 5, "genesis": 5, "megadrive": 5, "genh": 5, "segacd": 5, "gamegear": 5,
    "sfc": 6, "snes": 6,
    "gb": 7, "gbc": 7, "gba": 7, "gbah": 7,
    "n64": 66,              # FIXED: firmware guesses 8 (mupen64plus, not shipped)
    "ps1": 9, "psx": 9,     # FIXED: firmware guesses 43 (handy) for 'psx'
    "pce": 10, "pcengine": 10,
    "wsc": 35, "wonderswan": 35,
    "gg": 31, "sms": 34, "sg-1000": 36,
    "atari2600": 15, "atari5200": 42, "atari7800": 17, "atarilynx": 43,
    "ngp": 32, "ngpc": 32,
    "msx2": 37,
    "sega32x": 38,          # FIXED: firmware guesses 39 (pcsx chd)
    "mame": 44,
    "gameandwatch": 45, "pokemini": 45,
    "sgfx": 46,
    "psp": 88,
    "nds": 12, "dreamcast": 2, "naomi": 18, "cps3": 18, "Gun": 0,
}

# Per-folder extension overrides, for folders whose core depends on the file type.
EXT_TYPE = {
    ("ps1", ".chd"): 39, ("psx", ".chd"): 39,
    ("atari2600", ".a52"): 16, ("atari2600", ".a78"): 17,
}

TABLES = """
CREATE TABLE "tbl_path" ("path_id" TEXT,"path" TEXT);
CREATE TABLE "tbl_video" ("video_id" TEXT,"video" TEXT,"path_id" TEXT);
CREATE TABLE tbl_total(ID INTEGER PRIMARY KEY, total INTEGER);
CREATE TABLE tbl_ko (ko_id, ko_title);
CREATE TABLE tbl_zh (zh_id INTEGER, zh_title CHAR (50));
CREATE TABLE tbl_match (ID INTEGER, zh_match CHAR (50));
CREATE TABLE tbl_en (en_id INTEGER, en_title CHAR (50));
CREATE TABLE tbl_game (gameid INTEGER, game CHAR (50), suffix CHAR (4),
                       zh_id INTEGER, en_id INTEGER, ko_id INTEGER,
                       video_id INTEGER, class_type INTEGER, game_type INTEGER,
                       hard INTEGER, timer CHAR (50));
CREATE TABLE tbl_tw (tw_id INTEGER, tw_title CHAR (50));
"""


class Entry:
    """One game: a tbl_game row plus its four titles and its search key."""

    __slots__ = ("stem", "ext", "folder", "game_type", "class_type", "hard",
                 "en", "zh", "ko", "tw", "match")

    def __init__(self, stem, ext, folder, game_type, class_type=0, hard=0):
        self.stem = stem
        self.ext = ext
        self.folder = folder
        self.game_type = game_type
        self.class_type = class_type   # vestigial, but preserved from a base db
        self.hard = hard
        self.en = self.zh = self.ko = self.tw = stem
        self.match = stem

    @property
    def timer(self):
        return f"{DEVICE_GAME_DIR}/{self.folder}"


def classify(folder, ext):
    """Folder + extension -> game_type, or None if we have no mapping."""
    return EXT_TYPE.get((folder, ext.lower())) or FOLDER_TYPE.get(folder)


def scan_tree(romdir):
    """Walk ROMDIR/<system>/* and return (entries, skipped) in stable order."""
    entries, skipped = [], []
    for folder in sorted(os.listdir(romdir)):
        sub = os.path.join(romdir, folder)
        if not os.path.isdir(sub):
            continue
        game_type = classify(folder, "")
        for name in sorted(os.listdir(sub)):
            if not os.path.isfile(os.path.join(sub, name)):
                continue
            stem, ext = os.path.splitext(name)
            if not ext or ext.lower() in SKIP_EXT:
                continue
            gt = classify(folder, ext)
            if gt is None:
                skipped.append((folder, name, "unknown system folder"))
                continue
            if len(stem) > 50:
                skipped.append((folder, name, "name longer than 50 chars"))
                continue
            entries.append(Entry(stem, ext, folder, gt))
        if game_type is None and not any(e.folder == folder for e in entries):
            skipped.append((folder, "*", "unknown system folder"))
    return entries, skipped


def read_base(path):
    """Load an existing games.db into Entry objects, preserving row order."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT game, suffix, timer, game_type, class_type, hard"
        " FROM tbl_game ORDER BY rowid"
    ).fetchall()
    titles = {}
    for tbl, col in (("tbl_en", "en_title"), ("tbl_zh", "zh_title"),
                     ("tbl_ko", "ko_title"), ("tbl_tw", "tw_title")):
        titles[tbl] = [r[0] for r in con.execute(f"SELECT {col} FROM {tbl}")]
    match = [r[0] for r in con.execute("SELECT zh_match FROM tbl_match")]
    videos = con.execute("SELECT video_id, video FROM tbl_video").fetchall()
    vpath = con.execute("SELECT path FROM tbl_path LIMIT 1").fetchone()
    con.close()

    n = len(rows)
    for tbl, vals in titles.items():
        if len(vals) != n:
            print(f"warning: {path}: {tbl} has {len(vals)} rows, tbl_game has {n};"
                  " titles in the base db are already misaligned", file=sys.stderr)

    out = []
    for i, (game, suffix, timer, gt, ct, hard) in enumerate(rows):
        folder = (timer or "").rsplit("/", 1)[-1]
        e = Entry(game or "", suffix or "", folder, gt if gt is not None else 0,
                  ct if ct is not None else 0, hard if hard is not None else 0)
        for attr, tbl in (("en", "tbl_en"), ("zh", "tbl_zh"),
                          ("ko", "tbl_ko"), ("tw", "tbl_tw")):
            vals = titles[tbl]
            if i < len(vals) and vals[i] is not None:
                setattr(e, attr, vals[i])
        if i < len(match) and match[i] is not None:
            e.match = match[i]
        out.append(e)
    return out, videos, (vpath[0] if vpath else "/sdcard/roms/")


def apply_titles(entries, csv_path):
    """Override titles from a CSV keyed on folder+game (see the `titles` command)."""
    by_key = {}
    for e in entries:
        by_key[(e.folder, e.stem)] = e
    applied = unmatched = 0
    with open(csv_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            e = by_key.get((row["folder"], row["game"]))
            if e is None:
                unmatched += 1
                continue
            for col in ("en", "zh", "ko", "tw", "match"):
                if row.get(col):
                    setattr(e, col, row[col])
            if row.get("game_type"):
                e.game_type = int(row["game_type"])
            applied += 1
    return applied, unmatched


def write_db(path, entries, video_rows=None, video_path="/sdcard/roms/"):
    if os.path.exists(path):
        os.unlink(path)
    con = sqlite3.connect(path)
    con.executescript(TABLES)

    game, en, zh, ko, tw, match = [], [], [], [], [], []
    for i, e in enumerate(entries, start=1):
        game.append((i, e.stem, e.ext, i, i, i, i, e.class_type, e.game_type,
                     e.hard, e.timer))
        en.append((i, e.en))
        zh.append((i, e.zh))
        ko.append((i, e.ko))
        tw.append((i, e.tw))
        match.append((i, e.match))

    con.executemany("INSERT INTO tbl_game VALUES (?,?,?,?,?,?,?,?,?,?,?)", game)
    con.executemany("INSERT INTO tbl_en VALUES (?,?)", en)
    con.executemany("INSERT INTO tbl_zh VALUES (?,?)", zh)
    con.executemany("INSERT INTO tbl_ko VALUES (?,?)", ko)
    con.executemany("INSERT INTO tbl_tw VALUES (?,?)", tw)
    con.executemany("INSERT INTO tbl_match VALUES (?,?)", match)
    con.execute("INSERT INTO tbl_path VALUES ('1', ?)", (video_path,))
    con.executemany("INSERT INTO tbl_video VALUES (?,?,'1')", video_rows or [])
    con.execute("INSERT INTO tbl_total VALUES (?,?)", (len(entries), len(entries)))
    con.commit()

    # The invariant the launcher depends on. Never ship a db that fails this.
    n = con.execute("SELECT count(*) FROM tbl_game").fetchone()[0]
    for tbl in ("tbl_en", "tbl_zh", "tbl_ko", "tbl_tw", "tbl_match"):
        m = con.execute(f"SELECT count(*) FROM {tbl}").fetchone()[0]
        assert m == n, f"{tbl} has {m} rows, tbl_game has {n}"
    con.close()
    return n


def summarise(entries):
    by_folder = {}
    for e in entries:
        key = (e.folder, e.game_type)
        by_folder[key] = by_folder.get(key, 0) + 1
    print(f"{'folder':<16} {'type':>4}  {'n':>6}  core")
    print("-" * 64)
    for (folder, gt), n in sorted(by_folder.items()):
        core, shipped = CORES.get(gt, ("?unknown?", False))
        flag = "" if shipped else "   <-- CORE NOT SHIPPED"
        print(f"{folder:<16} {gt:>4}  {n:>6}  {core}{flag}")
    print("-" * 64)
    print(f"{'TOTAL':<16} {'':>4}  {len(entries):>6}")

    folders = {e.folder for e in entries}
    if len(folders) > 50:
        print(f"\nwarning: {len(folders)} categories; the launcher caps the menu at 50",
              file=sys.stderr)


def cmd_scan(args):
    entries, skipped = scan_tree(args.romdir)
    summarise(entries)
    if skipped:
        print(f"\nskipped {len(skipped)}:")
        for folder, name, why in skipped[:40]:
            print(f"  {folder}/{name}: {why}")
        if len(skipped) > 40:
            print(f"  ... and {len(skipped) - 40} more")


def cmd_build(args):
    if args.base:
        entries, videos, vpath = read_base(args.base)
    else:
        entries, videos, vpath = [], [], "/sdcard/roms/"
    base_n = len(entries)
    scanned, skipped = scan_tree(args.romdir)
    entries += scanned

    if args.titles:
        applied, unmatched = apply_titles(entries, args.titles)
        print(f"titles: {applied} applied, {unmatched} unmatched rows in CSV")

    n = write_db(args.output, entries, videos, vpath)
    if base_n:
        print(f"{args.output}: {n} games ({base_n} from base + {len(scanned)} scanned)")
    else:
        print(f"{args.output}: {n} games")
    if skipped:
        print(f"skipped {len(skipped)} files (run `scan` for the list)")
    summarise(entries)


def cmd_titles(args):
    entries, _videos, _vpath = read_base(args.db)
    with open(args.output, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["folder", "game", "game_type", "en", "zh", "ko", "tw", "match"])
        for e in entries:
            w.writerow([e.folder, e.stem, e.game_type, e.en, e.zh, e.ko, e.tw, e.match])
    print(f"{args.output}: {len(entries)} rows")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("scan", help="report what a ROM tree would produce")
    p.add_argument("romdir")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("build", help="write a games.db")
    p.add_argument("romdir")
    p.add_argument("-o", "--output", default="games.db")
    p.add_argument("--base", help="existing games.db to keep and append to")
    p.add_argument("--titles", help="CSV of title overrides")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("titles", help="dump a games.db to an editable titles CSV")
    p.add_argument("db")
    p.add_argument("-o", "--output", default="titles.csv")
    p.set_defaults(func=cmd_titles)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
