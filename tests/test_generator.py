import random

import pytest

from lotto.generator import (
    GRUENDE,
    MAX_VERSUCHE,
    ist_beliebtes_muster,
    smarter_tipp,
    zufallstipp,
)

SAUBER = (3, 14, 25, 36, 40, 47)


def test_zufallstipp_ist_gueltig_und_reproduzierbar():
    for seed in range(200):
        tipp = zufallstipp(random.Random(seed))
        assert len(tipp) == 6 and len(set(tipp)) == 6
        assert list(tipp) == sorted(tipp)
        assert all(1 <= z <= 49 for z in tipp)
    assert zufallstipp(random.Random(7)) == zufallstipp(random.Random(7))


def test_sauberer_tipp_hat_keine_gruende():
    assert ist_beliebtes_muster(SAUBER, None) == []


@pytest.mark.parametrize(
    "tipp, regel",
    [
        ((1, 5, 12, 19, 25, 31), "geburtstage"),
        ((10, 11, 12, 13, 30, 45), "folge"),
        ((4, 13, 22, 31, 40, 49), "abstaende"),
        ((36, 37, 38, 40, 41, 42), "zeile_spalte"),
        ((2, 9, 16, 23, 30, 44), "zeile_spalte"),
        ((1, 9, 17, 25, 33, 49), "diagonale"),
    ],
)
def test_jede_regel_greift_einzeln(tipp, regel):
    assert ist_beliebtes_muster(tipp, None) == [GRUENDE[regel]]


@pytest.mark.parametrize(
    "tipp",
    [
        (1, 5, 12, 19, 25, 32),
        (10, 11, 12, 30, 40, 45),
        (4, 13, 22, 31, 40, 48),
        (36, 37, 38, 40, 41, 45),
        (1, 9, 17, 25, 33, 48),
    ],
)
def test_knapp_daneben_greift_nicht(tipp):
    assert ist_beliebtes_muster(tipp, None) == []


def test_letzte_ziehung():
    letzte = (3, 14, 25, 1, 2, 4)
    assert ist_beliebtes_muster(SAUBER, letzte) == [GRUENDE["letzte"]]
    assert ist_beliebtes_muster(SAUBER, (3, 14, 1, 2, 4, 5)) == []


def test_smarter_tipp_verletzt_nie_eine_regel():
    rng = random.Random(1)
    letzte = (5, 7, 19, 24, 33, 46)
    for _ in range(1000):
        tipp = smarter_tipp(rng, letzte)
        assert ist_beliebtes_muster(tipp, letzte) == []


def test_smarter_tipp_bricht_ab(monkeypatch):
    monkeypatch.setattr("lotto.generator.ist_beliebtes_muster", lambda t, l: ["x"])
    with pytest.raises(RuntimeError, match=str(MAX_VERSUCHE)):
        smarter_tipp(random.Random(0))
