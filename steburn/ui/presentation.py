"""Shared visual language, window branding and contextual usage help."""
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk
from PIL import Image,ImageDraw,ImageTk

HELP={
'Mehr':'Zeigt weitere Hauptaktionen, wenn die Fensterbreite nicht für alle Schaltflächen reicht. Die Arbeitsfläche behält eine einzige obere Leiste.',
'Vorschau aktualisieren':'Berechnet Boxgeometrie und Schnittplatten aus den aktuellen Maßen neu. Es wird keine Maschine angesprochen.',
'Platte als SVG':'Exportiert nur die ausgewählte Schnittplatte als maßhaltige SVG-Datei. Alle Teile bleiben Vektorkonturen; Schnittspaltkorrektur ist gegebenenfalls bereits enthalten.',
'Platte als DXF':'Exportiert die ausgewählte Schnittplatte als geschlossene Polylinien in Millimetern. Erstellt keinen Maschinenauftrag.',
'Schnittteile übernehmen':'Übernimmt alle Platten als eigene Ebenen und speichert die Boxparameter im Projekt. Ausgabe ist zunächst AUS, Leistung 0. Teile sind pro Platte gruppiert.',
'Explosionsansicht':'Zieht die Teile im 3D-Schema auseinander, um Aufbau und Materiallagen zu erkennen. Ändert keine Schnittmaße.',
'Schließen':'Schließt das Modulfenster. Noch nicht übernommene Änderungen werden nicht ins Projekt geschrieben.',
'Neu':'Beginnt ein leeres Projekt. Speichere deine aktuelle Gestaltung vorher; bei ungesicherten Änderungen fragt Steburn nach.',
'Öffnen':'Lädt ein .steburn-Projekt einschließlich Objekten, Ebenen und Parametern. Für Bilder oder SVG-Dateien verwende Import.',
'Speichern':'Speichert die Gestaltung und Bearbeitungsparameter im Steburn-Projekt. Beim ersten Mal wählst du einen Dateinamen. Strg+S.',
'Import':'Übernimmt ein Bild oder unterstützte Vektordateien in die aktive Ebene. Danach Motiv auswählen, Größe und Bearbeitung prüfen.',
'Rückgängig':'Nimmt die letzte Projektänderung zurück. Maschinenbewegungen werden dadurch nicht rückgängig gemacht. Strg+Z.',
'Einpassen':'Passt den Zoom so an, dass die gesamte Arbeitsfläche sichtbar ist. Die echten Objektmaße bleiben unverändert.',
'Prüfen':'Berechnet den Bearbeitungsweg und meldet geometrische Auffälligkeiten. Prüfe Hinweise vor der Simulation und dem Auftrag.',
'Gestalten':'Aktiviert die bearbeitbare Arbeitsfläche. Wähle ein Werkzeug oder markiere vorhandene Objekte.',
'Simulation':'Zeigt geplante Bearbeitungswege, Leerfahrten und eine geschätzte Laufzeit. Bewegt keinen echten Laser.',
'Rahmen':'Simuliert das umschließende Rechteck der Auswahl; ohne Auswahl die ausgabefähigen Objekte. Keine reale Bewegung.',
'Lasern':'Öffnet das Auftragsfenster. Dort prüfst du den Auftrag und startest ihn separat. Dieser Klick bewegt den Laser nicht; derzeit sind nur Testläufe ohne Strahl freigegeben.',
'Auswählen / bewegen':'Klicke ein Objekt an und ziehe es zum Verschieben. Auf freier Fläche einen Rahmen ziehen, um enthaltene Objekte zu wählen. Strg ergänzt die Auswahl; Esc kehrt hierher zurück.',
'Rechteck':'Ziehe auf der Arbeitsfläche von einer Ecke zur gegenüberliegenden. Breite und Höhe lassen sich anschließend im Register Objekt genau einstellen.',
'Ellipse / Kreis':'Ziehe einen Begrenzungsrahmen für die Ellipse auf. Für einen Kreis anschließend gleiche Breite und Höhe einstellen.',
'Linie':'Ziehe vom Startpunkt zum Endpunkt. Offene Linien werden als Kontur markiert und können keine geschlossene Fläche füllen.',
'Text':'Klicke die gewünschte Position an und gib den Text ein. Schrift und Größe danach im Register Objekt einstellen.',
'Vieleck':'Klicke nacheinander die Eckpunkte. Enter oder Doppelklick schließt das Vieleck. Esc bricht das Werkzeug ab.',
'Knoten':'Wähle zuerst einen Linienzug oder ein Vieleck. Ziehe die eingeblendeten Knoten, um die Kontur zu verändern.',
'Messen':'Startpunkt klicken: Linie und Länge folgen live der Maus. Zweiter Klick speichert das Maß. Mit Alle Maße entfernen lassen sich die Bemaßungen löschen.',
'Laserziel':'Wählt per Klick ein physisches Fahrziel. Bewegung erfolgt erst nach Bestätigung und gültiger Referenzfreigabe. Laser bleibt in dieser Version aus.',
'Duplizieren':'Erstellt versetzte Kopien der ausgewählten Objekte. Bearbeitungsparameter werden mitkopiert. Strg+D.',
'Löschen':'Im Knotenmodus werden die markierten Knoten gelöscht, sonst die ausgewählten entsperrten Objekte. Strg+Z macht die Aktion rückgängig.',
'Werkzeug feststellen':'Eingeschaltet bleibt das Zeichenwerkzeug nach einer Form aktiv. Ausgeschaltet springt Steburn nach dem Zeichnen zurück zur Auswahl.',
'Seitenverhältnis beibehalten':'Hält beim Skalieren Breite und Höhe im ursprünglichen Verhältnis. Beim Ziehen der Rahmen-Griffe kehrt Shift diese Einstellung vorübergehend um.',
'Schriftdatei wählen …':'Wählt eine lokale TTF- oder OTF-Schriftdatei für den ausgewählten Text. Für portable Motive kannst du Text anschließend in Pfade umwandeln.',
'Änderungen übernehmen':'Übernimmt die eingegebenen Maße, Position, Bezeichnung und Texteigenschaften für das ausgewählte Objekt.',
'Horizontal zentrieren':'Setzt die ausgewählten Objekte horizontal in die Mitte der Arbeitsfläche. Zum Ausrichten untereinander das Kontextmenü verwenden.',
'Vertikal zentrieren':'Setzt die ausgewählten Objekte vertikal in die Mitte der Arbeitsfläche. Die Objektgröße wird nicht verändert.',
'Auf Auswahl anwenden':'Übernimmt die angezeigte Bearbeitungsart, Füllung und Parameter für alle ausgewählten, nicht gesperrten Objekte. Diese Werte haben Vorrang vor den Ebenenwerten.',
'Alle Werte wieder von Ebene':'Entfernt eigene Bearbeitungswerte der Auswahl. Die Objekte verwenden anschließend wieder die Parameter ihrer jeweiligen Ebene.',
'+':'Fügt eine neue farbige Ebene hinzu und aktiviert sie. Vorhandene Objekte bleiben ihrer bisherigen Ebene zugeordnet.',
'Name':'Benennt die aktive Ebene um. Alternativ doppelt auf ihren farbigen Reiter klicken.',
'Farbe':'Ändert die Darstellungsfarbe der aktiven Ebene. Die Farbe allein ändert keine Leistung oder Bearbeitungsart.',
'Vor':'Verschiebt die aktive Ebene in der Bearbeitungsreihenfolge nach vorne.',
'Nach':'Verschiebt die aktive Ebene in der Bearbeitungsreihenfolge nach hinten.',
'Ebene übernehmen':'Speichert die angezeigten Parameter für die aktive Ebene. Eigene Objektwerte bleiben vorrangig.',
'Anzeigen':'Blendet die Ebene im Editor ein oder aus. Ausgabe ist eine getrennte Einstellung: Unsichtbare Ebenen können weiterhin bearbeitet werden.',
'In Simulation / Ausgabe einbeziehen':'Bestimmt, ob diese Ebene zum gesamten Auftrag gehört. Deaktivieren schließt sie aus, ohne die Objekte zu löschen.',
'Air Assist (Parameter)':'Speichert den gewünschten Air-Assist-Parameter. Die tatsächliche Geräteansteuerung ist in diesem Teststand noch nicht umgesetzt.',
'Aktive Ebene als Vorlage speichern':'Speichert die Parameter der aktiven Ebene als Materialvorlage in diesem Projekt. Verwende einen Namen mit Material und Dicke.',
'Vorlage auf Ebene anwenden':'Übernimmt die ausgewählte Materialvorlage auf die aktive Ebene. Prüfe zuerst, ob Material, Dicke und Maschine passen.',
'Ports suchen':'Zeigt erkannte serielle Anschlüsse an. Schließe LightBurn, damit Steburn auf den Laseranschluss zugreifen kann.',
'Verbinden / $I und $$ lesen':'Öffnet den Anschluss und liest Firmware sowie Geräteeinstellungen. Das Öffnen kann einen Geräteneustart auslösen; Referenzfreigabe erfolgt separat.',
'Position / Versätze nur lesen':'Liest Status, Betriebsarten und Koordinatenversätze zur Diagnose. Löst selbst keine Bewegung aus.',
'Nullpunkt / Homing bestätigen':'Bestätigt die reale Ankunft links vorne nach einer in Steburn erfolgreich ausgeführten Referenzfahrt. Ein Dialog allein ersetzt kein Homing.',
'Referenzfahrt ausführen ($H)':'Startet die reale Referenzfahrt zu den Sensoren. Vorher den gesamten Verfahrweg freihalten; danach die reale Ankunft links vorne prüfen.',
'Sichtbaren Strahl ausdrücklich verwenden':'Sichtbare Ausrichtung ist in dieser Version noch gesperrt. Eine getestete niedrige Leistung garantiert kein spurenfreies Material.',
'Mausziel per Klick wählen':'Aktiviert die Zielauswahl auf der Arbeitsfläche. Vor einer physischen Fahrt werden Ziel und Freigabe geprüft.',
'Rechteck physisch abfahren':'Fährt den Begrenzungsrahmen tatsächlich am Gerät ab. Arbeitsbereich und Referenz müssen gültig sein. Verfahrweg freihalten; Laser bleibt aus.',
'ABBRUCH / Controller-Reset':'Sendet sofort einen Controller-Reset. Die Positionsfreigabe verfällt; danach neu verbinden und referenzieren. Ersetzt keinen Hardware-Notaus.',
'Trennen':'Schließt die serielle Verbindung. Bei laufendem Geräteauftrag wird zunächst ein Abbruch angefordert.',
'Auftrag starten · Testlauf':'Startet erst nach Bestätigung einen echten Bewegungstest des berechneten Auftrags mit Laser AUS. Referenz, Verfahrgrenzen und alle Ziele werden geprüft. Echte Gravurstarts sind noch gesperrt.',
'Pause':'Fordert kontrolliertes Anhalten an. Erst Hold:0 bestätigt die vollständige Pause; vorher bleibt Fortsetzen gesperrt.',
'Fortsetzen':'Setzt den vollständig pausierten Auftrag fort. Nur bei bestätigtem Hold:0 verfügbar; kein Wiederanlauf nach Reset oder Stromausfall.',
'Abbrechen / Reset':'Beendet den Auftrag durch Controller-Reset. Fortschritt wird nicht als sicher wiederaufnehmbar behandelt. Anschließend neu referenzieren; Hardware-Notaus bleibt unabhängig.',
'Vorschau ab hier':'Zeigt den verbleibenden Plan ab einem Segmentanfang zur eingegebenen Prozentzahl der geschätzten Planzeit. Startet keine Maschine.',
'Start / Fortsetzen':'Spielt die virtuelle Bahnsimulation ab oder setzt sie fort. Der reale Laser wird nicht angesprochen.',
'Zurücksetzen':'Setzt die virtuelle Simulation an den Anfang zurück. Ändert weder Projekt noch Maschinenposition.',
'Tiefenkarte umkehren (standardmäßig dunkel = tief)':'Kehrt die Interpretation der Graustufen um. Prüfe das Motiv: Bildhelligkeit ist zunächst nur eine angenommene Reliefhöhe.',
'Schichtvorschau als bearbeitbare Objekte übernehmen':'Erzeugt deckungsgleiche Reliefschichten in einer neuen Ebene mit Ausgabe AUS. Original bleibt erhalten. Materialabtrag ist noch nicht kalibriert.',
}

