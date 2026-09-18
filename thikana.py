#!/usr/bin/env python3.11
"""thikana: open 1 m geocode. Five words = 51 location bits + 4 check bits."""

from __future__ import annotations

import re
import sys
from pathlib import Path

LAT_N = 18_000_001  # (lat + 90) * 1e5, inclusive of both poles
LON_N = 36_000_000  # (lon + 180) * 1e5, wraps at the antimeridian
LAT_BITS, LON_BITS, CHECK_BITS, WORD_BITS, N_WORDS = 25, 26, 4, 11, 5

WORDS = (Path(__file__).with_name("wordlist_en.txt")).read_text().split()
_BY_PREFIX = {w[:4]: i for i, w in enumerate(WORDS)}
_BY_WORD = {w: i for i, w in enumerate(WORDS)}

_HI_CONS = "[क-ह]"


def fold_hi(w: str) -> str:
    """Spelling variants that sound the same: long/short i and u, anusvara vs half nasal."""
    k = w.replace("ी", "ि").replace("ू", "ु").replace("़", "")
    k = re.sub("[नमणङञ]्(?=" + _HI_CONS + ")", "", k)
    return k.replace("ं", "").replace("ँ", "")


WORDS_HI = (Path(__file__).with_name("wordlist_hi.txt")).read_text(encoding="utf-8").split()
_BY_HI = {fold_hi(w): i for i, w in enumerate(WORDS_HI)}


def load_aliases(name: str = "aliases_en.txt") -> dict[str, list[tuple[int, str]]]:
    out: dict[str, list[tuple[int, str]]] = {}
    f = Path(__file__).with_name(name)
    for line in f.read_text().splitlines() if f.exists() else []:
        heard, targets = line.split(" ")
        out[heard] = [(int(t[0]), t[1:]) for t in targets.split(",")]
    return out


ALIASES = load_aliases()


class BadCode(ValueError):
    pass


def _quantise(lat: float, lon: float) -> tuple[int, int]:
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise BadCode(f"coordinates out of range: {lat},{lon}")
    return round((lat + 90) * 1e5), round((lon + 180) * 1e5) % LON_N


def _unquantise(la: int, lo: int) -> tuple[float, float]:
    if la >= LAT_N or lo >= LON_N:
        raise BadCode("code decodes to a point that is not on Earth")
    return round(la / 1e5 - 90, 5), round(lo / 1e5 - 180, 5)


def _interleave(la: int, lo: int) -> int:
    n = 0
    for i in range(LON_BITS - 1, -1, -1):  # lon bit first, it has one extra
        n = (n << 1) | ((lo >> i) & 1)
        if i < LAT_BITS:
            n = (n << 1) | ((la >> i) & 1)
    return n


def _deinterleave(n: int) -> tuple[int, int]:
    la = lo = 0
    pos = LAT_BITS + LON_BITS
    for i in range(LON_BITS - 1, -1, -1):
        pos -= 1
        lo = (lo << 1) | ((n >> pos) & 1)
        if i < LAT_BITS:
            pos -= 1
            la = (la << 1) | ((n >> pos) & 1)
    return la, lo


def _crc4(n: int, bits: int) -> int:
    """CRC-4-ITU (x^4 + x + 1), MSB first."""
    reg = 0
    for i in range(bits - 1, -1, -1):
        top = ((reg >> 3) & 1) ^ ((n >> i) & 1)
        reg = (reg << 1) & 0xF
        if top:
            reg ^= 0x3
    return reg


def encode(lat: float, lon: float, lang: str = "en") -> str:
    loc = _interleave(*_quantise(lat, lon))
    payload = (loc << CHECK_BITS) | _crc4(loc, LAT_BITS + LON_BITS)
    idx = [(payload >> (WORD_BITS * k)) & 0x7FF for k in range(N_WORDS - 1, -1, -1)]
    if lang == "hi":
        return " ".join(WORDS_HI[i] for i in idx)
    return ".".join(WORDS[i] for i in idx)


def _tokens(code: str) -> list[str]:
    parts = re.findall(r"[a-z]+(?:'[a-z]+)?", code.lower().replace("\u2019", "'"))
    if len(parts) != N_WORDS:
        raise BadCode(f"need {N_WORDS} words, got {len(parts)}")
    return parts


def _index(token: str, aliases: dict[str, list[tuple[int, str]]]) -> int | None:
    """Exact word, else an unambiguous homophone, else the first-4-letters rule."""
    if token in _BY_WORD:
        return _BY_WORD[token]
    homophones = [w for d, w in aliases.get(token, []) if d == 0]
    if len(homophones) == 1:
        return _BY_WORD[homophones[0]]
    return _BY_PREFIX.get(token.replace("'", "")[:4])


def _from_indices(idx: list[int]) -> tuple[float, float]:
    payload = 0
    for i in idx:
        payload = (payload << WORD_BITS) | i
    loc, check = payload >> CHECK_BITS, payload & 0xF
    if _crc4(loc, LAT_BITS + LON_BITS) != check:
        raise BadCode("checksum mismatch: a word is wrong or misheard")
    return _unquantise(*_deinterleave(loc))


