# Lotto-Labor

Tipp-Generator und Musteranalyse für **Lotto 6 aus 49**, mit Web-App.

- **Smarte Tipps:** rein zufällige Tipps, die beliebte Muster vermeiden (nur Zahlen bis 31, Reihen und Diagonalen auf dem Schein, Zahlenfolgen, gleiche Abstände, Zahlen der letzten Ziehung). Die Gewinnchance bleibt gleich, aber im Gewinnfall teilt man wahrscheinlich mit weniger Leuten.
- **Backtest:** Heiße, kalte und überfällige Zahlen sowie ein KI-Modell (Gradient Boosting) treten gegen reinen Zufall an. Trainiert wird auf den Ziehungen bis Ende 2015, getestet auf den 1.123 Ziehungen ab 2016. Ergebnis: Keine Strategie ist signifikant besser als Zufall.
- **Superzahl-Analyse:** zeigt die Häufigkeit jeder Ziffer seit 1991 und testet auf Gleichverteilung (p = 0,67, unauffällig).
- **Web-App:** Tippscheine, gespeicherte Tipps mit automatischem Gewinncheck, persönliche Bilanz und Analyse. Läuft als claude.ai-Artifact mit Datenbank und Benutzerkonten.

Datenquelle: [daowa89/lottery-archive](https://github.com/daowa89/lottery-archive) (Ziehungen seit 1955).

## Nutzung

```bash
pip install -e ".[test]"
python -m lotto tipps --anzahl 5     # 5 smarte Tipps
python -m lotto analyse              # Backtest, schreibt ergebnisse.json
python -m lotto export --ordner export   # Ziehungen als DB-Dokumente
python web/build.py                  # baut dist/lotto-labor.html
```

## Tests

```bash
python -m pytest -q
node --test web/logik.test.js
```

## Aufbau

| Pfad | Inhalt |
|---|---|
| `lotto/daten.py` | Ziehungen laden und prüfen |
| `lotto/generator.py` | Zufalls- und Smart-Tipps |
| `lotto/merkmale.py` | Merkmale fürs KI-Modell, ohne Datenleck |
| `lotto/backtest.py` | Backtest, Monte-Carlo-Signifikanztest, Chi-Quadrat |
| `lotto/export_db.py`, `lotto/cli.py` | Datenbank-Export und Kommandozeile |
| `web/` | Spiellogik (JS), Seitenvorlage, Build-Skript |
| `zeitplan/aktualisierung.md` | Anleitung für die automatische Datenaktualisierung |
| `docs/superpowers/` | Design-Spezifikation und Umsetzungsplan |

> Lotto ist ein reines Glücksspiel. Kein Programm kann Gewinnzahlen vorhersagen.
