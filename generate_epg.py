#!/usr/bin/env python3
import argparse
import copy
import difflib
import hashlib
import json
import re
import subprocess
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CARACAS = ZoneInfo("America/Caracas")
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')

COUNTRY_HINTS = {
    "VENEZUELA": "ve", "COLOMBIA": "co", "MEXICO": "mx", "MÉXICO": "mx",
    "ARGENTINA": "ar", "CHILE": "cl", "PERU": "pe", "PERÚ": "pe",
    "ECUADOR": "ec", "URUGUAY": "uy", "PARAGUAY": "py", "BOLIVIA": "bo",
    "BRASIL": "br", "BRAZIL": "br", "ESPAÑA": "es", "SPAIN": "es",
    "PORTUGAL": "pt", "USA": "us", "CANADA": "ca", "UK": "gb",
    "FRANCE": "fr", "GERMANY": "de", "ITALIA": "it", "ITALY": "it",
}

SITE_PRIORITY = {
    "gatotv.com": 40,
    "mi.tv": 38,
    "tv.movistar.co": 36,
    "siba.com.co": 34,
    "epgshare01.online": 30,
    "directv.com.ar": 25,
    "directv.com.uy": 25,
    "directv.com": 20,
}

STOPWORDS = {
    "hd", "fhd", "sd", "uhd", "4k", "1080p", "720p", "hevc", "h265",
    "channel", "canal", "tv"
}

def strip_accents(text):
    return "".join(
        c for c in unicodedata.normalize("NFKD", text or "")
        if not unicodedata.combining(c)
    )

def norm(text):
    text = strip_accents(text).lower()
    text = re.sub(r"\b(fhd|hd|sd|uhd|4k|1080p|720p|hevc|h265)\b", " ", text)
    text = re.sub(r"^[a-z]{2,4}\s*[:|〢-]\s*", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())

def base_norm(text):
    return " ".join(t for t in norm(text).split() if t not in STOPWORDS)

def country_from_group(group):
    value = strip_accents(group or "").upper()
    for label, code in COUNTRY_HINTS.items():
        if strip_accents(label).upper() in value:
            return code
    return None

def country_from_source(src):
    site_id = src["site_id"].lower()
    match = re.match(r"([a-z]{2})#", site_id)
    if match:
        return match.group(1)

    xmltv_id = src["xmltv_id"].lower()
    match = re.search(r"\.([a-z]{2})(?:@|$)", xmltv_id)
    if match:
        return match.group(1)

    filename = src["file"].lower()
    match = re.search(r"[_-]([a-z]{2})\.channels\.xml$", filename)
    if match:
        return match.group(1)
    return None

