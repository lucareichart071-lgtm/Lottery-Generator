# Lotto-Labor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein Python-Paket, das Lotto-6-aus-49-Tipps erzeugt und per Backtest prüft, ob Muster die nächste Ziehung vorhersagen, plus eine Web-App mit Benutzerkonten, Gewinncheck und automatischer Datenaktualisierung.

**Architecture:** Kleine Python-Module mit je einer Aufgabe (`daten`, `generator`, `merkmale`, `backtest`, `export_db`, `cli`). Die Web-App ist eine einzelne HTML-Seite (claude.ai Artifact) mit den Capabilities `db` und `user`; ihre Tipp- und Gewinnlogik liegt in `web/logik.js` (mit Node getestet) und wird beim Bauen in die Seite eingefügt. Eine geplante Aufgabe schreibt neue Ziehungen in die Artifact-Datenbank.

**Tech Stack:** Python 3.11+, numpy, scipy, scikit-learn (`HistGradientBoostingClassifier`), pytest; Node 22 (`node:test`) für die JS-Logik; claude.ai Artifact (`db`, `user`), `ArtifactData`, Scheduled Tasks.

## Global Constraints

- Datenquelle: `https://raw.githubusercontent.com/daowa89/lottery-archive/main/de/lotto_6aus49/results.csv`, Spalten `date,n1,n2,n3,n4,n5,n6,superzahl`.
- Generator erzeugt nur 6 Zahlen (1–49); die Superzahl wird nie gewählt.
- Smart-Filter-Regeln (Python und JS identisch, gleiche Texte):
  1. „nur Zahlen bis 31 (Geburtstage)“
  2. „4 oder mehr aufeinanderfolgende Zahlen“
  3. „gleichmäßige Abstände“
  4. „alle in einer Zeile oder Spalte des Tippscheins“
  5. „alle auf einer Diagonale des Tippscheins“
  6. „3 oder mehr Zahlen aus der letzten Ziehung“
- Smart-Generator bricht nach 10.000 Fehlversuchen ab.
- Backtest: Test ab 2016-01-01, Aufwärmphase 200 Ziehungen, 1.000 Permutationen, Bonferroni über 5 Strategien, Signifikanzschwelle p_korr < 0,05.
- Merkmale für Ziehung *i* nutzen nur Ziehungen < *i*.
- Gewinnklassen: 1: 6+SZ, 2: 6, 3: 5+SZ, 4: 5, 5: 4+SZ, 6: 4, 7: 3+SZ, 8: 3, 9: 2+SZ.
- DB-Pfade: `ziehungen/{jahr}`, `meta/stand`, `data/users/{id}/{tippId}`. Regeln: `ziehungen` und `meta` read `view`, write `admin`.
- Sprache aller Texte: Deutsch. Arbeitsverzeichnis: `/home/claude/lotto-projekt`.

## Dateistruktur

```
lotto-projekt/
├── pyproject.toml
├── lotto/
│   ├── __init__.py
│   ├── __main__.py      # ruft cli.main()
│   ├── daten.py         # Ziehung, parse_csv, lade_ziehungen
│   ├── generator.py     # zufallstipp, ist_beliebtes_muster, smarter_tipp
│   ├── merkmale.py      # one_hot, merkmals_matrix
│   ├── backtest.py      # backtest, Ergebnis
│   ├── export_db.py     # export, schreibe_export
│   └── cli.py           # tipps | analyse | export
├── tests/
│   ├── __init__.py
│   ├── hilfen.py        # künstliche Ziehungen, CSV-Helfer
│   ├── test_daten.py
│   ├── test_generator.py
│   ├── test_merkmale.py
│   ├── test_backtest.py
│   ├── test_export_db.py
│   └── test_cli.py
├── web/
│   ├── logik.js         # Tipps, Filter, Gewinnklassen (Browser + Node)
│   ├── logik.test.js
│   ├── seite.html       # Seitenvorlage mit Platzhaltern
│   └── build.py         # erzeugt dist/lotto-labor.html
└── zeitplan/
    └── aktualisierung.md  # Prompt der geplanten Aufgabe
```

---

### Task 1: Projekt-Setup und Datenladen

**Files:**
- Create: `pyproject.toml`, `lotto/__init__.py`, `lotto/daten.py`, `tests/__init__.py`, `tests/hilfen.py`, `tests/test_daten.py`, `.gitignore`

**Interfaces:**
- Produces: `Ziehung(datum: date, zahlen: tuple[int, ...], superzahl: int | None)` (frozen dataclass, `zahlen` sortiert); `DatenFehler(ValueError)`; `parse_csv(text: str) -> list[Ziehung]` (nach Datum sortiert); `lade_ziehungen(quelle: str | Path | None = None) -> list[Ziehung]`; `CSV_URL`. Test-Helfer `kuenstliche_ziehungen(n, seed=0, fest=None, start=date(2000,1,1)) -> list[Ziehung]`, `als_csv(ziehungen) -> str`.

- [ ] **Step 1: Projektdateien anlegen**

`pyproject.toml`:
```toml
[project]
name = "lotto"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = ["numpy>=1.26", "scipy>=1.11", "scikit-learn>=1.4"]

[project.optional-dependencies]
test = ["pytest>=8"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

`.gitignore`:
```
__pycache__/
.pytest_cache/
dist/
export/
ergebnisse.json
```

`lotto/__init__.py` und `tests/__init__.py`: leer.

`tests/hilfen.py`:
```python
import random
from datetime import date, timedelta

from lotto.daten import Ziehung


def kuenstliche_ziehungen(n, seed=0, fest=None, start=date(2000, 1, 1)):
    """n zufällige Ziehungen; mit `fest` ist diese Zahl in jeder Ziehung."""
    rng = random.Random(seed)
    ziehungen = []
    for i in range(n):
        if fest is None:
            zahlen = rng.sample(range(1, 50), 6)
        else:
            zahlen = rng.sample([z for z in range(1, 50) if z != fest], 5) + [fest]
        ziehungen.append(
            Ziehung(start + timedelta(days=i), tuple(sorted(zahlen)), rng.randint(0, 9))
        )
    return ziehungen


def als_csv(ziehungen):
    zeilen = ["date,n1,n2,n3,n4,n5,n6,superzahl"]
    for z in ziehungen:
        sz = "" if z.superzahl is None else str(z.superzahl)
        zeilen.append(",".join([z.datum.isoformat(), *map(str, z.zahlen), sz]))
    return "\n".join(zeilen) + "\n"
```

- [ ] **Step 2: Failing Tests schreiben** – `tests/test_daten.py`:
```python
from datetime import date

import pytest

from lotto.daten import DatenFehler, Ziehung, lade_ziehungen, parse_csv
from tests.hilfen import als_csv, kuenstliche_ziehungen

KOPF = "date,n1,n2,n3,n4,n5,n6,superzahl\n"


def test_parst_gueltige_zeilen_sortiert():
    text = KOPF + "2025-04-12,44,7,14,19,28,35,3\n1955-10-09,3,12,13,16,23,41,\n"
    assert parse_csv(text) == [
        Ziehung(date(1955, 10, 9), (3, 12, 13, 16, 23, 41), None),
        Ziehung(date(2025, 4, 12), (7, 14, 19, 28, 35, 44), 3),
    ]


@pytest.mark.parametrize(
    "zeile",
    [
        "2025-04-12,7,14,19,28,35,35,3",
        "2025-04-12,0,14,19,28,35,44,3",
        "2025-04-12,7,14,19,28,35,50,3",
        "2025-04-12,7,14,19,28,35,44,10",
        "kein-datum,7,14,19,28,35,44,3",
        "2025-04-12,7,14,19,28,35,,3",
        "2025-04-12,7,14",
    ],
)
def test_lehnt_fehlerhafte_zeile_mit_zeilennummer_ab(zeile):
    with pytest.raises(DatenFehler, match="Zeile 2"):
        parse_csv(KOPF + zeile + "\n")


def test_lehnt_falsche_spalten_ab():
    with pytest.raises(DatenFehler, match="Spalten"):
        parse_csv("datum,a,b\n1,2,3\n")


def test_laedt_lokale_datei(tmp_path):
    ziehungen = kuenstliche_ziehungen(5)
    pfad = tmp_path / "results.csv"
    pfad.write_text(als_csv(ziehungen), encoding="utf-8")
    assert lade_ziehungen(pfad) == ziehungen


def test_nicht_erreichbare_url_gibt_klare_meldung():
    with pytest.raises(DatenFehler, match="nicht erreichbar"):
        lade_ziehungen("http://127.0.0.1:9/results.csv")
```

- [ ] **Step 3: Tests laufen lassen, Fehlschlag prüfen**

Run: `python -m pytest tests/test_daten.py -q`
Expected: FAIL mit `ModuleNotFoundError: No module named 'lotto.daten'`

- [ ] **Step 4: Implementierung** – `lotto/daten.py`:
```python
"""Laden und Prüfen der Lotto-6-aus-49-Ziehungen."""
from __future__ import annotations

import csv
import io
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path

CSV_URL = (
    "https://raw.githubusercontent.com/daowa89/lottery-archive/main/"
    "de/lotto_6aus49/results.csv"
)
SPALTEN = ["date", "n1", "n2", "n3", "n4", "n5", "n6", "superzahl"]


class DatenFehler(ValueError):
    """Die Ziehungsdaten fehlen oder sind ungültig."""


@dataclass(frozen=True)
class Ziehung:
    datum: date
    zahlen: tuple[int, ...]
    superzahl: int | None


