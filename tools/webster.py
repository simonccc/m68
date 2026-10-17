#!/usr/bin/env python3
"""Decrypt, re-encrypt and analyse /etc/webster from the SJGAM M68 firmware.

`game` turns /etc/webster into /tmp/webb.sh, chmod +x's it and runs it as an
alternative to start_game.sh. The cipher keys itself off three things that are
all supposed to be untouched on a genuine unit:

    /etc/version          -> keystream length and the offset into S50ui
    /etc/init.d/S50ui     -> the raw keystream block
    /proc/version         -> the builder's user@host, used as a repeating XOR

so editing S50ui, /etc/version or reflashing a different kernel all break it.

Derivation, reproducing game's own code:

    skip the first two lines of /etc/version, summing every byte (sum)
    parse the third line as "%d-%d-%d/%d"                     -> a, b, c, d
    klen   = (sum % 64) + d
    size   = klen + 512
    offset = (b*c*d + a) % (len(S50ui) - klen - 512)
    key    = text between the first '(' and the next ')' in /proc/version

    block[j] = S50ui[offset + j] ^ key[j % len(key)]          for j < size
    plain[i] = ((cipher[i] - klen) & 0xff) ^ block[i % size]

Commands:
    decrypt  FILE   write the plaintext (params derived, or given explicitly)
    encrypt  FILE   inverse, for putting a modified script back
    params          print what a given rootfs derives
    crack    FILE   recover size/offset/key with no /proc/version, given a
                    similar plaintext to score against
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from collections import Counter
from pathlib import Path

# Recovered for the shipped M68 V1.0.0 blob. The firmware's own derivation does
# NOT produce these from this rootfs -- see `crack` and the notes in NOTES.md.
SHIPPED = dict(size=582, offset=2215, sub=70, key=b"Percival@dell-build-sz-35")

PRINTABLE = set(range(32, 127)) | {9, 10, 13}


def derive(version: bytes, s50ui_len: int):
    """Reproduce game's parameter derivation from /etc/version."""
    p = nl = total = 0
    while p < len(version) and version[p] != 0 and nl <= 1:
        if version[p] == 0x0A:
            nl += 1
        total += version[p]
        p += 1
    m = re.match(rb"(\d+)-(\d+)-(\d+)/(\d+)", version[p:])
    if not m:
        raise ValueError("third line of /etc/version is not %d-%d-%d/%d")
    a, b, c, d = (int(x) for x in m.groups())
    klen = (total % 64) + d
    size = klen + 512
    denom = s50ui_len - klen - 512
    if denom <= 0:
        raise ValueError(f"S50ui too short ({s50ui_len}) for keystream {size}")
    return dict(sum=total, a=a, b=b, c=c, d=d, klen=klen, size=size,
                offset=(b * c * d + a) % denom, denom=denom)


def keyblock(s50ui: bytes, offset: int, size: int, key: bytes) -> bytes:
    if offset + size > len(s50ui):
        raise ValueError(f"window [{offset}:{offset+size}] past end of S50ui "
                         f"({len(s50ui)})")
    return bytes(s50ui[offset + j] ^ key[j % len(key)] for j in range(size))


def decrypt(cipher: bytes, block: bytes, sub: int) -> bytes:
    n = len(block)
    return bytes((((c - sub) & 0xFF) ^ block[i % n]) for i, c in enumerate(cipher))


def encrypt(plain: bytes, block: bytes, sub: int) -> bytes:
    n = len(block)
    return bytes((((p ^ block[i % n]) + sub) & 0xFF) for i, p in enumerate(plain))


def proc_version_key(proc_version: str) -> bytes:
    """The key game extracts: between the first '(' and the following ')'."""
    i = proc_version.find("(")
    if i < 0:
        raise ValueError("no '(' in /proc/version (game prints 'start error')")
    j = proc_version.find(")", i)
    if j < 0:
        raise ValueError("no ')' in /proc/version (game prints 'end error')")
    return proc_version[i + 1:j].encode()


def load_params(args, s50ui: bytes):
    """Explicit flags win; then --version-file; then the shipped constants."""
    if args.offset is not None and args.size is not None and args.key:
        return args.offset, args.size, args.sub, args.key.encode(), "flags"
    if args.version_file:
        p = derive(Path(args.version_file).read_bytes(), len(s50ui))
        if not args.key:
            raise SystemExit("--version-file gives size/offset but not the key; "
                             "pass --key (from /proc/version) too")
        return p["offset"], p["size"], p["klen"] & 0xFF, args.key.encode(), "derived"
    s = SHIPPED
    return (args.offset if args.offset is not None else s["offset"],
            args.size if args.size is not None else s["size"],
            args.sub if args.sub is not None else s["sub"],
            args.key.encode() if args.key else s["key"], "shipped defaults")


