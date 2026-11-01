# Steburn 0.3 – Erweiterungspunkte

- `core/model.py`: Projekt/Shape/Layer, Schema 3. Objekt-Overrides unter
  Shape.extra.processing, bestehende unbekannte Zusatzdaten bleiben erhalten.
- `core/processing.py`: einzige Auflösung von Objekt- und Ebenenwerten;
  Füllgeometrie. Änderungen an Parametern hier validieren, nicht nur im Widget.
- `core/planner.py`: Segmentplan mit exact-Flag. Eine vereinfachte Bildvorschau
  darf nie als exakter Maschinenauftrag verwendet werden.
- `core/jobs.py`: unveränderlicher Auftragssnapshot mit SHA256, Grenze zwischen
  Vorschau und ausführbarem Testlauf, Segment-basierter Fortschritt,
  ein serieller Leser, Steueranforderungen über Queue.
- `devices/grbl.py`: Protokoll, Statusbeobachtung, Referenzfreigabe, Randabstand.
  Der Worker muss sämtliche empfangenen Zeilen durch observe führen; besonders
  Starttexte dürfen nie stillschweigend übersprungen werden.
- `platform/power.py`: Windows Awake-Kontext, Threadbindung und Akkuabfrage.
  Keine dauerhafte Änderung am Windows-Energiesparplan.
- `ui/workbench.py`: moderne Ergänzung des vorhandenen Editors. Keine Geometrie
  oder Controllerbytes in Kontextmenüaktionen implementieren.
- `ui/job_window.py`: Status-/Zeitansicht, UI-Anforderungen an Worker. Reales
  Produktionsstreaming bleibt eine eigene zukünftige Implementierung.
- `ui/relief.py`: bewusst lazy geladen. Zukünftige KI-Provider sollen eine
  Tiefenkarte samt Unsicherheitsangaben liefern; Materialkalibrierung bleibt ein
  getrennter Schritt. Keine externen Übertragungen ohne deutliche Auswahl.

Nächste technische Schritte: GUI schrittweise aus dem bestehenden Editor in
kleinere Panels extrahieren, Produktionsstreamer mit Status-/Pufferabgleich und
verifizierbaren Wiederaufnahmepunkten, Autosave/Jobjournal, persistente vermessene
Maschinenprofile, materialgebundene Tiefenkalibrierung, besseres Schrift-Shaping,
Vektorisierung von Bitmaps und echte Relief-Geometrievorschau.

Scharfe Ausgabe nicht durch einen einfachen UI-Schalter freigeben. Vorher die
im Maschinenprotokoll offenen physikalischen Prüfungen abschließen und die
entsprechende Fehlerbehandlung mit simuliertem Controller testen.

## Ergänzungen in 0.4

- modules/boxes.py: eigenständiger parametrischer Geometriekern, Montageebenen,
  Schnittspaltkorrektur, Plattenlayout, atomare Projektübergabe und SVG/DXF.
- ui/boxes.py: optionales Modulfenster mit mm/Zoll, drehbarem 3D-Schema und
  Regeneration gespeicherter Modelle. Keine Maschinenanbindung im Modul.
- workbench.layout_workflow: eine obere Leiste mit responsivem Overflow.