def parse_csv(text: str) -> list[Ziehung]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != SPALTEN:
        raise DatenFehler(f"Unerwartete Spalten: {reader.fieldnames}")
    ziehungen = []
    for zeile_nr, zeile in enumerate(reader, start=2):
        try:
            datum = date.fromisoformat(zeile["date"])
            zahlen = tuple(sorted(int(zeile[f"n{i}"]) for i in range(1, 7)))
            sz_text = (zeile["superzahl"] or "").strip()
            superzahl = int(sz_text) if sz_text else None
        except (ValueError, TypeError) as fehler:
            raise DatenFehler(f"Zeile {zeile_nr}: {fehler}") from fehler
        if len(set(zahlen)) != 6 or not all(1 <= z <= 49 for z in zahlen):
            raise DatenFehler(f"Zeile {zeile_nr}: ungültige Zahlen {zahlen}")
        if superzahl is not None and not 0 <= superzahl <= 9:
            raise DatenFehler(f"Zeile {zeile_nr}: ungültige Superzahl {superzahl}")
        ziehungen.append(Ziehung(datum, zahlen, superzahl))
    ziehungen.sort(key=lambda z: z.datum)
    return ziehungen


def lade_ziehungen(quelle: str | Path | None = None) -> list[Ziehung]:
    """Lädt die Ziehungen von einer URL (Standard: Archiv) oder einem lokalen Pfad."""
    if quelle is None or str(quelle).startswith(("http://", "https://")):
        url = str(quelle or CSV_URL)
        try:
            with urllib.request.urlopen(url, timeout=30) as antwort:
                text = antwort.read().decode("utf-8")
        except OSError as fehler:
            raise DatenFehler(
                f"Daten nicht erreichbar ({url}): {fehler}. "
                "Gib mit --quelle einen lokalen Pfad zur CSV an."
            ) from fehler
    else:
        text = Path(quelle).read_text(encoding="utf-8")
    return parse_csv(text)
```

- [ ] **Step 5: Tests laufen lassen**

Run: `python -m pytest tests/test_daten.py -q`
Expected: 11 passed

- [ ] **Step 6: Echte Daten prüfen**

Run: `python -c "from lotto.daten import lade_ziehungen; z=lade_ziehungen(); print(len(z), z[-1])"`
Expected: `5052 Ziehung(datum=datetime.date(2026, 10, 3), …)` (oder mehr). Schlägt der Download fehl, mit `lade_ziehungen('/home/claude/lottery-archive/de/lotto_6aus49/results.csv')` gegenprüfen und den Fehler melden.

- [ ] **Step 7: Commit**
```bash
git add pyproject.toml .gitignore lotto tests
git commit -m "feat: Ziehungsdaten laden und prüfen"
```

---

### Task 2: Tipp-Generator mit Smart-Filter

**Files:**
- Create: `lotto/generator.py`, `tests/test_generator.py`

**Interfaces:**
- Produces: `zufallstipp(rng: random.Random) -> tuple[int, ...]`; `ist_beliebtes_muster(tipp: Sequence[int], letzte_ziehung: Sequence[int] | None = None) -> list[str]`; `smarter_tipp(rng: random.Random, letzte_ziehung: Sequence[int] | None = None) -> tuple[int, ...]`; Konstanten `GRUENDE` (dict Regelname → Text), `MAX_VERSUCHE = 10_000`.

- [ ] **Step 1: Failing Tests** – `tests/test_generator.py`:
```python
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
```

- [ ] **Step 2: Fehlschlag prüfen**

Run: `python -m pytest tests/test_generator.py -q`
Expected: FAIL mit `ModuleNotFoundError`

- [ ] **Step 3: Implementierung** – `lotto/generator.py`:
```python
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
```

- [ ] **Step 4: Tests laufen lassen**

Run: `python -m pytest tests/test_generator.py -q`
Expected: 16 passed

- [ ] **Step 5: Commit**
```bash
git add lotto/generator.py tests/test_generator.py
git commit -m "feat: Zufalls- und Smart-Tipp-Generator"
```

---

### Task 3: Merkmale ohne Datenleck

**Files:**
- Create: `lotto/merkmale.py`, `tests/test_merkmale.py`

**Interfaces:**
- Consumes: Zahlentupel aus `Ziehung.zahlen`.
- Produces: `one_hot(zahlen_liste) -> np.ndarray` (n, 49), int32; `merkmals_matrix(zahlen_liste) -> np.ndarray` (n, 49, 6), float; Spalten laut `MERKMAL_NAMEN = ("haeufigkeit_10", "haeufigkeit_50", "haeufigkeit_200", "seit_letztem", "rate_gesamt", "in_letzter")`. Zeile *i* nutzt nur Ziehungen < *i*.

- [ ] **Step 1: Failing Tests** – `tests/test_merkmale.py`:
```python
import numpy as np

from lotto.merkmale import MERKMAL_NAMEN, merkmals_matrix, one_hot
from tests.hilfen import kuenstliche_ziehungen

H10, H50, H200, SEIT, RATE, LETZTE = range(6)


def test_one_hot():
    x = one_hot([(1, 2, 3, 4, 5, 6)])
    assert x.shape == (1, 49) and x.sum() == 6 and x[0, :6].all()


def test_werte_an_kleinem_beispiel():
    zahlen = [(1, 2, 3, 4, 5, 6), (1, 7, 8, 9, 10, 11), (12, 13, 14, 15, 16, 17)]
    f = merkmals_matrix(zahlen)
    assert f.shape == (3, 49, len(MERKMAL_NAMEN))
    assert f[0, :, H10].sum() == 0
    assert f[2, 0, H10] == 2 and f[2, 0, H200] == 2
    assert f[2, 0, SEIT] == 1
    assert f[2, 1, SEIT] == 2
    assert f[2, 48, SEIT] == 3
    assert f[2, 0, RATE] == 1.0
    assert f[2, 0, LETZTE] == 1 and f[2, 1, LETZTE] == 0


def test_kein_datenleck():
    zahlen = [z.zahlen for z in kuenstliche_ziehungen(300, seed=3)]
    original = merkmals_matrix(zahlen)
    for i in (0, 150, 299):
        geaendert = list(zahlen)
        geaendert[i] = (44, 45, 46, 47, 48, 49)
        assert np.array_equal(merkmals_matrix(geaendert)[: i + 1], original[: i + 1])
```

- [ ] **Step 2: Fehlschlag prüfen**

Run: `python -m pytest tests/test_merkmale.py -q`
Expected: FAIL mit `ModuleNotFoundError`

- [ ] **Step 3: Implementierung** – `lotto/merkmale.py`:
```python
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
```

- [ ] **Step 4: Tests laufen lassen**

Run: `python -m pytest tests/test_merkmale.py -q`
Expected: 3 passed

- [ ] **Step 5: Commit**
```bash
git add lotto/merkmale.py tests/test_merkmale.py
git commit -m "feat: Merkmalsmatrix ohne Datenleck"
```

---

### Task 4: Backtest mit KI-Modell und Signifikanztest

**Files:**
- Create: `lotto/backtest.py`, `tests/test_backtest.py`

**Interfaces:**
- Consumes: `Ziehung`, `merkmals_matrix`, `one_hot`.
- Produces: `STRATEGIEN = ("zufall", "heiss", "kalt", "ueberfaellig", "modell")`; `StrategieErgebnis(name, mittel_treffer, anteil_3_plus, p_wert, p_korrigiert)`; `Ergebnis(n_ziehungen_gesamt, n_training, n_test, test_ab, erwartet_mittel, strategien, chi2_statistik, chi2_p_wert)` mit `als_dict() -> dict`; `backtest(ziehungen, test_ab: date, seed=0, n_permutationen=1000) -> Ergebnis`.

- [ ] **Step 1: Failing Tests** – `tests/test_backtest.py`:
```python
from datetime import date, timedelta

import pytest

from lotto.backtest import STRATEGIEN, backtest
from tests.hilfen import kuenstliche_ziehungen

START = date(2000, 1, 1)


def _strategie(ergebnis, name):
    return next(s for s in ergebnis.strategien if s.name == name)


def test_findet_kuenstlich_eingebautes_muster():
    ziehungen = kuenstliche_ziehungen(1500, seed=1, fest=7, start=START)
    e = backtest(ziehungen, START + timedelta(days=1000), n_permutationen=500)
    for name in ("heiss", "modell"):
        s = _strategie(e, name)
        assert s.mittel_treffer > 1.3, name
        assert s.p_korrigiert < 0.05, name


def test_zufallsdaten_bleiben_im_erwartbaren_bereich():
    ziehungen = kuenstliche_ziehungen(1500, seed=2, start=START)
    e = backtest(ziehungen, START + timedelta(days=1000), n_permutationen=500)
    assert e.n_training == 800 and e.n_test == 500
    assert [s.name for s in e.strategien] == list(STRATEGIEN)
    for s in e.strategien:
        assert 0.6 < s.mittel_treffer < 0.87, s.name
        assert 0 < s.p_wert <= 1 and s.p_wert <= s.p_korrigiert <= 1
    assert abs(e.erwartet_mittel - 36 / 49) < 1e-12
    assert 0 <= e.chi2_p_wert <= 1


def test_zu_wenig_trainingsdaten():
    ziehungen = kuenstliche_ziehungen(300, start=START)
    with pytest.raises(ValueError, match="Trainings"):
        backtest(ziehungen, START + timedelta(days=100))


def test_ergebnis_ist_json_tauglich():
    import json

    ziehungen = kuenstliche_ziehungen(400, seed=4, start=START)
    e = backtest(ziehungen, START + timedelta(days=300), n_permutationen=50)
    daten = json.loads(json.dumps(e.als_dict()))
    assert daten["strategien"][0]["name"] == "zufall"
