#!/usr/bin/env python3
import argparse
import calendar
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTOGRAPH_SOURCE = Path("/Users/markusburscher/Downloads/Autographenerfassung.xlsm")
DEFAULT_ARCHIVE_SOURCE = Path("/Users/markusburscher/Downloads/Archiverschließung.xlsm")
DEFAULT_ARCHIVE_TREE = ROOT / "assets" / "data" / "archiv" / "tree-data.json"
DEFAULT_OUTPUT = ROOT / "assets" / "data" / "archiv" / "correspondence-data.json"
DEFAULT_REPORT = ROOT / "docs" / "korrespondenzen-build-report.md"

AUTOGRAPH_SHEET = "Autographen"
ARCHIVE_CORRESPONDENCE_SHEET = "Korrespondenz"

INCLUDE_ARCHIVE_CATEGORIES = {
    "Brief",
    "Karte",
    "Visitenkarte",
    "Entwurf",
    "Amtliches Schreiben",
    "Ansuchen um Aufnahme ins Kloster",
}

EXCLUDE_ARCHIVE_CATEGORIES = {
    "Bestätigung",
    "Ernennung",
    "Fragment",
    "Gutachten",
    "Gymnasialzeugnis",
    "Jurisdiktion",
    "Litterae Testimoniales",
    "Matrikelschein",
    "Maturazeugnis",
    "Primizbild",
    "Skrutinium",
    "Studienbestätigung",
    "Vermögensregelung",
    "Weiheurkunde",
    "Zeugnis",
    "Zulassung",
}

PUBLIC_COLUMNS = ["Kategorie", "Schreiber", "Empfaenger", "Datierung", "Ort", "Regest", "Bemerkungen", "Olim"]


def clean(value):
    if value is None or pd.isna(value):
        return ""
    text = str(value).replace("_x000D_", "\n").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def compact_dict(values):
    return {key: value for key, value in values.items() if value not in ("", [], {}, None)}


def read_sheet(workbook_path, sheet_name):
    sheets = pd.ExcelFile(workbook_path)
    if sheet_name not in sheets.sheet_names:
        raise ValueError(f"Fehlendes Tabellenblatt {sheet_name} in {workbook_path}")
    return [{key: clean(value) for key, value in row.items()} for row in pd.read_excel(workbook_path, sheet_name=sheet_name, dtype=str).fillna("").to_dict("records")]


def iso_date(year, month, day):
    return f"{year:04d}-{month:02d}-{day:02d}"


def display_date(year, month=None, day=None):
    if month and day:
        return f"{day:02d}.{month:02d}.{year:04d}"
    if month:
        return f"{month:02d}.{year:04d}"
    return f"{year:04d}"


def parse_date_interval(value):
    original = clean(value)
    if not original:
        return {"display": "", "from": "", "to": "", "sortable": "9999-12-31", "precision": "", "interpretable": False}
    if "?" in original:
        return {"display": original, "from": "", "to": "", "sortable": "9999-12-31", "precision": "unsicher", "interpretable": False}

    digits = re.sub(r"\D", "", original)
    year = month = day = None
    if re.fullmatch(r"\d{8}", digits):
        year = int(digits[:4])
        month_text = digits[4:6]
        day_text = digits[6:8]
        if month_text == "99":
            return {
                "display": display_date(year),
                "from": iso_date(year, 1, 1),
                "to": iso_date(year, 12, 31),
                "sortable": iso_date(year, 1, 1),
                "precision": "year",
                "interpretable": True,
            }
        month = int(month_text)
        if not 1 <= month <= 12:
            return {"display": original, "from": "", "to": "", "sortable": "9999-12-31", "precision": "", "interpretable": False}
        if day_text == "99":
            last_day = calendar.monthrange(year, month)[1]
            return {
                "display": display_date(year, month),
                "from": iso_date(year, month, 1),
                "to": iso_date(year, month, last_day),
                "sortable": iso_date(year, month, 1),
                "precision": "month",
                "interpretable": True,
            }
        day = int(day_text)
    elif re.fullmatch(r"\d{4}", digits):
        year = int(digits)
        return {
            "display": display_date(year),
            "from": iso_date(year, 1, 1),
            "to": iso_date(year, 12, 31),
            "sortable": iso_date(year, 1, 1),
            "precision": "year",
            "interpretable": True,
        }
    else:
        return {"display": original, "from": "", "to": "", "sortable": "9999-12-31", "precision": "", "interpretable": False}

    try:
        last_day = calendar.monthrange(year, month)[1]
        if not 1 <= day <= last_day:
            return {"display": original, "from": "", "to": "", "sortable": "9999-12-31", "precision": "", "interpretable": False}
    except calendar.IllegalMonthError:
        return {"display": original, "from": "", "to": "", "sortable": "9999-12-31", "precision": "", "interpretable": False}

    return {
        "display": display_date(year, month, day),
        "from": iso_date(year, month, day),
        "to": iso_date(year, month, day),
        "sortable": iso_date(year, month, day),
        "precision": "day",
        "interpretable": True,
    }


