#!/usr/bin/env python3
"""Build the static Catalogus Codicum web layer from Markdown/YAML master files.

The Markdown/YAML files remain the scientific master data. This script creates a
stable, versioned web representation and reports source fields that are not yet
mapped into that representation.

Usage from the repository root:
    python3 scripts/build-catalogus-codicum.py

Dependency:
    PyYAML (pip install -r scripts/requirements-catalogus.txt)
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import html
import json
import re
import shutil
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover - friendly CLI failure
    raise SystemExit(
        "PyYAML fehlt. Bitte zuerst `pip install -r scripts/requirements-catalogus.txt` ausführen."
    ) from exc

SCHEMA_VERSION = 1
BUILD_NAME = "catalogus-web-schema"
IGNORE_FILES = {"Signaturen_nicht_MN_Uebersicht.md"}

ROLE_LABELS = {
    "author": "Autor",
    "scribe": "Schreiber",
    "lecturer": "Dozent",
    "owner": "Besitzer",
    "former_owner": "Vorbesitzer",
    "donor": "Schenker",
    "recipient": "Empfänger",
    "compiler": "Bearbeiter",
    "translator": "Übersetzer",
    "editor": "Herausgeber",
    "dedicatee": "Widmungsempfänger",
    "dedicator": "Widmender",
    "patron": "Auftraggeber",
    "student": "Student",
    "respondent": "Respondent",
    "president": "Präses",
    "printer": "Drucker",
    "publisher": "Verleger",
    "mentioned": "erwähnt",
}

RELATION_LABELS = {
    "same_work_as": "gleiche Textüberlieferung / gleiches Werk",
    "same_text_as": "gleicher Text",
    "same_scribe_as": "gleicher Schreiber",
    "possible_same_scribe_as": "möglicherweise gleicher Schreiber",
    "continuation_of": "Fortsetzung von",
    "continued_by": "fortgesetzt durch",
    "parallel_to": "Parallelüberlieferung",
    "related_to": "verwandte Handschrift",
    "course_series": "gleicher Kurs / Kursserie",
    "same_author_series": "gleicher Autor / Werkzusammenhang",
}

TITLE_TYPE_LABELS = {
    "supplied": "erschlossener Titel",
    "original": "überlieferter Titel",
    "shortened_from_original": "aus dem Originaltitel gekürzt",
    "inferred": "erschlossener Titel",
}

MANUSCRIPT_RELATION_TYPES = {
    "same_work_as", "same_text_as", "same_scribe_as", "possible_same_scribe_as",
    "continuation_of", "continued_by", "parallel_to", "related_to", "course_series",
    "same_author_series", "same_lectures_as", "parallel_texts", "same_scribe_probably_as",
    "probably_different_scribe_from", "same_scribe_series", "other_copy",
}


TOP_LEVEL_MAPPED = {
    "aliases", "tags", "signature", "catalog_page", "ms_identifier", "ms_contents",
    "phys_desc", "history", "responsibility", "relations", "additions", "editorial_notes",
    "persons", "publication_history", "references", "source_references", "places",
    "bibliography", "catalog_annotations",
}

ITEM_MAPPED = {
    "item", "label", "type", "title", "title_type", "title_source", "title_note",
    "parent_title", "translation", "translation_note", "locus", "end_locus", "extent",
    "language", "languages", "text_lang", "text_language", "title_language", "incipit",
    "incipits", "explicit", "responsibility", "responsibility_statement", "persons", "author",
    "author_or_lecturer", "lecturer", "note", "summary", "description", "contents_note",
    "catalog_statement", "date", "date_display", "content_date", "text_date", "event_date",
    "start_date", "start_date_display", "end_date", "end_date_display", "end_time_display",
    "alternative_date", "compilation_date", "dated_clausula", "dated_clausulae", "dated_note",
    "dated_notes", "event", "place", "places", "subject", "thema", "certainty",
    "completeness", "status", "physical_unit", "support", "layout", "print_status",
    "lecture_count", "number_of_conclusions", "number_of_theses", "first_section_number",
    "final_section_number", "source_loci", "source_work", "related_text", "work_history",
    "structure", "index", "indexed_parts", "incipit_section", "subitems", "parts",
    "catalogue_title_or_summary", "overall_title", "contents", "context", "genre",
    "language_note", "manuscript_additions", "missing_contents", "part", "printed_work",
    "publication_status", "relations",
}


def plain(value: Any) -> str:
    """Return a conservative, human-readable string without inventing semantics."""
    if value is None:
        return ""
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, bool):
        return "ja" if value else "nein"
    if isinstance(value, (int, float, str)):
        return str(value).strip()
    if isinstance(value, list):
        return "; ".join(filter(None, (plain(v) for v in value)))
    if isinstance(value, dict):
        # Prefer common display-bearing keys, otherwise retain key/value meaning.
        for key in ("display", "text", "original", "translation", "name", "label", "title", "note"):
            if key in value and plain(value.get(key)):
                return plain(value.get(key))
        return "; ".join(
            f"{k}: {plain(v)}" for k, v in value.items() if plain(v)
        )
    return str(value).strip()


def normalize_search(value: Any) -> str:
    text = plain(value)
    expanded = (
        text.replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
        .replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
        .replace("ß", "ss").replace("æ", "ae").replace("Æ", "Ae")
        .replace("œ", "oe").replace("Œ", "Oe")
    )
    both = text + " " + expanded
    both = unicodedata.normalize("NFD", both)
    both = "".join(ch for ch in both if unicodedata.category(ch) != "Mn")
    both = both.lower()
    both = re.sub(r"[^\w]+", " ", both, flags=re.UNICODE)
    return re.sub(r"\s+", " ", both).strip()


def slugify(value: str) -> str:
    value = value.replace("₀", "0").replace("₁", "1").replace("₂", "2").replace("₃", "3")
    value = value.replace("₄", "4").replace("₅", "5").replace("₆", "6").replace("₇", "7")
    value = value.replace("₈", "8").replace("₉", "9")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().replace("ß", "ss")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "record"


def split_frontmatter(text: str, path: Path) -> tuple[dict[str, Any], str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if not match:
        raise ValueError(f"{path.name}: YAML-Frontmatter fehlt oder ist ungültig abgegrenzt.")
    data = yaml.safe_load(match.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: YAML-Frontmatter ist kein Mapping.")
    return data, text[match.end():]


def split_catalogue_sections(body: str) -> tuple[str, str]:
    de_marker = re.search(r"(?m)^# Deutsche Übersetzung\s*$", body)
    la_marker = re.search(r"(?m)^# Lateinischer Originaltext\s*$", body)
    if not de_marker or not la_marker or la_marker.start() < de_marker.end():
        return "", ""
    german = body[de_marker.end():la_marker.start()].strip("\n")
    latin = body[la_marker.end():].strip("\n")
    return german, latin


def inline_md(text: str) -> str:
    escaped = html.escape(text, quote=False)
    # Very small, source-preserving inline subset; input is escaped first.
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<em>\1</em>", escaped)
    escaped = re.sub(r"`([^`\n]+?)`", r"<code>\1</code>", escaped)
    return escaped


def markdown_lite_to_html(markdown: str) -> str:
    """Render the limited Markdown used by the catalogue texts without extra dependencies."""
    lines = markdown.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    blockquote: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(line.strip() for line in paragraph).strip()
            if text:
                out.append(f"<p>{inline_md(text)}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            out.append("<ul>" + "".join(f"<li>{inline_md(item)}</li>" for item in list_items) + "</ul>")
            list_items = []

    def flush_quote() -> None:
        nonlocal blockquote
        if blockquote:
            text = " ".join(blockquote).strip()
            out.append(f"<blockquote><p>{inline_md(text)}</p></blockquote>")
            blockquote = []

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush_paragraph(); flush_list(); flush_quote()
            continue
        if re.match(r"^\s*---+\s*$", line):
            flush_paragraph(); flush_list(); flush_quote(); out.append("<hr>")
            continue
        m = re.match(r"^\s*[-*]\s+(.+)$", line)
        if m:
            flush_paragraph(); flush_quote(); list_items.append(m.group(1).strip()); continue
        m = re.match(r"^\s*>\s?(.*)$", line)
        if m:
            flush_paragraph(); flush_list(); blockquote.append(m.group(1).strip()); continue
        # Any headings accidentally retained are rendered semantically but at low level.
        m = re.match(r"^\s*#{1,6}\s+(.+)$", line)
        if m:
            flush_paragraph(); flush_list(); flush_quote(); out.append(f"<h4>{inline_md(m.group(1).strip())}</h4>"); continue
        flush_list(); flush_quote(); paragraph.append(line)
    flush_paragraph(); flush_list(); flush_quote()
    return "\n".join(out)


def clean_wikilink(value: str) -> str:
    value = value.strip()
    match = re.fullmatch(r"\[\[(.+?)(?:\|.+?)?\]\]", value)
    return match.group(1).strip() if match else value


def year_value(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (dt.date, dt.datetime)):
        return value.year
    if isinstance(value, int) and 500 <= value <= 2100:
        return value
    text = str(value).strip()
    match = re.match(r"^(\d{4})(?:-\d{2}-\d{2})?$", text)
    return int(match.group(1)) if match else None


def derive_intervals(date_data: Any) -> tuple[list[dict[str, Any]], str]:
    """Normalize origin dates conservatively; never inspect unrelated free text."""
    if not isinstance(date_data, dict):
        return [], "none"
    intervals: list[dict[str, Any]] = []
    when = year_value(date_data.get("when"))
    start = year_value(date_data.get("from"))
    end = year_value(date_data.get("to"))
    not_before = year_value(date_data.get("not_before"))
    not_after = year_value(date_data.get("not_after"))
    if when:
        intervals.append({"from": when, "to": when, "source": "structured"})
        return intervals, "structured"
    if start or end:
        a, b = start or end, end or start
        intervals.append({"from": min(a, b), "to": max(a, b), "source": "structured"})
        return intervals, "structured"
    if not_before or not_after:
        a, b = not_before or not_after, not_after or not_before
        intervals.append({"from": min(a, b), "to": max(a, b), "source": "structured_bounds"})
        return intervals, "structured_bounds"

    display = plain(date_data.get("display"))
    if not display:
        return [], "none"
    # Derive only from unambiguous year expressions in the designated origin date display.
    # Multiple comma-separated points/ranges stay separate rather than becoming one broad span.
    pieces = [p.strip() for p in re.split(r"[,;]", display) if p.strip()]
    derived: list[dict[str, Any]] = []
    for piece in pieces:
        p = piece.lower().replace("–", "-").replace("—", "-")
        p = re.sub(r"\b(ca\.?|circa|um|etwa|wohl|vermutlich|nach|vor)\b", " ", p)
        p = re.sub(r"\s+", " ", p).strip()
        m = re.fullmatch(r"(\d{4})", p)
        if m:
            y = int(m.group(1)); derived.append({"from": y, "to": y, "source": "display_derived"}); continue
        m = re.fullmatch(r"(\d{4})\s*[/]\s*(\d{2,4})", p)
        if m:
            a = int(m.group(1)); btxt = m.group(2); b = int(btxt) if len(btxt) == 4 else (a // 100) * 100 + int(btxt)
            if b < a: b += 100
            derived.append({"from": a, "to": b, "source": "display_derived"}); continue
        m = re.fullmatch(r"(\d{4})\s*-\s*(\d{2,4})", p)
        if m:
            a = int(m.group(1)); btxt = m.group(2); b = int(btxt) if len(btxt) == 4 else (a // 100) * 100 + int(btxt)
            if b < a: b += 100
            derived.append({"from": min(a,b), "to": max(a,b), "source": "display_derived"}); continue
        # Century expressions are deliberately not expanded in v1.
        return [], "display_unparsed"
    return (derived, "display_derived") if derived else ([], "display_unparsed")


def normalize_responsibilities(value: Any, *, scope: str, item_id: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []

    def add(role: Any, name: Any, extra: dict[str, Any] | None = None) -> None:
        name_text = plain(name)
        if not name_text:
            return
        role_text = plain(role) or "unspecified"
        entry = {
            "name": name_text,
            "roleRaw": role_text,
            "roleLabel": ROLE_LABELS.get(role_text, role_text.replace("_", " ")),
            "scope": scope,
        }
        if item_id:
            entry["itemId"] = item_id
        if extra:
            for key in ("affiliation", "certainty", "note", "locus", "date"):
                val = plain(extra.get(key))
                if val:
                    entry[key] = val
        out.append(entry)

    if value is None:
        return out
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                if "name" in item:
                    add(item.get("role"), item.get("name"), item)
                else:
                    out.extend(normalize_responsibilities(item, scope=scope, item_id=item_id))
            elif plain(item):
                add("unspecified", item)
        return out
    if isinstance(value, dict):
        if "name" in value:
            add(value.get("role"), value.get("name"), value)
            return out
        for role, persons in value.items():
            if role in {"note", "certainty", "affiliation"}:
                continue
            if isinstance(persons, list):
                for person in persons:
                    if isinstance(person, dict):
                        add(role, person.get("name") or person.get("label") or person, person)
                    else:
                        add(role, person)
            elif isinstance(persons, dict):
                add(role, persons.get("name") or persons.get("label") or persons, persons)
            else:
                add(role, persons)
        return out
    add("unspecified", value)
    return out


def normalize_incipit(value: Any) -> dict[str, str] | None:
    if not value:
        return None
    if isinstance(value, dict):
        result = {k: plain(v) for k, v in value.items() if plain(v)}
        return result or None
    return {"text": plain(value)}


def item_title(item: dict[str, Any]) -> str:
    for key in ("title", "overall_title", "parent_title", "catalogue_title_or_summary", "catalog_statement", "summary", "description", "contents_note"):
        if plain(item.get(key)):
            return plain(item.get(key))
    label = plain(item.get("label") or item.get("item"))
    return f"Inhaltseinheit {label}" if label else "Inhaltseinheit"


def item_identifier(item: dict[str, Any], index: int, used: set[str]) -> str:
    base = plain(item.get("label") or item.get("item") or index + 1)
    stem = "item-" + slugify(base)
    candidate = stem
    suffix = 2
    while candidate in used:
        candidate = f"{stem}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate

def normalize_item(item: dict[str, Any], index: int, used: set[str], unmapped: Counter[str]) -> dict[str, Any]:
    item_id = item_identifier(item, index, used)
    for key in item:
        if key not in ITEM_MAPPED:
            unmapped[f"ms_contents.items.{key}"] += 1

    title = item_title(item)
    title_type = plain(item.get("title_type"))
    result: dict[str, Any] = {
        "id": item_id,
        "label": plain(item.get("label") or item.get("item")),
        "type": plain(item.get("type")),
        "title": {
            "text": title,
            "typeRaw": title_type or None,
            "typeLabel": TITLE_TYPE_LABELS.get(title_type, title_type.replace("_", " ") if title_type else None),
        },
        "locus": plain(item.get("locus")),
        "language": plain(item.get("language") or item.get("languages") or item.get("text_lang") or item.get("text_language")),
        "incipit": normalize_incipit(item.get("incipit") or item.get("incipits")),
        "explicit": normalize_incipit(item.get("explicit")),
        "notes": [],
        "dates": [],
        "persons": [],
        "subitems": [],
    }
    for key in ("translation", "title_note", "contents_note", "note", "summary", "description", "catalog_statement", "certainty", "status", "completeness", "context", "genre", "language_note", "manuscript_additions", "missing_contents", "part", "printed_work", "publication_status", "contents"):
        val = plain(item.get(key))
        if val:
            result["notes"].append({"type": key, "text": val})
    for key in ("start_date", "start_date_display", "end_date", "end_date_display", "date", "date_display", "content_date", "text_date", "event_date", "alternative_date", "compilation_date", "dated_clausula", "dated_clausulae", "dated_note", "dated_notes"):
        val = plain(item.get(key))
        if val:
            result["dates"].append({"type": key, "display": val})

    result["persons"].extend(normalize_responsibilities(item.get("responsibility"), scope="item", item_id=item_id))
    result["persons"].extend(normalize_responsibilities(item.get("persons"), scope="item", item_id=item_id))
    if item.get("author"):
        result["persons"].extend(normalize_responsibilities({"author": item.get("author")}, scope="item", item_id=item_id))
    if item.get("lecturer"):
        result["persons"].extend(normalize_responsibilities({"lecturer": item.get("lecturer")}, scope="item", item_id=item_id))
    if item.get("author_or_lecturer"):
        result["persons"].extend(normalize_responsibilities({"author_or_lecturer": item.get("author_or_lecturer")}, scope="item", item_id=item_id))

    children = item.get("subitems") or item.get("parts") or []
    if isinstance(children, dict):
        children = [children]
    if isinstance(children, list):
        for child_index, child in enumerate(children):
            if isinstance(child, dict):
                result["subitems"].append(normalize_item(child, child_index, used, unmapped))
    return result


def content_units(ms_contents: Any, unmapped: Counter[str]) -> tuple[str, str, list[dict[str, Any]], list[dict[str, Any]]]:
    overall_title = ""
    title_type = ""
    top_persons: list[dict[str, Any]] = []
    raw_items: list[dict[str, Any]] = []
    if isinstance(ms_contents, list):
        raw_items = [x for x in ms_contents if isinstance(x, dict)]
    elif isinstance(ms_contents, dict):
        raw_title = ms_contents.get("title") or ms_contents.get("overall_title") or ms_contents.get("catalogue_title_or_summary")
        if isinstance(raw_title, dict):
            overall_title = plain(raw_title.get("title") or raw_title.get("text") or raw_title)
            title_type = plain(raw_title.get("title_type"))
        else:
            overall_title = plain(raw_title)
            title_type = plain(ms_contents.get("title_type"))
        top_persons.extend(normalize_responsibilities(ms_contents.get("responsibility"), scope="contents"))
        candidate = ms_contents.get("items")
        if isinstance(candidate, list):
            raw_items = [x for x in candidate if isinstance(x, dict)]
        elif isinstance(candidate, dict):
            raw_items = [candidate]
        elif not candidate and any(ms_contents.get(k) for k in ("title", "overall_title", "catalogue_title_or_summary", "summary", "locus")):
            # Older source variants sometimes describe the only content unit at ms_contents level.
            raw_items = [copy.deepcopy(ms_contents)]
    used: set[str] = set()
    items = [normalize_item(item, i, used, unmapped) for i, item in enumerate(raw_items)]
    if not overall_title and items:
        overall_title = items[0]["title"]["text"]
        title_type = items[0]["title"].get("typeRaw") or ""
    return overall_title, title_type, items, top_persons


def normalize_contents_overview(ms_contents: Any) -> dict[str, Any]:
    if not isinstance(ms_contents, dict):
        return {}
    raw_title = ms_contents.get("title") or ms_contents.get("overall_title") or ms_contents.get("catalogue_title_or_summary")
    if isinstance(raw_title, dict):
        title_text = plain(raw_title.get("title") or raw_title.get("text") or raw_title)
        title_type = plain(raw_title.get("title_type"))
        language = plain(raw_title.get("language"))
        translation = plain(raw_title.get("translation"))
    else:
        title_text = plain(raw_title)
        title_type = plain(ms_contents.get("title_type"))
        language = plain(ms_contents.get("language") or ms_contents.get("languages") or ms_contents.get("text_lang"))
        translation = plain(ms_contents.get("translation"))
    return {
        "title": title_text,
        "titleTypeRaw": title_type,
        "titleTypeLabel": TITLE_TYPE_LABELS.get(title_type, title_type.replace("_", " ") if title_type else ""),
        "translation": translation,
        "summary": plain(ms_contents.get("summary")),
        "language": language,
        "locus": plain(ms_contents.get("locus")),
        "incipit": normalize_incipit(ms_contents.get("incipit") or ms_contents.get("incipits")),
        "explicit": normalize_incipit(ms_contents.get("explicit")),
        "part": plain(ms_contents.get("part")),
        "note": plain(ms_contents.get("note")),
        "completeness": plain(ms_contents.get("completeness")),
    }

def normalize_physical(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    binding = data.get("binding")
    if isinstance(binding, dict):
        binding_out = {
            "code": plain(binding.get("catalog_code") or binding.get("code")),
            "description": plain(binding.get("description")),
            "certainty": plain(binding.get("certainty")),
            "note": plain(binding.get("note")),
        }
    else:
        binding_out = {"description": plain(binding)} if plain(binding) else {}
    return {
        "objectForm": plain(data.get("object_form")),
        "support": plain(data.get("support")),
        "extent": plain(data.get("extent")),
        "format": plain(data.get("format")),
        "binding": binding_out,
        "handDescription": data.get("hand_desc") if isinstance(data.get("hand_desc"), (dict, list)) else plain(data.get("hand_desc")),
        "condition": plain(data.get("condition")),
        "decoration": plain(data.get("deco_desc")),
        "collation": plain(data.get("collation") or data.get("collation_note")),
        "layout": plain(data.get("layout_desc") or data.get("layout")),
    }


def normalize_history(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {}
    origin = data.get("origin") if isinstance(data.get("origin"), dict) else {}
    date_data = origin.get("date") if isinstance(origin, dict) else None
    intervals, method = derive_intervals(date_data)
    return {
        "origin": {
            "date": {
                "display": plain(date_data.get("display")) if isinstance(date_data, dict) else plain(date_data),
                "intervals": intervals,
                "normalization": method,
                "certainty": plain(date_data.get("certainty")) if isinstance(date_data, dict) else "",
                "qualifier": plain(date_data.get("qualifier")) if isinstance(date_data, dict) else "",
            },
            "place": plain(origin.get("place")) if isinstance(origin, dict) else "",
            "institution": plain(origin.get("institution") or origin.get("affiliation")) if isinstance(origin, dict) else "",
            "note": plain(origin.get("note")) if isinstance(origin, dict) else "",
        },
        "provenance": data.get("provenance") if isinstance(data.get("provenance"), list) else ([data.get("provenance")] if data.get("provenance") else []),
        "notes": [
            {"type": key, "value": value}
            for key, value in data.items()
            if key not in {"origin", "provenance"} and value not in (None, "", [], {})
        ],
    }


def signature_keys(signature: str, aliases: Iterable[Any]) -> set[str]:
    values = {signature}
    values.update(plain(a) for a in aliases if plain(a))
    expanded: set[str] = set()
    for value in values:
        base = re.sub(r"^Bibl\.\s*Cod\.\s*", "", value, flags=re.I)
        variants = {
            value,
            base,
            base.replace("Arch. Cod.", "Archivcodex"),
            base.replace("Arch. Cod.", "Arch."),
        }
        for variant in variants:
            expanded.add(variant)
            expanded.add(re.sub(r"\s*\([^)]*\)\s*$", "", variant).strip())
    return {normalize_search(v) for v in expanded if normalize_search(v)}

def resolve_relation_target(raw: str, records: list[dict[str, Any]], alias_map: dict[str, set[str]]) -> str | None:
    target = clean_wikilink(raw)
    norm = normalize_search(target)
    if not norm:
        return None
    direct = alias_map.get(norm, set())
    if len(direct) == 1:
        return next(iter(direct))
    # Conservative prefix resolution for targets that omit an archival parenthetical shelf location.
    candidates = set()
    for rec in records:
        sig_norm = normalize_search(rec["signature"])
        sig_no_paren = normalize_search(re.sub(r"\s*\([^)]*\)\s*$", "", rec["signature"]))
        target_arch = normalize_search(target.replace("Archivcodex", "Arch. Cod."))
        if target_arch in {sig_norm, sig_no_paren}:
            candidates.add(rec["id"])
    return next(iter(candidates)) if len(candidates) == 1 else None


def expand_relation_targets(value: Any) -> list[str]:
    """Expand simple target lists/ranges without interpreting relation semantics."""
    if value is None:
        return []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(expand_relation_targets(item))
        return out
    raw = plain(value).strip()
    if not raw:
        return []
    # Slash-separated explicitly named signatures.
    if re.search(r"\s+/\s+", raw):
        parts = [p.strip() for p in re.split(r"\s+/\s+", raw) if p.strip()]
        if len(parts) > 1:
            out: list[str] = []
            for part in parts:
                out.extend(expand_relation_targets(part))
            return out
    # Ranges of two wiki links: [[MN II 278]]–[[MN II 285]].
    m = re.fullmatch(r"\[\[(.+?)\]\]\s*[–—-]\s*\[\[(.+?)\]\]", raw)
    if m:
        start, end = m.group(1).strip(), m.group(2).strip()
        expanded = expand_signature_range(start, end)
        return expanded or [start, end]
    # Fully written simple numeric ranges, e.g. 97.1.7–97.1.9.
    m = re.fullmatch(r"(.+?\d+)\s*[–—-]\s*(.+?\d+)", raw)
    if m:
        expanded = expand_signature_range(m.group(1).strip(), m.group(2).strip())
        if expanded:
            return expanded
    return [raw]


def expand_signature_range(start: str, end: str) -> list[str]:
    a = clean_wikilink(start)
    b = clean_wikilink(end)
    ma = re.match(r"^(.*?)(\d+)$", a)
    mb = re.match(r"^(.*?)(\d+)$", b)
    if not ma or not mb:
        return []
    prefix_a, num_a = ma.group(1), int(ma.group(2))
    prefix_b, num_b = mb.group(1), int(mb.group(2))
    if normalize_search(prefix_a) != normalize_search(prefix_b):
        return []
    if num_b < num_a or num_b - num_a > 100:
        return []
    return [f"{prefix_a}{n}" for n in range(num_a, num_b + 1)]


def normalize_relations(raw_relations: Any, records: list[dict[str, Any]], alias_map: dict[str, set[str]]) -> list[dict[str, Any]]:
    if not isinstance(raw_relations, list):
        return []
    out: list[dict[str, Any]] = []
    for rel in raw_relations:
        if not isinstance(rel, dict):
            continue
        rel_type = plain(rel.get("type"))
        targets = expand_relation_targets(rel.get("targets") if rel.get("targets") is not None else rel.get("target"))
        for target in targets:
            raw = plain(target)
            if not raw:
                continue
            resolved = resolve_relation_target(raw, records, alias_map)
            target_signature = next((r["signature"] for r in records if r["id"] == resolved), "") if resolved else clean_wikilink(raw)
            out.append({
                "typeRaw": rel_type,
                "typeLabel": RELATION_LABELS.get(rel_type, rel_type.replace("_", " ") if rel_type else "Relation"),
                "targetRaw": raw,
                "targetId": resolved,
                "targetSignature": target_signature,
                "appliesTo": [plain(v) for v in (rel.get("applies_to") or [])] if isinstance(rel.get("applies_to"), list) else ([plain(rel.get("applies_to"))] if rel.get("applies_to") else []),
                "certainty": plain(rel.get("certainty")),
                "note": plain(rel.get("note")),
            })
    return out


def flatten_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    def walk(entries: list[dict[str, Any]]) -> None:
        for item in entries:
            out.append(item)
            walk(item.get("subitems") or [])
    walk(items)
    return out


def unique_persons(persons: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for p in persons:
        key = (p.get("name", ""), p.get("roleRaw", ""), p.get("scope", ""), p.get("itemId", ""))
        if key not in seen:
            seen.add(key); out.append(p)
    return out


def preferred_title(data: dict[str, Any], overall_title: str, items: list[dict[str, Any]]) -> tuple[str, str]:
    title_type = plain((data.get("ms_contents") or {}).get("title_type")) if isinstance(data.get("ms_contents"), dict) else ""
    if overall_title:
        return overall_title, title_type
    if items:
        return items[0]["title"]["text"], items[0]["title"].get("typeRaw") or ""
    return f"Handschrift {plain(data.get('signature'))}", "supplied"


def record_search_text(record: dict[str, Any]) -> dict[str, str]:
    items = flatten_items(record.get("contents") or [])
    people = record.get("persons") or []
    overview = record.get("contentsOverview") or {}
    title_values = [record["heading"]["title"], plain(overview.get("translation"))] + [i["title"]["text"] for i in items]
    incipits = [plain(overview.get("incipit"))] + [plain(i.get("incipit")) for i in items]
    explicits = [plain(overview.get("explicit"))] + [plain(i.get("explicit")) for i in items]
    notes = [plain(overview.get(k)) for k in ("summary", "note", "part", "completeness", "language")]
    notes += [plain(n.get("text")) for i in items for n in i.get("notes", [])]
    notes += [plain(n) for n in record.get("editorialNotes", [])]
    physical = record.get("physicalDescription") or {}
    physical_values = [plain(physical.get(k)) for k in ("support", "extent", "format", "condition", "decoration", "collation", "layout")]
    physical_values += [plain(physical.get("binding"))]
    return {
        "signature": record["signature"],
        "titles": " \n".join(filter(None, title_values)),
        "persons": " \n".join(f"{p.get('name','')} {p.get('roleLabel','')} {p.get('roleRaw','')}" for p in people),
        "incipits": " \n".join(filter(None, incipits)),
        "explicits": " \n".join(filter(None, explicits)),
        "notes": " \n".join(filter(None, notes)),
        "physical": " \n".join(filter(None, physical_values)),
    }


def make_search_docs(record: dict[str, Any]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    base = {
        "recordId": record["id"],
        "signature": record["signature"],
        "recordTitle": record["heading"]["title"],
        "dateDisplay": record["heading"]["date"],
        "dateIntervals": record.get("date", {}).get("intervals", []),
        "repository": record["repository"],
        "url": record["url"],
    }
    search = record["search"]
    docs.append({
        **base,
        "id": record["id"] + "::manuscript",
        "type": "manuscript",
        "sourceLabel": "Strukturierte Erschließung",
        "title": record["heading"]["title"],
        "anchor": "",
        "rank": 100,
        "fields": search,
    })
    for item in flatten_items(record.get("contents") or []):
        people = item.get("persons") or []
        item_fields = {
            "signature": record["signature"],
            "titles": item["title"]["text"],
            "persons": " \n".join(f"{p.get('name','')} {p.get('roleLabel','')} {p.get('roleRaw','')}" for p in people),
            "incipits": plain(item.get("incipit")),
            "explicits": plain(item.get("explicit")),
            "notes": " \n".join(plain(n.get("text")) for n in item.get("notes", [])),
            "locus": item.get("locus", ""),
        }
        docs.append({
            **base,
            "id": record["id"] + "::" + item["id"],
            "type": "item",
            "sourceLabel": "Inhaltseinheit",
            "title": item["title"]["text"],
            "locus": item.get("locus", ""),
            "anchor": "#" + item["id"],
            "rank": 85,
            "fields": item_fields,
        })
    for lang, key, label, rank in (
        ("de", "german", "Deutsche Übersetzung", 35),
        ("la", "latin", "Lateinischer Originaltext", 30),
    ):
        raw = record["catalogue"][key]
        if raw:
            docs.append({
                **base,
                "id": record["id"] + "::catalogue-" + lang,
                "type": "catalogue_" + lang,
                "sourceLabel": label,
                "title": record["heading"]["title"],
                "anchor": "#catalogue-" + lang,
                "rank": rank,
                "fields": {"catalogue": raw, "signature": record["signature"]},
            })
    return docs


def json_dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_detail_page(record: dict[str, Any]) -> str:
    return f'''---
layout: default
extra_css:
  - /assets/css/catalogus.css
extra_js:
  - /assets/js/catalogus-data.js
  - /assets/js/catalogus-record.js
---

<p><a class="back-link" href="{{{{ site.baseurl }}}}/bibliothek/catalogus-codicum/">&larr; Zurück zur Catalogus-Suche</a></p>
<section class="catalogus-record-shell" data-catalogus-record data-record-url="{{{{ site.baseurl }}}}/assets/data/catalogus-codicum/records/{record['id']}.json">
    <p class="search-meta" data-record-status>Handschriftenbeschreibung wird geladen ...</p>
    <div data-record-content></div>
</section>
'''


def build(source_dir: Path, repo_root: Path) -> dict[str, Any]:
    data_dir = repo_root / "assets" / "data" / "catalogus-codicum"
    records_dir = data_dir / "records"
    pages_dir = repo_root / "bibliothek" / "catalogus-codicum" / "handschriften"
    for target in (data_dir, pages_dir):
        if target.exists():
            shutil.rmtree(target)
    records_dir.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)

    source_paths = sorted(
        [p for p in source_dir.glob("*.md") if p.name not in IGNORE_FILES],
        key=lambda p: p.name.casefold(),
    )
    errors: list[str] = []
    warnings: list[str] = []
    unmapped: Counter[str] = Counter()
    raw_entries: list[dict[str, Any]] = []
    seen_signatures: dict[str, str] = {}
    seen_ids: dict[str, str] = {}

    for path in source_paths:
        try:
            text = path.read_text(encoding="utf-8")
            data, body = split_frontmatter(text, path)
        except Exception as exc:
            errors.append(str(exc)); continue
        signature = plain(data.get("signature"))
        if not signature:
            errors.append(f"{path.name}: signature fehlt."); continue
        if signature in seen_signatures:
            errors.append(f"Doppelte Signatur {signature!r}: {seen_signatures[signature]} und {path.name}")
            continue
        seen_signatures[signature] = path.name
        record_id = slugify(signature)
        if record_id in seen_ids:
            errors.append(f"Kollidierende Web-ID {record_id!r}: {seen_ids[record_id]} und {path.name}")
            continue
        seen_ids[record_id] = path.name
        german, latin = split_catalogue_sections(body)
        if not german:
            errors.append(f"{path.name}: Abschnitt '# Deutsche Übersetzung' fehlt oder ist leer.")
        if not latin:
            errors.append(f"{path.name}: Abschnitt '# Lateinischer Originaltext' fehlt oder ist leer.")
        for key in data:
            if key not in TOP_LEVEL_MAPPED:
                unmapped[key] += 1
        overall_title, overall_title_type, items, contents_persons = content_units(data.get("ms_contents"), unmapped)
        contents_overview = normalize_contents_overview(data.get("ms_contents"))
        title, title_type = preferred_title(data, overall_title, items)
        history = normalize_history(data.get("history"))
        origin_date = history.get("origin", {}).get("date", {})
        physical = normalize_physical(data.get("phys_desc"))
        repository = plain((data.get("ms_identifier") or {}).get("repository")) if isinstance(data.get("ms_identifier"), dict) else ""
        persons = []
        persons.extend(normalize_responsibilities(data.get("responsibility"), scope="manuscript"))
        persons.extend(normalize_responsibilities(data.get("persons"), scope="manuscript"))
        persons.extend(contents_persons)
        for item in flatten_items(items):
            persons.extend(item.get("persons") or [])
        persons = unique_persons(persons)
        raw_entries.append({
            "schemaVersion": SCHEMA_VERSION,
            "id": record_id,
            "signature": signature,
            "aliases": [plain(a) for a in (data.get("aliases") or []) if plain(a)],
            "repository": repository,
            "catalogPage": plain(data.get("catalog_page")),
            "heading": {
                "title": title,
                "titleTypeRaw": title_type or overall_title_type or None,
                "titleTypeLabel": TITLE_TYPE_LABELS.get(title_type or overall_title_type, (title_type or overall_title_type).replace("_", " ") if (title_type or overall_title_type) else None),
                "date": origin_date.get("display", ""),
            },
            "date": origin_date,
            "contentsOverview": contents_overview,
            "contents": items,
            "persons": persons,
            "physicalDescription": physical,
            "history": history,
            "relationsRaw": (data.get("relations") or []) + ((data.get("ms_contents") or {}).get("relations") or [] if isinstance(data.get("ms_contents"), dict) else []),
            "additions": data.get("additions") if isinstance(data.get("additions"), list) else ([data.get("additions")] if data.get("additions") else []),
            "editorialNotes": data.get("editorial_notes") if isinstance(data.get("editorial_notes"), list) else ([data.get("editorial_notes")] if data.get("editorial_notes") else []),
            "references": {
                "publicationHistory": data.get("publication_history"),
                "references": data.get("references"),
                "sourceReferences": data.get("source_references"),
                "bibliography": data.get("bibliography"),
            },
            "catalogue": {
                "german": german,
                "germanHtml": markdown_lite_to_html(german),
                "latin": latin,
                "latinHtml": markdown_lite_to_html(latin),
            },
            "source": {"file": path.name},
            "url": f"/bibliothek/catalogus-codicum/handschriften/{record_id}/",
        })

    if errors:
        sys.stderr.write("\n".join("FEHLER: " + e for e in errors) + "\n")
        raise SystemExit(f"Build abgebrochen: {len(errors)} harte Fehler.")

    alias_map: dict[str, set[str]] = defaultdict(set)
    for record in raw_entries:
        for key in signature_keys(record["signature"], record["aliases"]):
            alias_map[key].add(record["id"])
    for record in raw_entries:
        record["relations"] = normalize_relations(record.pop("relationsRaw"), raw_entries, alias_map)
        record["search"] = record_search_text(record)

    # Statistics and warnings after relation/date normalization.
    unparsed_dates = [r["signature"] for r in raw_entries if r["date"].get("display") and not r["date"].get("intervals")]
    unresolved_relations = [
        {"signature": r["signature"], "target": rel["targetRaw"], "type": rel["typeRaw"]}
        for r in raw_entries for rel in r.get("relations", [])
        if not rel.get("targetId") and rel.get("typeRaw") in MANUSCRIPT_RELATION_TYPES
    ]
    if unparsed_dates:
        warnings.append(f"{len(unparsed_dates)} Entstehungsdatierungen sind für den Jahresfilter nicht numerisch normalisiert.")
    if unresolved_relations:
        warnings.append(f"{len(unresolved_relations)} Relationsziele konnten nicht eindeutig aufgelöst werden.")

    raw_entries.sort(key=lambda r: natural_signature_key(r["signature"]))
    search_docs: list[dict[str, Any]] = []
    for record in raw_entries:
        json_dump(records_dir / f"{record['id']}.json", record)
        detail_dir = pages_dir / record["id"]
        detail_dir.mkdir(parents=True, exist_ok=True)
        (detail_dir / "index.html").write_text(render_detail_page(record), encoding="utf-8")
        search_docs.extend(make_search_docs(record))

    repositories = Counter(r["repository"] for r in raw_entries)
    item_count = sum(len(flatten_items(r["contents"])) for r in raw_entries)
    incipit_count = sum(1 for r in raw_entries for i in flatten_items(r["contents"]) if i.get("incipit"))
    explicit_count = sum(1 for r in raw_entries for i in flatten_items(r["contents"]) if i.get("explicit"))
    relation_count = sum(len(r.get("relations", [])) for r in raw_entries)
    filterable_dates = sum(1 for r in raw_entries if r["date"].get("intervals"))

    manifest = {
        "schema": BUILD_NAME,
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "recordCount": len(raw_entries),
        "itemCount": item_count,
        "searchDocumentCount": len(search_docs),
        "repositories": dict(repositories),
        "filterableDateRecordCount": filterable_dates,
        "records": [
            {
                "id": r["id"], "signature": r["signature"], "title": r["heading"]["title"],
                "dateDisplay": r["heading"]["date"], "repository": r["repository"], "url": r["url"],
            }
            for r in raw_entries
        ],
    }
    report = {
        "schema": BUILD_NAME,
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": manifest["generatedAt"],
        "status": "ok",
        "statistics": {
            "records": len(raw_entries),
            "items": item_count,
            "incipits": incipit_count,
            "explicits": explicit_count,
            "relations": relation_count,
            "filterableDates": filterable_dates,
            "repositories": dict(repositories),
        },
        "warnings": warnings,
        "unparsedOriginDates": unparsed_dates,
        "unresolvedRelations": unresolved_relations,
        "unmappedSourceFields": dict(sorted(unmapped.items())),
        "notes": [
            "Der Datierungsfilter verwendet ausschließlich history.origin.date.",
            "Aus display abgeleitete Datumsintervalle werden nur bei einfachen, eindeutigen Jahresangaben erzeugt.",
            "Unbekannte Rollen und Relationstypen werden im Webmodell mit ihrem Rohwert erhalten.",
            "Die wissenschaftlichen Masterdateien werden durch den Build nicht verändert.",
        ],
    }
    json_dump(data_dir / "manifest.json", manifest)
    json_dump(data_dir / "search-index.json", {"schemaVersion": SCHEMA_VERSION, "documents": search_docs})
    json_dump(data_dir / "build-report.json", report)
    return report


def natural_signature_key(value: str) -> list[Any]:
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", value)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("_catalogus-codicum"), help="Verzeichnis der Markdown/YAML-Masterdateien")
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Wurzel des Findmittel-Repositories")
    args = parser.parse_args()
    source = args.source.resolve()
    repo_root = args.repo_root.resolve()
    if not source.is_dir():
        raise SystemExit(f"Quellverzeichnis nicht gefunden: {source}")
    report = build(source, repo_root)
    s = report["statistics"]
    print(
        f"Catalogus-Build erfolgreich: {s['records']} Handschriften, {s['items']} Inhaltseinheiten, "
        f"{s['relations']} Relationen, {s['filterableDates']} Datensätze mit Datumsfilter."
    )
    if report["warnings"]:
        print("Warnungen:")
        for warning in report["warnings"]:
            print(" - " + warning)


if __name__ == "__main__":
    main()