```

- [ ] **Step 2: Fehlschlag prüfen**

Run: `python -m pytest tests/test_backtest.py -q`
Expected: FAIL mit `ModuleNotFoundError`

- [ ] **Step 3: Implementierung** – `lotto/backtest.py`:
```python
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
```

- [ ] **Step 4: Tests laufen lassen**

Run: `python -m pytest tests/test_backtest.py -q`
Expected: 4 passed

- [ ] **Step 5: Commit**
```bash
git add lotto/backtest.py tests/test_backtest.py
git commit -m "feat: Backtest mit Gradient Boosting und Permutationstest"
```

---

### Task 5: Datenbank-Export

**Files:**
- Create: `lotto/export_db.py`, `tests/test_export_db.py`

**Interfaces:**
- Consumes: `Ziehung`.
- Produces: `export(ziehungen, seit_jahr: int | None = None, jetzt: datetime | None = None) -> dict[str, dict]` – Schlüssel `"ziehungen/<jahr>"` → `{"ziehungen": [{"datum", "zahlen", "superzahl"}]}` und `"meta/stand"` → `{"letzte_ziehung", "aktualisiert_am", "anzahl"}`; `schreibe_export(dokumente, ordner: Path) -> list[Path]` (eine JSON-Datei pro Dokument unter `ordner/<collection>/<doc_id>.json`).

- [ ] **Step 1: Failing Tests** – `tests/test_export_db.py`:
```python
import json
from datetime import date, datetime, timezone

from lotto.export_db import export, schreibe_export
from tests.hilfen import kuenstliche_ziehungen

JETZT = datetime(2026, 10, 6, 21, 0, tzinfo=timezone.utc)


def test_jahresdokumente_enthalten_genau_alle_ziehungen():
    ziehungen = kuenstliche_ziehungen(800, start=date(2024, 6, 1))
    docs = export(ziehungen, jetzt=JETZT)
    jahre = sorted(k for k in docs if k.startswith("ziehungen/"))
    assert jahre == ["ziehungen/2024", "ziehungen/2025", "ziehungen/2026"]
    alle = [e for k in jahre for e in docs[k]["ziehungen"]]
    assert len(alle) == 800
    assert alle[0] == {
        "datum": "2024-06-01",
        "zahlen": list(ziehungen[0].zahlen),
        "superzahl": ziehungen[0].superzahl,
    }


def test_stand():
    ziehungen = kuenstliche_ziehungen(10, start=date(2026, 9, 1))
    assert export(ziehungen, jetzt=JETZT)["meta/stand"] == {
        "letzte_ziehung": "2026-09-10",
        "aktualisiert_am": "2026-10-06T21:00:00+00:00",
        "anzahl": 10,
    }


def test_seit_jahr_filtert_ganze_jahre():
    ziehungen = kuenstliche_ziehungen(800, start=date(2024, 6, 1))
    docs = export(ziehungen, seit_jahr=2026, jetzt=JETZT)
    assert sorted(docs) == ["meta/stand", "ziehungen/2026"]
    assert docs["meta/stand"]["anzahl"] == 800


def test_schreibe_export(tmp_path):
    docs = export(kuenstliche_ziehungen(3), jetzt=JETZT)
    pfade = schreibe_export(docs, tmp_path)
    assert sorted(p.relative_to(tmp_path).as_posix() for p in pfade) == [
        "meta/stand.json",
        "ziehungen/2000.json",
    ]
    assert json.loads((tmp_path / "meta/stand.json").read_text())["anzahl"] == 3
```

- [ ] **Step 2: Fehlschlag prüfen**

Run: `python -m pytest tests/test_export_db.py -q`
Expected: FAIL mit `ModuleNotFoundError`

- [ ] **Step 3: Implementierung** – `lotto/export_db.py`:
```python
"""Ziehungen als Datenbank-Dokumente für die Web-App."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from lotto.daten import Ziehung


def export(
    ziehungen: list[Ziehung],
    seit_jahr: int | None = None,
    jetzt: datetime | None = None,
) -> dict[str, dict]:
    jahre: dict[str, list] = defaultdict(list)
    for z in ziehungen:
        if seit_jahr is not None and z.datum.year < seit_jahr:
            continue
        jahre[f"ziehungen/{z.datum.year}"].append(
            {"datum": z.datum.isoformat(), "zahlen": list(z.zahlen), "superzahl": z.superzahl}
        )
    dokumente = {pfad: {"ziehungen": liste} for pfad, liste in sorted(jahre.items())}
    jetzt = jetzt or datetime.now(timezone.utc)
    dokumente["meta/stand"] = {
        "letzte_ziehung": ziehungen[-1].datum.isoformat(),
        "aktualisiert_am": jetzt.isoformat(timespec="seconds"),
        "anzahl": len(ziehungen),
    }
    return dokumente


def schreibe_export(dokumente: dict[str, dict], ordner: Path) -> list[Path]:
    pfade = []
    for pfad, inhalt in dokumente.items():
        datei = Path(ordner) / f"{pfad}.json"
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text(json.dumps(inhalt, ensure_ascii=False), encoding="utf-8")
        pfade.append(datei)
    return pfade
```

- [ ] **Step 4: Tests laufen lassen**

Run: `python -m pytest tests/test_export_db.py -q`
Expected: 4 passed

- [ ] **Step 5: Commit**
```bash
git add lotto/export_db.py tests/test_export_db.py
git commit -m "feat: Export der Ziehungen als DB-Dokumente"
```

---

### Task 6: Kommandozeile und echte Analyse

**Files:**
- Create: `lotto/cli.py`, `lotto/__main__.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `lade_ziehungen`, `DatenFehler`, `smarter_tipp`, `backtest`, `export`, `schreibe_export`.
- Produces: `main(argv: list[str] | None = None) -> int`; Befehle `tipps [--anzahl N] [--seed S] [--quelle Q]`, `analyse [--test-ab YYYY-MM-DD] [--ausgabe ergebnisse.json] [--quelle Q]`, `export [--ordner export] [--seit-jahr J] [--quelle Q]`. `ergebnisse.json` = `Ergebnis.als_dict()`.

- [ ] **Step 1: Failing Tests** – `tests/test_cli.py`:
```python
import json
import re
from datetime import date

from lotto.cli import main
from tests.hilfen import als_csv, kuenstliche_ziehungen


def _csv(tmp_path, n=400):
    pfad = tmp_path / "results.csv"
    pfad.write_text(als_csv(kuenstliche_ziehungen(n, start=date(2010, 1, 1))), encoding="utf-8")
    return str(pfad)


def test_tipps(tmp_path, capsys):
    assert main(["tipps", "--anzahl", "3", "--seed", "1", "--quelle", _csv(tmp_path)]) == 0
    ausgabe = capsys.readouterr().out
    assert len(re.findall(r"^\s+\d\)\s+(\d+\s+){5}\d+$", ausgabe, re.M)) == 3
    assert "Letzte Ziehung" in ausgabe and "Hinweis" in ausgabe


def test_analyse_schreibt_json(tmp_path, capsys):
    ausgabe = tmp_path / "ergebnisse.json"
    code = main(["analyse", "--quelle", _csv(tmp_path), "--test-ab", "2010-08-01",
                 "--ausgabe", str(ausgabe)])
    assert code == 0
    daten = json.loads(ausgabe.read_text())
    assert {s["name"] for s in daten["strategien"]} == {
        "zufall", "heiss", "kalt", "ueberfaellig", "modell"}
    assert "KI-Modell" in capsys.readouterr().out


def test_export(tmp_path):
    ordner = tmp_path / "export"
    assert main(["export", "--quelle", _csv(tmp_path), "--ordner", str(ordner)]) == 0
    assert (ordner / "meta" / "stand.json").exists()
    assert (ordner / "ziehungen" / "2010.json").exists()


def test_fehlende_daten(capsys):
    assert main(["tipps", "--quelle", "http://127.0.0.1:9/x.csv"]) == 1
    assert "nicht erreichbar" in capsys.readouterr().err
```

- [ ] **Step 2: Fehlschlag prüfen**

Run: `python -m pytest tests/test_cli.py -q`
Expected: FAIL mit `ModuleNotFoundError`

- [ ] **Step 3: Implementierung**

`lotto/cli.py`:
```python
"""Kommandozeile: python -m lotto tipps | analyse | export"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date
from pathlib import Path

from lotto.backtest import backtest
from lotto.daten import DatenFehler, lade_ziehungen
from lotto.export_db import export, schreibe_export
from lotto.generator import smarter_tipp

HINWEIS = (
    "Hinweis: Jede Kombination hat dieselbe Chance (1 : 139.838.160 auf den Jackpot). "
    "Smarte Tipps vermeiden beliebte Muster, damit du einen Gewinn seltener teilen musst."
)
NAMEN = {
    "zufall": "Reiner Zufall",
    "heiss": "Heiße Zahlen (letzte 10)",
    "kalt": "Kalte Zahlen (letzte 10)",
    "ueberfaellig": "Überfällige Zahlen",
    "modell": "KI-Modell (Gradient Boosting)",
}


def _tipps(ziehungen, args) -> None:
    letzte = ziehungen[-1]
    rng = random.Random(args.seed)
    print(f"Letzte Ziehung {letzte.datum:%d.%m.%Y}: {' '.join(map(str, letzte.zahlen))}")
    print()
    for nr in range(1, args.anzahl + 1):
        tipp = smarter_tipp(rng, letzte.zahlen)
        print(f"  {nr})  " + "  ".join(f"{z:2d}" for z in tipp))
    print()
    print(HINWEIS)


