#!/usr/bin/env python3
"""Audita una EPG XMLTV sin inventar horarios ni validar señales por su nombre."""
import argparse
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CARACAS = ZoneInfo("America/Caracas")
DATE_RE = re.compile(r"^(\d{14})\s*([+-]\d{4})$")


def parse_date(raw):
    match = DATE_RE.fullmatch((raw or "").strip())
    if not match:
        return None
    try:
        value = datetime.strptime(match.group(1), "%Y%m%d%H%M%S")
        sign = 1 if match.group(2)[0] == "+" else -1
        offset = timedelta(hours=int(match.group(2)[1:3]), minutes=int(match.group(2)[3:5]))
        return value.replace(tzinfo=timezone(sign * offset))
    except ValueError:
        return None


def audit(epg_path, coverage_path, original_entries=6066):
    coverage = json.loads(Path(coverage_path).read_text(encoding="utf-8"))
    declared_ids = set()
    programmes = Counter()
    duplicate_rows = 0
    malformed_rows = 0
    outside_window_rows = 0
    seen = set()
    now = datetime.now(CARACAS)
    end = now + timedelta(hours=36)
    last_stop = None

    for _, elem in ET.iterparse(epg_path, events=("end",)):
        if elem.tag == "channel":
            if elem.get("id"):
                declared_ids.add(elem.get("id"))
            elem.clear()
        elif elem.tag == "programme":
            channel = elem.get("channel", "")
            start = parse_date(elem.get("start"))
            stop = parse_date(elem.get("stop"))
            if not channel or not start or not stop or stop <= start:
                malformed_rows += 1
            else:
                if stop.astimezone(CARACAS) <= now or start.astimezone(CARACAS) >= end:
                    outside_window_rows += 1
                if last_stop is None or stop > last_stop:
                    last_stop = stop
                title = tuple((x.text or "") for x in elem.findall("title"))
                fingerprint = (channel, elem.get("start"), elem.get("stop"), title)
                if fingerprint in seen:
                    duplicate_rows += 1
                else:
                    seen.add(fingerprint)
                programmes[channel] += 1
            elem.clear()

    covered = set(programmes)
    total = coverage.get("total_live_entries")
    return {
        "audited_at_venezuela": now.isoformat(),
        "original_inventory_entries": original_entries,
        "generator_live_entries": total,
        "inventory_difference": total - original_entries if isinstance(total, int) else None,
        "inventory_reconciled": total == original_entries,
        "xmltv_declared_channel_ids": len(declared_ids),
        "xmltv_channel_ids_with_programmes": len(covered),
        "xmltv_programme_rows": sum(programmes.values()),
        "xmltv_duplicate_programme_rows": duplicate_rows,
        "xmltv_invalid_time_rows": malformed_rows,
        "xmltv_outside_next_36h_rows": outside_window_rows,
        "xmltv_orphan_programme_channel_ids": len(covered - declared_ids),
        "xmltv_declared_ids_without_programmes": len(declared_ids - covered),
        "last_programme_stop_venezuela": last_stop.astimezone(CARACAS).isoformat() if last_stop else None,
        "reported_unique_channels_with_programmes": coverage.get("unique_channels_with_programmes"),
        "reported_programme_rows": coverage.get("programme_rows"),
        "counts_match_report": (
            coverage.get("unique_channels_with_programmes") == len(covered)
            and coverage.get("programme_rows") == sum(programmes.values())
        ),
        "unmatched_entries_from_report": coverage.get("unmatched_entries"),
        "verification_status": "NOT_INDIVIDUALLY_VERIFIED",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epg", default="EPG_Joel_36h.xml")
    parser.add_argument("--coverage", default="coverage.json")
    parser.add_argument("--output", default="audit.json")
    args = parser.parse_args()
    result = audit(args.epg, args.coverage)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["xmltv_invalid_time_rows"] or result["xmltv_orphan_programme_channel_ids"]:
        raise SystemExit("EPG con errores estructurales; no publicar.")


if __name__ == "__main__":
    main()
