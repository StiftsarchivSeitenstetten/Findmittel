#!/usr/bin/env python3
import csv
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ITEMS_PATH = ROOT / "bibliothek" / "Items.csv"
OUTPUT_DIR = ROOT / "assets" / "data" / "bibliothek"
MARC_CANDIDATES = [
    ROOT / "bibliothek" / "MARC-bibliographic.xml",
    ROOT / "bibliothek" / "MARC_Bibliographic.xml",
]


def first_existing_path(paths):
    for path in paths:
        if path.exists():
            return path

    names = ", ".join(str(path.relative_to(ROOT)) for path in paths)
    raise FileNotFoundError(f"Keine MARCXML-Datei gefunden. Erwartet wurde eine von: {names}")


MARC_PATH = first_existing_path(MARC_CANDIDATES)


def clean(value):
    value = (value or "").strip()
    while len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


def text_of(element):
    return clean(element.text) if element is not None else ""


def control(record, tag):
    return text_of(record.find(f'controlfield[@tag="{tag}"]'))


def subfields(field):
    return [(subfield.get("code"), clean(subfield.text)) for subfield in field.findall("subfield")]


def field_values(record, tag, codes=None):
    values = []
    for field in record.findall(f'datafield[@tag="{tag}"]'):
        parts = []
        for code, text in subfields(field):
            if text and (codes is None or code in codes):
                parts.append(text)
        if parts:
            values.append(" ".join(parts))
    return values


def first_field_value(record, tag, codes=None):
    values = field_values(record, tag, codes)
    return values[0] if values else ""


def parse_publication(record):
    values = field_values(record, "264", {"a", "b", "c"}) or field_values(record, "260", {"a", "b", "c"})
    publication_text = " | ".join(values)
    years = re.findall(r"(1[4-9]\d{2}|20\d{2})", publication_text)

    return {
        "text": publication_text,
        "year": years[-1] if years else "",
    }


def parse_links(record):
    links = []
    for field in record.findall('datafield[@tag="856"]'):
        values = defaultdict(list)
        for code, text in subfields(field):
            if text:
                values[code].append(text)

        url = " ".join(values.get("u", []))
        if url:
            links.append(
                {
                    "url": url,
                    "label": " ".join(values.get("z", []) or values.get("3", [])),
                }
            )

    return links


def parse_holdings(record):
    holdings = []
    for field in record.findall('datafield[@tag="852"]'):
        values = defaultdict(list)
        for code, text in subfields(field):
            if text:
                values[code].append(text)

        holdings.append(
            {
                "holdingId": " ".join(values.get("8", [])),
                "library": " ".join(values.get("b", [])),
                "location": " ".join(values.get("c", [])),
                "callNumber": " ".join(values.get("h", [])),
            }
        )

    return holdings


def extract_ac_number(value):
    match = re.search(r"AC\d+", value or "")
    return match.group(0) if match else ""


def parse_host_relations(record):
    relations = []
    for field in record.findall('datafield[@tag="773"]'):
        values = defaultdict(list)
        for code, text in subfields(field):
            if text:
                values[code].append(text)

        ac_numbers = [extract_ac_number(value) for value in values.get("w", [])]
        ac_numbers = [value for value in ac_numbers if value]
        citation_parts = []
        for code in ("i", "t", "d", "g", "q", "w"):
            citation_parts.extend(values.get(code, []))

        relations.append(
            {
                "acNumber": ac_numbers[0] if ac_numbers else "",
                "title": " ".join(values.get("t", [])),
                "pages": " ".join(values.get("g", []) or values.get("q", [])),
                "text": " ".join(citation_parts),
            }
        )

    return relations


