# Datenmodell fuer Bibliotheksdaten

## Leitentscheidung

Das kanonische Datenmodell orientiert sich an Alma.

Begruendung:

- Alma ist das produktive System und wird weiter wachsen.
- Neue Erschliessung soll ohne Modellwechsel uebernommen werden koennen.
- Der Altbestand aus dem frueheren System ist eine abnehmende Uebergangsquelle.
- Die Website soll Alma-Datensaetze, Alma-Exemplare und Altdaten gemeinsam anzeigen, aber ihre Herkunft transparent halten.

Der Altbestand wird daher auf das Alma-nahe Modell abgebildet. Felder, die im Altbestand nicht vorhanden sind, bleiben leer oder werden als abgeleitete Angaben gekennzeichnet.

## Grundprinzip

Der Build-Schritt erzeugt intern vollstaendige Datensaetze. Fuer GitHub Pages werden daraus sparsame Ausgabedateien erzeugt:

- ein Suchindex fuer Trefferliste und Filter
- Detaildaten in Chunks
- ein Manifest mit Zaehlern, Facetten und Build-Informationen

Die Suchseite soll nicht die kompletten Detaildaten aller Titel beim Start laden.

## Kanonischer Titeldatensatz

Ein Titel entspricht grundsaetzlich einem bibliographischen Datensatz. Bei Alma ist das ein MARCXML-Record mit `001` als MMS-ID. Beim Altbestand ist es ein lokaler MARCXML-Record mit `001` als alter System-ID.

```json
{
  "id": "alma:9910407509524",
  "source": "Alma",
  "sourceRecordId": "9910407509524",
  "mmsId": "9910407509524",
  "acNumber": "AC00322387",
  "title": "Bayerisches Woerterbuch ...",
  "responsibility": "von J. Andreas Schmeller ...",
  "variantTitles": [],
  "creators": ["Schmeller, Johann Andreas 1785-1852"],
  "contributors": ["Frommann, Georg Carl 1814-1887"],
  "publication": {
    "text": "Muenchen Rudolf Oldenbourg 1872",
    "place": "Muenchen",
    "publisher": "Rudolf Oldenbourg",
    "yearDisplay": "1872",
    "yearStart": 1872,
    "yearEnd": 1872,
    "yearApproximate": false
  },
  "extent": "XV Seiten, 1784 Spalten 26 cm",
  "languages": ["ger"],
  "subjects": [],
  "genres": [],
  "series": [],
  "identifiers": [
    {
      "type": "AC",
      "value": "AC00322387"
    }
  ],
  "links": [],
  "relations": [],
  "holdings": [],
  "items": []
}
```

### Pflichtfelder

Diese Felder sollen bei jedem Datensatz vorhanden sein:

- `id`: stabile Web-ID mit Quellenpraefix, z. B. `alma:991...` oder `alt:0000014`
- `source`: lesbare Quelle, z. B. `Alma` oder `Altbestand`
- `sourceRecordId`: urspruengliche System-ID aus `001`
- `title`
- `publication`
- `creators`
- `contributors`
- `relations`
- `items`

Leere Inhalte werden als leere Strings, leere Arrays oder `null` gefuehrt, nicht durch wechselnde Feldnamen ersetzt.

## Alma-Felder

Die Alma-Daten bleiben der Normalfall. Wichtige Zuordnungen:

- MARC `001` -> `sourceRecordId`, `mmsId`, Teil von `id`
- MARC `009` -> `acNumber`
- MARC `020` -> `identifiers` mit Typ `ISBN`
- MARC `035` -> `identifiers` mit Ursprungssystemen, soweit sinnvoll
- MARC `041` -> `languages`
- MARC `100/110/111` -> `creators`
- MARC `245 $a $b $n $p` -> `title`
- MARC `245 $c` -> `responsibility`
- MARC `246` -> `variantTitles`
- MARC `250` -> `edition`
- MARC `260/264` -> `publication`
- MARC `300` -> `extent`
- MARC `490/830` -> `series` und ggf. `relations`
- MARC `600/610/650/651/689` -> `subjects`
- MARC `655` -> `genres`
- MARC `700/710/711` -> `contributors`
- MARC `773` -> `relations`
- MARC `852` -> `holdings`
- MARC `856` -> `links`
- MARC `970` -> lokale technische Hinweise, z. B. Adligat-Marker

## Altbestand-Felder

Der Altbestand wird nicht zum Normmodell erhoben, sondern auf das Alma-Modell gemappt:

- MARCXML `001` -> `sourceRecordId`, Teil von `id`
- kein Alma-MMS -> `mmsId` bleibt leer
- keine AC-Nummer -> `acNumber` bleibt leer
- MARC `245`, `100/110/111`, `260/264`, `300`, `700/710/711`, `773` werden wie bei Alma ausgewertet
- MAB-Signaturen werden als synthetische Exemplare in `items` abgelegt
- In der Exemplaranzeige steht beim Standort `Altdaten`, also an derselben Stelle, an der bei Alma `Hauptsaal`, `Studierzimmer` usw. steht
- fehlende Verfuegbarkeits- und Statusangaben bleiben leer

Beispiel fuer ein synthetisches Exemplar aus dem Altbestand:

