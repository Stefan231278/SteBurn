# Prüfstand Steburn 0.4.0

120 automatisierte Tests bestanden, einschließlich 25 neuer Boxprüfungen:

- Alle vier Bauformen und drei Deckelvarianten ergeben gültige Geometrie.
- Innen-/Außenmaße, Deckelhöhe und Materialstärke werden berücksichtigt.
- Gemeinsame Kanten und Dreifachecken verzinkter Rechteckboxen anhand von
  Volumen, systematischen Kantenproben und deterministischen Zufallspunkten
  ohne Überschneidungen/Lücken geprüft; zusätzlich 40 gebrochene Maßkombinationen.
- Halbholzschlitze kreuzender Gefache auf Materialkollision geprüft.
- Schnittspaltkorrektur von Außenkonturen und Innenlöchern geprüft. Ein
  Schnittspalt ab Materialstärke wird bei Steckverbindungen abgewiesen, damit
  schmale Verbindungsmerkmale nicht durch die Korrektur verschwinden.
- Plattenlayout auf Grenzen, Überschneidungen und Vollständigkeit geprüft.
- Zu große Einzelteile werden abgewiesen; keine Skalierung.
- Parameter-Roundtrip, nur erste Platte sichtbar, Ausgabe AUS und Regeneration
  unter Erhalt fremder Projektobjekte geprüft.
- SVG mit Löchern wieder importiert; DXF-Einheit Millimeter und geschlossene
  Polylinien geprüft. mm/Zoll-Rundungsfall als Regression abgesichert.

Grafische Prüfungen für neue Oberfläche und Boxmodul:

- Eine Kopfzeile und größere Arbeitsfläche, responsives Mehr-Menü.
- Lasern bleibt erreichbar, Hilfen und Logo erhalten.
- Parametereingabe, Gefache, 3D-Schema/Explosionsansicht, Einheitenwechsel.
- Ungültige Eingaben sperren Übernahme/Export statt alten Entwurf zu verwenden.
- Übernahme, gespeicherte Parameter, erneutes Öffnen und Regeneration.

Zusätzlich bestehende Editor-, Präsentations- und 0.3-Bedienprüfungen sowie
Syntaxprüfung. Keine Tests öffnen einen COM-Port oder bewegen einen echten Laser.

Noch offen: reale Montage-/Passproben und Windows-Darstellung der neuen Version.
Alle bisherigen Einschränkungen für Strahlbearbeitung und Maschinenfreigabe
bestehen fort. Details der bisherigen Controllerprüfungen im Maschinenprotokoll.

Befehle im Projektordner:

    python -m unittest discover -s tests
    python -m compileall -q steburn main.py
    python tests/gui_smoke.py
    python tests/gui_v03.py
    python tests/gui_presentation.py
    python tests/gui_boxes.py
