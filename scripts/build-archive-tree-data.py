#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "assets" / "data" / "archiv" / "tree-data.json"
SHEET_NAME = "Metadaten"

PUBLIC_FIELD_GROUPS = [
    ("Umfang", "Umfang"),
    ("Provenienz", "Provenienz"),
    ("VerwaltungsgeschichteBiographischeAngaben", "Verwaltungsgeschichte / biographische Angaben"),
    ("Bestandsgeschichte", "Bestandsgeschichte"),
    ("FormUndInhalt", "Form und Inhalt"),
    ("BewertungUndSkartierung", "Bewertung und Skartierung"),
    ("Neuzugaenge", "Neuzugänge"),
    ("OrdnungUndKlassifikation", "Ordnung und Klassifikation"),
    ("Zulassungsbestimmungen", "Zugangsbestimmungen"),
    ("Reproduktionsbestimmungen", "Reproduktionsbestimmungen"),
    ("SpracheSchrift", "Sprache / Schrift"),
    ("PhysischeBeschaffenheitTechnischeAnforderungen", "Physische Beschaffenheit / technische Anforderungen"),
    ("Findmittel", "Findmittel"),
    ("KopienReproduktionen", "Kopien / Reproduktionen"),
    ("VerwandtesMaterial", "Verwandtes Material"),
    ("Veroeffentlichungen", "Veröffentlichungen"),
    ("AllgemeineAnmerkungen", "Allgemeine Anmerkungen"),
    ("Bearbeiter", "Bearbeiter"),
    ("Verzeichnungsgrundsaetze", "Verzeichnungsgrundsätze"),
    ("DatumDerVerzeichnung", "Datum der Verzeichnung"),
    ("Technik", "Technik"),
    ("Material", "Material"),
]

CONTROLLED_FIELDS = [
    ("Personen", "Personen"),
    ("Orte", "Orte"),
    ("Schlagworte", "Schlagworte"),
]

DESCRIPTION_COLUMNS = [key for key, _ in PUBLIC_FIELD_GROUPS]
DATE_COLUMNS = ["EntstehungszeitVerbal", "EntstehungszeitVon", "EntstehungszeitBis"]


def clean(value):
    if value is None or pd.isna(value):
        return ""
    text = str(value).replace("_x000D_", "\n").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def compact_dict(values):
    return {key: value for key, value in values.items() if value not in ("", [], {}, None)}


def sort_key(value):
    parts = re.split(r"(\d+)", clean(value))
    return [int(part) if part.isdigit() else part.casefold() for part in parts]


def format_date(value):
    text = clean(value)
    if re.fullmatch(r"\d{8}", text):
        return f"{text[6:8]}.{text[4:6]}.{text[0:4]}"
    if re.fullmatch(r"\d{4}", text):
        return text
    return text


def date_label(row):
    verbal = clean(row.get("EntstehungszeitVerbal"))
    if verbal:
        return verbal
    start = format_date(row.get("EntstehungszeitVon"))
    end = format_date(row.get("EntstehungszeitBis"))
    if start and end and start != end:
        return f"{start}–{end}"
    return start or end


def parse_semicolon_values(value):
    items = []
    for raw_part in clean(value).split(";"):
        part = raw_part.strip()
        if not part:
            continue
        match = re.match(r"^(.*?)\s*\[([^\]]+)\]\s*$", part)
        if match:
            items.append({"label": match.group(1).strip(), "role": match.group(2).strip()})
        else:
            items.append({"label": part})
    return items


def visible_value_text(values):
    parts = []
    for value in values:
        label = value.get("label", "")
        role = value.get("role", "")
        if label and role:
            parts.append(f"{label} [{role}]")
        elif label:
            parts.append(label)
    return "; ".join(parts)