HELP.update({
    'Abbrechen + Referenzposition':'Hält den Job kontrolliert an, leert den Auftragsplan per Reset und referenziert danach automatisch. Bei Gerätefehlern erfolgt keine automatische Fahrt.',
    'Notstopp / Reset':'Sendet sofort einen Controller-Reset. Die Position wird ungültig und es startet keine automatische Rückfahrt.',
    'Planwerte wiederherstellen':'Verwendet wieder die im Auftrag gespeicherten Geschwindigkeiten und Leistungen der einzelnen Objekte.',
    'Bildstudio öffnen':'Bearbeitet das ausgewählte Bild mit Originalvergleich, Helligkeit, Kontrast, Gamma, Schärfe, Zuschnitt und Laser-Rasterverfahren. Das Original bleibt erhalten.',
    'Bild bearbeiten':'Öffnet das Bildstudio für das ausgewählte Bild. Ein Doppelklick auf ein Bild öffnet es ebenfalls.',
    'Raster an Planlimit anpassen':'Berechnet einen konservativen Rasterabstand für Bildgröße und Durchgänge. Prüfe anschließend die angezeigte Auflösung und Vorschau.',
    'Bildkorrekturen zurücksetzen':'Setzt Tonwertkorrekturen auf neutrale Werte. Original, Zuschnitt und Rasterverfahren bleiben erhalten.',
    'Feststellen':'Das Zeichenwerkzeug bleibt nach dem Erstellen eines Objekts aktiv.',
    'Bézier':'Vier Punkte setzen: Start, zwei Kontrollpunkte, Ende. Anschließend Anker und Tangenten im Knotenmodus bearbeiten.',
    'Auswahl':'Objekte auswählen und verschieben. Strg ergänzt die Auswahl, Ziehen auf freier Fläche spannt eine Mehrfachauswahl auf.',
    'Radius auf Auswahl anwenden':'Rundet die Ecken ausgewählter Rechtecke. Der Radius wird auf die halbe kleinere Seitenlänge begrenzt.',
    'Knotenposition übernehmen':'Übernimmt X/Y für den gewählten Anker oder Griff. Bézier-Anker nehmen angrenzende Griffe mit.',
    'Teilen / Einfügen':'Teilt ein Béziersegment formtreu in zwei Segmente oder fügt einen Mittelpunkt in einen Linienzug ein.',
    'Knoten löschen':'Entfernt alle markierten Knoten. Geschlossene Konturen bleiben geschlossen; Konturen mit zu wenigen verbleibenden Knoten werden entfernt. Strg+Z macht rückgängig.',
    'Fangen':'Fängt den nächsten vorhandenen Punkt innerhalb von 10 Bildschirmpixeln, danach das Raster oder Hilfslinien. Alt setzt das Fangen vorübergehend aus.',
    'Verbinden':'Verbindet offene Konturen über eine Gerade, Kurve oder tangentiale Kurve. Zwei Endknoten markieren oder zwei offene Konturen auswählen.',
    'Alle Maße entfernen':'Entfernt sämtliche gespeicherten Bemaßungen aus dem Projekt. Die Aktion lässt sich rückgängig machen.',
    'Bézier-Tangenten spiegeln':'Spiegelt bei Bézier-Griffbewegungen den gegenüberliegenden Griff am gemeinsamen Anker.',
    'Neuen Text erstellen':'Erstellt aus dem Textinhalt ein neues editierbares Textobjekt auf der aktiven Ebene.',
    'Text übernehmen':'Übernimmt Inhalt, Schriftgröße, Laufweite, Zeilenabstand und Ausrichtung. Strg+Enter im Textfeld.',
    'Profil speichern':'Speichert das Materialprofil in der lokalen Bibliothek und im aktuellen Projekt.',
    'Profil anwenden':'Übernimmt die angezeigten Materialwerte auf die aktive Ebene oder ausgewählte entsperrte Objekte.',
    'Rahmenvorschau':'Öffnet eine virtuelle Vorschau des Rahmens. Bewegt keine Maschine.',
    'Rahmen fahren':'Startet die wiederholte Rahmenfahrt mit optionalem schwachem Rahmenlicht aus Vorbereitung. Stopp beendet die Fahrt positionsbewahrend.',
    'Stopp':'Beendet die aktive Rahmenfahrt per Jog-Cancel. Die bestätigte Position bleibt erhalten.',
    'Cockpit':'Öffnet die Auftragsansicht mit Live-Status und Parametern. Ein eigener Startbutton beginnt die Bearbeitung.',
    'Job-Cockpit':'Öffnet die Auftragsansicht mit Live-Status und Parametern. Ein eigener Startbutton beginnt die Bearbeitung.',
    'Weiter zum Job-Cockpit':'Öffnet die Auftragsansicht mit Live-Status und Parametern. Ein eigener Startbutton beginnt die Bearbeitung.',
    '−250':'Senkt den absoluten Vorschub sofort um 250 mm/min. Annahme und Bahnstatusbestätigung erscheinen im Cockpit.',
    '+250':'Erhöht den absoluten Vorschub sofort um 250 mm/min. Annahme und Bahnstatusbestätigung erscheinen im Cockpit.',
    '−5':'Senkt die absolute Leistung um 5 Prozentpunkte, bis mindestens 0 %. Die Änderung wird im Jobbericht protokolliert.',
    '+5':'Erhöht die absolute Leistung um 5 Prozentpunkte, bis maximal 100 %. Die Änderung wird im Jobbericht protokolliert.',
    'Schwaches Rahmenlicht':'Optionales Positionslicht während der Rahmenbewegung, maximal 0,5 %. Auch schwaches Licht kann Material markieren.',
    'Materialtest …':'Öffnet ein positionierbares Prüfmuster mit wählbarer Größe, 15 Schnitt- und 15 Gravurfeldern sowie gespeicherten Materialbewertungen.',
    'Rahmen':'Fährt den Begrenzungsrahmen wiederholt ab. Optionales schwaches Rahmenlicht unter Vorbereitung. Mit Rahmen stoppen beenden.',
    'Rahmen starten':'Fährt den Begrenzungsrahmen wiederholt ab. Optionales schwaches Rahmenlicht unter Vorbereitung; auch geringe Leistung kann Spuren erzeugen.',
    'Rahmen stoppen':'Bricht die Rahmenfahrt mit GRBL-Jog-Cancel ab. Nach bestätigtem Stillstand bleibt die Position gültig.',
    'Verbinden + Referenzfahrt':'Verbindet den gewählten Anschluss und startet direkt die reale Referenzfahrt. Danach wird der Arbeitsnullpunkt eingerichtet und geprüft.',
    'Neu referenzieren':'Startet die reale Referenzfahrt erneut und richtet nach erfolgreicher Prüfung den Nullpunkt ein.',
    'Lasern':'Öffnet das Auftragsfenster. Auftrag starten · Lasern startet dort mit den eingestellten Leistungs- und Geschwindigkeitswerten.',
    'Auftrag starten · Lasern':'Startet direkt den Laserauftrag mit den gespeicherten Bearbeitungswerten. Referenz, Arbeitsbereich und Controllerprofil werden vorher geprüft.',
    'Laserziel':'Mausfahrt: Klick fährt den Kopf direkt zum Ziel. Optionales Pointerlicht unter Vorbereitung: kurzer, begrenzter Impuls am Ziel.',
    'Mausfahrt / Pointer':'Wechselt zum Mausziel-Werkzeug. Jeder Klick fährt den Kopf zum Ziel; das optionale Pointerlicht wird am Ziel kurz eingeschaltet.',
    'Nur Beschriftung testen':'Öffnet einen eigenständigen Auftrag nur für Beschriftungen und Umriss an der Testposition. Die 30 Testfelder werden nicht bearbeitet.',
    'Zuordnung als Bild …':'Speichert eine lesbare Zuordnungsgrafik mit Feldkennungen, Leistungen, Vorschüben und Durchgängen, auch für ältere Versuche.',
})

