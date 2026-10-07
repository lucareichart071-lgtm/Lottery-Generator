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