def read_rows(workbook_path):
    sheets = pd.ExcelFile(workbook_path)
    if SHEET_NAME not in sheets.sheet_names:
        raise ValueError(f"Fehlendes Tabellenblatt: {SHEET_NAME}")

    df = pd.read_excel(workbook_path, sheet_name=SHEET_NAME, dtype=str).fillna("")
    required_columns = ["Signatur", "SignaturUeberordnung", "Titel", "Verzeichnungsstufe", *DATE_COLUMNS]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Fehlende Spalten im Blatt {SHEET_NAME}: {', '.join(missing_columns)}")

    return [{key: clean(value) for key, value in row.items()} for row in df.to_dict("records")]


def validate(rows):
    errors = []
    warnings = Counter()
    ids = [row.get("Signatur", "") for row in rows]
    counts = Counter(ids)
    duplicate_ids = sorted(record_id for record_id, count in counts.items() if record_id and count > 1)
    missing_ids = sum(1 for record_id in ids if not record_id)

    if missing_ids:
        errors.append(f"{missing_ids} Datensätze ohne Signatur/ID")
    if duplicate_ids:
        errors.append("Doppelte Signatur/ID: " + ", ".join(duplicate_ids[:20]))

    records_by_id = {row["Signatur"]: row for row in rows if row.get("Signatur")}
    missing_titles = sorted(row["Signatur"] for row in rows if row.get("Signatur") and not row.get("Titel"))
    if missing_titles:
        errors.append("Fehlender Titel bei: " + ", ".join(missing_titles[:20]))

    missing_parents = []
    for row in rows:
        parent = row.get("SignaturUeberordnung", "")
        if parent and parent not in records_by_id:
            missing_parents.append((row.get("Signatur", ""), parent))
    if missing_parents:
        preview = ", ".join(f"{child} -> {parent}" for child, parent in missing_parents[:20])
        errors.append("Parent verweist auf nicht vorhandenen Datensatz: " + preview)

    visiting = set()
    visited = set()
    cycle_nodes = set()

    def visit(record_id, stack):
        if record_id in visited:
            return
        if record_id in visiting:
            cycle_nodes.update(stack[stack.index(record_id):] if record_id in stack else [record_id])
            return
        visiting.add(record_id)
        parent = records_by_id.get(record_id, {}).get("SignaturUeberordnung", "")
        if parent and parent in records_by_id:
            visit(parent, [*stack, parent])
        visiting.remove(record_id)
        visited.add(record_id)

    for record_id in records_by_id:
        visit(record_id, [record_id])
    if cycle_nodes:
        errors.append("Zyklische Parent-Beziehung bei: " + ", ".join(sorted(cycle_nodes, key=sort_key)[:20]))

    for row in rows:
        if not row.get("Verzeichnungsstufe"):
            warnings["missingLevel"] += 1
        if not any(row.get(column) for column in DATE_COLUMNS):
            warnings["missingDate"] += 1
        if not any(row.get(column) for column in DESCRIPTION_COLUMNS):
            warnings["missingDescription"] += 1
        if not any(row.get(column) for column, _ in CONTROLLED_FIELDS):
            warnings["missingControlledMetadata"] += 1
        if row.get("VorlaeufigeSignatur", "").casefold() == "ja":
            warnings["temporarySignature"] += 1

    return errors, warnings