def cmd_params(args):
    root = Path(args.root)
    s50ui = (root / "etc/init.d/S50ui").read_bytes()
    version = (root / "etc/version").read_bytes()
    p = derive(version, len(s50ui))
    print(f"/etc/version      {version!r}")
    print(f"  sum(2 lines)    {p['sum']}  (% 64 = {p['sum'] % 64})")
    print(f"  date fields     a={p['a']} b={p['b']} c={p['c']} d={p['d']}")
    print(f"len(S50ui)        {len(s50ui)}")
    print(f"keystream length  {p['klen']}        (subtracted byte)")
    print(f"window size       {p['size']}")
    print(f"window offset     {p['offset']}       (mod {p['denom']})")
    print()
    s = SHIPPED
    if (p["size"], p["offset"]) != (s["size"], s["offset"]):
        print("MISMATCH: the blob shipped on this card decrypts with")
        print(f"  size={s['size']} offset={s['offset']} sub={s['sub']} "
              f"key={s['key'].decode()!r}")
        print("so /etc/webster was built against a different /etc/version and")
        print("this firmware cannot decrypt it. See `crack`.")
    else:
        print("matches the shipped blob's parameters")


def cmd_decrypt(args):
    root = Path(args.root)
    s50ui = (root / "etc/init.d/S50ui").read_bytes()
    cipher = Path(args.file).read_bytes()
    off, size, sub, key, how = load_params(args, s50ui)
    out = decrypt(cipher, keyblock(s50ui, off, size, key), sub)
    print(f"params from {how}: offset={off} size={size} sub={sub} key={key.decode()!r}",
          file=sys.stderr)
    bad = sum(1 for b in out if b not in PRINTABLE)
    print(f"{len(out)} bytes, {bad} non-ASCII "
          f"({100*(len(out)-bad)/len(out):.1f}% printable)", file=sys.stderr)
    try:
        out.decode("utf-8")
        print("valid UTF-8", file=sys.stderr)
    except UnicodeDecodeError:
        print("NOT valid UTF-8 -- parameters are probably wrong", file=sys.stderr)
    Path(args.output).write_bytes(out) if args.output else sys.stdout.buffer.write(out)
    if args.output:
        print(f"wrote {args.output}", file=sys.stderr)


def cmd_encrypt(args):
    root = Path(args.root)
    s50ui = (root / "etc/init.d/S50ui").read_bytes()
    plain = Path(args.file).read_bytes()
    off, size, sub, key, how = load_params(args, s50ui)
    out = encrypt(plain, keyblock(s50ui, off, size, key), sub)
    print(f"params from {how}: offset={off} size={size} sub={sub}", file=sys.stderr)
    Path(args.output).write_bytes(out) if args.output else sys.stdout.buffer.write(out)
    if args.output:
        print(f"wrote {args.output} ({len(out)} bytes)", file=sys.stderr)


