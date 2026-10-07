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
