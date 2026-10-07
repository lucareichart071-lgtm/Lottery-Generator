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
