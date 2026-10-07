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
