import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from copy import deepcopy
from pathlib import Path
from steburn import __version__
from steburn.ui.widgets import ScrollPanel
from steburn.core.model import Project, Shape, Layer, History
from steburn.core.geometry import outline, checks
from steburn.core.extensions import Registry, Command
from steburn.io.svg import import_svg, export_svg

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'Steburn {__version__} · Entwerfen und vorbereiten')
        self.geometry('1320x850'); self.minsize(1000,650)
        self.p=Project(); self.history=History(); self.path=None; self.dirty=False
        self.selected=None; self.tool='select'; self.active_layer=self.p.layers[0].id
        self.scale=1.5; self.ox=40; self.oy=40; self.drag=None; self.preview=False
        self.registry=Registry(); self.vars={}; self.loading=False
        style=ttk.Style(self); style.theme_use('clam')
        style.configure('TFrame',background='#eef1f4'); style.configure('TLabel',background='#eef1f4')
        style.configure('TButton',padding=(9,6)); style.configure('Treeview',rowheight=27)
        self.build(); self.bind_shortcuts(); self.protocol('WM_DELETE_WINDOW',self.close)
        self.registry.register(Command('document.check','Projekt prüfen',self.check))
        extension_menu=tk.Menu(self.menubar,tearoff=False)
        self.menubar.add_cascade(label='Erweiterungen',menu=extension_menu)
        for command in self.registry.commands.values():
            extension_menu.add_command(label=command.label,command=command.run)
        self.after(80,self.fit)
    def build(self):
        menu=tk.Menu(self); self.menubar=menu; self.config(menu=menu)
        file=tk.Menu(menu,tearoff=False); menu.add_cascade(label='Datei',menu=file)
        for label,cmd in [('Neu',self.new),('Öffnen …',self.open),('Speichern',self.save),('Speichern unter …',lambda:self.save(True)),('SVG importieren …',self.import_file),('SVG exportieren …',self.export_file),('Beenden',self.close)]: file.add_command(label=label,command=cmd)
        edit=tk.Menu(menu,tearoff=False); menu.add_cascade(label='Bearbeiten',menu=edit)
        for label,cmd in [('Rückgängig',self.undo),('Wiederholen',self.redo),('Duplizieren',self.duplicate),('Löschen',self.delete)]: edit.add_command(label=label,command=cmd)
        helpmenu=tk.Menu(menu,tearoff=False); menu.add_cascade(label='Hilfe',menu=helpmenu)
        helpmenu.add_command(label='Kurzanleitung',command=lambda:messagebox.showinfo('Steburn','Links: Werkzeug wählen.\nAuf der Fläche ziehen: Form zeichnen / Objekt verschieben.\nRechts: Maße und Ebene einstellen, dann Übernehmen.\nMausrad: Zoom · mittlere Maustaste: Verschieben\nStrg+S speichern · Strg+Z rückgängig · Strg+D duplizieren\n\nVersion 0.3: Editor, Bahnsimulation und GRBL-Testbetrieb.\nKeine Schneid-/Gravurstarts.\nImportgrenzen: siehe README und IMPORTFORMATE.md.'))
        bar=ttk.Frame(self); bar.pack(fill='x',padx=8,pady=8)
        ttk.Label(bar,text='STEBURN',font=('Segoe UI',18,'bold')).pack(side='left',padx=(4,25))
        for label,cmd in [('Neu',self.new),('Öffnen',self.open),('Speichern',self.save),('Import',self.import_file),('Rückgängig',self.undo),('Einpassen',self.fit),('Prüfen',self.check)]: ttk.Button(bar,text=label,command=cmd).pack(side='left',padx=2)
        ttk.Label(bar,text='A40 Pro · 400 × 400 mm · OFFLINE',foreground='#a35d27').pack(side='right',padx=8)
        pane=ttk.Panedwindow(self,orient='horizontal'); self.main_pane=pane; pane.pack(fill='both',expand=True,padx=8)
        left=ttk.Frame(pane,width=205); center=ttk.Frame(pane); right=ttk.Frame(pane,width=275)
        pane.add(left,weight=0); pane.add(center,weight=1); pane.add(right,weight=0)
        ttk.Label(left,text='WERKZEUGE',font=('Segoe UI',10,'bold')).pack(anchor='w',padx=8,pady=8)
        for label,tool in [('Auswählen / bewegen','select'),('Rechteck','rect'),('Ellipse / Kreis','ellipse'),('Linie','line'),('Text','text')]: ttk.Button(left,text=label,command=lambda t=tool:self.set_tool(t)).pack(fill='x',padx=6,pady=2)
        ttk.Button(left,text='Duplizieren',command=self.duplicate).pack(fill='x',padx=6,pady=(15,2))
        ttk.Button(left,text='Löschen',command=self.delete).pack(fill='x',padx=6,pady=2)
        ttk.Label(left,text='OBJEKTE',font=('Segoe UI',10,'bold')).pack(anchor='w',padx=8,pady=(20,8))
        self.tree=ttk.Treeview(left,show='tree',selectmode='browse',height=12); self.tree.pack(fill='both',expand=True,padx=6,pady=6)
        self.tree.bind('<<TreeviewSelect>>',self.tree_selected)
        top=ttk.Frame(center); top.pack(fill='x')
        ttk.Button(top,text='Gestalten',command=lambda:self.set_preview(False)).pack(side='left')
        ttk.Button(top,text='Konturvorschau',command=lambda:self.set_preview(True)).pack(side='left',padx=4)
        ttk.Label(top,text='mm · maßhaltige Arbeitsfläche').pack(side='right',padx=8)
        self.canvas=tk.Canvas(center,bg='#dce2e8',highlightthickness=0); self.canvas.pack(fill='both',expand=True,pady=5)
        self.canvas.bind('<ButtonPress-1>',self.press); self.canvas.bind('<B1-Motion>',self.motion); self.canvas.bind('<ButtonRelease-1>',self.release)
        self.canvas.bind('<MouseWheel>',self.wheel); self.canvas.bind('<Button-4>',lambda e:self.zoom(1.15,e.x,e.y)); self.canvas.bind('<Button-5>',lambda e:self.zoom(1/1.15,e.x,e.y))
        self.canvas.bind('<ButtonPress-2>',lambda e:setattr(self,'pan',(e.x,e.y)))
        self.canvas.bind('<B2-Motion>',self.pan_move)
        self.canvas.bind('<Configure>',lambda e:self.render())
        notebook=ttk.Notebook(right); self.notebook=notebook; notebook.pack(fill='both',expand=True,padx=6,pady=5)
        self.page_tabs={key:ScrollPanel(notebook) for key in ('props','layers','materials','machine')}
        props,layers,materials,machine=[self.page_tabs[key].content for key in ('props','layers','materials','machine')]
        self.pages={'props':props,'layers':layers,'materials':materials,'machine':machine}
        for key,label in [('props','Objekt'),('layers','Ebenen'),('materials','Material'),('machine','Laser')]: notebook.add(self.page_tabs[key],text=label)
        for key,label in [('name','Name'),('x','X (mm)'),('y','Y (mm)'),('w','Breite (mm)'),('h','Höhe (mm)'),('text','Text')]:
            ttk.Label(props,text=label).pack(anchor='w',padx=8,pady=(8,0)); v=tk.StringVar(); self.vars[key]=v; ttk.Entry(props,textvariable=v).pack(fill='x',padx=8)
        ttk.Label(props,text='Ebene').pack(anchor='w',padx=8,pady=(8,0))
        self.object_layer=ttk.Combobox(props,state='readonly'); self.object_layer.pack(fill='x',padx=8)
        ttk.Button(props,text='Änderungen übernehmen',command=self.apply).pack(fill='x',padx=8,pady=12)
        for label,cmd in [('Horizontal zentrieren',lambda:self.align('x')),('Vertikal zentrieren',lambda:self.align('y'))]: ttk.Button(props,text=label,command=cmd).pack(fill='x',padx=8,pady=2)
        ttk.Label(layers,text='Aktive Ebene / neue Objekte').pack(anchor='w',padx=8,pady=8)
        self.layerbox=ttk.Combobox(layers,state='readonly'); self.layerbox.pack(fill='x',padx=8); self.layerbox.bind('<<ComboboxSelected>>',lambda e:self.layer_selected())
        ttk.Button(layers,text='Neue Ebene',command=self.add_layer).pack(fill='x',padx=8,pady=8)
        self.lvars={}
        for key,label in [('name','Ebenenname'),('speed','Geschwindigkeit (mm/min)'),('power','Leistung (%)'),('passes','Durchgänge')]:
            ttk.Label(layers,text=label).pack(anchor='w',padx=8,pady=(8,0)); v=tk.StringVar(); self.lvars[key]=v; ttk.Entry(layers,textvariable=v).pack(fill='x',padx=8)
        self.mode=tk.StringVar(value='Kontur'); ttk.Combobox(layers,textvariable=self.mode,values=['Kontur','Fläche'],state='readonly').pack(fill='x',padx=8,pady=8)
        self.visible=tk.BooleanVar(value=True); ttk.Checkbutton(layers,text='Ebene sichtbar',variable=self.visible).pack(anchor='w',padx=8)
        ttk.Button(layers,text='Ebene übernehmen',command=self.apply_layer).pack(fill='x',padx=8,pady=10)
        ttk.Label(layers,text='Parameter werden gespeichert.\nNoch keine Maschinenausgabe.\nFlächenfüllung folgt später.',wraplength=235).pack(anchor='w',padx=8,pady=8)
        ttk.Label(materials,text='Eigene Materialvorlagen',font=('Segoe UI',11,'bold')).pack(anchor='w',padx=8,pady=12)
        self.materialbox=ttk.Combobox(materials,state='readonly'); self.materialbox.pack(fill='x',padx=8)
        ttk.Button(materials,text='Aktive Ebene als Vorlage speichern',command=self.store_material).pack(fill='x',padx=8,pady=8)
        ttk.Button(materials,text='Vorlage auf Ebene anwenden',command=self.use_material).pack(fill='x',padx=8,pady=4)
        ttk.Label(materials,text='Vorlagen gehören zum Projekt.\nKeine ungeprüften Herstellerwerte\nwerden automatisch eingesetzt.',wraplength=230).pack(anchor='w',padx=8,pady=12)
        ttk.Label(machine,text='Atomstack A40 Pro',font=('Segoe UI',12,'bold')).pack(anchor='w',padx=8,pady=12)
        ttk.Label(machine,text='Arbeitsfläche: 400 × 400 mm\nVerbindung: nicht eingerichtet\nFirmware: noch nicht bestätigt\n\nDie Maschinenanbindung wird nach\nPrüfung deines Geräteprofils ergänzt.',wraplength=235).pack(anchor='w',padx=8)
        ttk.Button(machine,text='Laser starten (noch nicht verfügbar)',state='disabled').pack(fill='x',padx=8,pady=16)
        self.status=tk.StringVar(value='Bereit · Offline-Editor'); ttk.Label(self,textvariable=self.status,padding=8).pack(fill='x')
        self.refresh()
    def bind_shortcuts(self):
        for seq,cmd in [('<Control-s>',self.save),('<Control-o>',self.open),('<Control-n>',self.new),('<Control-z>',self.undo),('<Control-y>',self.redo)]: self.bind(seq,lambda e,c=cmd:c())
        self.bind('<Delete>',lambda e:self.delete() if not isinstance(self.focus_get(),(ttk.Entry,tk.Entry)) else None)
        self.bind('<Control-d>',lambda e:self.duplicate() if not isinstance(self.focus_get(),(ttk.Entry,tk.Entry)) else None)
        self.bind('<Escape>',lambda e:self.set_tool('select'))
    def changed(self): self.dirty=True; self.title(f'Steburn {__version__} · {self.p.title} *')
    def checkpoint(self): self.history.checkpoint(self.p)
    def current(self): return next((s for s in self.p.shapes if s.id==self.selected),None)
    def set_tool(self,t): self.tool=t; self.preview=False; self.status.set('Werkzeug: '+t+' · Maße in mm'); self.render()
    def coords(self,e): return ((e.x-self.ox)/self.scale,(e.y-self.oy)/self.scale)
    def press(self,e):
        if self.preview: return
        x,y=self.coords(e)
        if self.tool=='select':
            items=self.canvas.find_overlapping(e.x-3,e.y-3,e.x+3,e.y+3)
            sid=next((t[2:] for i in reversed(items) for t in self.canvas.gettags(i) if t.startswith('s:')),None)
            self.selected=sid; s=self.current()
            if s: self.drag=('move',x,y,deepcopy(s)); self.checkpoint()
            self.refresh(); return
        if self.tool=='text':
            text=simpledialog.askstring('Text','Beschriftung:',parent=self)
            if text:
                self.checkpoint(); s=Shape('text',x,y,max(20,len(text)*5),10,self.active_layer,'Text',text); self.p.shapes.append(s); self.selected=s.id; self.changed(); self.refresh()
            return
        self.drag=('draw',x,y)
    def motion(self,e):
        if not self.drag: return
        x,y=self.coords(e); kind,a,b,*rest=self.drag
        if kind=='move':
            s=self.current(); old=rest[0]
            if s: s.x=old.x+x-a; s.y=old.y+y-b; self.render()
        else:
            self.canvas.delete('ghost'); self.canvas.create_rectangle(self.ox+a*self.scale,self.oy+b*self.scale,e.x,e.y,outline='#456',dash=(4,3),tags='ghost')
    def release(self,e):
        if not self.drag: return
        kind,a,b,*rest=self.drag; self.drag=None; x,y=self.coords(e)
        if kind=='draw' and abs(x-a)+abs(y-b)>0.5:
            self.checkpoint()
            if self.tool=='line' and (x<a or y<b):
                s=Shape('polyline',min(a,x),min(b,y),abs(x-a),abs(y-b),self.active_layer,'Linie',points=[[a-min(a,x),b-min(b,y)],[x-min(a,x),y-min(b,y)]])
            else: s=Shape(self.tool,min(a,x),min(b,y),abs(x-a),abs(y-b),self.active_layer,{'rect':'Rechteck','ellipse':'Ellipse','line':'Linie'}.get(self.tool,'Objekt'))
            self.p.shapes.append(s); self.selected=s.id; self.changed()
        elif kind=='move': self.changed()
        self.refresh()
    def render(self):
        c=self.canvas; c.delete('all'); z=self.scale; ox=self.ox; oy=self.oy
        c.create_rectangle(ox,oy,ox+self.p.width*z,oy+self.p.height*z,fill='white',outline='#8997a5')
        step=10 if z>=2 else 50
        for x in range(0,int(self.p.width)+1,step): c.create_line(ox+x*z,oy,ox+x*z,oy+self.p.height*z,fill='#edf0f3'); c.create_text(ox+x*z,oy-12,text=str(x),fill='#627180',font=('Segoe UI',8))
        for y in range(0,int(self.p.height)+1,step): c.create_line(ox,oy+y*z,ox+self.p.width*z,oy+y*z,fill='#edf0f3'); c.create_text(ox-18,oy+y*z,text=str(y),fill='#627180',font=('Segoe UI',8))
        for s in self.p.shapes:
            l=next(l for l in self.p.layers if l.id==s.layer)
            if not l.visible: continue
            tags=('s:'+s.id,); width=3 if s.id==self.selected else 1.5
            if s.kind=='text':
                c.create_text(ox+s.x*z,oy+s.y*z,anchor='nw',text=s.text,font=('Segoe UI',max(1,int(s.h*z*0.75))),fill=l.color,tags=tags)
            else:
                pts=outline(s)
                if pts: c.create_line(*[v for x,y in pts for v in (ox+x*z,oy+y*z)],fill=l.color,width=width,tags=tags)
                if self.preview and pts:
                    x,y=pts[0]; c.create_oval(ox+x*z-3,oy+y*z-3,ox+x*z+3,oy+y*z+3,fill='#d77b26',outline='')
        if self.preview: c.create_text(12,12,anchor='nw',text='Konturvorschau · keine Simulation von Füllung, Textpfaden oder Laserwirkung',fill='#8a4c20',font=('Segoe UI',10,'bold'))
    def refresh(self):
        self.loading=True; self.tree.delete(*self.tree.get_children())
        for s in self.p.shapes: self.tree.insert('','end',iid=s.id,text=s.name)
        if self.current(): self.tree.selection_set(self.selected)
        labels=[l.name for l in self.p.layers]; self.layerbox['values']=labels; self.object_layer['values']=labels
        if self.active_layer not in [l.id for l in self.p.layers]: self.active_layer=self.p.layers[0].id
        self.layerbox.current(next(i for i,l in enumerate(self.p.layers) if l.id==self.active_layer)); self.layer_selected()
        s=self.current()
        for k,v in self.vars.items(): v.set(getattr(s,k) if s else '')
        if s: self.object_layer.current(next(i for i,l in enumerate(self.p.layers) if l.id==s.layer))
        else: self.object_layer.set('')
        self.materialbox['values']=list(self.p.extensions.get('materials',{})); self.loading=False; self.render()
    def tree_selected(self,e):
        if self.loading: return
        sel=self.tree.selection()
        if sel and self.selected!=sel[0]: self.selected=sel[0]; self.refresh()
    def apply(self):
        s=self.current()
        if not s: return
        try:
            candidate=deepcopy(self.p); target=next(t for t in candidate.shapes if t.id==s.id)
            for k in ('x','y','w','h'): setattr(target,k,float(self.vars[k].get()))
            target.name=self.vars['name'].get(); target.text=self.vars['text'].get()
            target.layer=candidate.layers[self.object_layer.current()].id
            if target.kind in {'polyline','polygon'}:
                if target.w!=s.w or target.h!=s.h: raise ValueError('Linienzüge: Größenänderung noch nicht verfügbar. X/Y verschiebt die Punkte.')
            candidate.validate(); self.checkpoint(); self.p=candidate; self.changed(); self.refresh()
        except (ValueError,IndexError) as ex: messagebox.showerror('Ungültige Eingabe',str(ex))
    def layer_selected(self):
        i=self.layerbox.current()
        if i<0: return
        l=self.p.layers[i]; self.active_layer=l.id
        for k,v in self.lvars.items(): v.set(getattr(l,k))
        self.mode.set(l.mode); self.visible.set(l.visible)
    def apply_layer(self):
        try:
            p=deepcopy(self.p); l=next(l for l in p.layers if l.id==self.active_layer)
            l.name=self.lvars['name'].get(); l.speed=float(self.lvars['speed'].get()); l.power=float(self.lvars['power'].get()); l.passes=int(self.lvars['passes'].get()); l.mode=self.mode.get(); l.visible=self.visible.get()
            p.validate(); self.checkpoint(); self.p=p; self.changed(); self.refresh()
        except ValueError as ex: messagebox.showerror('Ebene',str(ex))
    def add_layer(self):
        name=simpledialog.askstring('Neue Ebene','Name:',parent=self)
        if name: self.checkpoint(); l=Layer(name); self.p.layers.append(l); self.active_layer=l.id; self.changed(); self.refresh()
    def delete(self):
        if self.current(): self.checkpoint(); self.p.shapes=[s for s in self.p.shapes if s.id!=self.selected]; self.selected=None; self.changed(); self.refresh()
    def duplicate(self):
        s=self.current()
        if s:
            from uuid import uuid4
            self.checkpoint(); s=deepcopy(s); s.id=uuid4().hex; s.x+=5; s.y+=5; s.name+=' Kopie'; self.p.shapes.append(s); self.selected=s.id; self.changed(); self.refresh()
    def align(self,axis):
        s=self.current()
        if not s: return
        if s.kind in {'polyline','polygon','text'}: messagebox.showinfo('Zentrieren','Exakte Zentrierung aktuell für Rechtecke, Ellipsen und Linien verfügbar.'); return
        self.checkpoint(); setattr(s,axis,((self.p.width-s.w)/2 if axis=='x' else (self.p.height-s.h)/2)); self.changed(); self.refresh()
    def undo(self):
        if self.history.undo_stack: self.p=self.history.undo(self.p); self.changed(); self.refresh()
    def redo(self):
        if self.history.redo_stack: self.p=self.history.redo(self.p); self.changed(); self.refresh()
    def fit(self):
        self.scale=max(0.1,min((self.canvas.winfo_width()-85)/self.p.width,(self.canvas.winfo_height()-70)/self.p.height)); self.ox=45; self.oy=35; self.render()
    def wheel(self,e): self.zoom(1.15 if e.delta>0 else 1/1.15,e.x,e.y)
    def zoom(self,f,x,y):
        old=self.scale; self.scale=min(15,max(.15,old*f)); f=self.scale/old; self.ox=x-(x-self.ox)*f; self.oy=y-(y-self.oy)*f; self.render()
    def pan_move(self,e):
        x,y=self.pan; self.ox+=e.x-x; self.oy+=e.y-y; self.pan=(e.x,e.y); self.render()
    def set_preview(self,v): self.preview=v; self.render(); self.status.set('Konturvorschau · kein Maschinencode' if v else 'Gestalten · Offline')
    def check(self):
        issues=checks(self.p); messagebox.showinfo('Projektprüfung','\n'.join(issues) if issues else 'Keine Auffälligkeiten in den unterstützten Konturen.\nMaschinenprofil und Materialeignung noch nicht geprüft.')
    def confirm(self):
        if not self.dirty: return True
        result=messagebox.askyesnocancel('Ungespeicherte Änderungen','Änderungen speichern?')
        return self.save() if result else result is False
    def new(self):
        if self.confirm(): self.p=Project(); self.history=History(); self.selected=None; self.path=None; self.dirty=False; self.title('Steburn · Unbenannt'); self.refresh(); self.fit()
    def open(self):
        if not self.confirm(): return
        path=filedialog.askopenfilename(filetypes=[('Steburn Projekt','*.steburn')])
        if path:
            try:
                p=Project.load(path); self.p=p; self.path=path; self.selected=None; self.history=History(); self.dirty=False; self.title('Steburn · '+p.title); self.refresh(); self.fit()
            except Exception as ex: messagebox.showerror('Öffnen fehlgeschlagen',str(ex))
    def save(self,as_new=False):
        path=self.path if not as_new else None
        path=path or filedialog.asksaveasfilename(defaultextension='.steburn',filetypes=[('Steburn Projekt','*.steburn')])
        if not path: return False
        try:
            self.p.save(path); self.path=path; self.dirty=False; self.title('Steburn · '+self.p.title); self.status.set('Projekt gespeichert'); return True
        except Exception as ex: messagebox.showerror('Speichern fehlgeschlagen',str(ex)); return False
    def import_file(self):
        path=filedialog.askopenfilename(filetypes=[('SVG (einfache Formen)','*.svg')])
        if path:
            try:
                shapes=import_svg(path,self.active_layer); p=deepcopy(self.p); p.shapes.extend(shapes); p.validate(); self.checkpoint(); self.p=p; self.changed(); self.refresh()
            except Exception as ex: messagebox.showerror('Import abgebrochen',str(ex))
    def export_file(self):
        path=filedialog.asksaveasfilename(defaultextension='.svg',filetypes=[('SVG','*.svg')])
        if path:
            try: export_svg(self.p,path); self.status.set('SVG exportiert · keine Maschinendatei')
            except Exception as ex: messagebox.showerror('Export fehlgeschlagen',str(ex))
    def store_material(self):
        name=simpledialog.askstring('Materialvorlage','Material / Dicke / Bearbeitung:',parent=self)
        if not name: return
        self.checkpoint(); l=next(l for l in self.p.layers if l.id==self.active_layer)
        self.p.extensions.setdefault('materials',{})[name]={k:getattr(l,k) for k in ('speed','power','passes','mode')}; self.changed(); self.refresh()
    def use_material(self):
        preset=self.p.extensions.get('materials',{}).get(self.materialbox.get())
        if not preset: return
        try:
            p=deepcopy(self.p); l=next(l for l in p.layers if l.id==self.active_layer)
            for k in ('speed','power','passes','mode'): setattr(l,k,preset[k])
            p.validate(); self.checkpoint(); self.p=p; self.changed(); self.refresh()
        except (ValueError,KeyError) as ex: messagebox.showerror('Materialvorlage',str(ex))
    def close(self):
        if self.confirm(): self.destroy()
