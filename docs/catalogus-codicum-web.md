# Catalogus Codicum – Webschicht

## Grundprinzip

Die Markdown-/YAML-Dateien in `_catalogus-codicum/` sind der wissenschaftliche Masterbestand. Die Website liest diese Dateien **nicht direkt**. `scripts/build-catalogus-codicum.py` erzeugt daraus eine versionierte, kanonische Webrepräsentation.

```text
_catalogus-codicum/*.md
        ↓
scripts/build-catalogus-codicum.py
        ↓
assets/data/catalogus-codicum/
        ├── manifest.json
        ├── search-index.json
        ├── build-report.json
        └── records/*.json
        ↓
bibliothek/catalogus-codicum/
```

Die Webrepräsentation ist ausdrücklich kein wissenschaftliches Masterformat und kein Ersatz für das angestrebte Seitenstettner Handschriften-Anwendungsprofil bzw. TEI P5 `<msDesc>`.

## Neu erzeugte bzw. benötigte Dateien

- `_catalogus-codicum/*.md` – wissenschaftliche Masterdateien; vom Build nicht verändert.
- `scripts/build-catalogus-codicum.py` – alleinige Transformations-/Build-Schicht.
- `scripts/requirements-catalogus.txt` – Python-Abhängigkeit (PyYAML).
- `assets/data/catalogus-codicum/manifest.json` – Bestandsübersicht.
- `assets/data/catalogus-codicum/search-index.json` – clientseitiger Suchindex.
- `assets/data/catalogus-codicum/build-report.json` – Qualitäts-/Mappingbericht.
- `assets/data/catalogus-codicum/records/*.json` – kanonische Webdatensätze.
- `assets/css/catalogus.css` – Catalogus-spezifische Gestaltung.
- `assets/js/catalogus-data.js` – gemeinsame Daten-/Normalisierungsfunktionen.
- `assets/js/catalogus-search.js` – Suchoberfläche.
- `assets/js/catalogus-record.js` – Handschriftendetailansicht.
- `bibliothek/catalogus-codicum/index.html` – Suche/Startseite.
- `bibliothek/catalogus-codicum/handschriften/*/index.html` – stabile Detail-URLs.

Zusätzlich werden `_layouts/default.html` und `bibliothek/index.html` leicht erweitert.

## Build lokal ausführen

Aus der Repository-Wurzel:

```bash
python3 -m pip install -r scripts/requirements-catalogus.txt
python3 scripts/build-catalogus-codicum.py
```

Der Builder löscht vor dem Neubau ausschließlich die von ihm verwalteten Verzeichnisse

- `assets/data/catalogus-codicum/`
- `bibliothek/catalogus-codicum/handschriften/`

und erzeugt sie vollständig neu.

## Harte Fehler und Warnungen

Der Build bricht bei harten Konsistenzproblemen ab, insbesondere bei:

- ungültigem oder fehlendem YAML-Frontmatter,
- fehlender Signatur,
- doppelten Signaturen,
- kollidierenden Web-IDs,
- fehlender deutscher Übersetzung,
- fehlendem lateinischem Originaltext.

Nicht abschließend normalisierte wissenschaftliche Sachverhalte werden dagegen als Warnung dokumentiert und blockieren die Veröffentlichung nicht. Dazu gehören etwa nicht numerisch interpretierbare Entstehungsdatierungen oder nicht eindeutig auflösbare Relationsziele.

`build-report.json` listet außerdem neu auftretende, derzeit noch nicht in das kanonische Webmodell überführte Quellenfelder auf. Dadurch können spätere Schemaentwicklungen nicht unbemerkt an der Webschicht vorbeigehen.

## Datierungsfilter

Für den Datierungsfilter wird ausschließlich `history.origin.date` verwendet. Datierungen aus Randvermerken, historischen Ereignissen, Incipits oder Katalogfließtext fließen nicht in den Entstehungszeitfilter ein.

Numerische Felder (`when`, `from`, `to`, `not_before`, `not_after`) haben Vorrang. Aus `display` werden nur einfache eindeutige Jahresangaben wie `1685`, `1685/86` oder `1685–1686` abgeleitet. Jahrhundertangaben und komplexe Freitexte werden in Version 1 nicht künstlich in Jahresintervalle umgerechnet.

## Personen und Relationen

Personennamen werden nur innerhalb eines Datensatzes zusammengeführt, wenn Name, Rolle und Bezug identisch sind. Eine globale Personennormalisierung findet nicht statt.

Relationstypen und Rollen behalten immer ihren Rohwert (`typeRaw`, `roleRaw`). Für bekannte Werte erzeugt die Webschicht zusätzlich eine deutsche Anzeigeform. Unbekannte Werte bleiben deshalb sichtbar und führen nicht zum Datenverlust.

## Suchindex

Der Index unterscheidet vier Dokumenttypen:

1. `manuscript` – strukturierte Handschriftenerschließung,
2. `item` – konkrete Inhaltseinheit,
3. `catalogue_de` – deutsche Übersetzung,
4. `catalogue_la` – lateinischer Originaltext.

Strukturierte Treffer werden höher gewichtet als reine Fließtexttreffer. Inhaltseinheiten besitzen stabile Anker (`#item-*`) und können unmittelbar angesprungen werden.

## GitHub Pages

Es wird keine Serverkomponente benötigt. Alle Such- und Detaildaten liegen als statisches JSON vor und werden clientseitig geladen. Der Build muss **vor dem Commit** lokal ausgeführt werden; GitHub Pages selbst führt das Python-Skript nicht aus.