class ToolTip:
    def __init__(self,widget,text,delay=550):
        self.widget=widget; self.text=text; self.delay=delay; self.timer=None; self.window=None
        widget.bind('<Enter>',self.schedule,add='+')
        widget.bind('<Leave>',self.hide,add='+')
        widget.bind('<ButtonPress>',self.hide,add='+')
        widget.bind('<FocusIn>',self.schedule,add='+')
        widget.bind('<FocusOut>',self.hide,add='+')
        widget.bind('<Destroy>',self.hide,add='+')
    def schedule(self,e=None):
        self.hide(); self.timer=self.widget.after(self.delay,self.show)
    def show(self):
        self.timer=None
        if not self.widget.winfo_exists() or not self.widget.winfo_ismapped(): return
        self.hide()
        self.window=tk.Toplevel(self.widget); self.window.overrideredirect(True)
        frame=tk.Frame(self.window,bg='#172338',bd=0,padx=13,pady=10,highlightthickness=1,highlightbackground='#43546b'); frame.pack()
        label=tk.Label(frame,text=self.text,bg='#172338',fg='#f8fafc',font=('Segoe UI' if sys.platform=='win32' else 'DejaVu Sans',10),justify='left',wraplength=360); label.pack()
        self.window.update_idletasks()
        x=self.widget.winfo_rootx()+8; y=self.widget.winfo_rooty()+self.widget.winfo_height()+7
        x=max(0,min(x,self.widget.winfo_screenwidth()-self.window.winfo_reqwidth()-10))
        if y+self.window.winfo_reqheight()>self.widget.winfo_screenheight()-10: y=max(0,self.widget.winfo_rooty()-self.window.winfo_reqheight()-7)
        self.window.geometry(f'+{x}+{y}')
    def hide(self,e=None):
        if self.timer:
            try: self.widget.after_cancel(self.timer)
            except tk.TclError: pass
            self.timer=None
        if self.window:
            try: self.window.destroy()
            except tk.TclError: pass
            self.window=None

