# MakerCase – öffentliche Funktionsaufnahme und Steburn-Umsetzung

Stand: 16. Oktober 2026. Eigenständige Steburn-Implementierung, keine Übernahme
von MakerCase-Quellcode, Gestaltung oder proprietären Dateiformaten.

Die Startseite und alle dort verlinkten 13 Generatorseiten wurden abgerufen.
Die öffentlich lesbaren Seiten liefern Funktionsbeschreibungen, aber keine
vollständige technische Spezifikation der interaktiven Anwendung. Folgende
Aufstellung ist daher eine belegte öffentliche Funktionsaufnahme, keine Zusage,
jeden internen Parameter oder jede kontogebundene Funktion erfasst zu haben.

## Öffentliche Generatoren

| MakerCase | Öffentlich beschriebener Zweck | Steburn 0.4 |
| --- | --- | --- |
| Basic Box | Breite, Tiefe, Höhe, Materialstärke; Fingerzinken; SVG/DXF | Rechteckbox, Fingerzinken/Klebekanten, Innen-/Außenmaß, offen/fest/loser Deckel |
| Laser Hinge Box | Integrierter Scharnierdeckel, Deckelhöhe, Drehachsdurchmesser | Noch nicht implementiert |
| Grid Divider Box | Regelmäßige Gefache, Zeilen/Spalten | Lose Gefache mit kreuzenden Halbholzschlitzen |
| Custom Divider Box | Individuelle Fächer teilen und skalieren | Noch nicht implementiert |
| Grid Drawer Box | Schrank mit herausnehmbarer Schublade je Rasterfach | Noch nicht implementiert |
| Custom Drawer Box | Schubladen passend zu frei veränderten Fächern | Noch nicht implementiert |
| Sliding Lid Box | Schiebedeckel, Maße/Stärke, 3D-Vorschau | Noch nicht implementiert; loser Deckel ist kein Schiebedeckel |
| Stackable Parts Bin | Stapelbehälter mit offener Front, Laschen, optionalen Teilern | Noch nicht implementiert |
| Polygon Box | Vieleckige Grundrisse, Seitenzahl, Maße/Stärke | Vieleck als ausdrücklich bezeichnete Schichtbauweise aus Ringen |
| Curved Box | Gebogene Box mit Biegeschlitzen / Living Hinge | Abgerundete Schichtbox; keine Biegeschlitzkonstruktion |
| Basic 3D Printed Box | 3D-Druck-Box mit Wandstärke, STL/3MF | Kein 3D-Druck-Export |
| 3D Printed Grid Divider Box | Auf Startseite gelistet; Detailseite ohne lesbare Zusatzbeschreibung | Nicht implementiert |
| 3D Printed Custom Divider Box | Auf Startseite gelistet; Detailseite ohne lesbare Zusatzbeschreibung | Nicht implementiert |

Startseite: [MakerCase](https://www.makercase.com/)

Originalseiten:

- [Basic Box](https://www.makercase.com/basicBox)
- [Laser Hinge Box](https://www.makercase.com/laserHinge)
- [Grid Divider Box](https://www.makercase.com/divider)
- [Custom Divider Box](https://www.makercase.com/flexLaser)
- [Grid Drawer Box](https://www.makercase.com/dividerDrawer)
- [Custom Drawer Box](https://www.makercase.com/flexLaserDrawer)
- [Sliding Lid Box](https://www.makercase.com/laserSlide)
- [Stackable Parts Bin](https://www.makercase.com/stackableBin)
- [Polygon Box](https://www.makercase.com/polygon)
- [Curved Box](https://www.makercase.com/kerf)
- [Basic 3D Printed Box](https://www.makercase.com/basic3D)
- [3D Printed Grid Divider Box](https://www.makercase.com/grid3D)
- [3D Printed Custom Divider Box](https://www.makercase.com/flex3D)
- [About](https://www.makercase.com/about)

## Gemeinsamer Arbeitsablauf und Konsequenz für Steburn

Maße und Materialstärke → parametrisierte Vorschau → flache Schnittteile →
SVG/DXF beziehungsweise 3D-Druckformate. In Steburn kommt die direkte Übergabe
an Objektverwaltung, Ebenen und Simulation hinzu. Boxparameter werden separat
von den bearbeitbaren Konturen gespeichert. Nachbearbeitung ist möglich;
Regeneration ersetzt die zu diesem Modell gehörenden Schnittteile ausdrücklich.

MakerCase-Kompatibilität: Normales SVG/DXF kann über die vorhandenen Importer
als Geometrie geladen werden. MakerCase-interne Parameter oder dessen
Clone-from-file-Funktion werden nicht rekonstruiert. Steburn-eigene Parameter
bleiben im .steburn-Projekt erhalten; der Box-SVG-Export enthält zusätzlich
Metadaten, für die noch kein eigener Wiederimport-Assistent existiert.

## Ausbaufolge

Material-Passproben für Fingerzinken/Gefache; danach Schiebeführung und
Scharnierbox; freie Gefache und passende Schubladen; stapelbare Behälter;
gezielt kalibrierte Biegegeometrie. CNC-spezifische Werkzeuge und 3D-Druck
sind eigene Arbeitsbereiche. Das Boxmodul ist dafür vom Editor und der
Maschinenkommunikation getrennt angelegt.
