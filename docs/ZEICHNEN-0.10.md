# SteBurn 0.10 – Zeichnen und Knoten

Seitliche Anfasser am Auswahlrahmen ändern nur die zugehörige Dimension: links/rechts die Breite, oben/unten die Höhe. Die gegenüberliegende Seite bleibt stehen. Nur Eckanfasser berücksichtigen die Seitenverhältnis-Sperre; Shift kehrt diese Einstellung wie bisher um.

Objekte auswählen und „Knoten bearbeiten“ aktivieren. Nun erscheinen auch an Rechtecken und Ellipsen bearbeitbare Knoten. Ein Klick wählt einen Knoten, Shift/Strg ergänzt oder entfernt ihn. Mit einem Fangrahmen lassen sich mehrere Knoten der ausgewählten Objekte erfassen. Einen ausgewählten Knoten ziehen, um die gesamte Knotenauswahl zu verschieben. Die außerhalb des orangefarbenen Auswahlrahmens liegenden runden Griffe strecken oder stauchen nur die ausgewählten Knoten. Eine geschlossene Kontur bleibt geschlossen; vorhandene innere Konturen bleiben erhalten. Die Geometrie selbst verändert sich entsprechend der Knotenbewegung.

Rechtecke und Ellipsen werden beim ersten tatsächlichen Knoteneingriff in bearbeitbare Pfade umgewandelt. Die Knotenliste unterstützt Mehrfachauswahl. Gültige X/Y-Eingaben in der Seitenleiste verschieben die Knotenauswahl relativ zum gewählten Bezugsknoten; sie benötigen keinen Übernehmen-Button. Gesperrte Objekte bleiben von Eingriffen ausgeschlossen. Strg+Z macht den Eingriff rückgängig.

Bézierkurven werden weiterhin mit vier Klicks erstellt: Startanker, erster Tangentengriff, zweiter Tangentengriff, Endanker. Die gestrichelten Hilfslinien folgen der Maus; vor dem vierten Klick erscheint die resultierende Kurve. Anschließend wechselt das Programm zur Knotenbearbeitung. Anker werden eckig, Tangentengriffe rund dargestellt. Beim Verschieben eines Ankers bewegen sich die angrenzenden Griffe mit; bei geschlossenen Kurven gilt dies auch über die Naht hinweg. „Tangenten spiegeln“ spiegelt einen verschobenen Griff am zugehörigen Anker.

Beim Zeichnen einer Linie folgt eine Linie der Maus. Ellipsen erhalten eine Ellipsenvorschau. Beim Vieleck folgen die gestrichelte nächste Kante und die mögliche Schließkante der Maus, schon bevor ein weiterer Punkt gesetzt wird. Mit Enter beziehungsweise Doppelklick wird das Vieleck geschlossen; Esc bricht ab.

„−“ neben den Farbreitern oder im Ebenenbereich entfernt die aktive Ebene. Rechtsklick auf einen Farbreiter beziehungsweise die Ebenenauswahl bietet dieselbe Aktion. Objekte werden mit ihren wirksamen Bearbeitungsparametern auf die benachbarte Ebene verschoben; ihre Geometrie bleibt erhalten. Die letzte Ebene kann nicht entfernt werden. Strg+Z stellt eine entfernte Ebene wieder her.

Geprüft mit 189 automatischen Tests und GUI-Abläufen für primitive Formen, Mehrfachauswahl, Stauchen/Strecken, Konturschluss, Béziererstellung und Tangentenbewegung, Vorschauen sowie Ebenenentfernung und Undo. Es wurden keine Befehle an reale Laserhardware gesendet.