def _analyse(ziehungen, args) -> None:
    e = backtest(ziehungen, args.test_ab)
    print(f"Backtest: {e.n_training} Trainings- und {e.n_test} Testziehungen (Test ab {e.test_ab})")
    print()
    print(f"{'Strategie':32} {'Ø Treffer':>10} {'≥3 Richtige':>12} {'p (korr.)':>10}")
    for s in e.strategien:
        print(f"{NAMEN[s.name]:32} {s.mittel_treffer:10.3f} {s.anteil_3_plus:12.2%} "
              f"{s.p_korrigiert:10.3f}")
    print(f"{'Erwartet bei Zufall':32} {e.erwartet_mittel:10.3f}")
    print()
    print(f"Gleichverteilung aller {e.n_ziehungen_gesamt} Ziehungen (Chi-Quadrat): "
          f"p = {e.chi2_p_wert:.3f}")
    auffaellig = [s for s in e.strategien if s.name != "zufall" and s.p_korrigiert < 0.05]
    if auffaellig:
        namen = ", ".join(NAMEN[s.name] for s in auffaellig)
        print(f"Auffällig (p < 0,05 nach Korrektur): {namen}")
    else:
        print("Ergebnis: Keine Strategie ist signifikant besser als der Zufall.")
    Path(args.ausgabe).write_text(
        json.dumps(e.als_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Ergebnisse gespeichert in {args.ausgabe}")


def _export(ziehungen, args) -> None:
    pfade = schreibe_export(export(ziehungen, args.seit_jahr), Path(args.ordner))
    print(f"{len(pfade)} Dokumente geschrieben nach {args.ordner}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m lotto")
    sub = parser.add_subparsers(dest="befehl", required=True)
    t = sub.add_parser("tipps", help="smarte Tipps erzeugen")
    t.add_argument("--anzahl", type=int, default=5)
    t.add_argument("--seed", type=int)
    a = sub.add_parser("analyse", help="Strategien gegen den Zufall testen")
    a.add_argument("--test-ab", type=date.fromisoformat, default=date(2016, 1, 1))
    a.add_argument("--ausgabe", default="ergebnisse.json")
    x = sub.add_parser("export", help="Ziehungen als DB-Dokumente exportieren")
    x.add_argument("--ordner", default="export")
    x.add_argument("--seit-jahr", type=int)
    for p in (t, a, x):
        p.add_argument("--quelle", help="URL oder Pfad zur results.csv")
    args = parser.parse_args(argv)

    try:
        ziehungen = lade_ziehungen(args.quelle)
    except DatenFehler as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 1
    {"tipps": _tipps, "analyse": _analyse, "export": _export}[args.befehl](ziehungen, args)
    return 0
```

`lotto/__main__.py`:
```python
import sys

from lotto.cli import main

sys.exit(main())
```

- [ ] **Step 4: Tests laufen lassen**

Run: `python -m pytest -q`
Expected: alle Tests grün (42 passed)

- [ ] **Step 5: Echte Analyse ausführen**

Run: `python -m lotto analyse && python -m lotto tipps`
Expected: Tabelle mit 5 Strategien, Zeile „Ergebnis: …“, Datei `ergebnisse.json`; danach 5 Tipps. Ausgabe für den Nutzer festhalten (geht in die Abschlussnachricht).

- [ ] **Step 6: Commit**
```bash
git add lotto/cli.py lotto/__main__.py tests/test_cli.py
git commit -m "feat: Kommandozeile für Tipps, Analyse und Export"
```

---

### Task 7: JavaScript-Logik der Web-App

**Files:**
- Create: `web/logik.js`, `web/logik.test.js`

**Interfaces:**
- Produces (global `Lotto` im Browser, `module.exports` in Node): `GRUENDE` (dieselben Texte wie Python), `zufallstipp(rand?) -> number[6]`, `istBeliebtesMuster(tipp, letzte|null) -> string[]`, `smarterTipp(letzte|null, rand?) -> number[6]`, `auswertung(tipp, superzahl|null, ziehung{zahlen, superzahl}) -> {richtige, szTreffer, klasse|null}`, `erwarteteVerteilung() -> number[7]` (P(k Richtige)), `gewinnWahrscheinlichkeit() -> number`, `haeufigkeiten(ziehungen) -> number[49]`, `naechsteZiehungstage(heute: Date, n) -> string[]` (ISO-Daten, Mi/Sa).

- [ ] **Step 1: Failing Tests** – `web/logik.test.js`:
```js
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("./logik.js");

function seeded(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 2 ** 32);
}

test("zufallstipp ist gültig", () => {
  const rand = seeded(1);
  for (let i = 0; i < 500; i++) {
    const t = L.zufallstipp(rand);
    assert.equal(new Set(t).size, 6);
    assert.deepEqual(t, [...t].sort((a, b) => a - b));
    assert.ok(t.every((z) => z >= 1 && z <= 49));
  }
});

test("Filterregeln wie in Python", () => {
  const f = (t, l = null) => L.istBeliebtesMuster(t, l);
  assert.deepEqual(f([3, 14, 25, 36, 40, 47]), []);
  assert.deepEqual(f([1, 5, 12, 19, 25, 31]), [L.GRUENDE.geburtstage]);
  assert.deepEqual(f([10, 11, 12, 13, 30, 45]), [L.GRUENDE.folge]);
  assert.deepEqual(f([4, 13, 22, 31, 40, 49]), [L.GRUENDE.abstaende]);
  assert.deepEqual(f([36, 37, 38, 40, 41, 42]), [L.GRUENDE.zeile_spalte]);
  assert.deepEqual(f([2, 9, 16, 23, 30, 44]), [L.GRUENDE.zeile_spalte]);
  assert.deepEqual(f([1, 9, 17, 25, 33, 49]), [L.GRUENDE.diagonale]);
  assert.deepEqual(f([3, 14, 25, 36, 40, 47], [3, 14, 25, 1, 2, 4]), [L.GRUENDE.letzte]);
});

test("smarterTipp verletzt keine Regel", () => {
  const rand = seeded(2);
  const letzte = [5, 7, 19, 24, 33, 46];
  for (let i = 0; i < 1000; i++) {
    assert.deepEqual(L.istBeliebtesMuster(L.smarterTipp(letzte, rand), letzte), []);
  }
});

test("Gewinnklassen", () => {
  const z = { zahlen: [1, 2, 3, 4, 5, 6], superzahl: 7 };
  const k = (tipp, sz) => L.auswertung(tipp, sz, z).klasse;
  assert.equal(k([1, 2, 3, 4, 5, 6], 7), 1);
  assert.equal(k([1, 2, 3, 4, 5, 6], 0), 2);
  assert.equal(k([1, 2, 3, 4, 5, 40], 7), 3);
  assert.equal(k([1, 2, 3, 4, 5, 40], 0), 4);
  assert.equal(k([1, 2, 3, 4, 40, 41], 7), 5);
  assert.equal(k([1, 2, 3, 4, 40, 41], 0), 6);
  assert.equal(k([1, 2, 3, 40, 41, 42], 7), 7);
  assert.equal(k([1, 2, 3, 40, 41, 42], 0), 8);
  assert.equal(k([1, 2, 40, 41, 42, 43], 7), 9);
  assert.equal(k([1, 2, 40, 41, 42, 43], 0), null);
  assert.equal(k([1, 2, 3, 4, 5, 6], null), 2);
  const a = L.auswertung([1, 2, 3, 40, 41, 42], 7, z);
  assert.equal(a.richtige, 3);
  assert.equal(a.szTreffer, true);
});

test("Wahrscheinlichkeiten", () => {
  const p = L.erwarteteVerteilung();
  assert.ok(Math.abs(p.reduce((a, b) => a + b, 0) - 1) < 1e-12);
  assert.ok(Math.abs(p[6] - 1 / 13983816) < 1e-15);
  assert.ok(Math.abs(1 / L.gewinnWahrscheinlichkeit() - 31.4) < 0.5);
});

test("Häufigkeiten und Ziehungstage", () => {
  const h = L.haeufigkeiten([{ zahlen: [1, 2, 3, 4, 5, 6] }, { zahlen: [1, 7, 8, 9, 10, 11] }]);
  assert.equal(h.length, 49);
  assert.equal(h[0], 2);
  assert.equal(h[48], 0);
  // Dienstag, 6.10.2026 -> Mi 7.10., Sa 10.10., Mi 14.10.
  assert.deepEqual(L.naechsteZiehungstage(new Date(2026, 9, 6, 21, 0), 3),
    ["2026-10-07", "2026-10-10", "2026-10-14"]);
  // Samstag zählt mit
  assert.deepEqual(L.naechsteZiehungstage(new Date(2026, 9, 10, 9, 0), 1), ["2026-10-10"]);
});
```

- [ ] **Step 2: Fehlschlag prüfen**

Run: `node --test web/logik.test.js`
Expected: FAIL mit `Cannot find module './logik.js'`

- [ ] **Step 3: Implementierung** – `web/logik.js`:
```js
(function (root) {
  "use strict";
  const MAX_VERSUCHE = 10000;
  const GRUENDE = {
    geburtstage: "nur Zahlen bis 31 (Geburtstage)",
    folge: "4 oder mehr aufeinanderfolgende Zahlen",
    abstaende: "gleichmäßige Abstände",
    zeile_spalte: "alle in einer Zeile oder Spalte des Tippscheins",
    diagonale: "alle auf einer Diagonale des Tippscheins",
    letzte: "3 oder mehr Zahlen aus der letzten Ziehung",
  };
  const KLASSEN = [[6, true, 1], [6, false, 2], [5, true, 3], [5, false, 4],
    [4, true, 5], [4, false, 6], [3, true, 7], [3, false, 8], [2, true, 9]];

  function zufallstipp(rand = Math.random) {
    const pool = Array.from({ length: 49 }, (_, i) => i + 1);
    for (let i = 0; i < 6; i++) {
      const j = i + Math.floor(rand() * (49 - i));
      [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    return pool.slice(0, 6).sort((a, b) => a - b);
  }

  const zeile = (z) => Math.floor((z - 1) / 7);
  const spalte = (z) => (z - 1) % 7;
  const einheitlich = (t, f) => new Set(t.map(f)).size === 1;

  function istBeliebtesMuster(tipp, letzte) {
    const t = [...tipp].sort((a, b) => a - b);
    const g = [];
    if (t[5] <= 31) g.push(GRUENDE.geburtstage);
    let lauf = 1, laengster = 1;
    for (let i = 1; i < 6; i++) {
      lauf = t[i] === t[i - 1] + 1 ? lauf + 1 : 1;
      laengster = Math.max(laengster, lauf);
    }
    if (laengster >= 4) g.push(GRUENDE.folge);
    if (new Set(t.slice(1).map((z, i) => z - t[i])).size === 1) g.push(GRUENDE.abstaende);
    if (einheitlich(t, zeile) || einheitlich(t, spalte)) g.push(GRUENDE.zeile_spalte);
    if (einheitlich(t, (z) => zeile(z) - spalte(z)) || einheitlich(t, (z) => zeile(z) + spalte(z))) {
      g.push(GRUENDE.diagonale);
    }
    if (letzte && t.filter((z) => letzte.includes(z)).length >= 3) g.push(GRUENDE.letzte);
    return g;
  }

  function smarterTipp(letzte, rand = Math.random) {
    for (let i = 0; i < MAX_VERSUCHE; i++) {
      const t = zufallstipp(rand);
      if (istBeliebtesMuster(t, letzte).length === 0) return t;
    }
    throw new Error("Kein gültiger Tipp nach " + MAX_VERSUCHE + " Versuchen");
  }

  function auswertung(tipp, superzahl, ziehung) {
    const richtige = tipp.filter((z) => ziehung.zahlen.includes(z)).length;
    const szTreffer = superzahl != null && ziehung.superzahl != null &&
      Number(superzahl) === Number(ziehung.superzahl);
    const k = KLASSEN.find(([r, mitSz]) => r === richtige && (!mitSz || szTreffer));
    return { richtige, szTreffer, klasse: k ? k[2] : null };
  }

  function binom(n, k) {
    let r = 1;
    for (let i = 1; i <= k; i++) r = (r * (n - k + i)) / i;
    return r;
  }

  function erwarteteVerteilung() {
    const gesamt = binom(49, 6);
    return [0, 1, 2, 3, 4, 5, 6].map((k) => (binom(6, k) * binom(43, 6 - k)) / gesamt);
  }

  function gewinnWahrscheinlichkeit() {
    const p = erwarteteVerteilung();
    return p[3] + p[4] + p[5] + p[6] + p[2] * 0.1;
  }

  function haeufigkeiten(ziehungen) {
    const h = new Array(49).fill(0);
    for (const z of ziehungen) for (const n of z.zahlen) h[n - 1]++;
    return h;
  }

  function isoDatum(d) {
    const p = (n) => String(n).padStart(2, "0");
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
  }

  function naechsteZiehungstage(heute, n) {
    const tage = [];
    const d = new Date(heute.getFullYear(), heute.getMonth(), heute.getDate());
    while (tage.length < n) {
      if (d.getDay() === 3 || d.getDay() === 6) tage.push(isoDatum(d));
      d.setDate(d.getDate() + 1);
    }
    return tage;
  }

  const api = { GRUENDE, zufallstipp, istBeliebtesMuster, smarterTipp, auswertung,
    erwarteteVerteilung, gewinnWahrscheinlichkeit, haeufigkeiten, naechsteZiehungstage, isoDatum };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Lotto = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
```

- [ ] **Step 4: Tests laufen lassen**

Run: `node --test web/logik.test.js`
Expected: 6 Tests, alle pass

- [ ] **Step 5: Commit**
```bash
git add web/logik.js web/logik.test.js
git commit -m "feat: Tipp- und Gewinnlogik für die Web-App"
```

---

### Task 8: Web-App bauen, veröffentlichen und befüllen

**Files:**
- Create: `web/seite.html`, `web/build.py`
- Output: `dist/lotto-labor.html`

**Interfaces:**
- Consumes: `web/logik.js` (global `Lotto`), `ergebnisse.json` aus Task 6, Export-Ordner aus `python -m lotto export`.
- Produces: veröffentlichte Artifact-URL (für Task 9); DB-Dokumente laut Global Constraints.

Vor dem Schreiben der Seite den Skill `artifact-design` geladen haben (in dieser Sitzung bereits erledigt). Designrichtung: Tippschein-Optik – Raster 7×7 mit roten Kreuzen, schmale Display-Schrift für Zahlen, kühles Papiergrau, Signalrot als einziger Akzent.

- [ ] **Step 1: Build-Skript** – `web/build.py`:
```python
"""Fügt logik.js und ergebnisse.json in seite.html ein -> dist/lotto-labor.html"""
import json
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent


def baue(ergebnisse_pfad: Path, ziel: Path) -> Path:
    seite = (WURZEL / "web" / "seite.html").read_text(encoding="utf-8")
    logik = (WURZEL / "web" / "logik.js").read_text(encoding="utf-8")
    ergebnisse = json.loads(ergebnisse_pfad.read_text(encoding="utf-8"))
    ergebnisse_js = json.dumps(ergebnisse, ensure_ascii=False).replace("</", "<\\/")
    for platzhalter in ("/*__LOGIK__*/", "__ERGEBNISSE_JSON__"):
        if seite.count(platzhalter) != 1:
            raise SystemExit(f"Platzhalter {platzhalter} fehlt oder ist doppelt")
    html = seite.replace("/*__LOGIK__*/", logik).replace("__ERGEBNISSE_JSON__", ergebnisse_js)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(html, encoding="utf-8")
    return ziel


if __name__ == "__main__":
    quelle = Path(sys.argv[1]) if len(sys.argv) > 1 else WURZEL / "ergebnisse.json"
    print(baue(quelle, WURZEL / "dist" / "lotto-labor.html"))
```

- [ ] **Step 2: Seitenvorlage** – `web/seite.html`:
```html
<title>Lotto-Labor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;700&family=Source+Sans+3:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: eine Spalte; Tippscheine im Raster, darunter Meine Tipps, Bilanz, Analyse */
:root {
  --papier: #eef1ee;
  --flaeche: #fbfcfb;
  --tinte: #1b1f1d;
  --leise: #59635d;
  --linie: #cdd5cf;
  --signal: #c8102e;
  --signal-weich: #f7dfe3;
  --gut: #1d7348;
  --font-display: "Barlow Condensed", "Arial Narrow", sans-serif;
  --font-text: "Source Sans 3", system-ui, sans-serif;
  --font-zahl: "IBM Plex Mono", ui-monospace, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --papier: #121514; --flaeche: #1b1f1d; --tinte: #e6ebe7; --leise: #9aa49e;
    --linie: #313833; --signal: #ff5b6f; --signal-weich: #3a1d23; --gut: #5cc690;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --papier: #121514; --flaeche: #1b1f1d; --tinte: #e6ebe7; --leise: #9aa49e;
  --linie: #313833; --signal: #ff5b6f; --signal-weich: #3a1d23; --gut: #5cc690;
  color-scheme: dark;
}
* { box-sizing: border-box; }
body { background: var(--papier); color: var(--tinte); font-family: var(--font-text);
  font-size: 16px; line-height: 1.5; }
.seite { max-width: 1040px; margin: 0 auto; padding-inline: 16px; padding-block: 28px 56px;
  display: grid; gap: 44px; }
h1, h2 { font-family: var(--font-display); font-weight: 700; line-height: 1.05;
  text-wrap: balance; margin: 0; letter-spacing: 0.01em; }
h1 { font-size: clamp(2.4rem, 7vw, 3.6rem); }
h1 span { color: var(--signal); }
h2 { font-size: 1.75rem; }
p { margin: 0; max-width: 65ch; }
.leise { color: var(--leise); }
.etikett { font-family: var(--font-zahl); font-size: 0.75rem; text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--leise); }
header { display: grid; gap: 10px; }
.stand { font-family: var(--font-zahl); font-size: 0.85rem; color: var(--leise); }
section { display: grid; gap: 16px; }
.kopfzeile { display: flex; flex-wrap: wrap; align-items: end; justify-content: space-between; gap: 12px; }
button { font: 600 0.95rem var(--font-text); border-radius: 6px; cursor: pointer;
  padding: 9px 16px; border: 1px solid var(--tinte); background: var(--tinte); color: var(--papier); }
button.zweit { background: transparent; color: var(--tinte); border-color: var(--linie); }
button.gefahr { background: transparent; color: var(--signal); border-color: var(--signal); }
button:focus-visible, input:focus-visible, select:focus-visible { outline: 3px solid var(--signal); outline-offset: 2px; }
button:disabled { opacity: 0.5; cursor: default; }
.scheine { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 16px; }
.schein { background: var(--flaeche); border: 1px solid var(--linie); border-radius: 8px;
  padding: 14px; display: grid; gap: 12px; }
.feld { display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; }
.feld span { position: relative; aspect-ratio: 1; max-width: 100%; display: grid; place-items: center;
  font: 500 0.7rem var(--font-zahl); color: var(--leise); border: 1px solid var(--linie); border-radius: 2px; }
.feld span.an { color: var(--tinte); border-color: var(--signal); }
.feld span.an::before, .feld span.an::after { content: ""; position: absolute; left: 12%; right: 12%;
  top: 50%; height: 2px; background: var(--signal); }
.feld span.an::before { transform: rotate(45deg); }
.feld span.an::after { transform: rotate(-45deg); }
.zahlen { font: 700 1.35rem var(--font-display); letter-spacing: 0.04em;
  font-variant-numeric: tabular-nums; }
.speichern { display: grid; grid-template-columns: 1fr 64px; gap: 6px; }
.speichern button { grid-column: 1 / -1; }
label { display: grid; gap: 2px; font-size: 0.75rem; color: var(--leise); }
input, select { font: 400 0.9rem var(--font-text); padding: 6px 8px; border-radius: 5px;
  border: 1px solid var(--linie); background: var(--papier); color: var(--tinte); min-width: 0; }
.hinweis-box { border-left: 3px solid var(--signal); padding: 4px 0 4px 14px; }
.liste { display: grid; gap: 8px; }
.tipp-zeile { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 6px 16px; align-items: center;
  background: var(--flaeche); border: 1px solid var(--linie); border-radius: 8px; padding: 12px 14px; }
.tipp-zeile .zahlen { font-size: 1.15rem; }
.tipp-zeile .zahlen b { color: var(--signal); }
.chip { font: 500 0.75rem var(--font-zahl); padding: 3px 9px; border-radius: 99px; white-space: nowrap;
  border: 1px solid var(--linie); color: var(--leise); }
.chip.gewinn { border-color: var(--gut); color: var(--gut); }
.chip.signal { border-color: var(--signal); color: var(--signal); background: var(--signal-weich); }
.aktionen { display: flex; gap: 8px; grid-column: 1 / -1; flex-wrap: wrap; align-items: center; }
.aktionen button { padding: 4px 10px; font-size: 0.8rem; }
.leer { border: 1px dashed var(--linie); border-radius: 8px; padding: 18px; color: var(--leise); }
.tabelle-huelle { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; min-width: 520px; }
th, td { text-align: right; padding: 8px 10px; border-bottom: 1px solid var(--linie); }
th:first-child, td:first-child { text-align: left; }
th { font: 500 0.75rem var(--font-zahl); text-transform: uppercase; letter-spacing: 0.06em; color: var(--leise); }
td { font-family: var(--font-zahl); font-size: 0.9rem; }
td:first-child { font-family: var(--font-text); }
.diagramm { background: var(--flaeche); border: 1px solid var(--linie); border-radius: 8px; padding: 12px; }
.diagramm svg { display: block; width: 100%; height: auto; }
.zwei { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); gap: 24px; }
.zwei > * { min-width: 0; }
@media (prefers-reduced-motion: no-preference) {
  .schein { animation: rein 240ms ease-out both; }
  @keyframes rein { from { transform: translateY(4px); } to { transform: none; } }
}
</style>

<main class="seite">
  <header>
    <div class="etikett">Lotto 6 aus 49</div>
    <h1>Lotto-<span>Labor</span></h1>
    <p class="leise">Zufällige Tipps ohne beliebte Muster, deine gespielten Scheine mit Gewinncheck und ein Test, ob Muster die nächste Ziehung vorhersagen.</p>
    <div class="stand" id="stand">Ziehungen werden geladen …</div>
  </header>

  <section aria-labelledby="t-tipps">
    <div class="kopfzeile">
      <h2 id="t-tipps">Smarte Tipps</h2>
      <button id="neu" type="button">5 neue Tipps</button>
    </div>
    <p class="hinweis-box">Jeder Tipp hat dieselbe Chance von 1 : 139.838.160 auf den Jackpot. Diese Tipps meiden Geburtstage, Reihen auf dem Schein und die letzten Gewinnzahlen. So teilst du einen Gewinn mit weniger Leuten.</p>
    <div class="scheine" id="scheine"></div>
  </section>

  <section aria-labelledby="t-meine" id="bereich-meine">
    <h2 id="t-meine">Meine Tipps</h2>
    <div class="liste" id="meine"></div>
  </section>

  <section aria-labelledby="t-bilanz" id="bereich-bilanz">
    <h2 id="t-bilanz">Meine Bilanz</h2>
    <div id="bilanz"></div>
  </section>

  <section aria-labelledby="t-analyse">
    <h2 id="t-analyse">Gibt es Muster?</h2>
    <div class="zwei">
      <div class="liste">
        <div class="etikett">Wie oft kam jede Zahl seit 1955</div>
        <div class="diagramm" id="diagramm"></div>
        <p class="leise" id="diagramm-text"></p>
      </div>
      <div class="liste">
        <div class="etikett" id="backtest-titel"></div>
        <div class="tabelle-huelle"><table id="backtest"></table></div>
        <p id="backtest-fazit"></p>
      </div>
    </div>
  </section>
</main>

<script>/*__LOGIK__*/</script>
<script>
"use strict";
const ERGEBNISSE = __ERGEBNISSE_JSON__;
const NAMEN = { zufall: "Reiner Zufall", heiss: "Heiße Zahlen (letzte 10)",
  kalt: "Kalte Zahlen (letzte 10)", ueberfaellig: "Überfällige Zahlen",
  modell: "KI-Modell (Gradient Boosting)" };
const Z = { jahre: new Map(), stand: null, standGeladen: false, tipps: [], vorschlaege: [], geklickt: false,
  db: null, uid: null, speichernMoeglich: false, loeschFrage: null };

const $ = (id) => document.getElementById(id);
function el(tag, attrs, ...kinder) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v);
  }
  for (const kind of kinder.flat()) if (kind != null) e.append(kind);
  return e;
}
const fmtDatum = (iso) => { const [j, m, t] = iso.split("-"); return t + "." + m + "." + j; };
const fmtZahl = (x, n = 0) => x.toLocaleString("de-DE", { minimumFractionDigits: n, maximumFractionDigits: n });

