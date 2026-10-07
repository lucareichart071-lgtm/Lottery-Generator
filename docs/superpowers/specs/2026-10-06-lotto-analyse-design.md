# Lotto 6 aus 49: Tipp-Generator und Musteranalyse – Design

**Datum:** 2026-10-06
**Status:** vom Nutzer freigegeben (Chat), inkl. Konten und Auto-Update

## Ziel

1. Tipps für Lotto 6 aus 49 erzeugen, die der Nutzer tatsächlich spielt.
2. Ehrlich prüfen, ob sich in den historischen Ziehungen Muster finden, die die nächste Ziehung besser vorhersagen als Zufall.

## Grundannahme (wird im Projekt getestet, nicht vorausgesetzt)

Jede Ziehung ist unabhängig, jede Kombination hat die Chance 1 : 13.983.816 auf 6 Richtige (1 : 139.838.160 inkl. Superzahl). Der einzige echte Hebel ist der **erwartete Gewinn**: Kombinationen, die selten getippt werden, müssen im Gewinnfall mit weniger Leuten geteilt werden. Die Gewinnwahrscheinlichkeit selbst lässt sich nicht erhöhen.

Die Superzahl ist die letzte Ziffer der Losnummer auf dem Spielschein und wird **nicht** vom Spieler gewählt. Der Generator erzeugt deshalb nur 6 Zahlen.

## Datenquelle

`https://raw.githubusercontent.com/daowa89/lottery-archive/main/de/lotto_6aus49/results.csv`
Spalten: `date,n1..n6,superzahl` (Superzahl ab 1992). Stand 2026-10-06: 5.052 Ziehungen seit 1955-10-09.

## Teil 1: Python-Paket `lotto/`

| Modul | Aufgabe | Schnittstelle |
|---|---|---|
| `daten.py` | CSV laden (URL oder lokaler Pfad), validieren | `lade_ziehungen(quelle=None) -> list[Ziehung]`; `Ziehung(datum: date, zahlen: tuple[int,...6], superzahl: int \| None)` |
| `generator.py` | Tipps erzeugen | `zufallstipp(rng) -> tuple[int,...]`; `ist_beliebtes_muster(tipp, letzte_ziehung) -> list[str]` (Gründe); `smarter_tipp(rng, letzte_ziehung) -> tuple[int,...]` |
| `merkmale.py` | Merkmale pro Zahl und Zeitpunkt | `merkmale(ziehungen, index) -> array[49, k]` |
| `backtest.py` | Strategien vergleichen | `strategien`: zufall, heiss, kalt, ueberfaellig, modell; `backtest(ziehungen, split_datum) -> Ergebnis` |
| `cli.py` / `__main__.py` | Terminal-Befehle | `python -m lotto tipps --anzahl 5`, `python -m lotto analyse` |

### Smart-Filter (`ist_beliebtes_muster`)

Ein Tipp wird verworfen und neu gezogen, wenn mindestens eine Regel greift:

1. Alle 6 Zahlen ≤ 31 (Geburtstage)
2. 4 oder mehr direkt aufeinanderfolgende Zahlen
3. Alle 6 Zahlen mit gleichem Abstand (arithmetische Folge)
4. Alle 6 Zahlen in einer Zeile oder Spalte des 7×7-Tippscheins
5. 3 oder mehr Zahlen aus der letzten Ziehung

Innerhalb der erlaubten Menge bleibt die Auswahl gleichverteilt (Rejection Sampling).

### KI-Modell

Gradient Boosting (scikit-learn `HistGradientBoostingClassifier`). Eine Zeile pro (Ziehung, Zahl); Ziel: Zahl wird gezogen ja/nein. Merkmale:

- Häufigkeit in den letzten 10, 50 und 200 Ziehungen
- Ziehungen seit dem letzten Auftreten
- Häufigkeit über die gesamte Historie bis zu diesem Zeitpunkt
- Zahl in der letzten Ziehung (ja/nein)

Tipp der Strategie = die 6 Zahlen mit der höchsten vorhergesagten Wahrscheinlichkeit. Merkmale verwenden ausschließlich Ziehungen **vor** der vorhergesagten Ziehung (kein Datenleck).

### Backtest

- Training: Ziehungen bis 2015-12-31. Test: ab 2016-01-01 (≈ 1.000 Ziehungen).
- Pro Strategie und Testziehung: Anzahl Treffer (0–6).
- Kennzahlen: Ø Treffer (Erwartung bei Zufall 36/49 ≈ 0,735), Anteil mit ≥ 3 Richtigen.
- Signifikanz: Permutationstest gegen 1.000 Zufallsstrategien. p-Wert pro Strategie, Bonferroni-korrigiert für die Zahl der Strategien.
- Zusätzlich: Chi-Quadrat-Test auf Gleichverteilung der 49 Zahlen über alle Ziehungen.
- Ausgabe: Tabelle im Terminal plus `ergebnisse.json` für die Web-App.

## Teil 2: Web-App

Eine HTML-Seite (als Artifact veröffentlicht), handytauglich, mit den Capabilities `db` und `user`.