def attach_help(container):
    for child in container.winfo_children():
        if isinstance(child,(ttk.Button,ttk.Menubutton,ttk.Checkbutton,tk.Button)):
            label=str(child.cget('text'))
            text=HELP.get(label)
            if label=='Pause' and child.winfo_toplevel().__class__.__name__=='Simulation': text='Hält nur die virtuelle Simulation an. Die reale Maschine wird nicht angesprochen. Mit Start / Fortsetzen läuft die Vorschau weiter.'
            if label in {'−10 %','100 %','+10 %'}:
                group=str(child.master.cget('text')) if isinstance(child.master,ttk.LabelFrame) else 'Vorschub und Leistung'
                text=f'{group}: verändert den Controller-Override relativ zum Planwert. 100 % stellt den Planwert wieder her.'
            if isinstance(child,tk.Button) and child.master==getattr(container.winfo_toplevel(),'palette',None):
                text=f'Ebene „{label}“ aktivieren. Neue Objekte entstehen hier. Doppelklick benennt um; Rechtsklick bietet Zuordnung der Auswahl und weitere Ebenenaktionen.'
            if text:
                if hasattr(child,'usage_help'): child.usage_help.text=text
                else: child.usage_help=ToolTip(child,text)
        if not isinstance(child,tk.Toplevel): attach_help(child)

