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
