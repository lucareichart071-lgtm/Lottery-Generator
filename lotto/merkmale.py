"""Merkmale pro Zahl und Ziehung; Zeile i verwendet nur Ziehungen vor i."""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np

FENSTER = (10, 50, 200)
MERKMAL_NAMEN = (
    "haeufigkeit_10",
    "haeufigkeit_50",
    "haeufigkeit_200",
    "seit_letztem",
    "rate_gesamt",
    "in_letzter",
)


def one_hot(zahlen_liste: Sequence[Sequence[int]]) -> np.ndarray:
    x = np.zeros((len(zahlen_liste), 49), dtype=np.int32)
    for i, zahlen in enumerate(zahlen_liste):
        x[i, np.asarray(zahlen) - 1] = 1
    return x


def merkmals_matrix(zahlen_liste: Sequence[Sequence[int]]) -> np.ndarray:
    x = one_hot(zahlen_liste)
    n = len(x)
    kum = np.vstack([np.zeros((1, 49), np.int64), np.cumsum(x, axis=0)])
    idx = np.arange(n)
    f = np.zeros((n, 49, len(MERKMAL_NAMEN)))
    for spalte, k in enumerate(FENSTER):
        f[:, :, spalte] = kum[idx] - kum[np.maximum(idx - k, 0)]
    zuletzt = np.full(49, -1)
    for i in range(n):
        f[i, :, 3] = np.where(zuletzt >= 0, i - zuletzt, i + 1)
        zuletzt[x[i] == 1] = i
    f[:, :, 4] = kum[idx] / np.maximum(idx, 1)[:, None]
    f[1:, :, 5] = x[:-1]
    return f
