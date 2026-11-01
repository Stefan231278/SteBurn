# Importübersicht anhand des LightBurn-Screenshots

| Endungen | Steburn 0.2 | Grenzen |
|---|---|---|
| bmp, jpg, jpeg, png, gif, tif, tiff, tga, webp | Bildimport | Erstes Bild bei GIF/mehrseitigem TIFF, Hinweis vor Übernahme; Zielbreite zunächst 100 mm |
| svg | Einfache Formen, Text, Polygone und Bézier-/Bogenpfade | mm-Dokumentgröße und viewBox-Ursprung 0,0 erforderlich; Transformationen, Masken, eingebettete Bilder und komplexe Stile noch nicht unterstützt; Pfade auf ca. 0.4-mm-Segmente abgeflacht |
| dxf | LINE, LWPOLYLINE, POLYLINE, CIRCLE, ARC, ELLIPSE, SPLINE | Flache Geometrie; kein TEXT, INSERT/Block, DIMENSION, HATCH etc.; Einheiten umgerechnet, bei fehlender Einheit expliziter Hinweis „mm angenommen“ |
| pdf | Einseitige PDF als Bild bei 144 dpi | Keine editierbaren Vektoren; Mehrseiten-/passwortgeschützte Dateien abgelehnt |
| ai | PDF-kompatible AI als Bild | Andere Illustrator-Formate abgelehnt |
| gc, gcode, nc | Begrenzter Geometrieimport | G0/G1, mm/inch und absolute/relative Positionen; nur laseraktive G1-Wege; keine Kreisbögen, Makros oder Controllerprogramme; keine Ausführung |
| hpgl, plt | Einfacher Stiftpfadimport | PU/PD/PA/PR, 40 Einheiten/mm; kein SC/IP/AA/AR/LB oder andere Sonderbefehle; keine Übernahme von Maschinenparametern |
| sc | Noch nicht unterstützt | Über SVG/PDF austauschen |
| rd | Noch nicht unterstützt | Maschinenformat nicht ausführen; über SVG austauschen |
| scpro2 | Noch nicht unterstützt | Über SVG/PDF austauschen |
| lbrn, lbrn2 | Noch nicht unterstützt | Projekt in LightBurn als SVG exportieren; Parameter separat übernehmen |
| mage | Noch nicht unterstützt | Über SVG/PDF austauschen |
| steburn | Öffnen statt Import | Schema 1 wird migriert; Schema 2 direkt geöffnet |

Der Dateidialog zeigt auch noch nicht unterstützte Endungen, damit eine konkrete
Meldung erklärt, warum ein Format noch nicht gelesen wird. Das ist keine Behauptung
vollständiger LightBurn-Formatkompatibilität. Bei nicht unterstützten Elementen
bleibt das bestehende Projekt unverändert.

SVG-Export kann Bilder einbetten, der derzeitige SVG-Importer liest solche Bilder
noch nicht zurück. Bitmapdateien direkt importieren oder das Steburn-Projekt verwenden.
Import und Export sind daher noch kein universell verlustfreier Austausch.
