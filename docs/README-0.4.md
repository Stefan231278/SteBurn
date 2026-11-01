# Steburn 0.4.0

Modularer Windows-Editor für Atomstack A40 Pro, 400 × 400 mm.
Diese Version enthält Editor, Simulation, optionalen Relief-Assistenten und ein
Laserfenster für kontrollierte physische Testläufe mit ausgeschaltetem Strahl.
Ein vollständiger LightBurn-Ersatz ist dies noch nicht.

## Start und Aktualisierung

1. ZIP in einen neuen Ordner entpacken. Alte Version und Projekte behalten.
2. Falls nötig Python 3.11 oder neuer mit Tcl/Tk installieren.
3. Einmal `Einrichten-Steburn.bat`, dann `Start-Steburn.bat` starten.
4. Beispiel: `examples/Steburn-0.3-Beispiel.steburn` öffnen.

Keine fertige Windows-EXE enthalten. Bei bestehender Einrichtung können `main.py`,
`steburn` und `assets` ersetzt werden; keine neuen Bibliotheken erforderlich.
Neue Projekte werden als Schema 3 gespeichert, damit ältere Steburn-Versionen
neue Objektparameter nicht versehentlich ignorieren. Schema 1/2 wird gelesen;
beim ersten Speichern eine neue Datei verwenden. Alte Dateien bleiben bis zum
expliziten Speichern unverändert. Das Bild-/SVG-Exportformat ersetzt kein
Steburn-Projekt und enthält nicht alle Bearbeitungsparameter.

## Neu in 0.4

**Eine obere Leiste:** Gestalten, Simulation, Rahmen und Lasern stehen neben
Dateiaktionen und Logo. Die zweite Zeile über dem Arbeitsfenster entfällt.
Bei schmalen Fenstern liegen Nebenaktionen im Menü Mehr; Hauptaktionen bleiben
direkt erreichbar. Werkzeug feststellen sitzt bei den Zeichenwerkzeugen.

**Module → Boxen & Gehäuse:** Eigenständiger parametrischer Boxengenerator mit
Rechteckboxen, Fingerzinken/Klebekanten, Gefachen, offenen/festen/losen Deckeln
sowie runden, polygonalen und abgerundeten Schichtboxen. Innen-/Außenmaß,
Materialstärke, mm/Zoll, Fingerbreite, Schnittspalt und Teileabstand sind einstellbar.
Mit drehbarem 3D-Schema, Mehrplattenlayout, SVG/DXF-Export und Übergabe als
bearbeitbare Schnittteile. Gespeicherte Parameter per Rechtsklick erneut öffnen.

Neue Teile werden mit Ausgabe AUS und Leistung 0 übernommen. Mechanische
Passproben bleiben notwendig. Details: `docs/BOXEN.md`; recherchierter
MakerCase-Funktionsumfang und Unterschiede: `docs/MAKERCASE-RECHERCHE.md`.
Dies ist keine vollständige Umsetzung sämtlicher MakerCase-Generatoren.

Zum Aktualisieren `main.py`, `steburn` und `assets` ersetzen oder neu entpacken.
Keine zusätzlichen Python-Abhängigkeiten gegenüber 0.3.1.

## Oberfläche in 0.3.1

- Schaltflächen mit abgerundeten Flächen, sichtbaren Rändern, Hover-,
  Druck-, Tastaturfokus- und deaktivierten Zuständen. Aktives Werkzeug blau,
  primäre Aktion orange, Abbruch im Auftragsfenster rot.
- Mouseover-Hilfen nach ca. 0,55 Sekunden erklären Zweck und Anwendung aller
  sichtbaren Schaltflächen. Bei Tastaturfokus werden Hilfen ebenfalls angeboten.
- **Lasern** öffnet das Auftragsfenster ohne Maschinenbewegung. Erst der separate
  Button **Auftrag starten · Testlauf** startet nach Bestätigung die aktuell
  freigegebenen Bewegungen mit ausgeschaltetem Strahl. Echte Gravurstarts bleiben
  gesperrt; die Umbenennung ändert keine Maschinenfreigabe.