def parse_m3u(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read().decode("utf-8", errors="replace")

    lines = data.splitlines()
    entries = []

    for index, line in enumerate(lines):
        if not line.startswith("#EXTINF"):
            continue

        attrs = dict(ATTR_RE.findall(line))
        display = line.split(",", 1)[1].strip() if "," in line else attrs.get("tvg-name", "")
        stream = ""
        if index + 1 < len(lines) and not lines[index + 1].startswith("#"):
            stream = lines[index + 1].strip()

        lower_stream = stream.lower()
        if "/movie/" in lower_stream or "/series/" in lower_stream:
            continue

        name = (attrs.get("tvg-name") or display).strip()
        tvg_id = (attrs.get("tvg-id") or "").strip()
        target_id = tvg_id or name or display
        if not target_id:
            continue

        entries.append({
            "target_id": target_id,
            "tvg_id": tvg_id,
            "name": name,
            "display": display,
            "group": (attrs.get("group-title") or "").strip(),
        })

    return entries

def load_sources(epg_dir):
    sources = []

    for path in Path(epg_dir, "sites").glob("**/*.channels.xml"):
        try:
            root = ET.parse(path).getroot()
        except Exception:
            continue

        for channel in root.findall(".//channel"):
            name = (channel.text or "").strip()
            site = (channel.get("site") or path.parent.name).strip()
            site_id = (channel.get("site_id") or "").strip()
            if not name or not site_id:
                continue

            xmltv_id = (channel.get("xmltv_id") or "").strip()
            source_key = "src_" + hashlib.sha1(
                f"{site}|{site_id}|{name}".encode("utf-8")
            ).hexdigest()[:16]

            sources.append({
                "name": name,
                "norm": norm(name),
                "base": base_norm(name),
                "site": site,
                "site_id": site_id,
                "lang": (channel.get("lang") or "").strip(),
                "xmltv_id": xmltv_id,
                "source_key": source_key,
                "file": path.name,
                "logo": (channel.get("logo") or "").strip(),
            })

    return sources

def score_candidate(target, source):
    target_name = norm(target["name"])
    target_display = norm(target["display"])
    target_base = base_norm(target["name"] or target["display"])
    tvg_id = target["tvg_id"].lower()

    score = 0

    if tvg_id and source["xmltv_id"].lower() == tvg_id:
        score = 350

    if target_name and target_name == source["norm"]:
        score = max(score, 240)

    if target_display and target_display == source["norm"]:
        score = max(score, 238)

    if target_base and target_base == source["base"]:
        score = max(score, 220)

    if score < 180 and target_base and source["base"]:
        ratio = difflib.SequenceMatcher(None, target_base, source["base"]).ratio()
        if ratio >= 0.93:
            score = max(score, int(150 + ratio * 40))
        elif ratio >= 0.86:
            score = max(score, int(120 + ratio * 35))

    target_country = country_from_group(target["group"])
    source_country = country_from_source(source)

    if target_country and source_country:
        if target_country == source_country:
            score += 45
        else:
            score -= 30

    score += SITE_PRIORITY.get(source["site"], 0)

    if source["lang"] == "es" and target_country in {
        "ve", "co", "mx", "ar", "cl", "pe", "ec", "uy", "py", "bo"
    }:
        score += 10

    return score

def choose_matches(targets, sources):
    by_norm = defaultdict(list)
    by_base = defaultdict(list)
    by_id = defaultdict(list)
    by_first = defaultdict(list)

    for source in sources:
        if source["norm"]:
            by_norm[source["norm"]].append(source)
        if source["base"]:
            by_base[source["base"]].append(source)
            by_first[source["base"].split()[0]].append(source)
        if source["xmltv_id"]:
            by_id[source["xmltv_id"].lower()].append(source)

    chosen = []
    unmatched = []

    for target in targets:
        candidates = []

        if target["tvg_id"]:
            candidates.extend(by_id.get(target["tvg_id"].lower(), []))

        for key in {norm(target["name"]), norm(target["display"])}:
            if key:
                candidates.extend(by_norm.get(key, []))

        target_base = base_norm(target["name"] or target["display"])
        if target_base:
            candidates.extend(by_base.get(target_base, []))

        if not candidates and target_base:
            first = target_base.split()[0]
            candidates.extend(by_first.get(first, [])[:800])

        unique = {source["source_key"]: source for source in candidates}

        if not unique:
            unmatched.append(target)
            continue

        ranked = sorted(
            ((score_candidate(target, source), source) for source in unique.values()),
            key=lambda item: item[0],
            reverse=True,
        )

        best_score, best_source = ranked[0]

        if best_score < 155:
            unmatched.append(target)
            continue

        chosen.append((target, best_source, best_score))

    return chosen, unmatched

def write_custom_channels(chosen, path):
    root = ET.Element("channels")
    seen = set()

    for _, source, _ in chosen:
        if source["source_key"] in seen:
            continue

        seen.add(source["source_key"])

        attrs = {
            "site": source["site"],
            "site_id": source["site_id"],
            "lang": source["lang"] or "en",
            "xmltv_id": source["source_key"],
        }

        if source["logo"]:
            attrs["logo"] = source["logo"]

        element = ET.SubElement(root, "channel", attrs)
        element.text = source["name"]

    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)

def parse_xmltv_datetime(value):
    if not value:
        return None

    match = re.match(r"^(\d{14})(?:\s*([+-]\d{4}))?", value.strip())
    if not match:
        return None

    base = datetime.strptime(match.group(1), "%Y%m%d%H%M%S")
    offset = match.group(2)

    if offset:
        sign = 1 if offset[0] == "+" else -1
        delta = timedelta(
            hours=int(offset[1:3]),
            minutes=int(offset[3:5]),
        )
        return base.replace(tzinfo=timezone(sign * delta))

    return base.replace(tzinfo=timezone.utc)

def format_caracas(dt):
    return dt.astimezone(CARACAS).strftime("%Y%m%d%H%M%S %z")

