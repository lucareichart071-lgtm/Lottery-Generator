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
