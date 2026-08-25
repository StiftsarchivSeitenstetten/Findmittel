#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "assets" / "data" / "musikarchiv" / "search-data.json"


def clean(value):
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_row(row):
    return {key: clean(value) for key, value in row.items()}


def natural_id_key(value):
    text = clean(value)
    match = re.match(r"^([A-Za-z]+)-(\d+)$", text)
    if not match:
        return (text, 0)
    return (match.group(1), int(match.group(2)))


def numeric_text(value):
    value = clean(value)
    if not value:
        return ""
    try:
        number = float(value)
    except ValueError:
        return value
    if number.is_integer():
        return str(int(number))
    return value


def unique_sorted(values):
    return sorted({clean(value) for value in values if clean(value)}, key=lambda value: value.casefold())


def compact_dict(values):
    return {key: value for key, value in values.items() if value not in ("", [], {}, None)}


def read_sheet(workbook, name):
    return pd.read_excel(workbook, sheet_name=name, dtype=str).fillna("")


def build_payload(workbook_path):
    sheets = pd.ExcelFile(workbook_path)
    required_sheets = {
        "Bestand",
        "Werke",
        "Bestand_Werk",
        "Werkarten",
        "Werk_Werkart",
        "Feldschema",
        "Vokabular",
    }
    missing = sorted(required_sheets - set(sheets.sheet_names))
    if missing:
        raise ValueError(f"Fehlende Tabellenblaetter: {', '.join(missing)}")

    bestand_rows = [clean_row(row) for row in read_sheet(workbook_path, "Bestand").to_dict("records")]
    werk_rows = [clean_row(row) for row in read_sheet(workbook_path, "Werke").to_dict("records")]
    bestand_werk_rows = [clean_row(row) for row in read_sheet(workbook_path, "Bestand_Werk").to_dict("records")]
    werkart_rows = [clean_row(row) for row in read_sheet(workbook_path, "Werkarten").to_dict("records")]
    werk_werkart_rows = [clean_row(row) for row in read_sheet(workbook_path, "Werk_Werkart").to_dict("records")]

    works_by_id = {row["Werk_ID"]: row for row in werk_rows if row.get("Werk_ID")}
    work_types_by_id = {row["Werkart_ID"]: row for row in werkart_rows if row.get("Werkart_ID")}

    type_labels_by_work_id = defaultdict(list)
    for relation in werk_werkart_rows:
        work_id = relation.get("Werk_ID", "")
        type_row = work_types_by_id.get(relation.get("Werkart_ID", ""), {})
        label = type_row.get("Bezeichnung", "")
        if work_id and label:
            type_labels_by_work_id[work_id].append(label)

    work_ids_by_record_id = defaultdict(list)
    relationship_notes_by_key = {}
    for relation in bestand_werk_rows:
        record_id = relation.get("Bestand_ID", "")
        work_id = relation.get("Werk_ID", "")
        if record_id and work_id:
            work_ids_by_record_id[record_id].append(work_id)
            relationship_notes_by_key[(record_id, work_id)] = compact_dict(
                {
                    "level": relation.get("Erschließungsebene", ""),
                    "relationship": relation.get("Beziehung", ""),
                    "note": relation.get("Bemerkung", ""),
                }
            )

    records = []
    for bestand in sorted(bestand_rows, key=lambda row: natural_id_key(row.get("Bestand_ID", ""))):
        record_id = bestand.get("Bestand_ID", "")
        work_ids = work_ids_by_record_id.get(record_id, [])
        works = []
        for work_id in work_ids:
            work = works_by_id.get(work_id)
            if not work:
                continue
            works.append(
                compact_dict(
                    {
                        "id": work_id,
                        "composer": work.get("Komponist_normiert", ""),
                        "attribution": work.get("Zuschreibung", ""),
                        "title": work.get("Werktitel_normiert", ""),
                        "key": work.get("Tonart", ""),
                        "catalogNumber": work.get("Werkverzeichnisnummer", ""),
                        "note": work.get("Bemerkung", ""),
                        "recordCount": numeric_text(work.get("Anzahl_Bestandseinheiten", "")),
                        "types": unique_sorted(type_labels_by_work_id.get(work_id, [])),
                        "link": relationship_notes_by_key.get((record_id, work_id), {}),
                    }
                )
            )

        letter = record_id.split("-", 1)[0] if "-" in record_id else ""
        work_type_labels = unique_sorted(label for work in works for label in work.get("types", []))
        work_attributions = unique_sorted(work.get("attribution", "") for work in works)
        normalized_composers = unique_sorted(work.get("composer", "") for work in works)
        normalized_titles = unique_sorted(work.get("title", "") for work in works)

        search_text = " ".join(
            [
                record_id,
                letter,
                bestand.get("Signatur", ""),
                bestand.get("Komponist_Karte", ""),
                bestand.get("Titel_Karte", ""),
                bestand.get("Besetzung_Karte", ""),
                bestand.get("Materialart", ""),
                bestand.get("Umfang", ""),
                bestand.get("Druckangaben", ""),
                bestand.get("Datierung_Quelle", ""),
                bestand.get("Aufführungsdaten_Text", ""),
                bestand.get("Provenienz", ""),
                bestand.get("Vollständigkeit", ""),
                bestand.get("Kartentext_gesamt", ""),
                bestand.get("Bemerkung_modern", ""),
                " ".join(normalized_composers),
                " ".join(normalized_titles),
                " ".join(work_type_labels),
                " ".join(work_attributions),
            ]
        )

        records.append(
            compact_dict(
                {
                    "id": record_id,
                    "letter": letter,
                    "pdfPage": numeric_text(bestand.get("PDF_Seite", "")),
                    "cardUrl": bestand.get("Karte_URL", ""),
                    "signature": bestand.get("Signatur", ""),
                    "composerCard": bestand.get("Komponist_Karte", ""),
                    "titleCard": bestand.get("Titel_Karte", ""),
                    "scoringCard": bestand.get("Besetzung_Karte", ""),
                    "voiceCount": numeric_text(bestand.get("Stimmenzahl", "")),
                    "materialType": bestand.get("Materialart", ""),
                    "hasScore": bestand.get("Partitur", ""),
                    "voicesAvailable": bestand.get("Stimmen_vorhanden", ""),
                    "extent": bestand.get("Umfang", ""),
                    "dimensions": bestand.get("Maße_cm", ""),
                    "printing": bestand.get("Druckangaben", ""),
                    "sourceDate": bestand.get("Datierung_Quelle", ""),
                    "performanceDateStart": numeric_text(bestand.get("Aufführungsdaten_von", "")),
                    "performanceDateEnd": numeric_text(bestand.get("Aufführungsdaten_bis", "")),
                    "performanceDateText": bestand.get("Aufführungsdaten_Text", ""),
                    "provenance": bestand.get("Provenienz", ""),
                    "completeness": bestand.get("Vollständigkeit", ""),
                    "handwrittenAddition": bestand.get("Nachtrag_handschriftlich", ""),
                    "cardText": bestand.get("Kartentext_gesamt", ""),
                    "modernNote": bestand.get("Bemerkung_modern", ""),
                    "reviewStatus": bestand.get("Prüfstatus", ""),
                    "works": works,
                    "workTypes": work_type_labels,
                    "workAttributions": work_attributions,
                    "normalizedComposers": normalized_composers,
                    "normalizedTitles": normalized_titles,
                    "searchText": search_text,
                }
            )
        )

    letter_counts = Counter(record.get("letter", "") for record in records if record.get("letter"))
    payload = {
        "metadata": {
            "source": Path(workbook_path).name,
            "recordCount": len(records),
            "workCount": len(works_by_id),
            "relationshipCount": len(bestand_werk_rows),
            "workTypeCount": len(work_types_by_id),
            "letters": sorted(letter_counts),
            "letterCounts": dict(sorted(letter_counts.items())),
        },
        "facets": {
            "letters": sorted(letter_counts),
            "materialTypes": unique_sorted(record.get("materialType", "") for record in records),
            "voicesAvailable": unique_sorted(record.get("voicesAvailable", "") for record in records),
            "reviewStatuses": unique_sorted(record.get("reviewStatus", "") for record in records),
            "workAttributions": unique_sorted(value for record in records for value in record.get("workAttributions", [])),
            "workTypes": unique_sorted(value for record in records for value in record.get("workTypes", [])),
        },
        "records": records,
    }
    return payload


def main():
    parser = argparse.ArgumentParser(description="Build static music archive search data from the relational Excel model.")
    parser.add_argument("workbook", help="Path to Musikalien Excel workbook")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output JSON path")
    args = parser.parse_args()

    payload = build_payload(Path(args.workbook))
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    metadata = payload["metadata"]
    print(
        f"{metadata['recordCount']} Bestandseinheiten, {metadata['workCount']} Werke, "
        f"{metadata['relationshipCount']} Beziehungen -> {output_path.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
