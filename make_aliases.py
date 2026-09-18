#!/usr/bin/env python3.11
"""Build aliases_en.txt: spoken look-alikes of list words, from CMUdict.

Line format: <heard> <dist><word>[,<dist><word>...]   dist 0 = homophone, 1 = one phoneme off.
aliases_full_en.txt has everything; aliases_en.txt (shipped in the page) keeps homophones
plus list words that sound like other list words.
"""

from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
CMU = Path.home() / "nltk_data/corpora/cmudict/cmudict"
# Near-identical to a recogniser; folded before comparing.
FOLD = {"AO": "AA", "AX": "AH", "IH": "IY", "UH": "UW", "Z": "S", "ZH": "SH", "D": "T", "DH": "TH"}


def prons() -> dict[str, set[tuple[str, ...]]]:
    out: dict[str, set[tuple[str, ...]]] = collections.defaultdict(set)
    for line in CMU.read_text(encoding="latin-1").splitlines():
        p = line.split()
        if len(p) >= 3 and re.fullmatch(r"[a-z']+", p[0].lower()):
            out[p[0].lower()].add(tuple(re.sub(r"\d", "", x) for x in p[2:]))
    return out


def subs(p: tuple[str, ...]) -> set[tuple[str, ...]]:
    return {p[:i] + ("_",) + p[i + 1 :] for i in range(len(p))}


def dels(p: tuple[str, ...]) -> set[tuple[str, ...]]:
    return {p[:i] + p[i + 1 :] for i in range(len(p))}


def main() -> int:
    words = (HERE / "wordlist_en.txt").read_text().split()
    pr = prons()
    exact: dict[tuple[str, ...], set[str]] = collections.defaultdict(set)
    near: dict[tuple[str, ...], set[str]] = collections.defaultdict(set)
    for w in words:
        for p in pr.get(w, ()):
            f = tuple(FOLD.get(x, x) for x in p)
            exact[p].add(w)
            for v in subs(f) | dels(f) | {("=",) + f}:
                near[v].add(w)
    lines = []
    for heard in sorted(pr):
        hit: dict[str, int] = {}
        for p in pr[heard]:
            f = tuple(FOLD.get(x, x) for x in p)
            # same / one substitution / heard is one phoneme shorter / one longer
            for v in {("=",) + f} | subs(f) | {f} | {("=",) + d for d in dels(f)}:
                for w in near.get(v, ()):
                    hit.setdefault(w, 1)
            for w in exact.get(p, ()):
                hit[w] = 0
        hit.pop(heard, None)
        if hit:
            lines.append(heard + " " + ",".join(f"{d}{w}" for w, d in sorted(hit.items(), key=lambda kv: (kv[1], kv[0]))))
    (HERE / "aliases_full_en.txt").write_text("\n".join(lines) + "\n")
    # compact = what ships in the page: homophones, plus list words that sound like list words
    wset, compact = set(words), []
    for ln in lines:
        heard, targets = ln.split(" ")
        keep = [t for t in targets.split(",") if t[0] == "0" or heard in wset]
        if keep:
            compact.append(heard + " " + ",".join(keep))
    (HERE / "aliases_en.txt").write_text("\n".join(compact) + "\n")
    for name in ("aliases_full_en.txt", "aliases_en.txt"):
        f = HERE / name
        print(f"{name}: {len(f.read_text().splitlines())} heard-forms, {f.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
