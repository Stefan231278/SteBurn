# SteBurn 0.5 – Livebetrieb

Start: `Start-Steburn.bat` in diesem Projektordner. Die alte Version unter Downloads bleibt unverändert.

- Touchpad: Zwei Finger verschieben die Arbeitsfläche. Strg + Scrollen zoomt, Shift + Scrollen verschiebt horizontal. Seitenleisten unterstützen auch kleine Scrollschritte über Eingabefeldern.
- Das Fenster startet maximiert. Kompakte Eingabezeilen passen auf dem geprüften Bildschirm (1440 × 810 logische Pixel) ohne vertikales Scrollen in alle Hauptregister. Kleinere Fenster behalten Scrollleisten und das Menü „Mehr“.
- Oben rechts: grüner Punkt bei bestätigter Kommunikation, sonst rot. Im Leerlauf wird alle zwei Sekunden geprüft.
- Laserregister: COM5, 115200 Baud. „Verbinden + Referenzfahrt“ liest das Geräteprofil, führt $H aus und setzt danach G54 und G92 auf Nullversatz. Nullpunktfreigabe erst nach erfolgreicher Prüfung. Der Verbindungsbutton löst damit sofort reale Bewegung aus.
- „Rahmen“ fährt das umschließende Rechteck der Auswahl (sonst der Ausgabeobjekte) wiederholt ohne Strahl. „Rahmen stoppen“ stoppt per Controller-Reset; vor weiteren Fahrten erneut verbinden/referenzieren.
- „Lasern“ öffnet die Auftragsansicht. „Auftrag starten · Lasern“ startet direkt mit den gespeicherten Leistungs- und Geschwindigkeitswerten. M4 regelt die Leistung dynamisch; Leerfahrten verwenden S0. Kein zusätzlicher Bestätigungsdialog.
- Referenzprüfung, Controllergrenzen, Arbeitsfläche und der bestehende Randabstand von 5 mm bleiben Voraussetzungen für die Ausgabe. Nach Alarm, Reset oder Kommunikationsfehler wird die Positionsfreigabe aufgehoben.
- Geräteantworten und Fehler erscheinen im Status statt in zusätzlichen Antwortfenstern. Speichern-/Dateiauswahl und Schutz vor ungespeicherten Änderungen bleiben erhalten.

Prüfung: 125 automatische Tests bestanden, zusätzlich GUI-Prüfung aller Hauptregister, Scrollereignisse, Verbindungsanzeige und Auftragsfenster. Die Änderungen wurden ohne Befehle an den realen Laser getestet; der tatsächliche Materialtest steht noch aus.