- SB-Logo in der oberen Symbolleiste, mehrgrößige Fenstericons und explizite
  Windows-App-Kennung vor dem Fensterstart. Icon-Dateien zusätzlich im
  steburn-Paket, damit sie beim Kopieren des Programmordners erhalten bleiben.
- Icon-Einbindung und Logo wurden in der grafischen Testumgebung geprüft.
  Das native Verhalten in Windows-Titelleiste, Alt+Tab und Taskleiste muss auf
  dem Laptop bestätigt werden. Eine alte angeheftete Python-Verknüpfung kann
  weiterhin ihr eigenes Symbol zeigen.

Aktualisierung: Steburn vollständig schließen; `main.py`, den Ordner `steburn`
und `assets` aus dieser Version ersetzen oder das Paket neu entpacken. Keine
neuen Abhängigkeiten, bei vorhandener 0.3-Umgebung keine erneute Einrichtung nötig.

## Neu in 0.3

- Nach Zeichnen/Import/Text/Laserziel standardmäßig Auswahlmodus. Werkzeug
  optional feststellen; Esc aktiviert immer Auswahl.
- Auswahlrahmen auf freier Fläche: vollständig eingeschlossene Objekte wählen;
  Strg fügt hinzu. Gruppierte Objekte werden gemeinsam ausgewählt.
- Kontextmenüs auf Objekten, Objektliste und Ebenen. Keine physischen Fahrten im
  Rechtsklickmenü. Ebenenreiter aktivieren nur; Zuordnung ausdrücklich im Menü.
- Register **Bearbeitung**: Objekt übernimmt Ebenenwerte oder überschreibt sie.
  Schneiden, flächiges Gravieren und Konturmarkieren sind ausdrücklich wählbar.
  Schneiden und Konturmarkieren erzeugen beide Konturbahnen; Parameter machen
  den physikalischen Unterschied. Der Name einer Ebene ist keine Steueranweisung.
- Gravurfüllung als Schraffur auf der Fläche. Bildschirmdarstellung vereinfacht;
  Simulation berechnet gewählte Bahnen. Kreuzschraffur und Winkel für Vektoren,
  Punkte als kurze bewegte Striche (keine stationären Brandpunkte).
  Vollfläche und Schraffur werden durch Scanbahnen mit eingestelltem Abstand
  ausgeführt; die Bezeichnung allein ändert keinen Materialabtrag.
- Bitmap: Graustufenraster oder punktförmiges Schwarzweiß-Dithering. Winkel und
  Kreuzschraffur für Bitmaps noch nicht unterstützt. Kein stillschweigender
  Rechteckschnitt, wenn bei einem Bitmap Schneiden gewählt wird.
- Sichtbare Laserleistung bei Ausrichtung in der neuen Oberfläche gesperrt,
  bis Material-/Strahlprüfung erfolgt ist.
- SB-Icon in Fenster und `assets/Steburn.ico` für Windows-Verknüpfungen.

## Gerätesicherheit

LightBurn und andere Portnutzer schließen. COM4 / 115200 prüfen. Verbinden liest
Firmware und Parameter; es bestätigt keine Position. Danach **Referenzfahrt
  ausführen ($H)** aufrufen und erst nach realer störungsfreier Ankunft links
vorne die Sichtprüfung bestätigen.

Steburn verlangt $20/$21/$22=1, $13=0, $32=1 und passende 400 × 400-mm-Grenzen.
Es verändert diese Einstellungen nicht automatisch. Neustart, Alarm und
Zeitüberschreitung sperren Fahrten. Reset kann beim A40 Pro 0/0 anzeigen,
obwohl der Kopf real noch weit davon entfernt steht! Neu verbinden und
referenzieren. Diagnose: `docs/MASCHINENTESTS-2026-10-16.md`.

