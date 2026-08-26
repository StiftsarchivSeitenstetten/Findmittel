# Archivbaum-Prototyp

Der Prototyp liegt unter `archiv/archivbaum.html` und verwendet die statische JSON-Datei `assets/data/archiv/tree-data.json`.

## Datenfluss

`Archiverschließung.xlsm` wird nicht im Browser verarbeitet. Stattdessen erzeugt `scripts/build-archive-tree-data.py` aus dem Tabellenblatt `Metadaten` eine kompakte JSON-Repräsentation:

```bash
python3 scripts/build-archive-tree-data.py /pfad/zu/Archiverschließung.xlsm
```

Die Hierarchie wird ausschließlich aus `SignaturUeberordnung` gebildet. Die Signatur wird im Proof of Concept als ID verwendet, weil im Blatt `Metadaten` kein eigener persistenter technischer Identifier vorhanden ist.

## Validierung

Der Build bricht bei doppelten IDs, fehlenden Parent-Datensätzen, Zyklen und fehlenden Titeln ab. Warnungen zu fehlender Verzeichnungsstufe, Laufzeit, Beschreibung, kontrollierten Metadaten und vorläufigen Signaturen werden gezählt und im Terminal ausgegeben.

Interne Bearbeitungsfelder wie `Verzeichnungsstatus`, `VorlaeufigeSignatur`, `SignaturVorschlag`, `ZurueckgestelltGrund` und `ZuKlaeren` werden für Warnungen ausgewertet, aber nicht in die öffentliche JSON-Datei geschrieben.
