# Atomstack A40 Pro – Inbetriebnahmeprotokoll, 16. Oktober 2026

Befunde beruhen auf vom Benutzer vor Ort beobachteten Fahrten und übermittelten
Controllerantworten. Keine direkte USB-Verbindung aus der Entwicklungsumgebung.
Keine Strahlbearbeitung ausgeführt. Keine vollständige Maschinenfreigabe.

## Gerät und Einstellungen

Windows, COM4, 115200 Baud. Arbeitsfläche laut Firmware 400 × 400 mm.
USB-Firmware `[VER:1.1h.20221101:]`, Optionen `[OPT:VZHD0LI,254,255]`.
Referenzfahrt real links vorne; positive X-Richtung rechts, positive Y hinten.
G54 aktiv, alle angezeigten G54–G59/G92/TLO-Versätze null. Startblöcke leer.
$13=0, $30=1000, $31=0, $32=1, $21=1, $22=1, $23=3, $27=1.
$130=400, $131=400, $132=200. Z wurde nicht bewegt oder geprüft.
$110=30000, $111=6000; Beschleunigungen $120/$121=1000.
$35=1 ist herstellerspezifisch; Bedeutung nicht verifiziert, nicht verändern.
$20 wurde von 0 auf 1 geändert. Speicherung nach Ausschalten bestätigt.

## Ausgeführte Prüfungen

| Prüfung | Beobachtung | Bewertung / Grenze |
| --- | --- | --- |
| Kleine X/Y-Fahrten | X=10/Y=5 erreicht, ruhig und sauber | Richtung und kleine Fahrten bestätigt, keine Präzisionsmessung |
| 5 × 5-mm-Quadrat | Rückkehr bestätigt | Sichtprüfung; kein Messprotokoll |
| Innenbereich | 50/50, 200/50 und 200/200 erreicht | Y-Fahrt ausdrücklich als ruhig bestätigt; äußere Nutzfläche nicht vermessen |
| Untere X-Grenze | Jog X=-0,1: error:15; unverändert 5/5 | Logische Jog-Grenze geprüft |
| Untere Y-Grenze | Jog Y=-0,1: error:15; unverändert 5/5 | Logische Jog-Grenze geprüft |
| Obere X-Grenze | G1 X400,1 im bestätigten Check-Modus: ALARM:2 | Kein Nachweis der mechanisch sicheren X=400-Position |
| Obere Y-Grenze | G1 Y400,1 im Check-Modus: ALARM:2 | Kein Nachweis der mechanisch sicheren Y=400-Position |
| Pause in LightBurn | Hold:0 bestätigt | Fortsetzung über Konsoleneingabe blieb ungeklärt; keine Diagnose eines Firmwaredefekts |
| Direktzugriff PowerShell | COM4 nach Freigabe erreichbar | Ein frühes Skript verlor seinen Variablen-Gültigkeitsbereich; kein Gerätefehler |
| Direkte Pause | Hold:1, anschließend dreimal Hold:0 bei X=9,038 | Vollständiges Anhalten erst bei Hold:0 annehmen |
| Direkte Fortsetzung | Byte 0x7E, Run und steigende X-Position; Ende Idle X=20 | Ohne Strahl bestanden |
| Vorschub-Override | 110 %: FS=66; 100 %: FS=60 | Bei geplantem F60; Byte 0x91/0x90 |
| Leistungs-Override | Ov:100,100,110; anschließend 100,100,100 | Nur Register-/Protokolltest bei M5/S0; optische Wirkung ungeprüft |
| Reset während Fahrt | ALARM:3, Starttext, danach Idle und MPos 0/0 | Reale Position blieb bei ca. X=44! Referenz zwingend ungültig |
| Erneutes $H | Reale Referenzecke erreicht, ok und Idle 0/0 | Wiederherstellung bestätigt |

Einige frühere Beobachtungen nach ALARM:2 deuteten auf automatische Referenzierung.
Das ist kein zuverlässiges generelles Verhalten: Der gezielte Resetversuch
belegt Positionsverlust ohne reale Referenzfahrt. Nie aus Idle/0/0 ableiten,
dass referenziert wurde.

## Bildschirm und Offline-Betrieb

Bildschirm nach erneutem Anschließen betriebsfähig. Kennung Engraver_15492.
Anzeige: Working Size X400/Y400; Firmware Aug 22 2023 V1.365.
Dies ist die Anzeige des Bildschirm-/Offline-Systems, nicht die USB-GRBL-Version.
Carve-Menü fordert TF-Karte an. Keine Datei geladen oder ausgeführt.
Auf Benutzerwunsch zurückgestellt: Steburn soll Windows bei Netz- und Akkubetrieb
während Jobs wach halten. Das verhindert keinen leeren Akku, manuellen Schlaf,
USB-Verlust oder sämtliche Zuklappaktionen.

## Verbindliche Softwarefolgen

- Kein manueller Bestätigungsknopf allein darf eine unbekannte Position freigeben.
- Jede Verbindung, jeder Starttext, Alarm oder Kommunikationsfehler hebt die
  Positionsfreigabe auf. Ein eigener erfolgreicher $H-Zyklus plus Sichtprüfung
  ist erforderlich. Diese Freigabe wird nicht im Projekt gespeichert.
- Controllerparameter $20/$21/$22 müssen 1 sein; mm, Laserbetrieb,
  Leistungsskala und Arbeitsfläche prüfen.
- Alle Ziele vor Beginn prüfen, nicht erst einzelne Segmente während der Fahrt.
  Vorläufig 5 mm Randabstand; keine Behauptung einer vermessenen Nutzfläche.
- Steuerbytes direkt senden; Pause erst bei Hold:0, Fortsetzung erst nach
  Zustandsbestätigung. Reset ist kein Hardware-Notaus.
- Nur ein Worker liest seriell. Während physischer Jobs Windows wach halten,
  auch in Pause. Bei Akku <=15 % ohne Netzversorgung Halt anfordern.
- Physischer Testlauf und Produktionsjob sind getrennt. Aktuell keine Freigabe
  echter Strahlbearbeitung im neuen Jobfenster.

## Noch offen

Mechanische Nutzfläche samt Reserven und Riemen-/Kabelwegen vermessen;
Hardware-Endschalter identifizieren und elektrische Funktion ohne Kollision
prüfen; Strahl-Aus-Verhalten bei Pause, Abbruch und Kommunikationsverlust;
sichtbare Ausrichtleistung an Material; Gravurqualität und Fokus;
Windows-Wachhalten an Netz/Akku und Wechsel; Akkuwarnung auf echtem Windows;
Produktionsstreaming einschließlich Ausfall; belastbare Fortschrittspunkte;
Relief-Materialkalibrierung. TF-/Offline-Tests zurückgestellt.
