# SteBurn 0.8 – Überarbeitung nach dem Livetest

## Schnitt und Freihand

Die alte Ausführung wartete nach jedem kurzen Segment auf Idle. Das leerte den Bewegungsplaner und ließ auch zusammenhängende Konturen abschnittsweise anhalten. Der neue Jobrunner überträgt mit Character-Counting und einem konservativen Empfangsfenster von höchstens 96 Zeichen. Er liest Befehlsbestätigungen und Statusmeldungen in einem einzigen Geräteworker getrennt aus. Eine Bestätigung allein wird nicht als physisch erledigter Weg gezählt.

Schnittkonturen verwenden M3 (konstante programmierte Leistung), Gravur und Markierung M4 (dynamische Leistung). S-Werte werden zusammen mit der Bewegung gesetzt. Innerhalb zusammenhängender Konturen gibt es keine absichtlich eingefügten Idle-Wartepausen. Das PWM-Verfahren des Controllers und die reale Mechanik bleiben unverändert. Freihand-, Linien- und Bézierwerkzeuge übernehmen auf einer Schnittebene den Schnittmodus.

Grundlage: [GRBL-Streaming](https://github.com/gnea/grbl/blob/master/doc/markdown/interface.md), [GRBL-Lasermodus](https://github.com/gnea/grbl/blob/master/doc/markdown/laser_mode.md).

## Rahmen und Referenz

Die wiederholte Rahmenfahrt ist jetzt ein laserfreier Jog-Ablauf. Stopp sendet Jog-Cancel (0x85), wartet auf Idle und prüft die frische Position. Referenz und Nullpunkt bleiben erhalten; danach kann derselbe Controller direkt einen Job starten. Bei einer Störung gilt diese Freigabe nicht.

„Neu referenzieren“ führt die Referenzfahrt auf dem bestehenden Anschluss aus. Nach einem vorherigen Reset synchronisiert es das Protokoll neu, ohne den COM-Port zu schließen. Die Statusabfrage im Hintergrund verwendet einen separaten, nicht blockierenden Sperrversuch und setzt die Oberfläche nicht mehr regelmäßig auf „Geräteauftrag läuft“.

## Ende, Abbruch und Notstopp

- **Reguläres Ende:** Alle Wege müssen fertig und das Endziel bestätigt sein. Danach M5/S0 und Rückfahrt auf Maschinenposition X0/Y0; anschließend Jobabschluss und Statistik.
- **Abbrechen + Referenzposition:** Kontrollierter Feed-Hold, bestätigter Stillstand, Reset zum Leeren des alten Auftragsplans und automatische Referenzfahrt. Es wird nicht behauptet, ein Reset im laufenden G-Code erhalte die Position zuverlässig.
- **Notstopp / Reset:** Sofortiger Reset, Position ungültig. Keine automatische Rückfahrt.
- **Alarm oder Kommunikationsfehler:** Fehlerzustand und keine automatische Fahrt. Erneutes Referenzieren ist eine ausdrückliche Bedienaktion.

Pause und Fortsetzen referenzieren nicht. Ein Fortsetzen-Wunsch bleibt vorgemerkt, bis Hold:0 bestätigt ist, und wird dann mit dem GRBL-Cycle-Start fortgesetzt. Der Cockpitbutton wechselt entsprechend zwischen Pause und Fortsetzen.

## Cockpit und Parameter

„04 Lasern“ öffnet direkt das Cockpit. Das Fenster wird vom Betriebssystem auf den aktuellen Monitor maximiert; Start, Pause/Fortsetzen und Abbruch bleiben unten erreichbar. Unter „05 Gerät“ liegen nur Verbindungs-, Referenzierungs- und Diagnosefunktionen sowie die optionale optische Nennleistung.

Geschwindigkeit wird in **mm/s** eingestellt und für GRBL in mm/min umgerechnet. Leistung ist **absolut 0–100 %**, nicht ein Prozentfaktor mit der alten 10–200-%-Grenze. Zu Beginn erscheinen die tatsächlichen Planwerte, beispielsweise 60 % statt 100 % Override. Ohne manuelle Änderung bleiben unterschiedliche Planwerte je Objekt erhalten. „Planwerte wiederherstellen“ hebt manuelle Vorgaben wieder auf.

Änderungen wirken nach kurzer Eingabeverzögerung auf folgende Bahnabschnitte. Bereits gepufferte Bewegungen werden nicht nachträglich umgeschrieben. Lange Geraden werden ohne Halt in kurze Abschnitte unterteilt, um die Eingriffslatenz zu begrenzen. Bilder behalten die relativen Helligkeitswerte innerhalb der eingestellten maximalen Leistung. 0 % erzeugt S0-Wege.

## Statistik

Das Cockpit zeigt Laufzeit, Pausenzeit, Fahrweg in mm und Energie als Schätzung. Bei vollständigem Job kann der Bearbeitungsweg aus dem bestätigten Plan bestimmt werden; Rückfahrten und vorzeitig abgebrochene Wege verwenden Statuspositionen als Näherung.

Für Energie in Joule und Wh ist unter „05 Gerät“ die **optische Nennleistung in Watt** einzutragen. Ohne diese Angabe erscheint ein entsprechender Hinweis. Die Schätzung integriert gemeldete Leistung während Run und zählt Pausen nicht als Laserenergie. Sie ist weder eine Messung der tatsächlichen optischen Energie noch des elektrischen Verbrauchs.

## Direkte Änderungen und schnelle Modi

Gültige Eingaben an Geometrie, Text, Ebenen, Bearbeitungswerten, Radien, Knoten und numerischer Drehung werden nach etwa 350 ms übernommen; Fokuswechsel, Speichern und Jobstart übernehmen ausstehende gültige Eingaben ebenfalls. Unvollständige oder ungültige Zahlen werden nicht gespeichert und erzeugen keinen Bestätigungsdialog. Die alten Übernehmen-Schaltflächen sind ausgeblendet. Undo bleibt verfügbar.

Ein Klick auf einen Farbreiter unten weist die ausgewählten entsperrten Objekte der entsprechenden Ebene zu und entfernt bisherige eigene Bearbeitungswerte dieser Objekte. So wechselt gravierter Text mit einem Klick auf Schnitt wirklich in den Schnittmodus einschließlich dessen Leistungs-/Vorschubwerten. Ohne Auswahl wird nur die aktive Ebene gewechselt. Rechtsklick bietet weiterhin die getrennten Ebenenaktionen. Bitmaps werden nicht stillschweigend als rechteckige Schnittkontur ausgegeben.

Materialbibliothek speichern und der transaktionale Bildimport behalten ihre ausdrücklichen Speicher-/Übernahmeaktionen; sie verändern mehrere projektübergreifende Daten beziehungsweise übernehmen neue Bilddateien.

## Dateiformat und Prüfung

Format 4 ergänzt eine eindeutige Operation je Ebene. Ältere Formate 1–3 werden geladen und beim Speichern aktualisiert. Vor einem Wechsel zurück auf eine alte Programmversion eine unveränderte Projektkopie behalten.

155 automatische Tests bestehen, einschließlich eines simulierten GRBL mit Zeilenbestätigungen, begrenztem Empfangsfenster, Schnitttext, vollständigem Pause-/Fortsetzen-Zyklus, normalen und abgebrochenen Rückfahrten, Alarmbehandlung, Rahmenstopp und erneuter Referenzierung auf derselben Verbindung. Grafisch geprüft wurden automatische Text-/Geometrie-/Ebenenänderungen, schnelle Moduswechsel, mm/s und absolute Leistung, Monitoranpassung sowie ein vollständiger simulierter Job mit Pause, Fortsetzen und Abschlussstatistik.

Die Überarbeitung wurde ohne Befehle an den angeschlossenen Laser geprüft. Der reale Nachtest mit Material bleibt erforderlich; ein bestandener Simulationstest bestätigt keine mechanische Schnittqualität.