Alle Testlauf-/Ausrichtziele müssen im vorläufigen Bereich 5–395 mm liegen.
Das ist ein zusätzlicher Randabstand und **keine vermessene Maschinenfreigabe**.
Kein softwareseitiger Schutz garantiert Sicherheit bei Schrittverlusten,
defekten Sensoren oder verschobenem Gerät. Hardware-Abschaltung erreichbar halten.

## Lasern

**Testlauf ohne Strahl**: exakten Projektplan vorab prüfen und mit M5/S0 fahren;
Geschwindigkeit maximal 600 mm/min vor Override. Keine echten Gravurstarts.
Auftragssnapshot bleibt von späteren Editoränderungen unabhängig.

Pause, Fortsetzen und Reset verwenden die geprüften direkten Steuerbytes.
Fortsetzen ist erst bei Hold:0 verfügbar. Vorschub- und Leistungs-Override zeigen
Controllerwerte; bei Testlauf bleibt der Strahl aus. Fortschritt zählt tatsächlich
abgeschlossene Segmente, keine lediglich übertragenen Befehle. Einzelne Segmente
werden jeweils bis Idle bestätigt. Dies ist bewusst noch kein schneller
Produktionsstreamer. Restzeit ist eine grobe Schätzung ohne Beschleunigungsmodell.

Während physischem Auftrag einschließlich Pause fordert der ausführende Thread
Windows-Wachhalten an. Bildschirm darf ausgehen. Freigabe erfolgt bei Ende/Fehler.
Bei Akkustand <=15 % ohne Netzversorgung wird Pause angefordert. Ladezustand und
Netzversorgung erscheinen im Fenster; unbekannte Werte werden nicht als 0 %
interpretiert. Windows-API und Akkuverhalten sind hier mit Testdoubles geprüft,
**noch nicht auf Stefans Windows-Laptop**. Manuelles Schlafen, Zuklappen, leeren
Akku und USB-Verlust verhindert diese Funktion nicht zuverlässig. Laptop geöffnet
und verbunden lassen. USB-Verlust kann nicht über die bereits unterbrochene
Verbindung sicher einen Halt auslösen. Keine unbeaufsichtigte Strahlbearbeitung.

**Ab Prozent** ist derzeit eine Vorschau am Segmentanfang anhand geschätzter
Planzeit. Keine physische Wiederaufnahme nach Ausfall; dazu fehlen verifizierte
Fortschrittspunkte und Wiederherstellung der realen Werkstückposition.

## Optionaler Relief-Assistent

Genau ein Bild wählen → Relief → Assistent. Lokale Analyse von Bildgröße und
Kontrast, Interpretation dunkel = tief (umkehrbar), Material, gewünschte Tiefe
und 2–16 Schichten. Kein KI-Dienst angeschlossen. Keine Rekonstruktion sicherer
3D-Geometrie aus einem Foto; Grautöne sind zunächst eine Gestaltungsinterpretation.

Schichten werden als einzelne, deckungsgleiche Bitmapobjekte in einer eigenen
Ebene mit **Ausgabe AUS** übernommen; das Original bleibt bestehen. Schichten
in der Objektliste einzeln wählen und über Rechtsklick simulieren. Vor späterer
Bearbeitung Original und Schichten bewusst getrennt verwalten, sonst droht
Doppelbearbeitung. Die gewünschte Millimetertiefe ist unkalibriert und steuert
noch keinen belastbar vorhergesagten Materialabtrag. Keine automatischen
Produktionsparameter aus einer geratenen Tiefe ableiten.

## Tests und Ausbau

`python -m unittest discover -s tests`
Grafisch: `python tests/gui_smoke.py` und `python tests/gui_v03.py`.
Die grafischen Skripte erzeugen Beispiel-/Dokumentationsdateien im Projektordner.

Geometrie, Objektparameter, Geräteprotokoll, Windows-Energieverwaltung und
Oberfläche liegen in getrennten Modulen. Details: `docs/ARCHITEKTUR-0.3.md`.
Importgrenzen siehe `docs/IMPORTFORMATE.md` (weiterhin gültig).
