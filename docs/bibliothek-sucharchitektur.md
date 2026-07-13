# Sucharchitektur fuer Bibliotheksdaten

## Ziel

Die Bibliotheksdaten sollen langfristig bis zu ca. 150.000 Exemplare tragen, ohne dass die Grundarchitektur spaeter von einer interaktiven Tabelle auf ein anderes Modell umgebaut werden muss.

Die Website bleibt statisch und GitHub-Pages-tauglich. Alle komplexeren Schritte passieren vor der Auslieferung in einem Build-Schritt. Die Nutzerinnen und Nutzer erhalten eine schnelle Suchoberflaeche mit Trefferliste, Detailansicht und spaeter optionalen Facetten.

## Ausgangsdaten im Prototyp

Aktuell liegen im Ordner `bibliothek/` zwei relevante Exporte:

- `MARC_Bibliographic.xml`
  - MARCXML mit 1.548 bibliografischen Datensaetzen
  - zentrale Titelaufnahme
  - relevante Felder: `001`, `009`, `100`, `245`, `264`, `300`, `650`, `655`, `689`, `700`, `773`, `852`, `856`

- `Items.csv`
  - Alma-Export mit 2.339 echten Exemplardatensaetzen plus einer technischen Endzeile
  - konkrete Exemplare, Standorte, Signaturen, Heft-/Bandinformationen
  - relevante Felder: `MMS Record ID`, `HOL Record ID`, `Item PID`, `Title`, `Creator`, `Permanent Call Number`, `Permanent Physical Location`, `Description`, `Chronology`, `Enumeration`, `Status`, `Other System Number`

Die Verknuepfung ist belastbar:

- `Items.csv` `MMS Record ID` entspricht MARCXML `001`
- `Items.csv` `HOL Record ID` entspricht MARCXML `852 $8`
- `Items.csv` `Other System Number` enthaelt zusaetzlich AC-/OBV-Nummern, die zu MARCXML `009` und `035` passen

## Grundentscheidung

Nicht DataTables als Grundmodell verwenden.

Stattdessen:

1. Rohdaten bleiben als Quellen erhalten.
2. Ein Build-Schritt normalisiert die Quellen.
3. Daraus entstehen statische JSON-Dateien und Suchindex-Dateien.
4. Die Website laedt nur die fuer Suche und Anzeige noetigen Daten.
5. Detaildaten werden erst bei Bedarf geladen oder aus einem passenden Chunk gelesen.

Dieses Modell funktioniert fuer kleine Prototypen ebenso wie fuer groessere Datenmengen.

## Datenmodell

### Titelaufnahme

Eine Titelaufnahme beschreibt das Werk bzw. den bibliografischen Datensatz.

Vorgeschlagenes JSON-Feldmodell:

```json
{
  "id": "9911305809524",
  "acNumber": "AC16712762",
  "title": "Hieronymi Cardani ...",
  "responsibility": "Cura Caroli Sponii ...",
  "creators": ["Cardano, Girolamo 1501-1576"],
  "contributors": ["Spon, Charles 1609-1684"],
  "publication": {
    "place": "Lvgdvni [Lugduni]",
    "publisher": "Sumptibus Ioannis Antonii Hvgvetam & Marci Antonii Ravavd",
    "year": "1663"
  },
  "extent": "[4] Bl., 570 S.",
  "language": ["lat"],
  "subjects": ["..."],
  "genres": ["..."],
  "relations": [
    {
      "type": "containedIn",
      "target": "(AT-OBV)AC06359657",
      "label": "9"
    }
  ],
  "links": [
    {
      "type": "Volltext",
      "url": "..."
    }
  ]
}
```

### Exemplar

Ein Exemplar beschreibt das konkrete Stueck im Bestand.

Vorgeschlagenes JSON-Feldmodell:

```json
{
  "id": "234174040009524",
  "titleId": "9910994709524",
  "holdingId": "224174060009524",
  "callNumber": "Th 3.1700",
  "permanentCallNumber": "Th 3.1700",
  "location": "SEK",
  "localLocation": "BIB",
  "materialType": "BOOK",
  "chronology": "",
  "enumeration": "",
  "description": "",
  "status": "Item in place",
  "barcode": "",
  "publicNote": "",
  "internalNotes": []
}
```

