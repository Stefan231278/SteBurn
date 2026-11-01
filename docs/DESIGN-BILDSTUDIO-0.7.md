# SteBurn 0.7 · Zeichenbereich und Bildstudio

Start über `Start-Steburn.bat`. Die neue Oberfläche wird beim nächsten Programmstart geladen. Es sind keine zusätzlichen Bibliotheken erforderlich.

## Arbeitsfläche

Die schmale linke Werkzeugleiste bietet Auswahl, Rechteck, Ellipse, Linie, Bézier, Freihand, Vieleck, Knoten, Text, Messen und Laserziel. Die Werkzeugnamen erscheinen als Mouseover-Hilfe. Oben wechseln die Optionen mit Werkzeug und ausgewähltem Objekt. Für Formen sind Radius, Werkzeugfeststellung und Rasterfang direkt verfügbar; bei Bildern führt „Bild bearbeiten“ ins Bildstudio.

Die rechte Seitenleiste enthält passende Eigenschaften, Text-/Pfad-/Bildoptionen sowie Objekte und Ebenen. **Tab** oder der Bedienfeld-Button blendet sie ein/aus. In Eingabefeldern bleibt Tab für den Fokuswechsel verfügbar. Die Objektliste ist aus der linken Leiste in den rechten Bereich gewandert.

- **Leertaste + Ziehen:** Ansicht verschieben. Die mittlere Maustaste bleibt ebenfalls verfügbar.
- **Zwei Finger / Scrollen:** Ansicht verschieben; Strg + Scrollen zoomt, Shift + Scrollen verschiebt horizontal.
- **Home / Einpassen:** Arbeitsfläche vollständig zeigen.
- **Hilfslinien:** Aus dem oberen oder linken Lineal auf die Fläche ziehen. Bestehende Hilfslinien lassen sich im Auswahlmodus verschieben; außerhalb der Fläche fallen lassen entfernt sie. Sie werden im Projekt gespeichert und erzeugen keine Laserwege.
- **Fangen:** Raster und nahe Hilfslinien verwenden. Alt während einer Bewegung setzt das Fangen vorübergehend aus. Bei kleinem Zoom zeigt das Raster nur ausreichend weit auseinanderliegende Hauptlinien, der eingestellte Fangabstand bleibt bestehen.
- **Freihand:** Linie ziehen; die einstellbare Vereinfachung in mm reduziert unnötige Knoten. 0 erhält die aufgezeichneten Punkte. Die Linie bleibt ein editierbarer Vektorpfad.
- **Drehen:** Bei einem einzelnen entsperrten Vektorobjekt den grünen Griff über dem Auswahlrahmen ziehen; Shift rastet auf 15° ein. Numerische Drehung steht bei ausgewählten Vektorpfaden oben zur Verfügung. Rechtecke/Ellipsen werden dabei in Pfade umgewandelt, Bézier-Kontrollpunkte bleiben erhalten. Bilder werden im Bildstudio gedreht; Text bleibt im Textbereich editierbar.

## Import

„Import“, Strg+I oder das Plus in der Werkzeugleiste öffnet die Dateiauswahl. Mehrere Bilder können gemeinsam gewählt werden. Fotos und Bitmaps gehen zunächst ins Bildstudio und werden erst mit „Bilder ins Projekt übernehmen“ eingefügt. Abbrechen verändert das Projekt nicht. SVG/DXF und weitere Vektoren werden wie bisher als Geometrie importiert; PDF/kompatibles AI werden als Bild ins Bildstudio geleitet. Die bisherigen Formatgrenzen bleiben bestehen.

Unterstützte Bildformate: PNG, JPEG, BMP, TIFF, WebP, GIF und TGA. EXIF-Ausrichtung wird beim Dateiimport berücksichtigt, Transparenz auf Weiß gelegt. Bei Mehrbilddateien wird das erste Bild verwendet. Maximal 40 Megapixel je Quelle.

## Bildstudio

Links stehen die importierten Bilder, in der Mitte Original und Laserbild, rechts die Register **Bild**, **Zuschnitt** und **Laser**. Jedes Bild behält seine eigenen Einstellungen; beim Übernehmen wird die gesamte Importliste verarbeitet. Zum späteren Bearbeiten ein Bild doppelt anklicken oder „Bild bearbeiten“ verwenden.

