# Prüfstand Steburn 0.3.1

- Präsentationsprüfung bestanden: Buttonflächen, Hervorhebung des aktiven
  Werkzeugs, vollständige Hilfetextabdeckung aller Hauptfenster-Schaltflächen,
  Tooltip-Anzeige/Schließen/Zerstören, SB-Logo und Lasern-Navigation ohne
  Portöffnung oder Jobstart.
- 95 automatisierte Tests bestanden, Python 3.12 unter Linux.
- Syntaxprüfung der Python-Module bestanden.
- Bestehende grafische Bedienprüfung: Editor, Mehrfachauswahl, Undo/Redo,
  Gruppieren, Transformieren, Bildgriffe, Seitenverhältnis, Schriftwahl,
  scrollbare Panels und Simulation bestanden.
- Neue grafische Bedienprüfung: Werkzeug-Rücksprung/Feststellen, Esc,
  Rahmenauswahl, Objektgravur, Kontextmenü, getrennte Ebenenaktivierung,
  Laserfenster und Relief-Schichtübernahme bestanden.
- Simulierte Controllerprüfungen: Reset vor Status/ok, Alarm, Timeout,
  unbekannte Referenz, Soft-Limit-Anforderung, Randabstand, Homing,
  direkte Bytes, vollständige Pause, Testlauf ohne Emission,
  Verbindungsfehler, niedriger Akku und Windows-Awake-Fehlerfälle bestanden.
- Materialbearbeitung mit Steburn 0.3 nicht getestet oder freigegeben.
- Windows-Oberfläche, echtes Windows-Wachhalten und Akkuwerte noch nicht am
  Laptop getestet. Die Win32-API wurde mit Testdoubles geprüft.
- Maschinenversuche vom 16.10. wurden mit LightBurn/PowerShell durchgeführt,
  nicht mit dieser neuen Steburn-Version. Sie sind separat protokolliert.

Befehle im Projektordner:

    python -m unittest discover -s tests
    python -m compileall -q steburn main.py
    python tests/gui_smoke.py
    python tests/gui_v03.py
    python tests/gui_presentation.py

Grafische Prüfungen benötigen einen Desktop bzw. Displayserver. Sie erstellen
Beispielprojekte und Screenshots im Projektordner. Keine Tests öffnen COM4
oder bewegen ein echtes Gerät.
