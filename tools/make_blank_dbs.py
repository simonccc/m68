#!/usr/bin/env python3
"""Write an empty games.db and games_fav.db for the SJGAM M68.

games.db gets the stock nine-table schema with no games (the same output as
`build_gamesdb.py build` on an empty tree). games_fav.db gets the single
Users table the launcher keeps favourites in.

Usage
-----
  make_blank_dbs.py OUTDIR            # writes OUTDIR/games.db, OUTDIR/games_fav.db
  make_blank_dbs.py OUTDIR --force    # overwrite existing files
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_gamesdb import write_db  # noqa: E402

FAV_TABLES = "CREATE TABLE Users (ID INTEGER PRIMARY KEY, Name TEXT NOT NULL);"


def write_fav_db(path):
    if os.path.exists(path):
        os.unlink(path)
    con = sqlite3.connect(path)
    con.executescript(FAV_TABLES)
    con.commit()
    con.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir")
    ap.add_argument("-f", "--force", action="store_true",
                    help="overwrite existing databases")
    args = ap.parse_args()

    games = os.path.join(args.outdir, "games.db")
    fav = os.path.join(args.outdir, "games_fav.db")
    if not args.force:
        existing = [p for p in (games, fav) if os.path.exists(p)]
        if existing:
            sys.exit(f"refusing to overwrite {', '.join(existing)} (use --force)")

    os.makedirs(args.outdir, exist_ok=True)
    write_db(games, [])
    write_fav_db(fav)
    print(f"{games}: 0 games")
    print(f"{fav}: 0 favourites")


if __name__ == "__main__":
    main()
