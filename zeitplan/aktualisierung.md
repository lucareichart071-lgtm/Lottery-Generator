Aktualisiere die Ziehungsdaten der Web-App „Lotto-Labor" (Artifact: https://claude.ai/artifact/GFGjuYm5Co71UfgSPRYxPf). Frag nichts nach, arbeite selbstständig.

1. Führe dieses Python-Skript aus. Es lädt die Ziehungen und schreibt pro Jahr eine JSON-Datei nach `export/ziehungen/<jahr>.json` sowie `export/meta/stand.json`:

```python
import csv, io, json, os, urllib.request
from collections import defaultdict
from datetime import datetime, timezone
URL = "https://raw.githubusercontent.com/daowa89/lottery-archive/main/de/lotto_6aus49/results.csv"
text = urllib.request.urlopen(URL, timeout=30).read().decode("utf-8")
rows = list(csv.DictReader(io.StringIO(text)))
assert rows and list(rows[0].keys()) == ["date","n1","n2","n3","n4","n5","n6","superzahl"]
jahre = defaultdict(list)
for r in rows:
    zahlen = sorted(int(r[f"n{i}"]) for i in range(1, 7))
    assert len(set(zahlen)) == 6 and all(1 <= z <= 49 for z in zahlen), r
    sz = r["superzahl"].strip()
    jahre[r["date"][:4]].append({"datum": r["date"], "zahlen": zahlen, "superzahl": int(sz) if sz else None})
for liste in jahre.values():
    liste.sort(key=lambda e: e["datum"])
os.makedirs("export/ziehungen", exist_ok=True); os.makedirs("export/meta", exist_ok=True)
for jahr, liste in jahre.items():
    json.dump({"ziehungen": liste}, open(f"export/ziehungen/{jahr}.json", "w"))
letzte = max(r["date"] for r in rows)
json.dump({"letzte_ziehung": letzte, "aktualisiert_am": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "anzahl": len(rows)}, open("export/meta/stand.json", "w"))
print("letzte Ziehung:", letzte, "Anzahl:", len(rows))
```

2. Lies mit `ArtifactData` (`action: get`, `collection: meta`, `doc_id: stand`) den aktuellen Stand. Ist `letzte_ziehung` dort gleich der letzten Ziehung aus Schritt 1, ist nichts zu tun: beende den Lauf mit „Keine neue Ziehung" und schreibe nichts.
3. Sonst: Bestimme alle Jahre vom Jahr der gespeicherten `letzte_ziehung` bis zum Jahr der neuen letzten Ziehung (fehlt `meta/stand`, alle Jahre). Lies für jedes dieser Jahre `ziehungen/<jahr>` mit `get`, um dessen `version` zu erhalten.
4. Schreibe mit einem `ArtifactData`-`batch` für jedes dieser Jahre `{op: "set", collection: "ziehungen", doc_id: "<jahr>", file_path: "export/ziehungen/<jahr>.json"}` und zuletzt `{op: "set", collection: "meta", doc_id: "stand", file_path: "export/meta/stand.json"}`. Gib bei jedem Dokument, das schon existiert, `if_version` mit der gelesenen Version mit; bei neuen Dokumenten nicht. Schlägt der Batch wegen einer Versionsänderung fehl, lies die betroffenen Dokumente neu und wiederhole einmal.
5. Melde in einem Satz, welche Ziehungen neu hinzugekommen sind.