def normalize_marc_record(record):
    publication = parse_publication(record)
    host_relations = parse_host_relations(record)
    creators = (
        field_values(record, "100", {"a", "d"})
        + field_values(record, "110", {"a", "b"})
        + field_values(record, "111", {"a", "d"})
    )
    contributors = (
        field_values(record, "700", {"a", "d"})
        + field_values(record, "710", {"a", "b"})
        + field_values(record, "711", {"a", "d"})
    )
    subjects = (
        field_values(record, "600", {"a"})
        + field_values(record, "610", {"a"})
        + field_values(record, "650", {"a"})
        + field_values(record, "651", {"a"})
        + field_values(record, "689", {"a"})
    )
    genres = field_values(record, "655", {"a"})

    return {
        "id": control(record, "001"),
        "acNumber": control(record, "009"),
        "title": first_field_value(record, "245", {"a", "b", "n", "p"}),
        "responsibility": first_field_value(record, "245", {"c"}),
        "variantTitles": field_values(record, "246", {"a", "b", "n", "p"}),
        "creators": creators,
        "contributors": contributors,
        "publication": publication,
        "extent": first_field_value(record, "300", {"a", "b", "c"}),
        "languages": field_values(record, "041", {"a"}),
        "subjects": subjects,
        "genres": genres,
        "series": field_values(record, "490", {"a", "v"}) + field_values(record, "830", {"a", "v"}),
        "relations": [relation["text"] for relation in host_relations if relation["text"]],
        "hostRelations": host_relations,
        "holdings": parse_holdings(record),
        "links": parse_links(record),
    }


def read_items():
    with ITEMS_PATH.open(newline="", encoding="utf-8-sig") as handle:
        rows = []
        for row in csv.DictReader(handle):
            title_id = clean(row.get("MMS Record ID"))
            if not title_id or title_id == "end-of-file":
                continue

            rows.append(
                {
                    "id": clean(row.get("Item PID")),
                    "titleId": title_id,
                    "holdingId": clean(row.get("HOL Record ID")),
                    "barcode": clean(row.get(" Barcode")),
                    "title": clean(row.get(" Title")),
                    "creator": clean(row.get(" Creator")),
                    "callNumber": clean(row.get(" Call Number")),
                    "permanentCallNumber": clean(row.get(" Permanent Call Number")),
                    "location": clean(row.get(" Permanent Physical Location")),
                    "localLocation": clean(row.get(" Local Location")),
                    "holdingType": clean(row.get(" Holding Type")),
                    "materialType": clean(row.get(" Item Material Type")),
                    "chronology": clean(row.get("Chronology")),
                    "enumeration": clean(row.get("Enumeration")),
                    "issueYear": clean(row.get("Issue year")),
                    "description": clean(row.get("Description")),
                    "publicNote": clean(row.get("Public note")),
                    "status": clean(row.get("Status")),
                    "otherSystemNumber": clean(row.get(" Other System Number")),
                }
            )

    return rows


def record_reference(record):
    return {
        "id": record["id"],
        "acNumber": record["acNumber"],
        "title": record["title"],
        "creator": "; ".join(record["creators"][:3]),
        "year": record["publication"]["year"],
        "publication": record["publication"]["text"],
    }


def attach_record_relationships(records):
    records_by_ac = {record["acNumber"]: record for record in records if record["acNumber"]}
    children_by_parent_id = defaultdict(list)

    for record in records:
        superordinates = []
        for relation in record["hostRelations"]:
            parent = records_by_ac.get(relation["acNumber"])
            if not parent:
                continue

            parent_reference = record_reference(parent)
            parent_reference.update(
                {
                    "relationText": relation["text"],
                    "pages": relation["pages"],
                }
            )
            superordinates.append(parent_reference)

            child_reference = record_reference(record)
            child_reference.update(
                {
                    "relationText": relation["text"],
                    "pages": relation["pages"],
                    "hasOwnItems": bool(record["items"]),
                }
            )
            children_by_parent_id[parent["id"]].append(child_reference)

        record["superordinates"] = superordinates
        record["superordinate"] = superordinates[0] if superordinates else None

    for record in records:
        record["childRecords"] = sorted(
            children_by_parent_id.get(record["id"], []),
            key=lambda child: (child["title"] or "", child["acNumber"] or ""),
        )