def build_final(raw_guide, chosen, output_path, report_path, total_targets, unmatched):
    source_to_targets = defaultdict(dict)
    group_by_target = {}

    for target, source, _ in chosen:
        source_to_targets[source["source_key"]][target["target_id"]] = target
        group_by_target[target["target_id"]] = target["group"]

    input_root = ET.parse(raw_guide).getroot()
    output_root = ET.Element(
        "tv",
        {"generator-info-name": "EPG Joel 36h - iptv-org"}
    )

    written_channels = set()
    programmes_per_target = Counter()

    now = datetime.now(CARACAS)
    window_end = now + timedelta(hours=36)

    for targets in source_to_targets.values():
        for target_id, target in targets.items():
            if target_id in written_channels:
                continue

            channel = ET.SubElement(output_root, "channel", {"id": target_id})
            display_name = ET.SubElement(channel, "display-name")
            display_name.text = target["display"] or target["name"] or target_id
            written_channels.add(target_id)

    for programme in input_root.findall("programme"):
        source_id = programme.get("channel", "")

        if source_id not in source_to_targets:
            continue

        start = parse_xmltv_datetime(programme.get("start"))
        stop = parse_xmltv_datetime(programme.get("stop"))

        if not start:
            continue

        if stop is None:
            stop = start + timedelta(hours=2)

        start_local = start.astimezone(CARACAS)
        stop_local = stop.astimezone(CARACAS)

        if stop_local <= now or start_local >= window_end:
            continue

        for target_id in source_to_targets[source_id]:
            copy_programme = copy.deepcopy(programme)
            copy_programme.set("channel", target_id)
            copy_programme.set("start", format_caracas(start))
            copy_programme.set("stop", format_caracas(stop))
            output_root.append(copy_programme)
            programmes_per_target[target_id] += 1

    ET.ElementTree(output_root).write(
        output_path,
        encoding="utf-8",
        xml_declaration=True
    )

    matched_ids = set(group_by_target)
    covered_ids = {key for key, value in programmes_per_target.items() if value > 0}

    missing_by_group = Counter()

    for target in unmatched:
        missing_by_group[target["group"] or "(sin grupo)"] += 1

    for target_id in matched_ids - covered_ids:
        missing_by_group[group_by_target.get(target_id, "(sin grupo)")] += 1

    report = {
        "generated_at_venezuela": now.isoformat(),
        "window_hours": 36,
        "total_live_entries": total_targets,
        "matched_entries": len(chosen),
        "unique_matched_channel_ids": len(matched_ids),
        "unique_channels_with_programmes": len(covered_ids),
        "programme_rows": sum(programmes_per_target.values()),
        "unmatched_entries": len(unmatched),
        "groups_with_most_missing": missing_by_group.most_common(30),
    }

    Path(report_path).write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report, ensure_ascii=False, indent=2))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--m3u-url", required=True)
    parser.add_argument("--epg-dir", required=True)
    parser.add_argument("--output", default="EPG_Joel_36h.xml")
    parser.add_argument("--report", default="coverage.json")
    args = parser.parse_args()

    if not args.m3u_url.strip():
        raise SystemExit("Falta configurar IPTV_M3U_URL en GitHub Actions.")

    work_dir = Path("work")
    work_dir.mkdir(exist_ok=True)

    custom_channels = work_dir / "custom.channels.xml"
    raw_guide = work_dir / "guide.xml"

    print("Descargando inventario IPTV...")
    targets = parse_m3u(args.m3u_url)
    print(f"Entradas de TV en vivo detectadas: {len(targets)}")

    print("Leyendo catálogo de iptv-org/epg...")
    sources = load_sources(args.epg_dir)
    print(f"Fuentes candidatas encontradas: {len(sources)}")

    chosen, unmatched = choose_matches(targets, sources)
    print(f"Mapeadas: {len(chosen)} | Sin mapa seguro: {len(unmatched)}")

    write_custom_channels(chosen, custom_channels)

    command = [
        "npm", "run", "grab", "---",
        f"--channels={custom_channels.resolve()}",
        f"--output={raw_guide.resolve()}",
        "--days=2",
        "--maxConnections=12",
        "--timeout=30000",
    ]

    print("Descargando programación...")
    result = subprocess.run(command, cwd=args.epg_dir)

    if result.returncode != 0 or not raw_guide.exists():
        raise SystemExit("Falló la descarga de programación desde iptv-org/epg.")

    build_final(
        raw_guide,
        chosen,
        args.output,
        args.report,
        len(targets),
        unmatched,
    )

if __name__ == "__main__":
    main()