def cmd_crack(args):
    """Recover the parameters without /proc/version.

    1. size and the subtracted byte are linked (sub = size - 512), so one scan
       over size finds both: at the true value, cipher[i]^cipher[i+size] has the
       keystream cancelled and the plaintext's own redundancy shows up as a
       spike in the index of coincidence.
    2. the offset falls out of a crib on the first bytes, filtered by requiring
       the implied key bytes to look like a user@host string.
    3. the key is then solved per position against a similar plaintext.
    """
    root = Path(args.root)
    s50ui = (root / "etc/init.d/S50ui").read_bytes()
    cipher = Path(args.file).read_bytes()
    model = Path(args.model).read_bytes() if args.model else None

    print("[1] scanning size (sub = size - 512) by index of coincidence")
    scored = []
    for size in range(512, 600):
        sub = (size - 512) & 0xFF
        s = bytes((b - sub) & 0xFF for b in cipher)
        pairs = [s[i] ^ s[i + size] for i in range(len(s) - size)]
        c = Counter(pairs)
        n = len(pairs)
        ic = sum(v * (v - 1) for v in c.values()) / (n * (n - 1) / 256)
        scored.append((ic, size, sub))
    scored.sort(reverse=True)
    for ic, size, sub in scored[:3]:
        print(f"    size={size} sub={sub}  IC={ic:.3f}")
    _, size, sub = scored[0]
    print(f"    -> size={size} sub={sub}")

    s = bytes((b - sub) & 0xFF for b in cipher)

    print(f"\n[2] searching S50ui offset with crib {args.crib!r}")
    crib = args.crib.encode().decode("unicode_escape").encode()
    ok = set(b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@._-")
    cands = []
    for off in range(len(s50ui) - size + 1):
        k = bytes(s[i] ^ s50ui[off + i] ^ crib[i] for i in range(len(crib)))
        if all(ch in ok for ch in k):
            cands.append((off, k))
            print(f"    offset={off:5}  key starts {k!r}")
    if not cands:
        sys.exit("    no offset matched the crib; try a different --crib")

    if not model:
        print("\npass --model <similar script> to solve the key")
        return

    print(f"\n[3] solving the key against {args.model}")
    best = None
    for off, _ in cands:
        base = bytes(s[i] ^ s50ui[off + (i % size)] for i in range(len(s)))
        for L in range(6, 49):
            key = bytearray(L)
            for j in range(L):
                idx = [i for i in range(len(base)) if (i % size) % L == j]
                key[j] = max(ok, key=lambda k: sum(
                    3 if (base[i] ^ k) in (10, 9) else
                    2 if 32 <= (base[i] ^ k) < 127 else -6 for i in idx))
            pt = bytes(base[i] ^ key[(i % size) % L] for i in range(len(base)))
            sc = sum(1 for b in pt if b in PRINTABLE) / len(pt)
            if best is None or sc > best[0]:
                best = (sc, off, L, bytes(key))
    sc, off, L, key = best
    print(f"    offset={off} keylen={L} key={key!r} printable={sc*100:.1f}%")

    # Per-position guessing gets a few bytes wrong; fix them by aligning the
    # result with the model and reading the true keystream off the overlap.
    block = bytearray(s50ui[off + j] ^ key[j % L] for j in range(size))
    for _ in range(8):
        pt = bytes(s[i] ^ block[i % size] for i in range(len(s)))
        votes = {}
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                None, pt, model, autojunk=False).get_opcodes():
            if tag == "equal" or (tag == "replace" and (i2 - i1) == (j2 - j1)):
                for d in range(i2 - i1):
                    votes.setdefault((i1 + d) % size, []).append(s[i1 + d] ^ model[j1 + d])
        n = 0
        for j, v in votes.items():
            cand, cnt = Counter(v).most_common(1)[0]
            if cnt >= 2 and cand != block[j]:
                block[j] = cand
                n += 1
        if not n:
            break
    recovered = bytes(block[j] ^ s50ui[off + j] for j in range(size))
    period = next((p for p in range(1, 65)
                   if all(recovered[i] == recovered[i % p] for i in range(len(recovered)))),
                  None)
    print(f"\n[4] keystream after alignment repeats with period {period}")
    print(f"    key = {recovered[:period or 64]!r}")
    if period:
        print("    (a clean period confirms the S50ui window is byte-identical "
              "to the build machine's)")
    out = bytes(s[i] ^ block[i % size] for i in range(len(s)))
    if args.output:
        Path(args.output).write_bytes(out)
        print(f"\nwrote {args.output}")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="squash", help="extracted rootfs (default: squash)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--offset", type=int)
        p.add_argument("--size", type=int)
        p.add_argument("--sub", type=int)
        p.add_argument("--key", help="the user@host from /proc/version")
        p.add_argument("--version-file", help="an /etc/version to derive from")
        p.add_argument("-o", "--output")

    p = sub.add_parser("params", help="show what a rootfs derives")
    p.set_defaults(func=cmd_params)

    p = sub.add_parser("decrypt", help="webster -> webb.sh")
    p.add_argument("file")
    common(p)
    p.set_defaults(func=cmd_decrypt)

    p = sub.add_parser("encrypt", help="webb.sh -> webster")
    p.add_argument("file")
    common(p)
    p.set_defaults(func=cmd_encrypt)

    p = sub.add_parser("crack", help="recover parameters without /proc/version")
    p.add_argument("file")
    p.add_argument("--model", help="a similar plaintext to score against")
    p.add_argument("--crib", default="#!/bin/sh\\n")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_crack)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