def effective_items(record, records_by_id):
    if record["items"]:
        return record["items"]

    superordinate = record.get("superordinate")
    if not superordinate:
        return []

    parent = records_by_id.get(superordinate["id"])
    return parent["items"] if parent else []


def build_search_doc(record, records_by_id):
    items = effective_items(record, records_by_id)
    locations = sorted({item["location"] for item in items if item["location"]})
    call_numbers = sorted({item["permanentCallNumber"] or item["callNumber"] for item in items if item["permanentCallNumber"] or item["callNumber"]})
    material_types = sorted({item["materialType"] for item in items if item["materialType"]})
    title = record["title"]
    creator = "; ".join(record["creators"][:3])
    year = record["publication"]["year"]
    superordinate = record.get("superordinate")

    search_parts = [
        title,
        record["responsibility"],
        creator,
        "; ".join(record["contributors"]),
        record["publication"]["text"],
        record["extent"],
        "; ".join(record["variantTitles"]),
        "; ".join(record["subjects"]),
        "; ".join(record["genres"]),
        "; ".join(record["series"]),
        "; ".join(locations),
        "; ".join(call_numbers),
        "; ".join(item["description"] for item in items),
        "; ".join(item["chronology"] for item in items),
        "; ".join(item["enumeration"] for item in items),
        superordinate["title"] if superordinate else "",
        superordinate["acNumber"] if superordinate else "",
        "Aufsatz Beitrag" if superordinate else "",
    ]

    return {
        "id": record["id"],
        "title": title,
        "creator": creator,
        "year": year,
        "publication": record["publication"]["text"],
        "locations": locations,
        "callNumbers": call_numbers,
        "materialTypes": material_types,
        "languages": record["languages"],
        "genres": record["genres"],
        "itemCount": len(record["items"]),
        "displayItemCount": len(items),
        "inheritedItemCount": len(items) if not record["items"] and superordinate else 0,
        "recordType": "Aufsatz/Beitrag" if superordinate else "",
        "superordinateTitle": superordinate["title"] if superordinate else "",
        "searchText": " ".join(part for part in search_parts if part),
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    root = ET.parse(MARC_PATH).getroot()
    records = [normalize_marc_record(record) for record in root.findall("record")]
    records_by_id = {record["id"]: record for record in records}

    items = read_items()
    items_by_title_id = defaultdict(list)
    unmatched_items = []

    for item in items:
        if item["titleId"] in records_by_id:
            items_by_title_id[item["titleId"]].append(item)
        else:
            unmatched_items.append(item)

    for record in records:
        record["items"] = items_by_title_id.get(record["id"], [])

    attach_record_relationships(records)
    search_docs = [build_search_doc(record, records_by_id) for record in records]

    manifest = {
        "sourceFiles": {
            "marc": str(MARC_PATH.relative_to(ROOT)),
            "items": str(ITEMS_PATH.relative_to(ROOT)),
        },
        "titleCount": len(records),
        "itemCount": len(items),
        "linkedItemCount": len(items) - len(unmatched_items),
        "unmatchedItemCount": len(unmatched_items),
        "titlesWithItems": sum(1 for record in records if record["items"]),
        "titlesWithoutItems": sum(1 for record in records if not record["items"]),
        "recordsWithSuperordinate": sum(1 for record in records if record["superordinate"]),
        "recordsWithChildRecords": sum(1 for record in records if record["childRecords"]),
        "recordsWithInheritedItems": sum(
            1
            for record in records
            if not record["items"] and effective_items(record, records_by_id)
        ),
        "locations": Counter(item["location"] for item in items if item["location"]).most_common(),
        "materialTypes": Counter(item["materialType"] for item in items if item["materialType"]).most_common(),
    }

    (OUTPUT_DIR / "records.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "search-docs.json").write_text(
        json.dumps(search_docs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