def build_payload(workbook_path):
    rows = read_rows(workbook_path)
    errors, warnings = validate(rows)
    if errors:
        raise ValueError("\n".join(errors))

    children_by_parent = defaultdict(list)
    for row in rows:
        children_by_parent[row.get("SignaturUeberordnung", "")].append(row.get("Signatur", ""))

    root_rows = [row for row in rows if not row.get("SignaturUeberordnung")]
    main_branch_count = len(children_by_parent.get(root_rows[0]["Signatur"], [])) if len(root_rows) == 1 else len(children_by_parent.get("StAS", []))

    records = []
    for index, row in enumerate(rows):
        record_id = row["Signatur"]
        field_groups = [
            {"key": key, "label": label, "value": row.get(key, "")}
            for key, label in PUBLIC_FIELD_GROUPS
            if row.get(key, "")
        ]
        controlled = [
            {"key": key, "label": label, "values": parse_semicolon_values(row.get(key, ""))}
            for key, label in CONTROLLED_FIELDS
            if row.get(key, "")
        ]
        controlled_text = [
            {"label": group["label"], "value": visible_value_text(group["values"])}
            for group in controlled
            if group.get("values")
        ]
        body_text = " ".join(field["value"] for field in field_groups)
        term_text = " ".join(item["value"] for item in controlled_text)
        search_text = " ".join(
            part
            for part in [
                record_id,
                row.get("Titel", ""),
                row.get("Verzeichnungsstufe", ""),
                date_label(row),
                body_text,
                term_text,
            ]
            if part
        )

        records.append(
            compact_dict(
                {
                    "id": record_id,
                    "parent": row.get("SignaturUeberordnung", ""),
                    "signature": record_id,
                    "title": row.get("Titel", ""),
                    "level": row.get("Verzeichnungsstufe", ""),
                    "date": date_label(row),
                    "dateStart": format_date(row.get("EntstehungszeitVon")),
                    "dateEnd": format_date(row.get("EntstehungszeitBis")),
                    "hasChildren": bool(children_by_parent.get(record_id)),
                    "children": children_by_parent.get(record_id, []),
                    "order": index,
                    "fields": field_groups,
                    "controlled": controlled,
                    "search": {
                        "title": row.get("Titel", ""),
                        "signature": record_id,
                        "date": date_label(row),
                        "level": row.get("Verzeichnungsstufe", ""),
                        "description": body_text,
                        "terms": term_text,
                        "text": search_text,
                    },
                }
            )
        )

    payload = {
        "metadata": {
            "source": Path(workbook_path).name,
            "sheet": SHEET_NAME,
            "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "recordCount": len(records),
            "rootCount": len(root_rows),
            "mainBranchCount": main_branch_count,
            "sort": "Excel-Reihenfolge; natürliche Signaturreihenfolge als Fallback in der Oberfläche",
            "hierarchyRule": "Parent-Child-Beziehungen werden ausschließlich aus SignaturUeberordnung gebildet.",
            "stableIdentifierNote": "Im Blatt Metadaten wurde kein eigener persistenter technischer Identifier gefunden; für den PoC dient Signatur als ID.",
            "searchNote": "Die Volltextsuche durchsucht die öffentlichen Felder in dieser JSON-Datei mit UND-Logik über normalisierte Teilbegriffe.",
            "hardErrors": {
                "duplicateIds": 0,
                "missingParents": 0,
                "cycles": 0,
                "missingTitles": 0,
            },
            "warnings": dict(warnings),
        },
        "records": records,
    }
    return payload


def print_summary(payload, output_path):
    meta = payload["metadata"]
    warnings = meta["warnings"]
    print(f"{meta['recordCount']} Datensätze verarbeitet")
    print(f"{meta['rootCount']} Wurzel")
    print(f"{meta['mainBranchCount']} Hauptzweige")
    print("0 doppelte IDs")
    print("0 verwaiste Parent-Beziehungen")
    print("0 Zyklen")
    print(f"{warnings.get('missingLevel', 0)} Datensätze ohne Verzeichnungsstufe")
    print(f"{warnings.get('missingDate', 0)} Datensätze ohne Laufzeit")
    print(f"{warnings.get('missingDescription', 0)} Datensätze ohne Beschreibung")
    print(f"{warnings.get('missingControlledMetadata', 0)} Datensätze ohne kontrollierte Metadaten")
    print(f"{warnings.get('temporarySignature', 0)} Datensätze mit vorläufiger Signatur")
    print(f"JSON geschrieben: {output_path.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser(description="Build static archive hierarchy data from Archiverschließung.xlsm.")
    parser.add_argument("workbook", help="Pfad zur Excel-Datei Archiverschließung.xlsm")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Ausgabepfad für die JSON-Datei")
    args = parser.parse_args()

    payload = build_payload(Path(args.workbook))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print_summary(payload, output_path)


if __name__ == "__main__":
    main()
