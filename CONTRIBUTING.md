# Zu SteBurn beitragen

Fehlermeldungen, Verbesserungsideen, Dokumentation und Pull Requests sind willkommen. Deutsch und Englisch sind möglich.

## Entwicklung

1. Repository forken und den eigenen Fork klonen.
2. Python 3.11 oder neuer mit Tcl/Tk installieren.
3. Unter Windows `Einrichten-Steburn.bat` ausführen.
4. Mit `Start-Steburn.bat` oder `.venv\Scripts\python.exe main.py` starten.
5. Einen eigenen Branch für eine überschaubare Änderung anlegen.

Automatische Tests ohne angeschlossene Maschine:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

Grafische Prüfungen sind separat unter `tests/gui_*.py` verfügbar. Sie benötigen einen Desktop und gehören nicht zum automatischen Testlauf.

## Fehler und Ideen melden

Bitte zuerst nach vorhandenen Issues suchen. Bei Fehlern Programmversion, Windows- und Python-Version, Schritte zur Reproduktion sowie erwartetes und tatsächliches Verhalten angeben. Ein kleines, anonymisiertes Beispielprojekt hilft. Passwörter, persönliche Daten und vollständige Geräteprotokolle vor dem Hochladen prüfen und entfernen.

## Pull Requests

- Problem und geändertes Verhalten beschreiben, bei UI-Änderungen möglichst mit Screenshot.
- Relevante Tests und deren Ergebnis nennen; nicht ausgeführte Prüfungen benennen.
- Geometrie-, Projektformat- und Übertragungsänderungen mit passenden Tests absichern.
- Projektformate abwärtskompatibel halten oder eine ausdrückliche Migration vorsehen.
- Keine lokalen Einstellungen, virtuellen Umgebungen oder erzeugten Dateien einchecken.
- Lizenz und Herkunft neuer Abhängigkeiten und Medien angeben.

## Geräteansteuerung

Änderungen an Laserleistung, Referenzfahrt, Nullpunkt, GRBL-Streaming, Pause und Abbruch ausdrücklich kennzeichnen. Automatische Tests dürfen keine reale Maschine bewegen oder den Laser einschalten. Simulation und geprüfter Ausgabeplan müssen übereinstimmen. Reale Maschinentests nur bewusst und unter geeigneten Schutzbedingungen durchführen; Simulation ist kein Nachweis für die Sicherheit am Gerät.

Einstieg in den Code: `steburn/core` für Daten, Geometrie und Planung, `steburn/io` für Import/Export, `steburn/devices` für Gerätekommunikation und `steburn/ui` für die Oberfläche. Historische Architekturtexte in `docs` können ältere Funktionen beschreiben; der aktuelle Funktionsstand steht in der README.