def source_row_id(source_code, index):
    return f"{source_code}:{index + 1:04d}"


def normalize_record(row, source_label, source_code, index, own_signature):
    date = parse_date_interval(row.get("Datierung", ""))
    text_parts = [own_signature, *(row.get(column, "") for column in PUBLIC_COLUMNS)]
    return compact_dict(
        {
            "id": source_row_id(source_code, index),
            "sources": [source_label],
            "signature": own_signature,
            "category": row.get("Kategorie", ""),
            "sender": row.get("Schreiber", ""),
            "recipient": row.get("Empfaenger", ""),
            "dateOriginal": row.get("Datierung", ""),
            "dateDisplay": date["display"],
            "dateFrom": date["from"],
            "dateTo": date["to"],
            "dateSort": date["sortable"],
            "datePrecision": date["precision"],
            "dateInterpretable": date["interpretable"],
            "place": row.get("Ort", ""),
            "regest": row.get("Regest", ""),
            "remarks": row.get("Bemerkungen", ""),
            "olim": row.get("Olim", ""),
            "searchText": " ".join(part for part in text_parts if part),
            "archiveMatch": False,
        }
    )


def merge_duplicates(records):
    merged = []
    by_signature = {}
    duplicates = []
    for record in records:
        signature = record.get("signature", "")
        if signature and signature in by_signature:
            existing = by_signature[signature]
            duplicates.append({"signature": signature, "kept": existing["id"], "merged": record["id"], "sources": [*existing.get("sources", []), *record.get("sources", [])]})
            existing["sources"] = sorted(set(existing.get("sources", []) + record.get("sources", [])))
            for key in ["category", "sender", "recipient", "dateOriginal", "dateDisplay", "dateFrom", "dateTo", "place", "regest", "remarks", "olim"]:
                if not existing.get(key) and record.get(key):
                    existing[key] = record[key]
            existing["searchText"] = " ".join(part for part in [existing.get("searchText", ""), record.get("searchText", "")] if part)
        else:
            merged.append(record)
            if signature:
                by_signature[signature] = record
    return merged, duplicates


def attach_archive_matches(records, tree_path):
    tree = json.loads(Path(tree_path).read_text(encoding="utf-8"))
    archive_ids = {record["id"] for record in tree.get("records", [])}
    for record in records:
        signature = record.get("signature", "")
        if signature and signature in archive_ids:
            record["archiveMatch"] = True
            record["archiveId"] = signature


def validate_records(records, source_stats, duplicate_records):
    warnings = Counter()
    signature_counts = Counter(record.get("signature", "") for record in records if record.get("signature", ""))
    duplicate_signatures = sorted(signature for signature, count in signature_counts.items() if count > 1)
    no_archive_match = []
    no_signature = []
    uninterpretable_dates = []

    for record in records:
        if not record.get("category"):
            warnings["missingCategory"] += 1
        if not record.get("sender"):
            warnings["missingSender"] += 1
        if not record.get("recipient"):
            warnings["missingRecipient"] += 1
        if record.get("dateOriginal") and not record.get("dateInterpretable"):
            warnings["uninterpretableDate"] += 1
            uninterpretable_dates.append(record)
        if not record.get("signature"):
            warnings["missingOwnSignature"] += 1
            no_signature.append(record)
        elif not record.get("archiveMatch"):
            warnings["signatureWithoutArchiveMatch"] += 1
            no_archive_match.append(record)

    return {
        "warnings": dict(warnings),
        "duplicateOwnSignatures": duplicate_signatures,
        "secureDuplicates": duplicate_records,
        "signaturesWithoutArchiveMatch": [{"id": r["id"], "signature": r.get("signature", ""), "source": ", ".join(r.get("sources", []))} for r in no_archive_match],
        "recordsWithoutOwnSignature": [{"id": r["id"], "category": r.get("category", ""), "sender": r.get("sender", ""), "recipient": r.get("recipient", "")} for r in no_signature],
        "uninterpretableDates": [{"id": r["id"], "dateOriginal": r.get("dateOriginal", ""), "signature": r.get("signature", "")} for r in uninterpretable_dates],
        "sourceStats": source_stats,
    }


