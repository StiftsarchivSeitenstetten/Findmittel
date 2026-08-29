# Build-Bericht – Catalogus Codicum

Stand dieses Einbaupakets: 29. August 2026.

Der Build wurde mit dem im Paket enthaltenen `scripts/build-catalogus-codicum.py` vollständig aus den 521 Markdown-/YAML-Masterdateien erzeugt und technisch geprüft.

## Ergebnis

- 521 Handschriftendatensätze
- 452 Datensätze der Stiftsbibliothek Seitenstetten
- 69 Datensätze des Stiftsarchivs Seitenstetten
- 1.758 im Webmodell abgebildete Inhaltseinheiten einschließlich Untereinheiten und älterer Einheitsbeschreibungen
- 191 strukturierte Incipits
- 22 strukturierte Explicits
- 392 auf einzelne Zielangaben aufgelöste Relationen
- 3.321 Suchdokumente
- 448 Handschriften mit derzeit numerisch nutzbarer Entstehungsdatierung für den Von-bis-Filter

## Nicht blockierende Hinweise

60 vorhandene `history.origin.date.display`-Angaben werden in Version 1 bewusst nicht in Jahresintervalle umgerechnet. Dabei handelt es sich insbesondere um komplexe bzw. nicht eindeutig numerisch interpretierbare Datierungen. Diese Handschriften bleiben vollständig recherchierbar, erscheinen bei gesetztem Jahresfilter aber nur dann, wenn bereits strukturierte numerische Grenzen vorhanden sind.

Ein als Handschriftenrelation interpretierter Zielverweis konnte nicht auf einen Datensatz des aktuellen 521er-Bestands aufgelöst werden:

- `MN II 306` → `L II 2` (`other_copy`)

Der Rohwert bleibt im Webdatensatz erhalten und wird als Text angezeigt. Der Build wird dadurch nicht blockiert.

## Technische Prüfungen

Durchgeführt wurden:

- erneutes vollständiges Parsen aller YAML-Frontmatter,
- Prüfung auf 521 eindeutige Signaturen und Web-IDs,
- Prüfung auf vorhandene deutsche Übersetzung und lateinischen Originaltext,
- Prüfung aller 521 erzeugten Record-JSON-Dateien,
- Prüfung aller 521 stabilen Detailseiten,
- Prüfung auf eindeutige Item-Anker innerhalb jedes Datensatzes,
- Prüfung aller aufgelösten Relationsziele gegen vorhandene Record-IDs,
- Prüfung auf eindeutige IDs der 3.321 Suchdokumente,
- Python-Syntaxprüfung des Builders,
- JavaScript-Syntaxprüfung aller drei Catalogus-Skripte.

Der maschinenlesbare Detailbericht liegt unter `assets/data/catalogus-codicum/build-report.json`.