function alleZiehungen() {
  return [...Z.jahre.values()].flat().sort((a, b) => (a.datum < b.datum ? -1 : 1));
}
function letzteZiehung() { const a = alleZiehungen(); return a.length ? a[a.length - 1] : null; }

/* ---------- Tipps ---------- */
function neueVorschlaege() {
  const letzte = letzteZiehung();
  Z.vorschlaege = Array.from({ length: 5 }, () => Lotto.smarterTipp(letzte ? letzte.zahlen : null));
  renderVorschlaege();
}

function feld(tipp) {
  return el("div", { class: "feld", "aria-hidden": "true" },
    Array.from({ length: 49 }, (_, i) => el("span", { class: tipp.includes(i + 1) ? "an" : "" }, String(i + 1))));
}

function renderVorschlaege() {
  const tage = Lotto.naechsteZiehungstage(new Date(), 4);
  $("scheine").replaceChildren(...Z.vorschlaege.map((tipp, nr) => {
    const kinder = [feld(tipp), el("div", { class: "zahlen" }, tipp.join("  "))];
    if (Z.speichernMoeglich) {
      const datum = el("select", { id: "datum-" + nr, "aria-label": "Ziehung" },
        tage.map((t) => el("option", { value: t }, fmtDatum(t))));
      const sz = el("input", { id: "sz-" + nr, inputmode: "numeric", maxlength: "1",
        placeholder: "0–9", "aria-label": "Superzahl" });
      const knopf = el("button", { class: "zweit", type: "button" }, "Als gespielt speichern");
      knopf.addEventListener("click", () => speichern(tipp, datum.value, sz.value, knopf));
      kinder.push(el("div", { class: "speichern" },
        el("label", {}, "Ziehung", datum),
        el("label", {}, "Superzahl", sz),
        knopf));
    }
    return el("div", { class: "schein" }, kinder);
  }));
}