class Appearance:
    def __init__(self,root):
        self.root=root; self.images=[]; self.icon_images=[]; self.logo=None; self.icon_error=''
        self.install_theme(); self.load_icons()
    def surface(self,fill,outline):
        image=Image.new('RGBA',(40,40),(0,0,0,0)); draw=ImageDraw.Draw(image)
        draw.rounded_rectangle((1,1,38,38),radius=8,fill=fill,outline=outline,width=1)
        photo=ImageTk.PhotoImage(image,master=self.root); self.images.append(photo); return photo
    def install_theme(self):
        style=ttk.Style(self.root)
        palettes={
            'TButton':('#ffffff','#c4ceda','#eaf1f9','#d9e6f5','#233247'),
            'Accent.TButton':('#ed842b','#cf691c','#ff963e','#d66b19','#182536'),
            'Danger.TButton':('#b63636','#942828','#cc4646','#9c2828','#ffffff'),
            'Selected.TButton':('#e5effc','#3879c5','#d5e6fb','#c6dcf7','#144c8d'),
        }
        for name,(fill,border,hover,pressed,fg) in palettes.items():
            normal=self.surface(fill,border); hot=self.surface(hover,border); down=self.surface(pressed,border)
            off=self.surface('#e8ecf1','#d6dde5'); focus=self.surface(fill,'#2678d7')
            element='Steburn.'+name+'.surface'
            style.element_create(element,'image',normal,('disabled',off),('pressed',down),('active',hot),('focus',focus),border=(10,10,10,10),sticky='nsew')
            style.layout(name,[(element,{'sticky':'nsew','children':[('Button.padding',{'sticky':'nsew','children':[('Button.label',{'sticky':'nsew'})]})]})])
            style.configure(name,padding=(12,8),foreground=fg,background='#eef1f5',anchor='center')
            style.map(name,foreground=[('disabled','#8995a5')])
        for name,base in [('Toolbar.TButton','TButton'),('Toolbar.Accent.TButton','Accent.TButton')]:
            style.layout(name,style.layout(base)); style.configure(name,background='#243247')
        style.configure('TEntry',padding=5,fieldbackground='#ffffff',bordercolor='#c4ceda',lightcolor='#c4ceda',darkcolor='#c4ceda')
        style.configure('TCombobox',padding=5,fieldbackground='#ffffff',bordercolor='#c4ceda',arrowsize=13)
        style.map('TCombobox',fieldbackground=[('readonly','#ffffff')],foreground=[('readonly','#233247')])
        style.configure('TNotebook',background='#e7edf4',borderwidth=0)
        style.configure('TNotebook.Tab',padding=(13,8),background='#dce4ef')
        style.map('TNotebook.Tab',background=[('selected','#ffffff'),('active','#eaf1f9')],foreground=[('selected','#144c8d')])
    def load_icons(self):
        # Keep assets inside the Python package too: copying only steburn/ must retain branding.
        candidates=[Path(__file__).resolve().parents[1]/'assets',Path(__file__).resolve().parents[2]/'assets']
        for folder in candidates:
            if (folder/'steburn.png').exists():
                try:
                    with Image.open(folder/'steburn.png') as original:
                        self.icon_images=[ImageTk.PhotoImage(original.resize((n,n),Image.Resampling.LANCZOS),master=self.root) for n in (16,32,48,64,128)]
                        self.logo=ImageTk.PhotoImage(original.resize((48,48),Image.Resampling.LANCZOS),master=self.root)
                    self.ico=folder/'Steburn.ico'; self.apply_icon(self.root); return
                except Exception as ex: self.icon_error=str(ex)
        self.icon_error=self.icon_error or 'SB-Logodateien fehlen. Bitte vollständiges Paket entpacken.'
    def apply_icon(self,window):
        if self.icon_images:
            window.iconphoto(True,*self.icon_images)
            if sys.platform=='win32' and self.ico.exists():
                # Explicitly set the existing window AND defaults for later windows.
                try:
                    window.iconbitmap(str(self.ico)); window.iconbitmap(default=str(self.ico))
                except tk.TclError as ex: self.icon_error=str(ex)
    def brand_header(self,app):
        brand=next((w for bar in app.winfo_children() if isinstance(bar,ttk.Frame) for w in bar.winfo_children() if isinstance(w,ttk.Label) and str(w.cget('text'))=='STEBURN'),None)
        if brand:
            bar=brand.master; bar.configure(style='Dark.TFrame',padding=(8,6))
            brand.configure(text='Steburn',style='Dark.TLabel',compound='left',padding=(0,0,15,0),font=('Segoe UI' if sys.platform=='win32' else 'DejaVu Sans',18,'bold'))
            if self.logo: brand.configure(image=self.logo)
            for child in bar.winfo_children():
                if isinstance(child,ttk.Label) and child!=brand: child.configure(style='Dark.TLabel')
                elif isinstance(child,ttk.Button):
                    child.configure(style='Toolbar.TButton'); child.pack_configure(padx=4,pady=3)
        if self.icon_error: app.status.set('Programmsymbol: '+self.icon_error)
    def present(self,window):
        self.apply_icon(window); attach_help(window)
        if hasattr(self.root,'theme'): self.root.theme.style_widgets(window)
        for child in window.winfo_children():
            if isinstance(child,ttk.Button) and str(child.cget('text')).startswith('Schichtvorschau'): child.configure(style='Accent.TButton')