def decode(code: str) -> tuple[float, float]:
    idx = []
    hi = re.findall("[ऀ-ॿ]+", code)
    if hi:
        if len(hi) != N_WORDS:
            raise BadCode(f"need {N_WORDS} words, got {len(hi)}")
        for h in hi:
            if fold_hi(h) not in _BY_HI:
                raise BadCode(f"unknown word: {h}")
        return _from_indices([_BY_HI[fold_hi(h)] for h in hi])
    for p in _tokens(code):
        i = _index(p, ALIASES)
        if i is None:
            raise BadCode(f"unknown word: {p}")
        idx.append(i)
    return _from_indices(idx)


def repair(
    code: str, aliases: dict[str, list[tuple[int, str]]] | None = None
) -> list[tuple[int, str, tuple[float, float]]]:
    """Suggestions for a code that failed: ONE word swapped for a sound-alike, checksum valid.

    Returns (distance, words, (lat, lon)) best first. Suggestions only: with 4 check bits
    about 1 in 16 wrong swaps also passes, so a human must confirm.
    """
    aliases = ALIASES if aliases is None else aliases
    parts = _tokens(code)
    base = [_index(p, aliases) for p in parts]
    out = []
    for pos, tok in enumerate(parts):
        if any(b is None for k, b in enumerate(base) if k != pos):
            continue
        for dist, word in aliases.get(tok, []):
            idx = list(base)
            idx[pos] = _BY_WORD[word]
            if idx[pos] == base[pos]:
                continue
            try:
                where = _from_indices(idx)  # type: ignore[arg-type]
            except BadCode:
                continue
            out.append((dist, ".".join(WORDS[i] for i in idx), where))  # type: ignore[index]
    return sorted(set(out))


def _luhn(digits: str) -> int:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch) * (2 if i % 2 == 0 else 1)
        total += d - 9 if d > 9 else d
    return (10 - total % 10) % 10


def encode_digits(lat: float, lon: float) -> str:
    la, lo = _quantise(lat, lon)
    body = f"{la * LON_N + lo:015d}"
    s = body + str(_luhn(body))
    return " ".join(s[i : i + 4] for i in range(0, 16, 4))


def decode_digits(code: str) -> tuple[float, float]:
    s = re.sub(r"\D", "", code)
    if len(s) != 16 or _luhn(s[:15]) != int(s[15]):
        raise BadCode("bad numeric code: wrong length or check digit")
    return _unquantise(*divmod(int(s[:15]), LON_N))


_DIGI = ("FC98", "J327", "K456", "LMPT")


def digipin(lat: float, lon: float) -> str | None:
    """India Post DIGIPIN (10 chars, about 4 m). None outside its India bounding box."""
    a, b, c, d = 2.5, 38.5, 63.5, 99.5
    if not (a <= lat <= b and c <= lon <= d):
        return None
    out = ""
    for _ in range(10):
        dl, dn = (b - a) / 4, (d - c) / 4
        row = max(0, min(3, 3 - int((lat - a) // dl)))
        col = max(0, min(3, int((lon - c) // dn)))
        out += _DIGI[row][col]
        a, b = a + dl * (3 - row), a + dl * (4 - row)
        c = c + dn * col
        d = c + dn
    return out


def message(lat: float, lon: float, base: str = "https://dtensor.github.io/thikana/") -> str:
    code = encode(lat, lon)
    la, lo = decode(code)
    return f"{code}\n{la:.5f},{lo:.5f}\n{base}#{code}"


def main(argv: list[str]) -> int:
    arg = " ".join(argv)
    if argv[:1] == ["build"]:
        here = Path(__file__).parent
        words = "[" + ",".join(f'"{w}"' for w in WORDS) + "]"
        html = (here / "page.template.html").read_text().replace("/*WORDS*/[]", words)
        hi = "[" + ",".join(f'"{w}"' for w in WORDS_HI) + "]"
        html = html.replace("/*WORDS_HI*/[]", hi)
        alias_text = (here / "aliases_en.txt").read_text().strip().replace("\n", "|")
        html = html.replace('/*ALIASES*/""', '"' + alias_text + '"')
        (here / "index.html").write_text(html)
        print(f"wrote {here / 'index.html'} ({len(html) // 1024} KB)")
        return 0
    try:
        m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)\s*", arg)
        if m:
            lat, lon = float(m[1]), float(m[2])
            print(message(lat, lon))
            print(encode_digits(lat, lon))
            print(encode(lat, lon, "hi") + "   (Hindi list is a DRAFT, may change)")
            if digipin(lat, lon):
                print(f"DIGIPIN {digipin(lat, lon)}")
        elif re.search(r"[a-zA-Zऀ-ॿ]", arg):
            print("%.5f,%.5f" % decode(arg))
        elif arg.strip():
            print("%.5f,%.5f" % decode_digits(arg))
        else:
            print("usage: thikana <lat,lon> | <five.words> | <16 digits>")
            return 1
    except BadCode as e:
        print(f"BAD CODE: {e}", file=sys.stderr)
        try:
            found = repair(arg) or repair(arg, load_aliases("aliases_full_en.txt"))
            for _, words, (la, lo) in found[:5]:
                print(f"did you mean: {words}  ({la:.5f},{lo:.5f})", file=sys.stderr)
        except BadCode:
            pass
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
