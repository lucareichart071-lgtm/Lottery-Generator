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


# Hinweis: zeitplan/aktualisierung.md enthält eine eigenständige Kopie dieser Validierung (beide synchron halten).
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
