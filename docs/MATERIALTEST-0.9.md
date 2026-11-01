# SteBurn 0.9.2 – Rahmenlicht, Liveparameter und Materialtests

## Ergänzungen in 0.9.2

Rahmen stoppen setzt eine Stoppanforderung; ausschließlich der Geräteworker sendet einmal Jog-Cancel und wartet auf zwei übereinstimmende Idle-Positionen. Erst danach werden weitere G-Code-Befehle gesendet und die nächste Fahrt freigegeben. Bei regulärer Fahrt wird zusätzlich das Ziel geprüft. Eine normale Rahmenfahrt mit Stoppen verändert keine Referenz- oder Nullpunktfreigabe. Reset, Alarm oder nicht bestätigte Kommunikation bleiben Gründe für eine erneute Referenzierung. Unter `user-data/device-traces` stehen Ablaufprotokolle mit Controllerantworten und Freigabegrund. Das Standardverhalten von GRBL ist in [Jogging](https://github.com/gnea/grbl/blob/master/doc/markdown/jogging.md) beschrieben; die konkrete Firmware muss praktisch geprüft werden.

Mausfahrt aktivieren: Vorbereitung → „Mausfahrt / Pointer“ oder im Materialtest → „Position auf Werkstück“ → „Mausfahrt / Pointer“. Ein Klick fährt den Kopf direkt an die angeklickte Position; die Testfläche wird in diesem Modus nicht verschoben. Eine bestätigte Position erscheint als Fadenkreuz. Ohne Pointerlicht bleibt der Strahl aus. Bei aktivem Pointerlicht wird am Ziel ein 0,15-s-Impuls mit der separat gewählten schwachen Leistung ausgegeben (Vorgabe 0,1 %, maximal 0,5 %, $31=0 und ausreichende Controllerauflösung erforderlich). Anfahrt ohne Strahl; M3, Zeitbegrenzung und M5 werden zusammen an den Controller übertragen. Auch ein schwacher Impuls kann Material markieren. „Rahmen stoppen“ beendet auch eine laufende Pointerfahrt.

Neue Muster (Version 3) verwenden für die Schrift konstante Leistung entlang der Schriftwege, statt die Leistung auf kurzen Wegen dynamisch zu reduzieren. Die Vorgabe ist nun 20 % bei 600 mm/min, weiterhin separat einstellbar. Es gibt keinen materialunabhängig geeigneten Wert: mit „Nur Beschriftung testen“ zunächst nur Schrift und Umriss an der gewählten Position prüfen; die Matrixfelder werden dabei nicht bearbeitet. Dieser Button öffnet das Cockpit, erst dessen Startbutton beginnt die Bearbeitung. Historische Testmuster behalten ihre ursprünglichen Parameter und Leistungsart.

„Zuordnung als Bild …“ speichert eine große PNG-Grafik mit C01–C15 und G01–G15, Leistung, Vorschub und Durchgängen je Feld. Damit bleiben auch bereits gebrannte Versuche ohne sichtbare Schrift auswertbar. Beim geladenen Versuch entsprechen die Zeilen und Spalten exakt dessen gespeicherten Werten; oben steht Schnitt, unten Gravur.

183 automatische Tests sowie der GUI-Ablauf Rahmen → Stopp → verschieben → Rahmen → Stopp → Pointer → Beschriftungsprobe → Materialtest ohne zusätzliche Referenzfahrt bestanden. Es wurde nur ein simulierter Controller verwendet; die reale Fehlerursache des gemeldeten Referenzverlusts ist damit noch nicht abschließend bestätigt.

## Ergänzungen in 0.9.1

Im Materialtest bietet „Position auf Werkstück“ eine Gesamtansicht der Maschinenfläche. Werkstückposition und -maße eingeben und das orange Testquadrat ziehen oder per Klick platzieren. X/Y bezeichnen die linke untere Ecke in Maschinenkoordinaten. Das verändert keinen Nullpunkt. Die vorhandene Zeichnung wird grau zur Orientierung gezeigt, aber nicht mitgelasert. Außerhalb des eingezeichneten Werkstücks erscheint eine rote Begrenzung; die Gerätefläche mit 5 mm Randabstand bleibt verbindlich geprüft. Werkstückmaße sind eine manuelle Orientierung, keine Vermessung.

Die quadratische Testgröße ist von 50 bis 300 mm einstellbar. Das gesamte Muster einschließlich Beschriftung wird geometrisch skaliert; Leistungen, Vorschübe und physischer Gravurabstand bleiben gleich. Größere Flächen verlängern den Test und können das Material anders erwärmen. Beim Wechsel von Position, Größe oder Testwerten entsteht ein neuer gespeicherter Versuch; der bisherige bleibt erhalten. Unveränderte Werte erhalten den Versuch mit seinen Bewertungen.

„Testfläche rahmen“ fährt genau den Testumriss wiederholt ab, „Rahmen stoppen“ beendet ihn positionsbewahrend. Für sichtbares Licht gilt die Einstellung unter Vorbereitung. Erst der gesonderte Start im Cockpit bearbeitet das Prüfmuster.

Die neue Beschriftung verwendet konventionelle, durchgehende Ziffern anstelle der Siebensegment-Ziffern. Vorschubangaben sind bei 50 mm Testgröße 1,8 statt 1,25 mm hoch, Leistungsangaben 1,9 statt 1,4 mm. Beim Vergrößern wachsen sie mit. Beschriftungsleistung und -vorschub sind separat einstellbar. Historische Muster werden bei erneutem Laden in ihrer ursprünglichen Version rekonstruiert.

Bei fehlender Verbindung oder Referenz wird der Start bereits vor dem Streaming gesperrt. Fehler während der Controllerprüfung erscheinen mit Originalursache und konkreter Empfehlung im Cockpit und Ereignisprotokoll. Fehlgeschlagene Aufträge speichern diese Angaben zusätzlich im Jobbericht. „05 Gerät / Verbindung“ führt unmittelbar zur Geräteverwaltung. Es wird keine automatische Referenzfahrt als Reaktion auf einen Fehler ausgelöst.

## Rahmenlicht

In Vorbereitung „Schwaches Rahmenlicht“ einschalten. Vorgabe: 0,1 %, einstellbar bis maximal 0,5 %. Standardmäßig bleibt es ausgeschaltet. Auch diese geringe Leistung kann Material markieren oder erwärmen; eine Garantie für spurenfreies Licht gibt es nicht. Sichtbarkeit hängt von Material, Controllerauflösung und Schutzbrille ab.

Die Anfahrt zum ersten Eckpunkt bleibt dunkel. Auf den Rahmenkanten wird M4 verwendet: dynamische Leistung nur während der Bewegung, M5/S0 an den Übergängen und beim Stoppen. Ein Umschalten während des Rahmenfahrens stoppt den aktuellen Jog kontrolliert und setzt dieselbe Kante mit der neuen Einstellung fort. Position und Referenz bleiben erhalten.

Voraussetzung ist $31=0; SteBurn verändert dafür keine Firmwareeinstellungen. Ein Wert unterhalb der Auflösung von $30 wird abgelehnt, niemals automatisch erhöht. Die interne Spindelübersteuerung wird vor dem Rahmenfahren auf 100 % gesetzt. Das Leistungsmaximum bezieht sich auf den programmierten S-Wert, nicht auf eine gemessene optische Leistung. GRBL-Verhalten: [Laser Mode](https://github.com/gnea/grbl/blob/master/doc/markdown/laser_mode.md).

## Cockpit

Vorschub: −250 / +250 mm/min. Zusätzlich wird die Umrechnung in mm/s angezeigt. Leistung: −5 / +5 Prozentpunkte, absolut zwischen 0 und 100 %. Beispielsweise wird aus 60 % durch einmaliges Plus 65 %. Die Werte gelten für folgende Bahnabschnitte. Bildintensitäten bleiben relativ zur gewählten Maximalleistung erhalten; Leerwege bleiben dunkel.

Jeder Klick wird sofort an den Streaming-Worker gegeben. Die Anzeige unterscheidet „angefordert“, „übermittelt“, „vom Controller angenommen“ und „im Bahnablauf bestätigt“. Der GRBL-Bewegungspuffer kann die Wirkung kurz verzögern. Eine Annahme allein wird nicht als Wirksamkeitsnachweis angezeigt. Die Bahnstatusbestätigung verwendet bestätigte Befehle und Positionsmeldungen; sie ist keine Messung von optischer Leistung oder mechanischem Istvorschub. Bei regulär vollständig beendetem Programm gelten angenommene Parameterbefehle als ausgeführt. Beim Abbruch bleiben ungeklärte Änderungen ausdrücklich unbestätigt beziehungsweise nicht angewendet.

„Statistik / Ereignisse“ zeigt Wert, Anforderungszeit, Controllerannahme und Bestätigung. Nach Ende wird zusätzlich ein JSON-Bericht unter `user-data/job-reports` gespeichert, einschließlich Zeit, Weg, Energieschätzung und Ereignisverlauf. Energie bleibt eine Schätzung anhand der unter Gerät hinterlegten optischen Nennleistung.

## Materialtest (Vorgabe 50 × 50 mm)

Materialien → „Materialtest …“. Fünf Leistungen und je drei Schnitt- und Gravurvorschübe einstellen; Listen mit Semikolon trennen. Durchgänge, Gravurabstand, Beschriftungsleistung, Beschriftungsvorschub, Position und Testgröße sind separat einstellbar. „Neues Prüfmuster erzeugen“ aktualisiert die Vorschau. Der Außenumriss der gesamten Geometrie entspricht exakt der gewählten quadratischen Testgröße, zusätzlich gilt der Maschinenrandabstand.

Das Muster ist immer gleich aufgebaut: oben 15 geschlossene Schnittrechtecke, unten 15 gefüllte Gravurflächen. Spalten variieren die Leistung, Zeilen den Vorschub. Werte werden als feste Vektorzeichen aufgebracht. Gravur und Beschriftung laufen vor den Schnitten; der Außenumriss wird nur markiert. Feldnummern C01–C15 und G01–G15 sind in Vorschau und Ergebnistabelle zugeordnet; ein Klick auf ein Feld öffnet dessen Bewertung. Die Beschriftungsleistung bei Bedarf passend zum Material wählen.

„Prüfmuster im Cockpit öffnen“ erstellt einen eigenständigen Auftrag. Die aktuelle Zeichnung wird weder ersetzt noch mitgelasert. Erst „Auftrag starten · Lasern“ startet die Bearbeitung. Die Plus/Minus-Übersteuerungen sind für diesen Kalibrierauftrag gesperrt, damit die eingetragenen Matrixwerte reproduzierbar bleiben; Pause, Fortsetzen und Abbruch sind weiterhin verfügbar.

Nach dem Versuch pro Feld die gemessene Tiefe, Durchtrennung, Qualität und Notizen eintragen. Diese Beobachtungen sind keine automatischen Sensormessungen. Die Daten bleiben unter `user-data/material-tests` gespeichert, lassen sich erneut laden und als CSV exportieren. Geeignete bewertete Felder können direkt als Materialprofil gespeichert werden; Test- und Feldkennung sowie die Bewertung bleiben im Profil hinterlegt. Unterschiedliche Holzarten, Beschichtungen oder Materialchargen können abweichende Ergebnisse liefern.

## Prüfung

175 automatische Tests bestanden, darunter Änderungen während laufenden Streamings, getrennte Annahme-/Bahnstatusbestätigung, Rahmenlichtbegrenzung und Abschalten, skalierte Geometrie, historische Muster, Schnitt-/Gravurreihenfolge und Ergebnisexport. Der GUI-Test prüft zusätzlich die Platzierung eines 100-mm-Musters, einen gesperrten Offline-Start und eine Controller-Zeitüberschreitung mit sichtbarer Abhilfe und gespeicherter Fehlerursache. Es wurde kein realer Laserauftrag gestartet. Sichtbarkeit, tatsächliche Materialtiefe und Verhalten der angeschlossenen Firmware benötigen den Liveversuch.