### Bereiche der Seite

1. **Tipps erzeugen:** Button „5 smarte Tipps“; jeder Tipp auf einem 7×7-Tippscheinraster. Dieselben Filterregeln wie in Python, in JavaScript nachgebaut. Pro Tipp ein Button „Speichern“.
2. **Meine Tipps:** gespeicherte Tipps des angemeldeten Nutzers mit Ziehungsdatum und Superzahl (letzte Ziffer der Losnummer). Nach der Ziehung: Anzahl Richtige, Superzahl-Treffer, Gewinnklasse.
3. **Meine Bilanz:** Anzahl gespielter Tipps, Verteilung der Richtigen, Anzahl Tipps mit Gewinnklasse; daneben die bei Zufall erwartete Anzahl.
4. **Analyse:** Balkendiagramm Häufigkeit jeder Zahl seit 1955 (aus der Datenbank berechnet) und Tabelle der Backtest-Ergebnisse (beim Bauen aus `ergebnisse.json` eingebettet).
5. Stand der Daten („letzte Ziehung: …, aktualisiert am …“) und kurzer, ehrlicher Hinweistext: keine Strategie erhöht die Gewinnchance.

### Benutzerkonten

Identität über die `user`-Capability (Claude-Konto des Betrachters); kein eigenes Login. Nutzbar für alle, mit denen der Besitzer die Seite teilt. Wer nicht angemeldet ist oder keine Datenbank erhält, kann weiterhin Tipps erzeugen und die Analyse sehen; Speichern ist dann ausgeblendet.

### Datenbank (`db`)

| Pfad | Inhalt | Zugriff |
|---|---|---|
| `ziehungen/{jahr}` | `{ziehungen: [{datum, zahlen[6], superzahl}]}` pro Kalenderjahr (≈ 72 Dokumente) | alle lesen, nur Besitzer/Claude schreibt |
| `meta/stand` | `{letzte_ziehung, aktualisiert_am, anzahl}` | wie oben |
| `data/users/{id}/{tippId}` | `{ziehungsdatum, zahlen[6], superzahl, erstellt_am}` | privat für den jeweiligen Nutzer |

Gewinnklassen werden im Browser berechnet, nicht gespeichert: Kl. 1: 6 + SZ, 2: 6, 3: 5 + SZ, 4: 5, 5: 4 + SZ, 6: 4, 7: 3 + SZ, 8: 3, 9: 2 + SZ. Ist die Ziehung zum gespeicherten Datum noch nicht in der Datenbank, zeigt der Tipp „wartet auf Ziehung“.

### Automatische Datenaktualisierung

Geplante Aufgabe (claude.ai Scheduled Task), Mi + Sa 23:00 und Do + So 09:00 (Europe/Berlin; der zweite Lauf fängt verspätete Archiv-Updates ab). Jeder Lauf:

1. lädt die CSV aus dem Archiv und validiert sie mit `lotto.daten`,
2. liest `meta/stand` und schreibt nur das aktuelle Jahresdokument plus `meta/stand` neu, wenn es neue Ziehungen gibt (idempotent: mehrfaches Ausführen ändert nichts),
3. beendet sich ohne Schreibzugriff, wenn nichts Neues da ist.

Die Erstbefüllung aller Jahresdokumente macht ein Skript `lotto/export_db.py`, das die Dokumente als JSON erzeugt; Claude schreibt sie per `ArtifactData`-Batch.

## Fehlerbehandlung

- Daten nicht erreichbar → klare Meldung, Fallback auf lokalen Pfad, falls angegeben.
- Ungültige Zeilen (falsche Anzahl, Zahl außerhalb 1–49, Duplikate) → Abbruch mit Zeilennummer.
- Smart-Generator: Abbruch nach 10.000 Fehlversuchen (praktisch unerreichbar, verhindert Endlosschleife).

## Tests (pytest)

- `zufallstipp`: 6 verschiedene Zahlen, sortiert, alle in 1–49; reproduzierbar mit festem Seed.
- `ist_beliebtes_muster`: je ein positives und negatives Beispiel pro Regel.
- `smarter_tipp`: 1.000 Tipps, keiner verletzt eine Regel.
- `merkmale`: kein Datenleck (Merkmale für Ziehung *i* ändern sich nicht, wenn Ziehung *i* verändert wird).
- `daten`: korrekte Zeilen werden geparst, fehlerhafte abgelehnt.
- `export_db`: Jahresdokumente enthalten zusammen exakt alle Ziehungen; `meta/stand` zeigt die letzte.
- Gewinnklassen-Logik (JS): je ein Beispiel pro Klasse plus „kein Gewinn“, geprüft mit Node.
- `backtest`: auf künstlich manipulierten Daten (Zahl 7 kommt immer) muss die Strategie „heiss“ signifikant gewinnen. Damit ist bewiesen, dass der Test echte Muster überhaupt finden kann.

## Nicht im Umfang

Andere Lotterien (AT, EuroMillions), LSTM-Modell, öffentliche Registrierung ohne Claude-Konto, eigener Server, Benachrichtigungen bei Gewinn.