```json
{
  "id": "altitem:0000014:1",
  "source": "Altbestand",
  "titleId": "alt:0000014",
  "holdingId": "",
  "barcode": "",
  "location": "Altdaten",
  "locationCode": "ALT",
  "callNumber": "Bi 3.0523",
  "permanentCallNumber": "Bi 3.0523",
  "materialType": "",
  "chronology": "",
  "enumeration": "",
  "issueYear": "",
  "description": "",
  "status": "",
  "publicNote": "Signatur aus altem Bibliothekssystem"
}
```

## Exemplar

Das Exemplar-Modell bleibt Alma-nah. Auch Altdaten-Signaturen werden als Exemplare abgebildet, weil die Anzeige und Suche sonst zwei verschiedene Logiken braeuchten.

```json
{
  "id": "alma-item:234128960009524",
  "source": "Alma",
  "titleId": "alma:9910407509524",
  "sourceTitleId": "9910407509524",
  "holdingId": "224128980009524",
  "barcode": "",
  "location": "Stiftsarchiv",
  "locationCode": "ARCHIV",
  "localLocation": "BIB",
  "callNumber": "",
  "permanentCallNumber": "",
  "materialType": "BOOK",
  "chronology": "",
  "enumeration": "",
  "issueYear": "",
  "description": "",
  "status": "Item in place",
  "publicNote": ""
}
```

Die Anzeige verwendet immer die Reihenfolge:

1. Standort
2. Signatur
3. Beschreibung/Band/Heft
4. Status oder Anmerkung, falls oeffentlich sinnvoll

## Beziehungen

Beziehungen werden einheitlich als Objekte gefuehrt. Dadurch koennen Aufsaetze, Reihen, Baende und Adligate gemeinsam verarbeitet werden.

```json
{
  "type": "host",
  "sourceField": "773",
  "targetId": "alma:9910407509524",
  "targetSourceRecordId": "9910407509524",
  "targetAcNumber": "AC00322387",
  "label": "Enthalten in",
  "pages": "S. 12-24",
  "text": "In: ...",
  "resolved": true
}
```

Vorgesehene Relationstypen:

- `host`: Datensatz ist enthalten in einem uebergeordneten Titel, z. B. Aufsatz
- `child`: inverse Beziehung fuer uebergeordnete Datensaetze, wird im Build erzeugt
- `series`: Reihenbeziehung aus `490/830`
- `adligateHost`: lokales Adligat bzw. Bibliotheksbindung

Bei Adligaten bleibt sichtbar, dass das angezeigte Exemplar nicht zwingend bibliographisch zum Titel gehoert, sondern physisch ueber eine Bibliotheksbindung vermittelt ist.

## Normalisierung

Normalisierung ist Teil des Build-Schritts, nicht der Anzeige.

Aktuell vorgesehen:

- doppelte Spitzklammern als Nichtsortierzeichen entfernen: `<<Das>>` -> `Das`
- MAB-Nichtsortierzeichen entfernen: `¬Die¬` -> `Die`
- mehrfache Leerzeichen zusammenziehen
- Jahresangaben aus `260/264` als `yearDisplay`, `yearStart`, `yearEnd` normalisieren
- Standortcodes in Anzeigeformen aufloesen

Die Rohangaben sollen bei Bedarf in Detailfeldern nachvollziehbar bleiben, aber die Anzeige verwendet normalisierte Werte.

## Suchindex

Der allgemeine Suchindex ist aus dem Titeldatensatz abgeleitet und bewusst kleiner als die Detaildaten. Fuer die Auslieferung wird er nicht als Liste von Objekten mit wiederholten Feldnamen geschrieben, sondern als kompaktes `fields`/`records`-Format.

```json
{
  "fields": ["id", "source", "title", "creator", "yearDisplay"],
  "records": [
    ["alma:9910407509524", "Alma", "Bayerisches Woerterbuch ...", "Schmeller, Johann Andreas 1785-1852", "1872"]
  ]
}
```

Filterfaehige Felder im ersten Ausbau:

- `source`
- `locations` bzw. `locationCodes`
- `materialTypes`
- `languages`
- `genres`
- `yearStart` / `yearEnd`

## Detaildaten

Detaildaten werden nicht komplett beim Seitenstart geladen. Sie werden in Chunks ausgegeben, z. B.:

```text
assets/data/bibliothek/records/chunk-000.json
assets/data/bibliothek/records/chunk-001.json
```

Das Manifest merkt sich, welche ID in welchem Chunk liegt.

```json
{
  "recordChunks": {
    "alma:9910407509524": "records/chunk-000.json",
    "alt:0000014": "records/chunk-012.json"
  }
}
```

## Konsequenz fuer die naechste Implementierung

Der naechste technische Schritt ist nicht sofort der Import aller Altdaten in die bestehende `records.json`, sondern eine Umstellung der Build-Ausgabe:

1. IDs mit Quellenpraefix einfuehren.
2. Alma-Datensaetze in das kanonische Modell ueberfuehren.
3. Bestehende Suchseite auf diese IDs vorbereiten.
4. Suchindex und Detaildaten trennen.
5. Danach den Altbestand als zweite Quelle in dasselbe Modell mappen.

So bleibt Alma der stabile Normalfall, waehrend der Altbestand ohne Sonderlogik im Frontend mitsuchbar wird.