### Zusammengesetzter Suchdatensatz

Fuer die Suche wird aus Titelaufnahme und Exemplaren ein kompakter Suchdatensatz erzeugt.

```json
{
  "id": "9910994709524",
  "title": "Gesammelte Schriften",
  "creator": "Kasper, Walter 1933-",
  "year": "",
  "publisher": "Herder",
  "subjects": [],
  "genres": [],
  "languages": [],
  "locations": ["SEK"],
  "callNumbers": ["Th 3.1700"],
  "itemCount": 1,
  "searchText": "Gesammelte Schriften Kasper Walter Herder Th 3.1700 SEK ..."
}
```

Wichtig: Der Suchdatensatz ist kleiner als der vollstaendige Detaildatensatz.

## Build-Pipeline

Vorgeschlagener Ablauf:

1. `ingest`
   - MARCXML einlesen
   - Items-CSV einlesen
   - technische Endzeilen und leere Zeilen verwerfen

2. `validate`
   - pruefen, ob alle `MMS Record ID`-Werte aus den Items in MARC `001` vorkommen
   - pruefen, ob `HOL Record ID` zu `852 $8` passt
   - Warnungen fuer Titel ohne Exemplar und Exemplare ohne Titel ausgeben

3. `normalize`
   - MARC-Felder in lesbare JSON-Felder ueberfuehren
   - Items an Titel haengen
   - Mehrfachexemplare und Zeitschriftenhefte gruppieren

4. `build-search-docs`
   - kompakte Suchdatensaetze erzeugen
   - Facettenwerte extrahieren: Standort, Jahr, Sprache, Materialtyp, Genre, ggf. Sachgruppe

5. `chunk-details`
   - Detaildaten in kleinere Dateien zerlegen
   - z. B. `details/chunk-000.json`, `details/chunk-001.json`
   - Manifest merkt sich, welcher Datensatz in welchem Chunk liegt

6. `build-index`
   - Suchindex aus den kompakten Suchdatensaetzen erzeugen
   - je nach Datenmenge ein Gesamtindex oder mehrere Index-Shards

7. `publish`
   - generierte Webdaten in `assets/data/bibliothek/` schreiben
   - Website greift nur auf diese generierten Dateien zu

## Vorgeschlagene Repository-Struktur

```text
bibliothek/
  index.html
  suche.html
  MARC_Bibliographic.xml
  Items.csv

assets/
  data/
    bibliothek/
      manifest.json
      search-docs.json
      index.json
      details/
        chunk-000.json
        chunk-001.json

scripts/
  build-library-data.mjs
  build-library-index.mjs

docs/
  bibliothek-sucharchitektur.md
```

Die Rohdaten koennen im Repository bleiben, muessen aber nicht dauerhaft oeffentlich mit ausgeliefert werden. Fuer GitHub Pages genuegen die generierten Dateien unter `assets/data/bibliothek/`.

## Suchstrategie fuer unterschiedliche Groessen

### Bis ca. 5.000 Titel

- ein kompakter JSON-Datensatz
- ein Suchindex
- Detaildaten koennen notfalls gemeinsam geladen werden

### Ca. 20.000 Titel oder Exemplare

- Suchdatensaetze getrennt von Detaildaten
- `defer`-Laden der Detail-Chunks
- Facetten und Trefferliste statt grosser Tabelle

### Ca. 150.000 Exemplare

- keine vollstaendige Tabelle im Browser
- kompakter Suchindex oder Index-Shards
- Detaildaten zwingend in Chunks
- Trefferliste begrenzen, z. B. erste 50 Treffer mit Nachladen
- Facetten nicht live aus allen Details berechnen, sondern im Build-Schritt vorberechnen

## Frontend-Konzept

Die Bibliothekssuche sollte eine eigene Seite erhalten, z. B. `bibliothek/suche.html`.

Elemente:

- Suchfeld
- Facettenbereich
  - Standort
  - Materialtyp
  - Zeitraum/Jahrhundert
  - Sprache
  - Form/Genre
- Trefferliste
  - Titel
  - Verfasser/Personen
  - Jahr
  - Signatur(en)
  - Standort(e)
  - Anzahl Exemplare
