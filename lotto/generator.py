"""Tipps für Lotto 6 aus 49: rein zufällig und ohne beliebte Muster."""
from __future__ import annotations

import random
from collections.abc import Sequence

MAX_VERSUCHE = 10_000
GRUENDE = {
    "geburtstage": "nur Zahlen bis 31 (Geburtstage)",
    "folge": "4 oder mehr aufeinanderfolgende Zahlen",
    "abstaende": "gleichmäßige Abstände",
    "zeile_spalte": "alle in einer Zeile oder Spalte des Tippscheins",
    "diagonale": "alle auf einer Diagonale des Tippscheins",
    "letzte": "3 oder mehr Zahlen aus der letzten Ziehung",
}


def zufallstipp(rng: random.Random) -> tuple[int, ...]:
    return tuple(sorted(rng.sample(range(1, 50), 6)))


def _zeile(z: int) -> int:
    return (z - 1) // 7


def _spalte(z: int) -> int:
    return (z - 1) % 7


def ist_beliebtes_muster(
    tipp: Sequence[int], letzte_ziehung: Sequence[int] | None = None
) -> list[str]:
    """Gründe, warum viele Leute diesen Tipp ebenfalls spielen könnten."""
    t = sorted(tipp)
    gruende = []
    if t[-1] <= 31:
        gruende.append(GRUENDE["geburtstage"])
    lauf = laengster = 1
    for a, b in zip(t, t[1:]):
        lauf = lauf + 1 if b == a + 1 else 1
        laengster = max(laengster, lauf)
    if laengster >= 4:
        gruende.append(GRUENDE["folge"])
    if len({b - a for a, b in zip(t, t[1:])}) == 1:
        gruende.append(GRUENDE["abstaende"])
    if len({_zeile(z) for z in t}) == 1 or len({_spalte(z) for z in t}) == 1:
        gruende.append(GRUENDE["zeile_spalte"])
    if (
        len({_zeile(z) - _spalte(z) for z in t}) == 1
        or len({_zeile(z) + _spalte(z) for z in t}) == 1
    ):
        gruende.append(GRUENDE["diagonale"])
    if letzte_ziehung is not None and len(set(t) & set(letzte_ziehung)) >= 3:
        gruende.append(GRUENDE["letzte"])
    return gruende


def smarter_tipp(
    rng: random.Random, letzte_ziehung: Sequence[int] | None = None
) -> tuple[int, ...]:
    """Zufallstipp ohne beliebte Muster (gleichverteilt über die erlaubten Tipps)."""
    for _ in range(MAX_VERSUCHE):
        tipp = zufallstipp(rng)
        if not ist_beliebtes_muster(tipp, letzte_ziehung):
            return tipp
    raise RuntimeError(f"Kein gültiger Tipp nach {MAX_VERSUCHE} Versuchen")
