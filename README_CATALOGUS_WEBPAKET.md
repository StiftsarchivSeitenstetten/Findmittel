# Einbaupaket Catalogus Codicum – Entitätssuche

Dieses Paket ist so strukturiert, dass sein Inhalt **pfadgleich in die Wurzel** des bestehenden GitHub-Repositories `StiftsarchivSeitenstetten/Findmittel` übernommen werden kann.

Datenstand der wissenschaftlichen Masterdateien: **Redaktionspaket_1_Gesamt(2)** vom 29. August 2026. Enthalten sind 521 eigentliche Handschriftendatensätze.

## Vorgehen für Commit/Push

1. Repository lokal auf den aktuellen Stand bringen.
2. Inhalt dieses Pakets pfadgleich in die Repository-Wurzel kopieren. Dabei werden insbesondere die bereits vorhandenen Dateien `_layouts/default.html` und `bibliothek/index.html` durch die mitgelieferten Fassungen ersetzt; alle Änderungen daran sind Teil dieses Webpakets.
3. Vor dem Commit den Catalogus-Build **zwingend** noch einmal im Zielrepository ausführen:

   ```bash
   python3 -m pip install -r scripts/requirements-catalogus.txt
   python3 scripts/build-catalogus-codicum.py
   ```

   Wenn PyYAML bereits installiert ist, ist der erste Befehl nicht erneut nötig. Der zweite Befehl ist vor dem Commit verpflichtend.

4. Danach kontrollieren:
   - `assets/data/catalogus-codicum/build-report.json`
   - den Git-Diff auf unerwartete Änderungen
   - die Catalogus-Suche lokal, soweit möglich
   - mehrere Detailseiten einschließlich Inhaltseinheiten, Incipits/Kolophone und Relationen
5. Erst danach committen und pushen.

## Neu in dieser Fassung

Die Suche besitzt nun zwei getrennte Auswahlachsen:

- **Entität / Treffertyp**: alle Entitätstypen oder gezielt Codex, Werk/Inhaltseinheit, physische Einheit, Person, Incipit, Explicit/Kolophon, Nachtrag/Vermerk oder historische Katalogbeschreibung.
- **Suche in**: alle Felder oder gezielt Signatur, Titel/Inhalt, Personen, Incipit, Explicit/Kolophon, physische Beschreibung, deutsche Übersetzung oder lateinischer Originaltext.

Nach jeder Suche werden die Ergebnisse **nach Entitätstyp gruppiert**. Oberhalb der Treffer erscheinen Schaltflächen mit Trefferzahl und Zahl der jeweils betroffenen Codices. Damit kann nach einer zunächst breiten Suche sofort auf einen einzelnen Entitätstyp umgeschaltet werden.

Die Statuszeile nennt zusätzlich die Zahl der **Codices mit mindestens einem Treffer**. Damit lassen sich Fragen wie „In wie vielen Codices kommt X vor?“ unmittelbar beantworten, ohne die einzelnen Inhaltstreffer händisch deduplizieren zu müssen.

## Wichtige wissenschaftliche Abgrenzung

- Die 521 Markdown-/YAML-Dateien in `_catalogus-codicum/` bleiben der wissenschaftliche Masterbestand.
- Die Masterdateien werden vom Builder nicht verändert.
- Alle Normalisierungen für Suche und Anzeige geschehen ausschließlich in der Webschicht.
- `Werk / Inhaltseinheit` bezeichnet in dieser Webfassung eine **konkrete überlieferte Einheit aus `ms_contents.items`**, keine bereits normierte abstrakte Werkentität.
- Physische Einheiten werden nur als eigene Webentität erzeugt, wenn sie in den Masterdaten ausdrücklich mit Inhaltseinheiten verknüpft sind. Es werden keine Faszikel oder `msPart`-Strukturen aus bloßen Zahlenangaben erfunden.
- Personen werden nicht global normalisiert. Identische Namensstrings werden nur innerhalb eines Codex für die Suchanzeige gebündelt.

Die technische Dokumentation liegt unter `docs/catalogus-codicum-web.md`.
