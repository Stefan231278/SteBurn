# SteBurn Studio 0.6

Start über `Start-Steburn.bat`. Eine bereits geöffnete Instanz lädt die neue Oberfläche erst nach einem Neustart. Vorher ihr Projekt speichern. Es sind keine neuen Bibliotheken erforderlich.

## Gestaltung

Links liegen Zeichenwerkzeuge, Bearbeitung und Objektliste. Rechts sind Maße, Text, Pfade und Ebenen als eigene Register zusammengefasst. Bestehende Anordnungs-, Import-, Boolesche- und Modulbefehle bleiben in den Menüs verfügbar.

- **Rechteckradien:** Rechteck auswählen → Pfade & Radien → Radius in mm → Anwenden. Der Wert wird auf die halbe kleinere Seitenlänge begrenzt. Die Rundung gehört auch zum exportierten und gelaserten Weg.
- **Bézier:** Vier Klicks setzen Start, ersten Griff, zweiten Griff und Ende. Danach zeigt der Knotenmodus Anker und Tangenten. Anker nehmen ihre angrenzenden Griffe mit. Optional werden gegenüberliegende Griffe gespiegelt.
- **Teilen / Einfügen:** Teilt das gewählte Béziersegment mit de Casteljau formtreu. Bei Linienzügen wird ein Mittelpunkt eingefügt. Durch weitere Teilungen und Griffbewegungen lassen sich mehrteilige Kurven gestalten.
- **Knoten:** Auf der Fläche oder in der Tabelle auswählen, ziehen oder X/Y numerisch übernehmen. Linienknoten und innere Bézier-Anker lassen sich löschen. Löschen im Knotenmodus bearbeitet den gewählten Knoten; sonst das Objekt.
- **Skalieren:** Bézier-Kontrollpunkte bleiben beim Skalieren und Spiegeln erhalten. Eine ausdrückliche Pfadumwandlung erzeugt dagegen einen Linienzug.

Kurven werden für die bestehende Maschinensteuerung adaptiv mit einer Flachheitstoleranz von 0,04 mm in Liniensegmente aufgeteilt; Kreisbögen der Rechteckradien mit 0,02 mm Sehnenabweichung. Kontrollpunkte bleiben zusätzlich im Projekt gespeichert. Das sind geometrische Näherungen, keine Aussage zur mechanischen Genauigkeit des Lasers.

## Text

Das Textwerkzeug platziert einen editierbaren Text ohne Eingabedialog. Im Register Text & Schrift Inhalt, Größe, Laufweite, Zeilenabstand und Ausrichtung bearbeiten. „Text übernehmen“ oder Strg+Enter übernimmt die Änderungen. Alternativ erstellt „Neuen Text erstellen“ ein weiteres Objekt.

Schriftgrößen sind mm auf Basis des Schrift-Em, Zeilenabstände Faktoren dieser Größe; tatsächliche Glyphenhöhen hängen von der Schrift ab. Laufweite wird in mm zwischen Zeichen hinzugefügt. Mehrere Zeilen werden am breitesten Zeilenfortschritt ausgerichtet. Schriftschnitte werden über die Systemschriftenliste gewählt. Komplexes OpenType-Shaping und Text auf Pfaden sind nicht enthalten.

Im Textfeld arbeiten Löschen, Duplizieren-/Undo-Tastenkombinationen am Text, ohne dabei Zeichnungsobjekte zu verändern. Nach einer Pfadumwandlung ist das Objekt als Kontur bearbeitbar; für eine spätere Textänderung vorher eine Textkopie behalten.

## Vorbereitung

Der Hauptbereich zeigt den berechneten Werkzeugweg: Rot für Bearbeitung, Blau für Leerfahrten. Die Seitenleiste führt Ausgabeebenen, eigene Objektparameter, Segmentzahl, geometrische Zeitschätzung und Planhinweise zusammen. Bei dichten Wegen wird nur die Hintergrunddarstellung ausgedünnt.

„Simulation“ öffnet den virtuellen Ablauf mit Zeitleiste, Tempo, Pause und Rücksetzen. „Rahmenvorschau“ ist ebenfalls virtuell. „Rahmen fahren“ bewegt die reale Maschine wiederholt ohne Strahl; „Stopp“ beendet die Fahrt mit Reset. Bearbeitungswerte und Ausgabeebenen liegen in den angrenzenden Registern.

## Materialien

Eine zentrale Profilansicht und eine getrennte Projektzuordnung ersetzen die frühere kleine Vorlagenliste. Profile enthalten Name, Material, Stärke, Bearbeitungsart, Leistung, Vorschub, Durchgänge, Linienabstand und den bereits vorhandenen Air-Assist-Parameter. Air Assist wird weiterhin als Parameter gespeichert, nicht zusätzlich an der Hardware geschaltet.

Die Bibliothek liegt unter `user-data/materials.json` neben dem Programm. Verwendete Profile werden in der `.steburn`-Datei mitgespeichert und sind dadurch auch ohne die lokale Bibliothek verfügbar. Die Zuordnung kann die aktive Ebene oder die entsperrte Objektauswahl betreffen. Eigene Objektwerte haben Vorrang vor Ebenenwerten. Neue Profile beginnen mit 0 % Leistung; es gibt keine automatisch geratenen Materialwerte.

## Job-Cockpit

„Job-Cockpit“ öffnet die Auftragsansicht vor dem Start. Der Startbutton beginnt wie bisher die reale Bearbeitung. Das Cockpit zeigt Controllerzustand, Position, Vorschub, S-Leistungswert, bestätigte Overrides, abgeschlossene Segmente, Werkzeugweg, vergangene Zeit, Restzeitschätzung und Ereignisse.

Vorschub und Leistung lassen sich als Overrides zwischen 10 und 200 % anfordern. „Live anwenden“ sendet die vorhandenen GRBL-Echtzeitbefehle im Geräteworker; die Ist-Anzeige folgt den vom Controller bestätigten Werten. Die Prozentwerte beziehen sich auf die gespeicherten Auftragswerte. „100 %“ setzt beide Overrides zurück. Pause, Fortsetzen bei Hold:0 und Abbruch per Reset bleiben verfügbar.

Der bestehende Ablauf für Verbindung, automatische Referenzfahrt, Nullpunkt, Grenzprüfung und Rahmenfahrt bleibt erhalten. Die Neugestaltung öffnet keine Verbindung und startet keinen Laser automatisch.

## Prüfung

136 automatische Tests bestanden. Zusätzlich grafisch geprüft: vier Arbeitsbereiche, Radien im Werkzeugweg, Bézier-Griffe, Segmentteilen, numerische Knoten, mehrzeiliger Text und Tastaturfokus, Material speichern/anwenden sowie simulierte Telemetrie und Override-Anforderungen im Cockpit. Während dieser Prüfung wurden keine Befehle an die reale Maschine gesendet.
