import random

import pytest

import thikana as t


def test_wordlist_shape():
    assert len(t.WORDS) == 2048
    assert len(set(t.WORDS)) == 2048
    assert len({w[:4] for w in t.WORDS}) == 2048


@pytest.mark.parametrize(
    "lat,lon",
    [(0, 0), (90, 180), (-90, -180), (90, -180), (27.17501, 78.04213), (-33.85678, 151.21530)],
)
def test_roundtrip_corners(lat, lon):
    la, lo = t.decode(t.encode(lat, lon))
    assert abs(la - lat) <= 5e-6 + 1e-12
    assert abs(((lo - lon) + 180) % 360 - 180) <= 5e-6 + 1e-12


def test_roundtrip_random():
    rng = random.Random(7)
    for _ in range(100_000):
        lat, lon = rng.uniform(-90, 90), rng.uniform(-180, 180)
        la, lo = t.decode(t.encode(lat, lon))
        assert abs(la - lat) <= 5.0001e-6
        assert abs(((lo - lon) + 180) % 360 - 180) <= 5.0001e-6


def test_numeric_roundtrip_and_check_digit():
    code = t.encode_digits(27.17501, 78.04213)
    assert len(code.replace(" ", "")) == 16
    assert t.decode_digits(code) == pytest.approx((27.17501, 78.04213), abs=1e-9)
    bad = code[:-1] + str((int(code[-1]) + 1) % 10)
    with pytest.raises(t.BadCode):
        t.decode_digits(bad)


def test_forgiving_input():
    code = t.encode(27.17501, 78.04213)
    messy = "  " + code.upper().replace(".", " - ") + " "
    assert t.decode(messy) == t.decode(code)
    short = ".".join(w[:4] for w in code.split("."))
    assert t.decode(short) == t.decode(code)


def test_neighbours_share_prefix():
    a = t.encode(27.17501, 78.04213).split(".")
    b = t.encode(27.17601, 78.04313).split(".")
    assert a[:2] == b[:2]


def test_unknown_word_rejected():
    with pytest.raises(t.BadCode):
        t.decode("zzzz.zzzz.zzzz.zzzz.zzzz")


def test_single_word_swap_catch_rate():
    """Measured, not assumed: a wrong word must usually be rejected."""
    rng = random.Random(11)
    caught = total = 0
    for _ in range(20_000):
        ws = t.encode(rng.uniform(-90, 90), rng.uniform(-180, 180)).split(".")
        i = rng.randrange(5)
        ws[i] = rng.choice([w for w in (rng.choice(t.WORDS),) if w != ws[i]] or [t.WORDS[0]])
        total += 1
        try:
            t.decode(".".join(ws))
        except t.BadCode:
            caught += 1
    assert caught / total > 0.90


def test_homophone_accepted():
    # find a point whose code contains "cereal", then say it as "serial"
    rng = random.Random(1)
    code = ""
    while "cereal" not in code.split("."):
        code = t.encode(rng.uniform(-90, 90), rng.uniform(-180, 180))
    assert t.decode(code.replace("cereal", "serial")) == t.decode(code)


def test_repair_finds_list_word_confusion():

    rng = random.Random(2)
    code = ""
    while "bind" not in code.split("."):
        code = t.encode(rng.uniform(-90, 90), rng.uniform(-180, 180))
    heard = code.replace("bind", "find")
    with pytest.raises(t.BadCode):
        t.decode(heard)
    assert code in [w for _, w, _ in t.repair(heard)]


def test_wordlist_is_frozen():
    """Changing the list changes every code ever shared. Bump the format version instead."""
    import hashlib
    from pathlib import Path

    data = Path(t.__file__).with_name("wordlist_en.txt").read_bytes()
    assert hashlib.sha256(data).hexdigest() == "2f5eed53a4727b4bf8880d8f3f199efc90e58503646d9ff8eff3a2ed3b24dbda"
