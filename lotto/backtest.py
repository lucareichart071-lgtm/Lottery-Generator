"""Treten Muster-Strategien gegen den Zufall an? Walk-forward-Backtest."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

import numpy as np
from scipy.stats import chisquare
from sklearn.ensemble import HistGradientBoostingClassifier

from lotto.daten import Ziehung
from lotto.merkmale import merkmals_matrix, one_hot

STRATEGIEN = ("zufall", "heiss", "kalt", "ueberfaellig", "modell")
AUFWAERMEN = 200
ERWARTET = 36 / 49


@dataclass
class StrategieErgebnis:
    name: str
    mittel_treffer: float
    anteil_3_plus: float
    p_wert: float
    p_korrigiert: float


@dataclass
class Ergebnis:
    n_ziehungen_gesamt: int
    n_training: int
    n_test: int
    test_ab: str
    erwartet_mittel: float
    strategien: list[StrategieErgebnis]
    chi2_statistik: float
    chi2_p_wert: float

    def als_dict(self) -> dict:
        return asdict(self)


def _top6(werte: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Die 6 Zahlen (1–49) mit den höchsten Werten; Gleichstände zufällig."""
    rauschen = rng.random(49) * 1e-9
    return np.argsort(-(werte + rauschen))[:6] + 1


def backtest(
    ziehungen: list[Ziehung],
    test_ab: date,
    seed: int = 0,
    n_permutationen: int = 1000,
) -> Ergebnis:
    zahlen = [z.zahlen for z in ziehungen]
    split = next((i for i, z in enumerate(ziehungen) if z.datum >= test_ab), None)
    if split is None or split <= AUFWAERMEN or split >= len(zahlen):
        raise ValueError("Zu wenig Trainings- oder Testdaten für den Backtest")

    f = merkmals_matrix(zahlen)
    x = one_hot(zahlen)
    k = f.shape[2]
    modell = HistGradientBoostingClassifier(
        max_iter=200, learning_rate=0.05, random_state=seed
    )
    modell.fit(f[AUFWAERMEN:split].reshape(-1, k), x[AUFWAERMEN:split].reshape(-1))
    proba = modell.predict_proba(f[split:].reshape(-1, k))[:, 1].reshape(-1, 49)

    rng = np.random.default_rng(seed)
    n_test = len(zahlen) - split
    treffer = {s: np.zeros(n_test, dtype=int) for s in STRATEGIEN}
    for t, i in enumerate(range(split, len(zahlen))):
        gezogen = x[i].astype(bool)
        tipps = {
            "zufall": rng.choice(49, 6, replace=False) + 1,
            "heiss": _top6(f[i, :, 0], rng),
            "kalt": _top6(-f[i, :, 0], rng),
            "ueberfaellig": _top6(f[i, :, 3], rng),
            "modell": _top6(proba[t], rng),
        }
        for name, tipp in tipps.items():
            treffer[name][t] = gezogen[tipp - 1].sum()

    # Nullverteilung: Treffer zufälliger Tipps sind hypergeometrisch verteilt.
    null = rng.hypergeometric(6, 43, 6, size=(n_permutationen, n_test)).mean(axis=1)
    ergebnisse = []
    for name in STRATEGIEN:
        mittel = float(treffer[name].mean())
        p = float((np.sum(null >= mittel) + 1) / (n_permutationen + 1))
        ergebnisse.append(
            StrategieErgebnis(
                name=name,
                mittel_treffer=mittel,
                anteil_3_plus=float((treffer[name] >= 3).mean()),
                p_wert=p,
                p_korrigiert=min(1.0, p * len(STRATEGIEN)),
            )
        )

    chi = chisquare(x.sum(axis=0))
    return Ergebnis(
        n_ziehungen_gesamt=len(zahlen),
        n_training=split - AUFWAERMEN,
        n_test=n_test,
        test_ab=ziehungen[split].datum.isoformat(),
        erwartet_mittel=ERWARTET,
        strategien=ergebnisse,
        chi2_statistik=float(chi.statistic),
        chi2_p_wert=float(chi.pvalue),
    )