def build_payload(autograph_path, archive_path, tree_path):
    autograph_rows = read_sheet(autograph_path, AUTOGRAPH_SHEET)
    archive_rows = read_sheet(archive_path, ARCHIVE_CORRESPONDENCE_SHEET)

    autograph_categories = Counter()
    included_archive_categories = Counter()
    excluded_categories = Counter()
    reviewed_cases = []
    records = []

    for index, row in enumerate(autograph_rows):
        autograph_categories[row.get("Kategorie", "") or "(ohne Kategorie)"] += 1
        records.append(normalize_record(row, "Autographen", "autographen", index, row.get("Signatur", "")))

    for index, row in enumerate(archive_rows):
        category = row.get("Kategorie", "")
        if category in INCLUDE_ARCHIVE_CATEGORIES:
            included_archive_categories[category] += 1
            records.append(normalize_record(row, "Archivis-Korrespondenz", "archivis", index, row.get("ErzeugteSignatur", "")))
        else:
            excluded_categories[category or "(ohne Kategorie)"] += 1
            if category in {"Fragment", "Gutachten", "Bestätigung"}:
                reviewed_cases.append(
                    {
                        "category": category,
                        "decision": "ausgeschlossen",
                        "reason": "Kein eindeutig als kommunikatives Schreiben erkennbarer Korrespondenzcharakter in Kategorie/Regest/Bemerkung.",
                        "sender": row.get("Schreiber", ""),
                        "recipient": row.get("Empfaenger", ""),
                        "regest": row.get("Regest", ""),
                    }
                )

    merged_records, secure_duplicates = merge_duplicates(records)
    attach_archive_matches(merged_records, tree_path)

    source_stats = {
        "autographRowsRead": len(autograph_rows),
        "archiveRowsRead": len(archive_rows),
        "archiveRowsIncluded": sum(1 for row in archive_rows if row.get("Kategorie", "") in INCLUDE_ARCHIVE_CATEGORIES),
        "archiveRowsExcluded": sum(1 for row in archive_rows if row.get("Kategorie", "") not in INCLUDE_ARCHIVE_CATEGORIES),
        "publishedRecords": len(merged_records),
        "recordsWithOwnSignature": sum(1 for record in merged_records if record.get("signature")),
        "archiveMatches": sum(1 for record in merged_records if record.get("archiveMatch")),
        "recordsWithoutOwnSignature": sum(1 for record in merged_records if not record.get("signature")),
        "secureDuplicates": len(secure_duplicates),
    }
    report = validate_records(merged_records, source_stats, secure_duplicates)

    payload = {
        "metadata": {
            "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sources": [
                {"file": Path(autograph_path).name, "sheet": AUTOGRAPH_SHEET, "rowsRead": len(autograph_rows)},
                {"file": Path(archive_path).name, "sheet": ARCHIVE_CORRESPONDENCE_SHEET, "rowsRead": len(archive_rows)},
            ],
            "recordCount": len(merged_records),
            "includedArchiveCategories": dict(sorted(included_archive_categories.items())),
            "includedAutographCategories": dict(sorted(autograph_categories.items())),
            "excludedArchiveCategories": dict(sorted(excluded_categories.items())),
            "dateNote": "Datierungen mit 99-Bestandteilen werden als Suchintervalle interpretiert; unsichere Angaben mit Fragezeichen bleiben nur als Text erhalten.",
            "archiveMatchNote": "Archivbaum-Links entstehen nur durch exakten Abgleich der eigenen Signatur mit einem Archivbaum-Datensatz.",
        },
        "facets": {"categories": sorted({record.get("category", "") for record in merged_records if record.get("category", "")})},
        "records": sorted(merged_records, key=lambda record: (record.get("dateSort", "9999-12-31"), record.get("sender", "").casefold(), record.get("recipient", "").casefold(), record.get("signature", ""))),
        "report": report,
        "reviewedCases": reviewed_cases,
    }
    return payload


