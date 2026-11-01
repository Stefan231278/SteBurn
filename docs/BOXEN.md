# Boxen & Gehäuse – Steburn 0.4

Öffnen: **Module → Boxen & Gehäuse**. Das Modul wird erst beim Öffnen geladen
und benötigt keine Internetverbindung. Es sendet keine Maschinenbefehle.

## Bauformen

- Rechteckbox: Fingerzinken oder stumpfe Klebekanten. Offen, fest geschlossener
  Deckel oder lose aufliegender Deckel. Lose Deckel haben keine Führung/Rastung.
- Gefache in Rechteckboxen: Zeilen/Spalten, herausnehmbare Kreuzteiler mit
  komplementären Halbschlitzen. Keine Wandverzahnung der Gefache.
- Runde, vieleckige und abgerundete Behälter: horizontale Wandringe werden
  übereinander geklebt. Kein Biegen, keine Gehrung erforderlich. Materialverbrauch
  kann hoch sein. Vieleckbreite ist der Eckkreis-Durchmesser.

Bei Schichtboxen wird die Höhe auf ganze Lagen aufgerundet. Die Vorschau zeigt
Zielabweichungen und tatsächliche Innen-/Außenmaße. Ein fester und ein loser
Deckel haben im Schichtbau dieselbe Plattenkontur; die Verbindung erfolgt
entsprechend der gewählten Montage, nicht durch automatisch erzeugte Beschläge.

## Maße und Passung

Innen-/Außenmaße ausdrücklich wählen. Bei Innenmaßen addiert Steburn die
benötigte Materialstärke für Wände, Boden und gegebenenfalls Deckel. Die Höhe
beinhaltet bei Außenmaßen den Deckel. mm/Zoll können gewechselt werden;
Projekt und Schnittdateien bleiben in Millimetern.

Gemessene Materialstärke verwenden. Fingerbreite ist ein Zielmaß; für passende
Gegenstücke wird je Kante eine ungerade Anzahl gleicher Abschnitte verwendet.
Drei benachbarte Platten teilen sich auch die Eckbereiche ohne doppelte
Materialbelegung. Sehr kleine Kanten relativ zur Stärke werden abgewiesen.

Schnittspalt ist die volle gemessene Schnittbreite. Konturen werden um die
halbe Breite nach außen versetzt; Innenkonturen werden entsprechend kleiner.
Daher keine zweite Schnittspaltkorrektur im nachfolgenden Programm anwenden.
Gefachspiel verbreitert die Steckschlitze zusätzlich. Es ist kein allgemeiner
Presspassungsregler für Fingerzinken. Der Diodenstrahl kann richtungsabhängig
unterschiedliche Schnittbreiten haben; reale Passprobe in beiden Richtungen
vorsehen. Es werden keine Material-/Leistungswerte geraten.

## Vorschau, Platten und Export

Die 2D-Vorschau zeigt Teile der gewählten Schnittplatte. Das drehbare 3D-Schema
zeigt den nominalen Zusammenbau, optional als Explosionsansicht. Es ist kein
physikalischer Belastungs- oder Biegetest. Fingerzinken wurden geometrisch
auf gemeinsame Kantenbelegung geprüft; reale Fertigung noch nicht getestet.

Teile werden mit Abstand und 5 mm Rand auf die Projekt-Arbeitsfläche gepackt.
Drehung um 90° ist möglich. Wenn mehrere Platten nötig sind, entstehen mehrere
Seiten. Ein zu großes Einzelteil wird abgewiesen und niemals automatisch
verkleinert. Die einfache Reihenanordnung ist noch kein optimales Kontur-Nesting.

**Platte als SVG/DXF** exportiert genau die ausgewählte Platte in Millimetern.
Beschriftungen der Vorschau sind nur Anzeigen und keine zusätzlichen Gravuren.

## Übergabe ins Projekt

**Schnittteile übernehmen** erzeugt eine Ebene je Platte. Nur die erste ist
zunächst sichtbar. Alle neuen Ebenen haben Ausgabe AUS und Leistung 0, bis
Material, Bearbeitungsparameter und Konturen geprüft sind. Andere Projektobjekte
werden nicht entfernt oder umgestellt.

Die Teile einer Platte sind gruppiert. Zum Bearbeiten eines einzelnen Teils
über Rechtsklick die Gruppierung aufheben. Die zugehörige Modellkennung bleibt
bestehen. **Rechtsklick → Boxparameter bearbeiten** öffnet die gespeicherten Werte.
Regeneration ersetzt alle zu diesem Modell gehörenden Teile einschließlich
nachträglich veränderter oder duplizierter Modellteile. Sie wird vorher bestätigt.
Unabhängige Objekte und auf den Ebenen ergänzte fremde Objekte bleiben erhalten.

Neu erzeugte Seiten können sich mit bestehenden Projektobjekten überlagern;
vor einer Ausgabe die gewünschten Ebenen gezielt sichtbar/ausgabefähig setzen.
Einheiten und Konstruktionsparameter bleiben im .steburn-Projekt gespeichert.

## Noch nicht enthalten

Scharnier- und Schiebedeckelmechanik, Biegeschlitze, beliebige Gefachaufteilungen,
Schubladenschränke, stapelbare Behälter, CNC-Dogbones, 3D-Druckexport und automatische
Parameterrekonstruktion aus MakerCase-Dateien. Die vollständige öffentliche
Funktionsaufnahme mit Originalquellen steht in MAKERCASE-RECHERCHE.md.