async function speichern(tipp, ziehungsdatum, szText, knopf) {
  const sz = szText.trim() === "" ? null : Number(szText.trim());
  if (sz !== null && !(Number.isInteger(sz) && sz >= 0 && sz <= 9)) {
    knopf.textContent = "Superzahl muss 0–9 sein";
    return;
  }
  knopf.disabled = true;
  knopf.textContent = "Speichert …";
  try {
    await Z.db.collection("data/users/" + Z.uid).add({
      ziehungsdatum, zahlen: tipp, superzahl: sz, erstellt_am: new Date().toISOString() });
    knopf.textContent = "Gespeichert";
  } catch (e) {
    knopf.disabled = false;
    knopf.textContent = e && e.code === "quota_exceeded"
      ? "Speicher voll – lösche alte Tipps" : "Nicht gespeichert – nochmal versuchen";
  }
}

/* ---------- Meine Tipps & Bilanz ---------- */
function ziehungNachDatum() {
  const m = new Map();
  for (const z of alleZiehungen()) m.set(z.datum, z);
  return m;
}

function renderMeine() {
  if (!Z.speichernMoeglich) {
    $("meine").replaceChildren(el("div", { class: "leer" },
      "Melde dich mit deinem Claude-Konto an (oder bitte um Mitwirkenden-Zugriff), um gespielte Tipps zu speichern und automatisch auszuwerten."));
    return;
  }
  if (!Z.tipps.length) {
    $("meine").replaceChildren(el("div", { class: "leer" },
      "Noch keine Tipps gespeichert. Wähle oben bei einem Schein die Ziehung, trag die Superzahl deines Scheins ein (letzte Ziffer der Losnummer) und tippe auf „Als gespielt speichern“."));
    return;
  }
  const ziehungen = ziehungNachDatum();
  const sortiert = [...Z.tipps].sort((a, b) => (a.daten.ziehungsdatum < b.daten.ziehungsdatum ? 1 : -1));
  $("meine").replaceChildren(...sortiert.map(({ id, daten }) => {
    const z = ziehungen.get(daten.ziehungsdatum);
    const zahlen = el("div", { class: "zahlen" });
    daten.zahlen.forEach((n, i) => {
      if (i) zahlen.append("  ");
      zahlen.append(z && z.zahlen.includes(n) ? el("b", {}, String(n)) : String(n));
    });
    let chip;
    if (!z) chip = el("span", { class: "chip" }, "wartet auf Ziehung");
    else {
      const a = Lotto.auswertung(daten.zahlen, daten.superzahl, z);
      const text = a.richtige + " Richtige" + (a.szTreffer ? " + SZ" : "");
      chip = a.klasse
        ? el("span", { class: "chip gewinn" }, text + " · Klasse " + a.klasse)
        : el("span", { class: "chip" }, text);
    }
    const info = el("div", { class: "leise" }, "Ziehung " + fmtDatum(daten.ziehungsdatum) +
      " · Superzahl " + (daten.superzahl == null ? "–" : daten.superzahl));
    const loeschen = el("button", { class: Z.loeschFrage === id ? "gefahr" : "zweit", type: "button" },
      Z.loeschFrage === id ? "Wirklich löschen" : "Löschen");
    loeschen.addEventListener("click", () => loesche(id));
    const aktionen = el("div", { class: "aktionen" }, info, loeschen);
    if (Z.loeschFrage === id) {
      const abbrechen = el("button", { class: "zweit", type: "button" }, "Abbrechen");
      abbrechen.addEventListener("click", () => { Z.loeschFrage = null; renderMeine(); });
      aktionen.append(abbrechen);
    }
    return el("div", { class: "tipp-zeile" }, zahlen, chip, aktionen);
  }));
}

