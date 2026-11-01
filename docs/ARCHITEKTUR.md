> Historischer Stand bis 0.2. Aktueller Stand: README.md und docs/ARCHITEKTUR-0.3.md.

# Steburn 0.2.2 – Architektur

| Modul | Verantwortung |
|---|---|
| core/model.py | Schema 2, Migration aus Schema 1, atomische Speicherung, Undo/Redo |
| core/paths.py | Textkonturen, Objektpfade, Grenzen, Transformationen, Polygonoperationen |
| core/resize.py | Ankerbasierte Skalierung mit optionalem Seitenverhältnis |
| core/fonts.py | Systemschriften, Windows-Registry und TTC-Schnitte |
| ui/widgets.py | Scrollbare Eigenschaften |
| core/planner.py | Kontur-/Füll-/Rasterplan, Leerfahrten, Durchgänge, Zeitabschätzung |
| core/extensions.py | Registry für explizit registrierte Befehle |
| core/geometry.py | Einfacher Konturkern aus 0.1 |
| io/importers.py | Formatdispatch, Bilder, PDF/AI, SVG-Pfade, DXF, HPGL/GCode-Geometrie, SVG-Export |
| io/svg.py | Konservativer SVG-Basisparser aus 0.1 |
| devices/grbl.py | Abfragen, geprüfte Positionierung und Rahmenfahrt; kein Bearbeitungsjobstart |
| devices/base.py | Adaptervertrag/Offlineadapter |
| ui/app.py | Basisoberfläche und einfache Editoraktionen |
| ui/editor.py | Erweiterter Editor, Farbpalette, Werkzeuge, Import und Gerätebedienung |
| ui/simulation.py | Animierte Vorschau mit Zeitleiste |

Weltkoordinaten: links unten. Canvaskoordinaten: oben links; Umrechnung nur an der
UI-Grenze. SVG/PDF-Koordinaten werden beim Import entsprechend umgesetzt.
Projekt-Schema 1 verwendet oben links und wird beim Laden explizit migriert.

Neue Daten unter Project.extensions oder Shape.extra speichern, mit Namensraum.
Neue Schemafelder brauchen Migration und Roundtrip-Tests. Konturen sind lokale
Punkte relativ zur Objektposition, bei mehreren Konturen in extra.contours.
Mehrfachkonturen werden beim Füllen nach Gerade/Ungerade-Regel ausgewertet.
Bilddaten sind normalisierte, eingebettete PNGs, damit Projektpfade nicht abbrechen.
Fonts sind lokale Referenzen; portable Weitergabe durch Text-zu-Pfad.

Jede Dokumentmutation: Kopie → Validierung → History.checkpoint → Übernahme →
Refresh. Keine Maschinentransporte aus Canvas-Callbacks; Geräteaufträge laufen in
separatem Thread, Rückmeldungen über Queue. Reset kann den laufenden Auftrag
unterbrechen; keine automatische Wiederaufnahme.

Nächster struktureller Ausbau: Foundation/Editor-Vererbung durch einzelne Canvas-,
Tool-, Panel- und Actionmodule ersetzen. Die momentane Vererbung hält die 0.1-
Basis wiederverwendbar, ist aber kein Ziel für einen großen Editor. Registry
später um Versionierung und panelbasierte Erweiterungen ergänzen. Kein Autoload
unbekannter Plugins und kein fertiges Plugin-SDK vorhanden.

Ein späterer Controller-Jobstart muss exakt denselben geprüften Bearbeitungsplan
verwenden wie die Simulation. Dafür fehlen noch Beschleunigungsmodell, vollständige
GRBL-Ausgabe/Pufferverwaltung, Geräteprofilpersistenz und reale Maschinentests.
Alignment-Ausgabe ist absichtlich vom Bearbeitungsjobplan getrennt.

Bildvorschau und exakter Plan sind getrennt: build_plan(preview=True) darf den
Rasterdetailgrad begrenzen und liefert einen Hinweis. build_plan(preview=False)
verändert die angeforderte Auflösung nicht. Keine Hardwareausgabe aus reduzierter
Simulation ableiten. Originalpixel und Ebenenintervall werden nicht mutiert.
