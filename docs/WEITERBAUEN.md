> Historischer Stand bis 0.2. Aktueller Stand: README.md und docs/ARCHITEKTUR-0.3.md.

# Weiterarbeitsauftrag

Arbeite am bestehenden Steburn-Projekt 0.2.2, ersetze es nicht durch einen neuen
Prototyp. Ziel: modulare Windows-Lasergestaltungssoftware für den
Atomstack A40 Pro, 400 × 400 mm. Nullpunkt links unten.

Lies README.md, ARCHITEKTUR.md, IMPORTFORMATE.md und ROADMAP.md. Bestehende
Schema-1-Projekte werden migriert, Schema 2 ist aktuell. Erweiterungsdaten erhalten.
Es gibt drei Farbebenen mit Schnellzuordnung, plus weitere Ebenen, Textpfade,
Layoutwerkzeuge, Import und eine deterministische Bahnsimulation.

Physische Ausrichtung ist implementiert, noch nicht am Laser getestet. Kein
Schneid-/Gravurjobstart. Nicht eigenmächtig Firmware-/Leistungswerte übernehmen;
Nullpunkt und Einstellungen bestätigen. Keine Laseraktivierung in automatisierten
Tests. Simulation und Controller-Ausgabe später aus demselben Plan ableiten.

Erweitere in überprüfbaren Schritten und füge aussagekräftige Tests für Geometrie,
Migration oder Übertragung hinzu. UI in kleinere Komponenten zerlegen.
Aktuelle Tests: python -m unittest discover -s tests -v.
Grafischer Test auf Desktop: python tests/gui_smoke.py.

Seit 0.2.2: Maus-Skalierung, Systemfonts, scrollbare Panels und adaptive
Rastervorschau. Vor produktiver Ausgabe stets exakten Plan verwenden; reduzierte
Vorschau ist bewusst nur visuell.
