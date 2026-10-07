Aktualisiere die Ziehungsdaten der Web-App “Lotto-Labor” (Artifact: https://claude.ai/artifact/GFGjuYm5Co71UfgSPRYxPf). Frag nichts nach, arbeite selbstständig.

1. Führe dieses Python-Skript aus. Es lädt die Ziehungen und schreibt pro Jahr eine JSON-Datei nach `export/ziehungen/<jahr>.json` sowie `export/meta/stand.json`:

```python
import csv, io, json, os, urllib.request
from collections import defaultdict
from datetime import datetime, timezone, date
URL = "https://raw.githubusercontent.com/daowa89/lottery-archive/main/de/lotto_6aus49/results.csv"
try:
    text = urllib.request.urlopen(URL, timeout=30).read().decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(text)))
    assert rows and list(rows[0].keys()) == ["date","n1","n2","n3","n4","n5","n6","superzahl"]
    jahre = defaultdict(list)
    seen_dates = set()
    for r in rows:
        d = r["date"]
        date.fromisoformat(d)
        assert d not in seen_dates, f"Duplikat: {d}"
        seen_dates.add(d)
        zahlen = sorted(int(r[f"n{i}"]) for i in range(1, 7))
        assert len(set(zahlen)) == 6 and all(1 <= z <= 49 for z in zahlen), r
        sz = r["superzahl"].strip()
        if sz:
            assert 0 <= int(sz) <= 9, f"Superzahl außerhalb 0–9: {sz}"
        jahre[d[:4]].append({"datum": d, "zahlen": zahlen, "superzahl": int(sz) if sz else None})
    for liste in jahre.values():
        liste.sort(key=lambda e: e["datum"])
    os.makedirs("export/ziehungen", exist_ok=True); os.makedirs("export/meta", exist_ok=True)
    for jahr, liste in jahre.items():
        with open(f"export/ziehungen/{jahr}.json", "w") as f:
            json.dump({"ziehungen": liste}, f)
    letzte = max(r["date"] for r in rows)
    with open("export/meta/stand.json", "w") as f:
        json.dump({"letzte_ziehung": letzte, "aktualisiert_am": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                   "anzahl": len(rows)}, f)
    print("letzte Ziehung:", letzte, "Anzahl:", len(rows))
except (AssertionError, urllib.error.URLError, json.JSONDecodeError, ValueError) as e:
    print(f"Fehler beim Skript: {e}")
    raise
```

Bricht das Skript mit einem Fehler ab, schreibe nichts in die Datenbank, beende den Lauf und melde den Fehler in einem Satz.

2. Lies mit `ArtifactData` (`action: get`, `collection: meta`, `doc_id: stand`) den aktuellen Stand. Wenn `meta/stand` nicht existiert, behandle es als “alle Jahre”. Sonst vergleiche die neue letzte Ziehung (aus Schritt 1) mit der gespeicherten `letzte_ziehung`: Ist die gespeicherte Ziehung später als die CSV-Ziehung, beende den Lauf mit einer Anomaliemeldung – das sollte nicht vorkommen. Wenn beide `letzte_ziehung` UND `anzahl` in `meta/stand` gleich den Werten aus Schritt 1 sind, ist nichts zu tun: beende den Lauf mit “Keine neue Ziehung” und schreibe nichts.

3. Sonst: Ist die `letzte_ziehung` gleich, aber `anzahl` unterschiedlich (ein Korrektionslauf), muss ALL diese Jahre neu geschrieben werden, da die Daten korrigiert wurden. Bestimme alle zu aktualisierenden Jahre vom Jahr der gespeicherten `letzte_ziehung` bis zum Jahr der neuen letzten Ziehung (bei fehlendem `meta/stand`: alle Jahre). Für die Bootstrap-Phase (meta/stand fehlt), hole mit `ArtifactData` `action: list`, `collection: ziehungen`, query limit 100 die Versionen aller existierenden Jahr-Dokumente; ein Jahr, das NICHT in der List-Ergebnis vorkommt, ist neu (kein `if_version`). Für inkrementelle Updates lies für jedes Jahr `ziehungen/<jahr>` mit `get`, um dessen `version` zu erhalten. Wenn ein `get` meldet, dass das Dokument nicht existiert (nicht gefunden), ist es neu – bei neuen Dokumenten omittiere `if_version`; existierende Dokumente benötigen immer die `version` aus dem `get` oder `list`.

4. Schreibe die gesammelten Jahre in Batches mit je maximal 49 Einträgen. Jeder Batch ist ein `ArtifactData`-`batch` mit Einträgen wie `{op: "set", collection: "ziehungen", doc_id: "<jahr>", file_path: "export/ziehungen/<jahr>.json"}`. Bei existierenden Dokumenten (die eine `version` haben) gib `if_version` mit an; bei neuen Dokumenten omittiere `if_version`. Nach allen Jahr-Batches schreibe in einem separaten finalen Batch `{op: "set", collection: "meta", doc_id: "stand", file_path: "export/meta/stand.json"}` mit `if_version` (wenn `meta/stand` bereits existiert, sonst ohne). Schlägt ein Batch wegen einer Versionsänderung fehl, lies die betroffenen Dokumente neu und wiederhole den Batch einmal. Schlägt der Batch auch beim Wiederholungsversuch fehl, beende den Lauf sofort, schreibe nichts Weiteres (insbesondere nicht `meta/stand`) und melde den Fehler in einem Satz.

5. Melde in einem Satz, welche Jahre neu hinzugekommen sind (z. B. “Hinzugefügt: 2024, 2025” oder “Aktualisiert: 2024–2026”).
