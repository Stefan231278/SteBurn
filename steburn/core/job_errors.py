"""Actionable job diagnostics without issuing device commands."""
def remedy(error,device):
    message=str(error); lower=message.lower()
    if not device.connected or any(s in lower for s in ('nicht verbunden','kein gerät','could not open port','permissionerror','access is denied','zugriff verweigert')):
        return '05 Gerät öffnen → Ports suchen → aktuellen Anschluss wählen → Verbinden + Referenzfahrt. USB-Verbindung und Stromversorgung prüfen; andere Programme müssen den Anschluss freigeben.'
    if any(s in lower for s in ('referenz','homing','nullpunkt','ursprung','neustart','abgebrochen','nullversatz','koordinatenversatz')):
        return '05 Gerät öffnen → Neu referenzieren. Falls der Controller nicht antwortet: Ports suchen und Verbinden + Referenzfahrt. Anschließend den Auftrag erneut starten.'
    if any(s in lower for s in ('antwort','timeout','zeitüberschreitung','serial','disconnected','frischer controllerstatus')):
        return 'USB und Stromversorgung prüfen. Unter 05 Gerät Ports suchen, Anschluss wählen und Verbinden + Referenzfahrt ausführen. Auftrag erst nach bestätigter Referenz erneut starten.'
    if any(s in lower for s in ('innenbereich','randabstand','arbeitsfläche','auftragsziel','arbeitsposition')):
        return 'Position und Größe des Auftrags prüfen: vollständig innerhalb der Gerätefläche mit mindestens 5 mm Randabstand. Projektmaße und Geräte-Arbeitsfläche müssen übereinstimmen.'
    if any(s in lower for s in ('alarm','idle','zustand')):
        return '05 Gerät öffnen und Controllerstatus prüfen. Ursache des Alarms beziehungsweise der laufenden Bewegung beheben; anschließend neu referenzieren und Auftrag erneut starten.'
    if '$' in message or 'controllerparameter' in lower:
        return 'Unter 05 Gerät die Diagnose prüfen. Erforderliche Firmwarewerte laut Fehlermeldung kontrollieren; SteBurn verändert sie nicht automatisch.'
    return 'Auftragswerte und Ausgabeobjekte prüfen. Unter 05 Gerät Verbindung und Diagnose kontrollieren. Die genaue Ursache steht oben und im Jobbericht.'