def write_report(payload, report_path):
    meta = payload["metadata"]
    report = payload["report"]
    stats = report["sourceStats"]
    lines = [
        "# Korrespondenz-Findmittel: Build-Prüfbericht",
        "",
        f"Generiert: {meta['generatedAt']}",
        "",
        "## Zusammenfassung",
        "",
        f"- Autographendatensätze eingelesen: {stats['autographRowsRead']}",
        f"- Korrespondenz-Blattzeilen eingelesen: {stats['archiveRowsRead']}",
        f"- Aus Quelle B als Korrespondenz übernommen: {stats['archiveRowsIncluded']}",
        f"- Aus Quelle B ausgeschlossen: {stats['archiveRowsExcluded']}",
        f"- Sichere Dubletten über eigene Signatur: {stats['secureDuplicates']}",
        f"- Veröffentlichte Datensätze: {stats['publishedRecords']}",
        f"- Datensätze mit eigener Signatur: {stats['recordsWithOwnSignature']}",
        f"- Exakte Treffer im Archivbaum: {stats['archiveMatches']}",
        f"- Datensätze ohne eigene Signatur: {stats['recordsWithoutOwnSignature']}",
        "",
        "## Einbezogene Kategorien aus Quelle B",
        "",
    ]
    lines.extend(f"- {category}: {count}" for category, count in meta["includedArchiveCategories"].items())
    lines.extend(["", "## Ausgeschlossene Kategorien aus Quelle B", ""])
    lines.extend(f"- {category}: {count}" for category, count in meta["excludedArchiveCategories"].items())
    lines.extend(["", "## Einbezogene Kategorien aus Autographen", ""])
    lines.extend(f"- {category}: {count}" for category, count in meta["includedAutographCategories"].items())
    lines.extend(["", "## Warnungen", ""])
    if report["warnings"]:
        lines.extend(f"- {key}: {value}" for key, value in sorted(report["warnings"].items()))
    else:
        lines.append("- Keine Warnungen.")
    lines.extend(["", "## Geprüfte Zweifelsfälle", ""])
    if payload["reviewedCases"]:
        for case in payload["reviewedCases"]:
            lines.append(f"- {case['category']}: {case['decision']} ({case['reason']})")
    else:
        lines.append("- Keine.")
    lines.extend(["", "## Signaturen ohne Archivbaum-Match", ""])
    if report["signaturesWithoutArchiveMatch"]:
        lines.extend(f"- {item['signature']} ({item['source']}, {item['id']})" for item in report["signaturesWithoutArchiveMatch"])
    else:
        lines.append("- Keine.")
    lines.extend(["", "## Datensätze ohne eigene Signatur", ""])
    if report["recordsWithoutOwnSignature"]:
        lines.extend(f"- {item['id']}: {item['category']} | {item['sender']} -> {item['recipient']}" for item in report["recordsWithoutOwnSignature"])
    else:
        lines.append("- Keine.")
    lines.extend(["", "## Nicht interpretierbare Datierungen", ""])
    if report["uninterpretableDates"]:
        lines.extend(f"- {item['id']}: {item['dateOriginal']} ({item['signature']})" for item in report["uninterpretableDates"])
    else:
        lines.append("- Keine.")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Build static correspondence search data from autograph and archive Excel workbooks.")
    parser.add_argument("--autograph-source", default=str(DEFAULT_AUTOGRAPH_SOURCE), help="Pfad zu Autographenerfassung.xlsm")
    parser.add_argument("--archive-source", default=str(DEFAULT_ARCHIVE_SOURCE), help="Pfad zu Archiverschließung.xlsm")
    parser.add_argument("--archive-tree", default=str(DEFAULT_ARCHIVE_TREE), help="Pfad zu tree-data.json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Ausgabepfad für correspondence-data.json")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="Ausgabepfad für den Prüfbericht")
    args = parser.parse_args()

    payload = build_payload(Path(args.autograph_source), Path(args.archive_source), Path(args.archive_tree))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    write_report(payload, Path(args.report))

    stats = payload["report"]["sourceStats"]
    warnings = payload["report"]["warnings"]
    print(f"{stats['autographRowsRead']} Autographendatensätze eingelesen")
    print(f"{stats['archiveRowsIncluded']} Korrespondenzdatensätze aus Quelle B übernommen")
    print(f"{stats['secureDuplicates']} sichere Dubletten erkannt")
    print(f"{stats['publishedRecords']} veröffentlichte Datensätze")
    print(f"{stats['recordsWithOwnSignature']} Datensätze mit eigener Signatur")
    print(f"{stats['archiveMatches']} exakte Treffer im Archivbaum")
    print(f"{warnings.get('signatureWithoutArchiveMatch', 0)} Signaturen ohne Archivbaum-Match")
    print(f"{stats['recordsWithoutOwnSignature']} Datensätze ohne eigene Signatur")
    print(f"JSON geschrieben: {output_path.relative_to(ROOT)}")
    print(f"Prüfbericht geschrieben: {Path(args.report).relative_to(ROOT)}")


if __name__ == "__main__":
    main()
