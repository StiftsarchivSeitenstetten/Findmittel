# Build-Bericht – Catalogus Codicum, Entitätssuche

Stand dieses Einbaupakets: 29. August 2026.  
Wissenschaftlicher Datenstand: `Redaktionspaket_1_Gesamt(2).zip`.

Der Build wurde vollständig aus den 521 aktuellen Markdown-/YAML-Masterdateien neu erzeugt und technisch geprüft.

## Ergebnis

- **521** Handschriftendatensätze
- **452** Datensätze der Stiftsbibliothek Seitenstetten
- **69** Datensätze des Stiftsarchivs Seitenstetten
- **1.758** Werk-/Inhaltseinheiten einschließlich Untereinheiten
- **11** ausdrücklich mit Inhalten verknüpfte physische Einheiten in **3 Codices**
- **841** Personen-Trefferdokumente in **474 Codices**
- **834** strukturierte Incipits in **304 Codices**
- **27** strukturierte Explicits
- **357** strukturierte Kolophone
- zusammen **384** Explicit-/Kolophon-Trefferdokumente in **198 Codices**
- **149** strukturierte Nachträge/Vermerke in **111 Codices**
- **392** auf einzelne Zielangaben expandierte Relationen
- **1.042** Quellen-Trefferdokumente für deutsche Übersetzung und lateinischen Originaltext
- insgesamt **5.540 Suchdokumente**
- **448** Handschriften mit derzeit numerisch nutzbarer Entstehungsdatierung für den Von-bis-Filter

## Neue Suchfunktion

Die Websuche kann nun bereits **vor der Suche** auf einen Entitätstyp eingeschränkt werden. Zusätzlich werden Treffer nach der Suche nach Entitätstyp gruppiert und können über Ergebnis-Schaltflächen selektiv ein- bzw. ausgeblendet werden.

Für jeden Entitätstyp wird neben der Trefferzahl auch die Zahl der **unterschiedlichen betroffenen Codices** berechnet. Die allgemeine Statuszeile nennt ebenfalls die Zahl der Codices mit mindestens einem Treffer.

Damit sind beispielsweise zwei unterschiedliche Fragen sauber trennbar:

- „Wie viele Codices enthalten einen Treffer?“ → Entität `Codex` bzw. Codex-Zählung der Ergebnisübersicht.
- „Wie viele konkrete Werk-/Textüberlieferungen enthalten einen Treffer?“ → Entität `Werk / Inhaltseinheit`.

Als Funktionskontrolle wurde unter anderem mit dem Suchstamm `Aristotel` geprüft. Bei Einschränkung auf `Titel / Inhalt` ergeben sich im aktuellen Datenstand:

- **82 Codex-Treffer**,
- **125 Werk-/Inhaltseinheiten in 79 Codices**.

Die Differenz ist fachlich sinnvoll: Ein Codex kann auf der übergeordneten Inhaltsebene einen aristotelischen Bezug tragen, ohne dass derselbe String zwingend in jedem darunterliegenden Einzeltitel vorkommt; umgekehrt können mehrere relevante Inhaltseinheiten in einem Codex liegen.

## Aktueller Mappingstand

Der Builder verarbeitet sämtliche im aktuellen 521er-Bestand vorkommenden Feldnamen. `unmappedSourceFields` ist im aktuellen Build leer.

Besonders gegenüber der vorigen Webfassung wurden nun korrekt berücksichtigt:

- `title_status`,
- mehrere `incipits`,
- mehrere `explicits`,
- `colophons`,
- `physical_unit` / `fascicle`,
- `notes` sowie weitere inzwischen redaktionell verwendete Item-Felder.

Das bedeutet **keine** endgültige wissenschaftliche Schemanormalisierung. Es bedeutet nur, dass keine gegenwärtig verwendeten Feldnamen stillschweigend an der Webtransformation vorbeigehen.

## Nicht blockierende Hinweise

60 vorhandene `history.origin.date.display`-Angaben werden bewusst nicht in Jahresintervalle umgerechnet, weil sie komplex bzw. nicht eindeutig numerisch interpretierbar sind. Die betreffenden Handschriften bleiben vollständig recherchierbar, erscheinen bei gesetztem Jahresfilter aber nur dann, wenn bereits strukturierte numerische Grenzen vorhanden sind.

Ein als Handschriftenrelation interpretierter Zielverweis konnte weiterhin nicht auf einen Datensatz des aktuellen 521er-Bestands aufgelöst werden:

- `MN II 306` → `L II 2` (`other_copy`)

Der Rohwert bleibt im Webdatensatz erhalten und wird angezeigt. Der Build wird dadurch nicht blockiert.

## Technische Prüfungen

Durchgeführt wurden:

- vollständiges Parsen aller 521 YAML-Frontmatter,
- Prüfung auf eindeutige Signaturen und Web-IDs,
- Prüfung auf vorhandene deutsche Übersetzung und lateinischen Originaltext,
- Neuerzeugung aller 521 Record-JSON-Dateien und Detailseiten,
- Prüfung der neuen Entitätstypen im Manifest,
- Prüfung auf **5.540 eindeutige Suchdokument-IDs**,
- Prüfung der Codex-Deduplizierung je Entitätstyp,
- Kontrolle, dass `unmappedSourceFields` leer ist,
- Python-Syntaxprüfung des Builders,
- JavaScript-Syntaxprüfung der Catalogus-Skripte.

Der maschinenlesbare Detailbericht liegt unter `assets/data/catalogus-codicum/build-report.json`.
