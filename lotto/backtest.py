"""Treten Muster-Strategien gegen den Zufall an? Backtest mit Signifikanztest.

Das Modell wird einmal auf dem Trainingszeitraum trainiert; die Merkmale
laufen im Testzeitraum weiter (jede Ziehung nutzt nur frühere Ziehungen).
Der Signifikanztest ist ein Monte-Carlo-Test gegen die analytische
(hypergeometrische) Nullverteilung zufälliger Tipps.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date

import numpy as np
from scipy.stats import chi2, chisquare
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


def nullverteilung(
    rng: np.random.Generator, n_permutationen: int, n_test: int
) -> np.ndarray:
    """Monte-Carlo-Stichprobe der Nullverteilung des mittleren Treffers.

    Ein zufälliger Tipp (6 aus 49) trifft hypergeometrisch verteilt
    (6 gezogene aus 43 nicht gezogenen); je Stichprobe wird über n_test
    Ziehungen gemittelt.
    """
    return rng.hypergeometric(6, 43, 6, size=(n_permutationen, n_test)).mean(axis=1)


def gleichverteilungstest(zaehlungen: np.ndarray) -> tuple[float, float]:
    """Chi-Quadrat-Test auf Gleichverteilung der 49 Zahlen.

    Lotto zieht 6 aus 49 ohne Zurücklegen; der Standard-Chi-Quadrat-Wert hat
    dann den Erwartungswert (N-n)/(N-1) * 48 = 43 statt 48. Korrektur:
    Statistik mit (N-1)/(N-n) = 48/43 multiplizieren, p-Wert aus chi2 mit
    48 Freiheitsgraden.
    """
    statistik = float(chisquare(zaehlungen).statistic) * 48 / 43
    return statistik, float(chi2.sf(statistik, 48))


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

    # Monte-Carlo-Test gegen die hypergeometrische Nullverteilung.
    null = nullverteilung(rng, n_permutationen, n_test)
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

    chi2_stat, chi2_p = gleichverteilungstest(x.sum(axis=0))
    return Ergebnis(
        n_ziehungen_gesamt=len(zahlen),
        n_training=split - AUFWAERMEN,
        n_test=n_test,
        test_ab=ziehungen[split].datum.isoformat(),
        erwartet_mittel=ERWARTET,
        strategien=ergebnisse,
        chi2_statistik=chi2_stat,
        chi2_p_wert=chi2_p,
    )