**Bild:** Helligkeit, Kontrast, Gamma, Schärfe, Schwarz- und Weißpunkt, automatische Tonwertspreizung und Negativ. Die Verarbeitung beginnt immer beim gespeicherten Original; wiederholtes Ändern verschlechtert dadurch nicht schrittweise die Bildquelle. „Bildkorrekturen zurücksetzen“ neutralisiert Tonwertkorrekturen, erhält aber Zuschnitt und Rasterverfahren.

**Zuschnitt:** Auf dem Original einen Ausschnitt aufziehen oder dessen Grenzen in Prozent eingeben. „Gesamtes Bild“ entfernt den Zuschnitt. Drehen in 90°-Schritten und horizontales Spiegeln sind ebenfalls verfügbar. Bei erhaltenem Seitenverhältnis bestimmt die eingegebene Breite die Höhe des zugeschnittenen/gedrehten Bildes; ohne diese Option sind beide Maße frei.

**Laser:**

- Graustufen: dunklere Pixel erhalten relativ mehr Leistung bis zum eingestellten Maximum.
- Floyd-Steinberg: Schwarzweiß-Raster mit Fehlerverteilung.
- Atkinson: alternatives Schwarzweiß-Raster mit einstellbarem Schwellwert.
- Schwellwert: harte Schwarzweißtrennung, etwa für Schrift oder kontrastreiche Vorlagen.

Helligkeit und Kontrast verändern das Bild. Die maximale Laserleistung, der Vorschub und die Durchgänge sind davon getrennte Bearbeitungswerte. Eine Bildschirmvorschau sagt nicht die tatsächliche Gravurtiefe oder Materialwirkung voraus; hierfür bleiben Materialproben erforderlich.

## Raster, Vorschau und Plan

Der Rasterabstand in mm bestimmt die Auflösung (`dpi = 25,4 / Abstand`). Die Vorschau zeigt die tatsächlichen berechneten Rasterpixel, auf die Bildschirmgröße skaliert. Die Originalvorschau ist bei großen Quellen für die Anzeige verkleinert; das Original selbst wird vollständig gespeichert.

Das Bildstudio arbeitet innerhalb des bestehenden Planlimits und reserviert konservativ höchstens 120.000 Rasterpixel einschließlich Durchgängen je Bild. „Raster an Planlimit anpassen“ schlägt dafür einen größeren Abstand vor. Es startet keinen Auftrag. Die Gesamtprüfung mehrerer Bilder und Vektoren erfolgt weiterhin in Vorbereitung bzw. beim Erstellen des exakten Auftragsplans; dessen bestehendes Segmentlimit wurde nicht erhöht.

Vorschau und Laserplan nutzen dieselbe Verarbeitung. Wird ein vorbereitetes Bild auf der Arbeitsfläche skaliert oder sein Rasterabstand geändert, berechnet der Plan die Rasterung aus Original und Korrekturen neu. Dadurch bleiben Schwarzweiß-Raster binär, statt beim bloßen Skalieren Graustufenartefakte zu bekommen. Die eingebettete Bilddarstellung auf der Arbeitsfläche ist eine skalierte Darstellung des zuletzt übernommenen Laserbilds; die aktuelle Rastervorschau lässt sich jederzeit im Bildstudio prüfen.

## Laserbetrieb und Prüfung

Verbindung, automatische Referenzfahrt, Nullpunkt, Rahmenfahrt, Live-Cockpit, Overrides, Pause, Fortsetzen und Reset bleiben erhalten. Bildverarbeitung und Import senden keine Gerätebefehle.

145 automatische Tests bestanden. Grafisch geprüft wurden Arbeitsfläche, Seitenleisten, Werkzeugoptionen, Fangfunktionen, Hilfslinien, Freihand, Drehung, Bildvorschau, Originalerhalt, Übernehmen/Wiederöffnen und Importabbruch. Auch die Studio-/Cockpit-Prüfung mit simulierter Telemetrie besteht weiterhin. Während der Entwicklung fand kein realer Laserauftrag statt.
