# Archivbaum-Prototyp

Der Prototyp liegt unter `archiv/archivbaum.html` und verwendet die statische JSON-Datei `assets/data/archiv/tree-data.json`. Die allgemeine Archivsuche liegt unter `archiv/suche.html` und nutzt dieselbe JSON-Datei.

## Datenfluss

`Archiverschließung.xlsm` wird nicht im Browser verarbeitet. Stattdessen erzeugt `scripts/build-archive-tree-data.py` aus dem Tabellenblatt `Metadaten` eine kompakte JSON-Repräsentation für Archivbaum und Suche:

```bash
python3 scripts/build-archive-tree-data.py /pfad/zu/Archiverschließung.xlsm
```

Die Hierarchie wird ausschließlich aus `SignaturUeberordnung` gebildet. Die Signatur wird im Proof of Concept als ID verwendet, weil im Blatt `Metadaten` kein eigener persistenter technischer Identifier vorhanden ist.

## Suche

Die Seite `archiv/suche.html` durchsucht ausschließlich öffentliche Felder aus `tree-data.json`: Signatur, Titel, Laufzeit, Verzeichnungsstufe, öffentliche ISAD(G)-Beschreibungfelder sowie Personen, Orte und Schlagworte. Spezialfindmittel wie Korrespondenz- oder Autographendaten werden nicht eingelesen.

Mehrere Suchbegriffe werden mit UND-Logik ausgewertet: Jeder normalisierte Teilbegriff muss im öffentlichen Suchtext eines Datensatzes vorkommen. Die Normalisierung ignoriert Groß-/Kleinschreibung, einfache Diakritika und unterstützt zusätzlich deutsche Umlautvarianten wie `ü`/`ue`.

Die Facette `Bestandsbereich` wird aus der echten Parent-Child-Struktur unterhalb der Wurzel abgeleitet, nicht aus der Signatursyntax. Die Facette `Verzeichnungsstufe` verwendet nur tatsächlich vorhandene Werte.

Treffer verlinken über den Hash der Signatur in den Archivbaum, wo der Pfad geöffnet und der Datensatz ausgewählt wird.

## Validierung

Der Build bricht bei doppelten IDs, fehlenden Parent-Datensätzen, Zyklen und fehlenden Titeln ab. Warnungen zu fehlender Verzeichnungsstufe, Laufzeit, Beschreibung, kontrollierten Metadaten und vorläufigen Signaturen werden gezählt und im Terminal ausgegeben.

Interne Bearbeitungsfelder wie `Verzeichnungsstatus`, `VorlaeufigeSignatur`, `SignaturVorschlag`, `ZurueckgestelltGrund` und `ZuKlaeren` werden für Warnungen ausgewertet, aber nicht in die öffentliche JSON-Datei geschrieben.