- Detailansicht
  - bibliografische Beschreibung
  - Exemplarliste
  - digitale Links aus `856`
  - MARC-/Systemnummern fuer Nachvollziehbarkeit

## Suchbibliothek

Fuer den Prototyp bietet sich MiniSearch oder FlexSearch an.

Empfehlung fuer den ersten Prototyp:

- MiniSearch, wenn Lesbarkeit und einfache Konfiguration wichtiger sind
- FlexSearch, wenn Geschwindigkeit und grosse Datenmengen frueher im Vordergrund stehen

Beide Varianten bleiben clientseitig und GitHub-Pages-tauglich.

## Wichtige Mapping-Regeln

### MARCXML zu Titel

- `001` -> interne Titel-ID / MMS-ID
- `009` -> AC-Nummer
- `020 $a` -> ISBN
- `041 $a` -> Sprache
- `100/110/111` -> Hauptverantwortliche
- `245 $a $b $n $p $c` -> Titel und Verantwortlichkeitsangabe
- `246 $a` -> abweichender Titel
- `250 $a` -> Ausgabe
- `264 $a $b $c` -> Ort, Verlag, Jahr
- `300 $a $b $c` -> Umfang
- `490/830` -> Reihe
- `650/655/689` -> Schlagwoerter, Formangaben, Sacherschliessung
- `700/710/711` -> weitere Personen und Koerperschaften
- `773` -> Beziehung zu uebergeordneten Werken
- `852` -> Holding/Standort, soweit vorhanden
- `856 $u $z $3` -> digitale Links

### Items.csv zu Exemplar

- `MMS Record ID` -> Titel-ID, Link zu MARC `001`
- `HOL Record ID` -> Holding-ID, Link zu MARC `852 $8`
- `Item PID` -> Exemplar-ID
- `Permanent Call Number` -> Signatur
- `Permanent Physical Location` -> Standort
- `Local Location` -> lokale Bibliothek / Bereich
- `Item Material Type` -> Exemplar-Materialtyp
- `Chronology`, `Enumeration`, `Issue year`, `Description` -> Heft-/Bandinformation
- `Status` -> Verfuegbarkeits-/Bearbeitungsstatus
- `Public note`, `Internal note (1-3)` -> Anmerkungen
- `Other System Number` -> AC-/OBV-/DNB-Nummern

## Offene Entscheidungen

1. Sollen Treffer titelzentriert oder exemplarzentrisch angezeigt werden?
   - Empfehlung: titelzentriert, mit Exemplaren in der Detailansicht.

2. Wie sollen Zeitschriften und mehrbaendige Werke erscheinen?
   - Empfehlung: Titel als Haupttreffer, Hefte/Baende als Exemplarliste bzw. Bestandsuebersicht.

3. Welche Felder duerfen oeffentlich sichtbar sein?
   - Interne Notizen aus Items sollten vor der Veroeffentlichung bewusst geprueft werden.

4. Welche Facetten sind fachlich wirklich sinnvoll?
   - Standort und Zeitraum wahrscheinlich sofort.
   - Sprache, Form/Genre, Sachbegriffe nach Qualitaet der Daten.

5. Sollen Rohdaten auf GitHub Pages oeffentlich erreichbar bleiben?
   - Fuer den Prototyp unkritisch.
   - Fuer produktive Daten sollte entschieden werden, ob nur generierte Webdaten veroeffentlicht werden.

## Naechster Prototyp-Schritt

Ein erster technischer Prototyp sollte nur generierte Daten erzeugen, noch ohne grosses Frontend:

1. Script `scripts/build-library-data.mjs` erstellen.
2. `bibliothek/MARC_Bibliographic.xml` und `bibliothek/Items.csv` einlesen.
3. Normalisierte Titel- und Exemplardaten erzeugen.
4. Verknuepfungsbericht ausgeben:
   - Titelanzahl
   - Exemplaranzahl
   - unverknuepfte Titel
   - unverknuepfte Exemplare
5. `assets/data/bibliothek/records.json` und `manifest.json` erzeugen.

Erst danach sollte die eigentliche Suchseite gebaut werden.
