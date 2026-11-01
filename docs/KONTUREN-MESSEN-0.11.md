# SteBurn 0.11.1 – Konturen, Messung und Ebenenfolge

## Knoten und Linien

Im Knotenmodus mehrere Knoten mit einem Fangrahmen oder Shift/Strg auswählen. Einen ausgewählten Knoten ziehen, um die Knotenauswahl gemeinsam zu verschieben. Entf oder „Löschen“ entfernt die ausgewählten Knoten, auch über mehrere ausgewählte Objekte hinweg. Eine geschlossene Linie wird wieder geschlossen; eine Kontur mit zu wenigen verbleibenden Knoten entfällt. Die Aktion ist mit Strg+Z rückgängig zu machen. Das Entfernen eines Béziergriffs setzt ihn auf seinen Anker zurück.

Gerade Linien haben im Auswahlmodus genau zwei Endpunktgriffe. An ihnen lässt sich jeweils ein Ende direkt verschieben; Ziehen an der Linie verschiebt sie als Ganzes. Ein Rahmen- und Drehgriff wird nicht angezeigt. Neue Linien auf einer Gravurebene verwenden Konturmarkierung; auf einer Schnittebene behalten sie Schnitt als Bearbeitungsart.

Bei aktiviertem „Fangen“ wird der geometrisch nächste vorhandene Knoten innerhalb von 10 Bildschirmpixeln bevorzugt. Gibt es dort keinen Punkt, gilt das eingestellte Raster beziehungsweise der Hilfslinienfang. Ein Kreis zeigt das Fangziel. Mit Alt lässt sich der Fang für die aktuelle Bewegung aussetzen. Ausgewählte Knoten werden beim Verschieben nicht an ihre eigenen vorherigen Positionen gefangen.

## Offene Konturen verbinden

Zwei offene Konturen auswählen oder im Knotenmodus genau zwei offene Endknoten markieren beziehungsweise einrahmen. Der Fangrahmen erfasst Endknoten auch von vorher nicht ausgewählten Konturen; die Konturen müssen nicht zuerst separat ausgewählt werden. Unter „Verbinden“, im rechten Pfade-Bereich oder im Kontextmenü zwischen Gerade, Kurve und tangentialer Kurve wählen. Ohne explizite Endpunktauswahl werden die nächstgelegenen Enden verbunden. Eine einzelne offene Kontur kann über ihre beiden Enden geschlossen werden.

Die bestehende Geometrie wird beibehalten und die Verbindung eingefügt; daraus entsteht eine gemeinsame Kontur. Die erste Auswahl bildet die Basis und wird an den Endpunkten als „1 · Basis“ gekennzeichnet. Bei nacheinander gewählten Endknoten bleibt die Klickreihenfolge erhalten. Bei einer gemeinsamen Rahmenauswahl hat eine bereits zuvor ausgewählte Kontur Vorrang; ansonsten kommt der dem Rahmenstart nächste Endpunkt zuerst. Die Markierung zeigt vor der Verbindung, welcher Endpunkt maßgeblich ist.

Kennung, Name, Ebene und Bearbeitungswerte stammen aus der Basis. Die zweite Kontur wird in diese übernommen, auch wenn sie zuvor auf einer anderen Ebene lag oder andere Werte besaß. Die Statuszeile nennt anschließend die Basis und deren Ebene. Die gemeinsame Kontur erhält zusätzlich eine Gruppenkennung. Vorhandene Gruppen beider Teile werden zu dieser Gruppe zusammengeführt, sodass weitere Gruppenmitglieder gemeinsam ausgewählt und verschoben werden. Geometrisch bleibt die Verbindung ein gemeinsamer Pfad. Strg+Z stellt die Ausgangsteile und ihre Gruppen wieder her. Gesperrte, geschlossene oder mehrteilige Konturen werden mit einem Hinweis abgelehnt.

„Tangentiale Kurve“ erzeugt einen kubischen Übergang, dessen Richtungen an den beiden Enden den angrenzenden Konturen entsprechen (G1-Tangentialität). Gerade Abschnitte werden dabei geometrisch unverändert als kubische Segmente dargestellt. An den Übergangsankern erscheinen T-Markierungen. Beim Bearbeiten der Griffe hält SteBurn die angrenzenden Richtungen kollinear; die gegenüberliegende Grifflänge bleibt erhalten. Eine auf den Anker zusammengezogene Tangente hat keine definierte Richtung. „Tangentialbedingung lösen“ entfernt die lokale Bindung an ausgewählten Ankern oder der gesamten ausgewählten Kontur. „Tangenten spiegeln“ bleibt eine separate Einstellung.

## Ebenenfolge

Die Auftragsübersicht unter Vorbereitung zeigt nummerierte Ebenen. Eine Ebene auswählen und mit ↑/↓ verschieben. In Simulation und Cockpit gibt es dieselbe nummerierte Auswahl, Pfeiltasten und eine sichtbare Reihenfolgekette. Deaktivierte Ausgabeebenen sind mit „[aus]“ gekennzeichnet und werden vom Plan übersprungen. Die aktuelle Ebene folgt in der Simulation dem Zeitschritt, im Cockpit dem gemeldeten Bahnfortschritt.

Eine geänderte Reihenfolge berechnet die Wege und Leerfahrten neu. Die Simulation wird dabei angehalten und auf den Anfang gesetzt. Die Reihenfolge wird im Projekt gespeichert. Bei einem eigenständigen Materialtest verändert das Cockpit nur dessen Testprojekt. Während eines Geräteauftrags, einschließlich Pause, sind Änderungen gesperrt; bereits gepufferte Befehle bleiben Teil des gestarteten Plans.

## Live-Messen und Scrollleisten

Messen aktivieren und den Startpunkt anklicken. Die Linie folgt jetzt der Maus und zeigt sofort ihre Länge in Millimetern. Ein zweiter Klick speichert dieses Maß, der nächste Klick beginnt eine neue Messung. „Alle Maße entfernen“ löscht die Bemaßungen; Strg+Z macht das rückgängig. Die Maße werden als Projektinformationen gespeichert und gelangen nicht in den Laserplan.

Die rechte Seitenleiste zeigt ihre Scrollleiste nur dann, wenn die angezeigten Inhalte höher als der verfügbare Bereich sind. Ändern sich Fenstergröße oder Inhalt, wird dies erneut geprüft.

## Prüfung

203 automatische Tests bestanden, einschließlich Endpunktorientierungen, erster Basis mit übernommenen Attributen und Gruppenkennung, tangentialer Verbindungen, Knotendeletion und Ebenenfolge. Der zusätzliche GUI-Test prüft Rahmenauswahl unselektierter Endpunkte, Auswahl entgegen der Objektlistenreihenfolge, unterschiedliche Bearbeitungswerte, das Zusammenführen zweier vorhandener Gruppen sowie Undo. Bestehende GUI-Prüfungen für Knoten und Zeichnen sowie Messung, Fang und Ebenenfolge sind weiterhin bestanden. Es wurden keine Befehle an reale Hardware gesendet.
