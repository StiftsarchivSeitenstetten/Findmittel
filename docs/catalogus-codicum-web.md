# Catalogus Codicum – Webschicht und Entitätssuche

## Grundprinzip

Die Markdown-/YAML-Dateien in `_catalogus-codicum/` sind der wissenschaftliche Masterbestand. Die Website liest sie nicht direkt. `scripts/build-catalogus-codicum.py` erzeugt daraus eine versionierte kanonische Webrepräsentation.

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

Die Webrepräsentation ist ausdrücklich **kein wissenschaftliches Masterformat** und kein Ersatz für das angestrebte Seitenstettner Handschriften-Anwendungsprofil bzw. TEI P5 `<msDesc>`.

## Entitätstypen der Discovery-Schicht

Version 2 des Webschemas erzeugt getrennte Suchdokumente für folgende Typen:

1. **Codex** (`codex`)  
   Eine Handschrift als zentrale Webentität. Der Codex-Suchdatensatz aggregiert die strukturierten Informationen des Datensatzes. Für die feldbezogene Suche werden auch deutsche Übersetzung und lateinischer Katalogtext dem Codex als durchsuchbare Quellenfelder zugeordnet. Dadurch liefert die Auswahl „Codex“ genau eine Ergebniseinheit je betroffener Handschrift.

2. **Werk / Inhaltseinheit** (`content`)  
   Eine konkrete Einheit aus `ms_contents.items` einschließlich strukturierter Untereinheiten. Diese Bezeichnung ist **keine abstrakte Werkidentifikation**. Sie bezeichnet eine konkrete Text-/Werküberlieferung innerhalb eines Codex.

3. **Physische Einheit** (`physical_unit`)  
   Wird nur erzeugt, wenn eine physische Einheit in den Masterdaten ausdrücklich mit einer Inhaltseinheit verknüpft ist, derzeit insbesondere über `physical_unit` bzw. `fascicle`. Bloße Angaben wie „52 Faszikel“ in der Kollation erzeugen nicht automatisch 52 Webentitäten.

4. **Person** (`person`)  
   Strukturierte Personenangaben aus Verantwortlichkeiten und Personenfeldern. Eine globale Normierung oder Gleichsetzung unterschiedlicher Namensformen erfolgt nicht. Nur identische Namensstrings innerhalb desselben Codex werden für die Webanzeige gebündelt.

5. **Incipit** (`incipit`)  
   Jedes strukturiert erfasste Incipit wird als eigener Treffertyp indexiert und kann direkt zum entsprechenden Abschnitt der Detailseite führen.

6. **Explicit / Kolophon** (`explicit_colophon`)  
   Strukturierte Explicits und Kolophone werden einzeln indexiert; ihr Untertyp bleibt erhalten.

7. **Nachtrag / Vermerk** (`addition`)  
   Strukturierte `additions` werden als eigene Trefferebene indexiert.

8. **Historische Katalogbeschreibung** (`catalogue`)  
   Deutsche Übersetzung und lateinischer Originaltext bleiben getrennte Quellenfelder, erscheinen aber in der Ergebnisgruppierung gemeinsam als historische Katalogbeschreibung.

Diese Typisierung gehört ausschließlich zur Discovery-Schicht. Sie verändert die wissenschaftliche Ontologie der Masterdaten nicht.

## Zwei unabhängige Suchachsen

Die Benutzeroberfläche unterscheidet bewusst:

### 1. Entität / Treffertyp

Hier wird festgelegt, **welche Art von Ergebniseinheit** gesucht werden soll:

- alle Entitätstypen,
- Codex,
- Werk / Inhaltseinheit,
- physische Einheit,
- Person,
- Incipit,
- Explicit / Kolophon,
- Nachtrag / Vermerk,
- historische Katalogbeschreibung.

### 2. Suche in

Hier wird festgelegt, **in welchem Feld bzw. Quellenbereich** gesucht wird:

- alle Felder,
- Signatur,
- Titel / Inhalt,
- Personen,
- Incipit,
- Explicit / Kolophon,
- physische Beschreibung / Einheit,
- deutsche Übersetzung,
- lateinischer Originaltext.

Beide Achsen können kombiniert werden. Beispiele:

- `Entität = Codex`, `Suche in = Incipit` → jeder betroffene Codex erscheint nur einmal.
- `Entität = Werk / Inhaltseinheit`, `Suche in = Titel / Inhalt` → konkrete Textüberlieferungen werden einzeln ausgegeben.
- `Entität = Physische Einheit`, `Suche in = Titel / Inhalt` → ausdrücklich strukturierte Faszikel o. Ä. werden nach ihrem enthaltenen Inhalt recherchiert.

## Ergebnisgruppierung und Codex-Zählung

Bei einer Suche über alle Entitätstypen werden die Treffer in fester Reihenfolge gruppiert:

1. Codices
2. Werke / Inhaltseinheiten
3. physische Einheiten
4. Personen
5. Incipits
6. Explicits / Kolophone
7. Nachträge / Vermerke
8. historische Katalogbeschreibungen

Oberhalb der Ergebnisliste erscheint für jeden vorhandenen Typ eine Schaltfläche mit:

- Zahl der Treffer dieses Typs,
- Zahl der betroffenen Codices.

Die allgemeine Statuszeile nennt ebenfalls die Zahl der **unterschiedlichen Codices mit mindestens einem Treffer**. Damit ist eine Deduplizierung auf Codexebene Teil der Suchoberfläche und muss nicht durch den Benutzer erfolgen.

## Hinweis zu historischen und lateinischen Flexionsformen

Die Suche normalisiert Groß-/Kleinschreibung, Diakritika, Umlaute, `ß/ss`, `æ/ae` und `œ/oe`. Sie führt derzeit **keine sprachwissenschaftliche Lemmatisierung** durch. Für Namen oder Termini mit unterschiedlichen lateinischen Flexionsformen kann deshalb eine Suche nach dem gemeinsamen Stamm sinnvoll sein, z. B. `Aristotel` für `Aristoteles`, `Aristotelis`, `Aristotelico` usw. Eine spätere normierte Personen-/Werkentität kann diese Funktion semantisch sauberer übernehmen.

## Build lokal ausführen

Aus der Repository-Wurzel:

```bash
python3 -m pip install -r scripts/requirements-catalogus.txt
python3 scripts/build-catalogus-codicum.py
```

Der Builder löscht vor dem Neubau ausschließlich die von ihm verwalteten Verzeichnisse:

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

`build-report.json` listet außerdem neu auftretende, derzeit noch nicht in das kanonische Webmodell überführte Quellenfelder auf. Im aktuellen Datenstand bleiben **keine Feldnamen ungemappt**; dies bedeutet jedoch nicht, dass alle wissenschaftlichen Werte bereits endgültig normalisiert wären.

## Datierungsfilter

Für den Datierungsfilter wird ausschließlich `history.origin.date` verwendet. Datierungen aus Randvermerken, historischen Ereignissen, Incipits, Kolophonen oder Katalogfließtext fließen nicht in den Entstehungszeitfilter ein.

## GitHub Pages

Es wird keine Serverkomponente benötigt. Alle Such- und Detaildaten liegen als statisches JSON vor und werden clientseitig geladen. Der Python-Build muss vor dem Commit lokal ausgeführt werden; GitHub Pages selbst führt das Python-Skript nicht aus.
