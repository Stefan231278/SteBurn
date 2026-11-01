> Historischer Stand bis 0.2. Aktueller Stand: README.md und docs/ARCHITEKTUR-0.3.md.

# Steburn – aktueller Stand und nächste Version

0.1: Offlineeditor-Grundgerüst.
0.2: links-unten-Koordinaten samt Migration, drei Farbebenen, Mehrfachauswahl,
Gruppen, Polygon-/Textpfade, zusätzliche Layout-/Geometriewerkzeuge, Importdispatch,
animierter Bearbeitungsplan und GRBL-Ausrichtung mit Freigabeprüfungen.

Nächste Aufgaben:
1. Einrichtung und Layout auf dem tatsächlichen Windows-Rechner prüfen.
2. Firmware ($I), Einstellungen ($$), Arbeitsnullpunkt, Anschluss und Baudrate des
   echten A40 Pro bestätigen; Ausrichtung zuerst ohne Laser beaufsichtigt testen.
3. Geräteprofil versioniert speichern, WCO-/Statusverwaltung verbessern, Hardware-
   Fehlerfälle und Abbruch prüfen. Erst danach Bearbeitungsjob-Ausgabe ergänzen.
4. Koordinatenraster/Snapping, Lineale, allgemeine Winkelrotation, echte Bezierknoten,
   Bildrotation/-spiegelung und nichtdestruktive Bildbearbeitung.
5. SVG-Transformationen, Stil-/Fillregeln und eingebettete Bilder; DXF-Blöcke und
   Schriften; PDF-Vektoren; gezielte LBRN2-Importanalyse anhand eigener Beispieldateien.
6. Automatische Wiederherstellung, größere Projektdateien, Bildassets aus Snapshot-
   Historie auslagern; klarere Werkstück-/Materialverwaltung.
7. Bildvektorisierung, Kamera, Drehachse, Materialtests, echte Konturschachtelung,
   Vorlagen mit variablen Namen/Maßen, Text auf Pfad und Verformungswerkzeuge.
8. Reproduzierbare Windows-EXE und Installer, Abhängigkeits-/Lizenzprüfung vor
   Veröffentlichung, automatisierte Regressionstests und dokumentiertes Plugin-SDK.

Die aktuelle Simulation ist geometrisch. Materialwirkung und Brand lassen sich
nicht durch eine rein grafische Bahnvorschau ausschließen. Keine universelle
spurenfreie Ausrichtleistung versprechen.

0.2.2 ergänzt skalierbare Objektgriffe, lesbare Systemschriften, Positionsanzeige
mit einer Dezimalstelle und vereinfachte Vorschau für größere Bitmaps.
