# Einbaupaket Catalogus Codicum

Dieses Paket ist so strukturiert, dass sein Inhalt in die Wurzel des bestehenden GitHub-Repositories `StiftsarchivSeitenstetten/Findmittel` übernommen werden kann.

## Vorgehen für Commit/Push

1. Repository lokal auf den aktuellen Stand bringen.
2. Inhalt dieses Pakets **pfadgleich** in die Repository-Wurzel kopieren.
3. Dabei die beiden vorhandenen Dateien
   - `_layouts/default.html`
   - `bibliothek/index.html`
   durch die Fassungen dieses Pakets ersetzen.
4. Optional, aber empfohlen: den Build im Zielrepository noch einmal ausführen:

   ```bash
   python3 -m pip install -r scripts/requirements-catalogus.txt
   python3 scripts/build-catalogus-codicum.py
   ```

5. `assets/data/catalogus-codicum/build-report.json` kontrollieren.
6. Website lokal bzw. nach GitHub-Pages-Build prüfen.
7. Commit und Push durchführen.

## Wichtige Abgrenzung

- Die 521 Handschriftendatensätze werden als wissenschaftliche Masterdateien in `_catalogus-codicum/` mitgeführt.
- Die redaktionelle Hilfsdatei `Signaturen_nicht_MN_Uebersicht.md` ist bewusst **nicht** Teil des Einbaupakets; sie ist kein Handschriftendatensatz und dient nicht als Bestandsmanifest.
- Die Masterdateien werden nicht umgeschrieben oder für Webzwecke vereinheitlicht.
- Alle Webnormalisierungen finden ausschließlich in den erzeugten JSON-Dateien statt.

Die technische Dokumentation liegt unter `docs/catalogus-codicum-web.md`.