async function loesche(id) {
  if (Z.loeschFrage !== id) { Z.loeschFrage = id; renderMeine(); return; }
  Z.loeschFrage = null;
  try { await Z.db.collection("data/users/" + Z.uid).doc(id).delete(); }
  catch (e) { renderMeine(); }
}

function renderBilanz() {
  $("bereich-bilanz").hidden = !Z.speichernMoeglich;
  if (!Z.speichernMoeglich) return;
  const ziehungen = ziehungNachDatum();
  const ausgewertet = Z.tipps
    .map(({ daten }) => { const z = ziehungen.get(daten.ziehungsdatum);
      return z ? Lotto.auswertung(daten.zahlen, daten.superzahl, z) : null; })
    .filter(Boolean);
  if (!ausgewertet.length) {
    $("bilanz").replaceChildren(el("div", { class: "leer" },
      "Sobald eine Ziehung deiner gespeicherten Tipps stattgefunden hat, siehst du hier, wie oft du wie viele Richtige hattest, im Vergleich zum reinen Zufall."));
    return;
  }
  const n = ausgewertet.length;
  const p = Lotto.erwarteteVerteilung();
  const zeilen = [0, 1, 2, 3, 4, 5, 6].map((k) => el("tr", {},
    el("td", {}, k + " Richtige"),
    el("td", {}, String(ausgewertet.filter((a) => a.richtige === k).length)),
    el("td", {}, fmtZahl(n * p[k], 2))));
  const gewinne = ausgewertet.filter((a) => a.klasse).length;
  zeilen.push(el("tr", {}, el("td", {}, el("b", {}, "Mit Gewinnklasse")),
    el("td", {}, String(gewinne)), el("td", {}, fmtZahl(n * Lotto.gewinnWahrscheinlichkeit(), 2))));
  $("bilanz").replaceChildren(
    el("p", { class: "leise" }, n + " ausgewertete Tipps. Rechts steht, wie viele bei reinem Zufall zu erwarten wären."),
    el("div", { class: "tabelle-huelle" }, el("table", {},
      el("thead", {}, el("tr", {}, el("th", {}, "Ergebnis"), el("th", {}, "Deine Tipps"), el("th", {}, "Erwartet"))),
      el("tbody", {}, zeilen))));
}

/* ---------- Analyse ---------- */
function renderDiagramm() {
  const ziehungen = alleZiehungen();
  if (!ziehungen.length) {
    $("diagramm").replaceChildren(el("div", { class: "leise" }, "Ziehungen werden geladen …"));
    $("diagramm-text").textContent = "";
    return;
  }
  const h = Lotto.haeufigkeiten(ziehungen);
  const erwartet = (ziehungen.length * 6) / 49;
  const max = Math.ceil(Math.max(...h) / 100) * 100;
  const B = 640, H = 240, L = 40, R = 8, O = 10, U = 26;
  const breite = (B - L - R) / 49;
  const y = (v) => O + (H - O - U) * (1 - v / max);
  const ns = "http://www.w3.org/2000/svg";
  const s = (tag, a, text) => { const e = document.createElementNS(ns, tag);
    for (const [k, v] of Object.entries(a)) e.setAttribute(k, v); if (text != null) e.textContent = text; return e; };
  const svg = s("svg", { viewBox: `0 0 ${B} ${H}`, role: "img",
    "aria-label": "Häufigkeit der Zahlen 1 bis 49; alle liegen nahe am Erwartungswert" });
  for (let t = 0; t <= max; t += max / 4) {
    svg.append(s("line", { x1: L, x2: B - R, y1: y(t), y2: y(t), stroke: "var(--linie)", "stroke-width": 1 }));
    svg.append(s("text", { x: L - 6, y: y(t) + 4, "text-anchor": "end", fill: "var(--leise)",
      "font-size": 10, "font-family": "IBM Plex Mono, monospace" }, fmtZahl(t)));
  }
  h.forEach((v, i) => {
    const x = L + i * breite;
    const balken = s("rect", { x: x + 1, y: y(v), width: breite - 2, height: y(0) - y(v), fill: "var(--tinte)", opacity: 0.8 });
    balken.append(s("title", {}, "Zahl " + (i + 1) + ": " + v + "×"));
    svg.append(balken);
    if ((i + 1) % 7 === 0 || i === 0) svg.append(s("text", { x: x + breite / 2, y: H - 8, "text-anchor": "middle",
      fill: "var(--leise)", "font-size": 10, "font-family": "IBM Plex Mono, monospace" }, String(i + 1)));
  });
  svg.append(s("line", { x1: L, x2: B - R, y1: y(erwartet), y2: y(erwartet), stroke: "var(--signal)",
    "stroke-width": 2, "stroke-dasharray": "5 4" }));
  $("diagramm").replaceChildren(svg);
  const min = Math.min(...h), maxV = Math.max(...h);
  $("diagramm-text").textContent = "Rote Linie: bei reinem Zufall erwartet (" + fmtZahl(erwartet) +
    "×). Die seltenste Zahl kam " + min + "×, die häufigste " + maxV + "×. Solche Abstände entstehen auch bei echtem Zufall.";
}

function renderBacktest() {
  const e = ERGEBNISSE;
  $("backtest-titel").textContent = "Backtest auf " + fmtZahl(e.n_test) + " Ziehungen ab " + fmtDatum(e.test_ab);
  const kopf = el("tr", {}, el("th", {}, "Strategie"), el("th", {}, "Ø Treffer"),
    el("th", {}, "≥ 3 Richtige"), el("th", {}, "Urteil"));
  const zeilen = e.strategien.map((s) => el("tr", {},
    el("td", {}, NAMEN[s.name]),
    el("td", {}, fmtZahl(s.mittel_treffer, 3)),
    el("td", {}, fmtZahl(s.anteil_3_plus * 100, 1) + " %"),
    el("td", {}, s.name === "zufall" ? el("span", { class: "chip" }, "Vergleich")
      : s.p_korrigiert < 0.05 ? el("span", { class: "chip signal" }, "besser als Zufall")
      : el("span", { class: "chip" }, "nicht besser"))));
  zeilen.push(el("tr", {}, el("td", {}, "Erwartet bei Zufall"), el("td", {}, fmtZahl(e.erwartet_mittel, 3)),
    el("td", {}, fmtZahl(Lotto.erwarteteVerteilung().slice(3).reduce((a, b) => a + b, 0) * 100, 1) + " %"), el("td", {}, "")));
  $("backtest").replaceChildren(el("thead", {}, kopf), el("tbody", {}, zeilen));
  const besser = e.strategien.filter((s) => s.name !== "zufall" && s.p_korrigiert < 0.05);
  $("backtest-fazit").textContent = besser.length
    ? "Auffällig: " + besser.map((s) => NAMEN[s.name]).join(", ") + " liegt signifikant über dem Zufall."
    : "Keine Strategie, auch nicht das KI-Modell, trifft signifikant öfter als reiner Zufall. Alle Modelle wurden bis " +
      fmtDatum(e.test_ab) + " trainiert und an Ziehungen getestet, die sie nie gesehen hatten.";
}

function renderStand() {
  if (!Z.standGeladen) return;
  const s = Z.stand;
  $("stand").textContent = s
    ? "Letzte Ziehung: " + fmtDatum(s.letzte_ziehung) + " · " + fmtZahl(s.anzahl) + " Ziehungen · aktualisiert " +
      new Date(s.aktualisiert_am).toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" })
    : "Noch keine Ziehungsdaten in der Datenbank.";
}

