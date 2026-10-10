#!/usr/bin/env python3
"""Auditoría de identidades XMLTV sin asumir que un nombre verifica una señal."""
import csv
import json
import sys
from collections import defaultdict

def main(original_csv, output_json):
    rows = list(csv.DictReader(open(original_csv, encoding="utf-8-sig", newline="")))
    if len(rows) != 6066:
        raise SystemExit(f"Inventario incorrecto: {len(rows)} filas, esperadas 6066")
    by_id = defaultdict(list)
    for row in rows:
        channel_id = row["tvg_id_original"].strip()
        if channel_id:
            by_id[channel_id].append(row)
    ambiguous = {}
    for channel_id, items in by_id.items():
        signatures = {(x["nombre"].strip().casefold(), x["grupo"].strip().casefold()) for x in items}
        if len(signatures) > 1:
            ambiguous[channel_id] = len(items)
    result = {
        "original_entries": len(rows),
        "missing_tvg_id": sum(not r["tvg_id_original"].strip() for r in rows),
        "ambiguous_tvg_ids": len(ambiguous),
        "entries_with_ambiguous_tvg_id": sum(ambiguous.values()),
        "verified_signals": 0,
        "warning": "Una coincidencia de nombre o ID no verifica la señal, región ni horario.",
    }
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Uso: python inventory_id_guard.py inventario_tv.csv resumen.json")
    main(sys.argv[1], sys.argv[2])