/* ---------- Start ---------- */
function alles() { renderStand(); renderMeine(); renderBilanz(); renderDiagramm(); }

async function start() {
  neueVorschlaege();
  renderBacktest();
  alles();
  $("neu").addEventListener("click", () => { Z.geklickt = true; neueVorschlaege(); });

  const c = window.claude;
  const [db, user] = c ? await Promise.all([c.use("db"), c.use("user")]) : [null, null];
  if (!db) { $("stand").textContent = "Ziehungsdaten sind in dieser Ansicht nicht verfügbar."; return; }
  Z.db = db;
  Z.uid = user ? await user.id() : null;
  Z.speichernMoeglich = Boolean(Z.uid);
  renderVorschlaege();

  db.collection("ziehungen").onSnapshot((snap) => {
    Z.jahre = new Map(snap.docs.filter((d) => d.exists).map((d) => [d.id, d.data().ziehungen || []]));
    if (!Z.geklickt) neueVorschlaege();
    alles();
  }, () => { $("stand").textContent = "Ziehungen konnten nicht geladen werden. Lade die Seite neu."; });
  db.doc("meta/stand").onSnapshot((d) => { Z.standGeladen = true; Z.stand = d.exists ? d.data() : null; renderStand(); });
  if (Z.uid) {
    db.collection("data/users/" + Z.uid).onSnapshot((snap) => {
      Z.tipps = snap.docs.filter((d) => d.exists).map((d) => ({ id: d.id, daten: d.data() }));
      renderMeine(); renderBilanz();
    }, () => { Z.speichernMoeglich = false; renderVorschlaege(); renderMeine(); renderBilanz(); });
  }
}
start();
</script>
```

- [ ] **Step 3: Bauen und Skript-Syntax prüfen**

Run:
```bash
python web/build.py && python - <<'EOF'
import re, pathlib, subprocess, tempfile
html = pathlib.Path("dist/lotto-labor.html").read_text()
for i, s in enumerate(re.findall(r"<script>(.*?)</script>", html, re.S)):
    p = pathlib.Path(tempfile.gettempdir()) / f"teil{i}.js"; p.write_text(s)
    subprocess.run(["node", "--check", str(p)], check=True)
print("Syntax ok")
EOF
```
Expected: Pfad `…/dist/lotto-labor.html` und `Syntax ok`

- [ ] **Step 4: Veröffentlichen**

Artifact `publish` mit `file_path: dist/lotto-labor.html`, `icon: "ticket"`, `description: "Smarte Lotto-Tipps, gespielte Scheine mit Gewinncheck und ein Backtest, ob Muster die nächste Ziehung vorhersagen."`, `capabilities: {"db": {"rules": [{"path": "ziehungen", "read": "view", "write": "admin"}, {"path": "meta", "read": "view", "write": "admin"}]}, "user": {}}`. URL für Task 9 notieren.

- [ ] **Step 5: Datenbank befüllen**

Run: `python -m lotto export --ordner export`
Dann `ArtifactData` `batch` mit der URL: erste Batch = `meta/stand` + die ersten 49 Jahresdokumente, zweite Batch = restliche Jahresdokumente. Jeder Eintrag `{op: "set", collection: "ziehungen" | "meta", doc_id: "<jahr>" | "stand", file_path: "export/<collection>/<doc_id>.json"}` (neue Dokumente, kein `if_version`).

- [ ] **Step 6: Funktionsprüfung**

`ArtifactData` `list` auf `ziehungen` (limit 100): Anzahl Dokumente = Anzahl Jahre im Export; `get` auf `meta/stand`: `letzte_ziehung` = letzte Ziehung der CSV. Dann `get` auf `meta/stand` mit `as_level: "view"` (muss lesbar sein) und `set` auf `ziehungen/test` mit `as_level: "interact"` (muss abgelehnt werden). Ergebnis in einer Zeile an den Nutzer.

- [ ] **Step 7: Commit**
```bash
git add web/seite.html web/build.py
git commit -m "feat: Web-App Lotto-Labor mit Konten und Gewinncheck"
```

---

### Task 9: Automatische Datenaktualisierung

**Files:**
- Create: `zeitplan/aktualisierung.md`

**Interfaces:**
- Consumes: Artifact-URL aus Task 8, DB-Format aus Task 5.

- [ ] **Step 1: Prompt der geplanten Aufgabe schreiben** – `zeitplan/aktualisierung.md` (`<ARTIFACT_URL>` beim Schreiben durch die echte URL aus Task 8 ersetzen):
````markdown
Aktualisiere die Ziehungsdaten der Web-App „Lotto-Labor“ (Artifact: <ARTIFACT_URL>). Frag nichts nach, arbeite selbstständig.

1. Führe dieses Python-Skript aus. Es lädt die Ziehungen und schreibt pro Jahr eine JSON-Datei nach `export/ziehungen/<jahr>.json` sowie `export/meta/stand.json`:

```python
import csv, io, json, os, urllib.request
from collections import defaultdict
from datetime import datetime, timezone
URL = "https://raw.githubusercontent.com/daowa89/lottery-archive/main/de/lotto_6aus49/results.csv"
text = urllib.request.urlopen(URL, timeout=30).read().decode("utf-8")
rows = list(csv.DictReader(io.StringIO(text)))
assert rows and list(rows[0].keys()) == ["date","n1","n2","n3","n4","n5","n6","superzahl"]
jahre = defaultdict(list)
for r in rows:
    zahlen = sorted(int(r[f"n{i}"]) for i in range(1, 7))
    assert len(set(zahlen)) == 6 and all(1 <= z <= 49 for z in zahlen), r
    sz = r["superzahl"].strip()
    jahre[r["date"][:4]].append({"datum": r["date"], "zahlen": zahlen, "superzahl": int(sz) if sz else None})
for liste in jahre.values():
    liste.sort(key=lambda e: e["datum"])
os.makedirs("export/ziehungen", exist_ok=True); os.makedirs("export/meta", exist_ok=True)
for jahr, liste in jahre.items():
    json.dump({"ziehungen": liste}, open(f"export/ziehungen/{jahr}.json", "w"))
letzte = max(r["date"] for r in rows)
json.dump({"letzte_ziehung": letzte, "aktualisiert_am": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "anzahl": len(rows)}, open("export/meta/stand.json", "w"))
print("letzte Ziehung:", letzte, "Anzahl:", len(rows))
```

2. Lies mit `ArtifactData` (`action: get`, `collection: meta`, `doc_id: stand`) den aktuellen Stand. Ist `letzte_ziehung` dort gleich der letzten Ziehung aus Schritt 1, ist nichts zu tun: beende den Lauf mit „Keine neue Ziehung“ und schreibe nichts.
3. Sonst: Bestimme alle Jahre vom Jahr der gespeicherten `letzte_ziehung` bis zum Jahr der neuen letzten Ziehung (fehlt `meta/stand`, alle Jahre). Lies für jedes dieser Jahre `ziehungen/<jahr>` mit `get`, um dessen `version` zu erhalten.
4. Schreibe mit einem `ArtifactData`-`batch` für jedes dieser Jahre `{op: "set", collection: "ziehungen", doc_id: "<jahr>", file_path: "export/ziehungen/<jahr>.json"}` und zuletzt `{op: "set", collection: "meta", doc_id: "stand", file_path: "export/meta/stand.json"}`. Gib bei jedem Dokument, das schon existiert, `if_version` mit der gelesenen Version mit; bei neuen Dokumenten nicht. Schlägt der Batch wegen einer Versionsänderung fehl, lies die betroffenen Dokumente neu und wiederhole einmal.
5. Melde in einem Satz, welche Ziehungen neu hinzugekommen sind.
````

- [ ] **Step 2: Geplante Aufgaben anlegen**

`create_trigger` zweimal, `initiation: "human_request"`, `prompt` = Inhalt von `zeitplan/aktualisierung.md`, `notifications: {}` (kein Push bei Routinelauf):
- Name „Lotto-Labor Update abends“, `cron_expression: "CRON_TZ=Europe/Berlin M 22 * * 3,6"` mit `M` = 60 − ((Anzahl Buchstaben im Namen mod 15) + 1) → Lauf kurz vor 23:00 laut Jitter-Regel.
- Name „Lotto-Labor Update morgens“, `cron_expression: "CRON_TZ=Europe/Berlin M 8 * * 4,0"` mit `M` nach derselben Regel → Lauf kurz vor 09:00.

- [ ] **Step 3: Einen Lauf testen**

`fire_trigger` für die Abend-Aufgabe; danach `ArtifactData` `get` `meta/stand`: `aktualisiert_am` unverändert (keine neue Ziehung) oder neuer Stand. Ergebnis und Genehmigungseinstellung (`permission_mode`) der Aufgabe dem Nutzer in einem Satz nennen.

- [ ] **Step 4: Commit**
```bash
git add zeitplan/aktualisierung.md
git commit -m "chore: Prompt für die automatische Datenaktualisierung"
```

---

### Task 10: Abschlussprüfung

- [ ] **Step 1:** `python -m pytest -q && node --test web/logik.test.js` → alles grün.
- [ ] **Step 2:** Skill `superpowers:verification-before-completion` anwenden: Backtest-Zahlen aus `ergebnisse.json` gegen die in der Web-App angezeigten prüfen (eine Artifact-`read`).
- [ ] **Step 3:** Nutzer bekommt: Link-Karte der Web-App, die Backtest-Tabelle (echte Zahlen), 5 smarte Tipps, Hinweis zum Teilen (Mitwirkende brauchen die Stufe „Contributor“, um Tipps zu speichern), und das Python-Projekt als Datei.
