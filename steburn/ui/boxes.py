"""Optional local box designer: parameter editing, assembly schema and cut layout."""
import math,tkinter as tk
from tkinter import ttk,messagebox,filedialog
from dataclasses import asdict
from steburn.ui.widgets import ScrollPanel
from steburn.modules.boxes import BoxSpec,generate,arrange,placed_geometry,into_project,export_page

STYLES={'Rechteckbox':'rect','Vieleck · Schichtbau':'polygon','Runde Dose · Schichtbau':'round','Abgerundet · Schichtbau':'rounded'}
JOINTS={'Fingerzinken':'finger','Stumpfe Klebekanten':'butt'}
CLOSURES={'Oben offen':'open','Geschlossen / verleimt':'closed','Loser Deckel':'loose'}
DIMENSIONS={'Außenmaße':'outer','Innenmaße':'inner'}
LENGTHS=('width','depth','height','thickness','finger','kerf','clearance','radius','gap')

class BoxDialog(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app); self.app=app; self.title('Steburn · Boxen & Gehäuse'); self.geometry('1150x850'); self.minsize(930,700)
        self.result=None; self.placements=[]; self.timer=None; self.ready=False; self.unit_previous='mm'; self.convert_guard=False
        current=app.current(); self.model_id=current.extra.get('box_model') if current else None
        saved=app.p.extensions.get('box_models',{}).get(self.model_id,{})
        params=saved.get('parameters',asdict(BoxSpec()))
        self.values={key:tk.StringVar(value=str(params[key])) for key in (*LENGTHS,'sides','columns','rows','material')}
        self.style=tk.StringVar(value=next(k for k,v in STYLES.items() if v==params['style']))
        self.joint=tk.StringVar(value=next(k for k,v in JOINTS.items() if v==params['joint']))
        self.closure=tk.StringVar(value=next(k for k,v in CLOSURES.items() if v==params['closure']))
        self.dimensions=tk.StringVar(value=next(k for k,v in DIMENSIONS.items() if v==params['dimensions']))
        self.units=tk.StringVar(value='mm'); self.page=tk.StringVar(value='Platte 1'); self.explode=tk.BooleanVar(value=False)
        self.yaw=-.65; self.pitch=.65; self.drag=None
        ttk.Label(self,text='Boxen & Gehäuse',font=('Segoe UI',18,'bold')).pack(anchor='w',padx=18,pady=(14,5))
        ttk.Label(self,text='Parametrisch konstruieren → Schnittteile prüfen → im Projekt weiterbearbeiten. Materialpassprobe vor Fertigung erforderlich.',wraplength=1090).pack(fill='x',padx=18,pady=(0,8))
        pane=ttk.Panedwindow(self,orient='horizontal'); pane.pack(fill='both',expand=True,padx=12)
        panel=ScrollPanel(pane); pane.add(panel,weight=0); panel.canvas.configure(width=300)
        form=panel.content; right=ttk.Frame(pane); pane.add(right,weight=1)
        def combo(label,var,options):
            ttk.Label(form,text=label).pack(anchor='w',padx=8,pady=(7,2))
            widget=ttk.Combobox(form,textvariable=var,values=list(options),state='readonly'); widget.pack(fill='x',padx=8); return widget
        combo('Bauform',self.style,STYLES)
        unitbox=combo('Eingabeeinheit',self.units,['mm','Zoll']); unitbox.bind('<<ComboboxSelected>>',self.change_units)
        combo('Maßbezug',self.dimensions,DIMENSIONS); combo('Deckel',self.closure,CLOSURES)
        self.jointbox=combo('Verbindung · Rechteckbox',self.joint,JOINTS)
        self.width_label=ttk.Label(form,text='Breite'); self.width_label.pack(anchor='w',padx=8,pady=(7,2))
        ttk.Entry(form,textvariable=self.values['width']).pack(fill='x',padx=8)
        self.entries={}
        for key,label in [('depth','Tiefe · Rechteck / abgerundet'),('height','Höhe'),('thickness','Gemessene Materialstärke'),('finger','Fingerbreite · Zielmaß'),('kerf','Gemessener Schnittspalt (Kerf)'),('clearance','Gefachspiel'),('radius','Eckenradius · abgerundet'),('sides','Seitenzahl · Vieleck'),('columns','Gefache: Spalten'),('rows','Gefache: Zeilen'),('gap','Abstand zwischen Schnittteilen'),('material','Materialbezeichnung')]:
            ttk.Label(form,text=label).pack(anchor='w',padx=8,pady=(7,2))
            entry=ttk.Entry(form,textvariable=self.values[key]); entry.pack(fill='x',padx=8); self.entries[key]=entry
        ttk.Label(form,text='Runde Formen werden aus horizontalen Ringen aufgebaut. Höhe wird auf ganze Lagen aufgerundet. Keine automatische Material-/Leistungsempfehlung.',wraplength=265).pack(fill='x',padx=8,pady=12)
        bar=ttk.Frame(right); bar.pack(fill='x',pady=(0,6))
        ttk.Label(bar,text='Schnittplatte:').pack(side='left')
        self.pagebox=ttk.Combobox(bar,textvariable=self.page,state='readonly',width=14); self.pagebox.pack(side='left',padx=6); self.pagebox.bind('<<ComboboxSelected>>',lambda e:self.draw())
        ttk.Checkbutton(bar,text='Explosionsansicht',variable=self.explode,command=self.draw_3d).pack(side='right')
        self.tabs=ttk.Notebook(right); self.tabs.pack(fill='both',expand=True)
        self.flat=tk.Canvas(self.tabs,bg='#f3f6fa',highlightthickness=0); self.three=tk.Canvas(self.tabs,bg='#f3f6fa',highlightthickness=0)
        self.tabs.add(self.flat,text='Schnittteile'); self.tabs.add(self.three,text='3D-Schema · Ziehen zum Drehen')
        self.flat.bind('<Configure>',lambda e:self.draw_flat()); self.three.bind('<Configure>',lambda e:self.draw_3d())
        self.three.bind('<ButtonPress-1>',lambda e:setattr(self,'drag',(e.x,e.y,self.yaw,self.pitch)))
        self.three.bind('<B1-Motion>',self.rotate); self.three.bind('<ButtonRelease-1>',lambda e:setattr(self,'drag',None))
        self.summary=tk.StringVar(); ttk.Label(right,textvariable=self.summary,wraplength=740,padding=6).pack(fill='x')
        self.notes=tk.Text(right,height=5,wrap='word',font=('Segoe UI',9),relief='flat',bg='#edf2f8'); self.notes.pack(fill='x')
        controls=ttk.Frame(self); controls.pack(fill='x',padx=16,pady=12)
        ttk.Button(controls,text='Vorschau aktualisieren',command=self.refresh_preview).pack(side='left')
        self.svg_button=ttk.Button(controls,text='Platte als SVG',command=lambda:self.export('svg')); self.svg_button.pack(side='left',padx=6)
        self.dxf_button=ttk.Button(controls,text='Platte als DXF',command=lambda:self.export('dxf')); self.dxf_button.pack(side='left')
        self.apply_button=ttk.Button(controls,text='Schnittteile übernehmen',command=self.apply,style='Accent.TButton'); self.apply_button.pack(side='right')
        ttk.Button(controls,text='Schließen',command=self.close).pack(side='right',padx=6)
        for var in (*self.values.values(),self.style,self.joint,self.closure,self.dimensions): var.trace_add('write',self.schedule)
        self.style.trace_add('write',self.style_changed)
        self.protocol('WM_DELETE_WINDOW',self.close); self.ready=True; self.refresh_preview()
        if getattr(app,'appearance',None): app.appearance.present(self)
    def style_changed(self,*args):
        if STYLES[self.style.get()]!='rect':
            self.values['columns'].set('1'); self.values['rows'].set('1')
        self.schedule()
    def change_units(self,e=None):
        target=self.units.get()
        if target==self.unit_previous: return
        oldFactor=25.4 if self.unit_previous=='Zoll' else 1.; newFactor=25.4 if target=='Zoll' else 1.
        try: converted={key:float(self.values[key].get().replace(',','.'))*oldFactor/newFactor for key in LENGTHS}
        except ValueError:
            self.units.set(self.unit_previous); messagebox.showerror('Einheit','Zuerst ungültige Maßfelder korrigieren.'); return
        self.convert_guard=True
        for key,value in converted.items(): self.values[key].set(f'{value:.8g}')
        self.unit_previous=target; self.convert_guard=False; self.schedule()
    def schedule(self,*args):
        if not self.ready or self.convert_guard: return
        self.result=None; self.buttons(False)
        if self.timer: self.after_cancel(self.timer)
        self.timer=self.after(300,self.refresh_preview)
    def read_spec(self):
        factor=25.4 if self.units.get()=='Zoll' else 1.
        values={key:float(self.values[key].get().replace(',','.'))*factor for key in LENGTHS}
        values.update({key:int(self.values[key].get()) for key in ('sides','rows','columns')})
        values.update(style=STYLES[self.style.get()],joint=JOINTS[self.joint.get()],closure=CLOSURES[self.closure.get()],dimensions=DIMENSIONS[self.dimensions.get()],material=self.values['material'].get())
        return BoxSpec(**values)
    def buttons(self,enabled):
        if not hasattr(self,'apply_button'): return
        for widget in (self.apply_button,self.svg_button,self.dxf_button): widget.configure(state='normal' if enabled else 'disabled')
    def refresh_preview(self):
        if self.timer: self.after_cancel(self.timer); self.timer=None
        self.result=None; self.placements=[]; self.buttons(False)
        try:
            spec=self.read_spec(); self.result=generate(spec)
            self.jointbox.configure(state='readonly' if spec.style=='rect' else 'disabled')
            for key,enabled in [('depth',spec.style in {'rect','rounded'}),('finger',spec.style=='rect' and spec.joint=='finger'),('radius',spec.style=='rounded'),('sides',spec.style=='polygon'),('columns',spec.style=='rect'),('rows',spec.style=='rect')]: self.entries[key].configure(state='normal' if enabled else 'disabled')
            self.width_label.configure(text='Durchmesser des Eckkreises' if spec.style=='polygon' else 'Durchmesser' if spec.style=='round' else 'Breite')
            self.placements=arrange(self.result,self.app.p.width,self.app.p.height)
            pages=max(v.page for v in self.placements)+1; self.pagebox['values']=[f'Platte {i+1}' for i in range(pages)]
            if self.page.get() not in self.pagebox['values']: self.page.set('Platte 1')
            outer=' × '.join(f'{v:.1f}' for v in self.result.outer); inner=' × '.join(f'{v:.1f}' for v in self.result.inner)
            self.summary.set(f'Außen: {outer} mm · Innen: {inner} mm\n{len(self.result.parts)} Teile auf {pages} Schnittplatte(n) à {self.app.p.width:g} × {self.app.p.height:g} mm')
            self.notes.configure(state='normal'); self.notes.delete('1.0','end'); self.notes.insert('1.0','\n'.join(self.result.warnings)); self.notes.configure(state='disabled')
            self.buttons(True)
        except Exception as ex:
            self.summary.set('Eingabe / Plattenlayout prüfen: '+str(ex))
        self.draw()
    def current_page(self):
        try: return int(self.page.get().split()[-1])-1
        except (ValueError,IndexError): return 0
    def draw(self): self.draw_flat(); self.draw_3d()
    def draw_flat(self):
        c=self.flat; c.delete('all')
        W,H=self.app.p.width,self.app.p.height
        z=max(.01,min((c.winfo_width()-50)/W,(c.winfo_height()-50)/H))
        def xy(x,y): return 25+x*z,25+(H-y)*z
        c.create_rectangle(*xy(0,H),*xy(W,0),fill='white',outline='#bac7d7')
        if not self.result: return
        for v in self.placements:
            if v.page!=self.current_page(): continue
            part=self.result.parts[v.part]; geo=placed_geometry(part,v)
            for i,ring in enumerate([geo.exterior,*geo.interiors]):
                coords=[n for x,y in ring.coords for n in xy(x,y)]
                c.create_polygon(*coords,fill='#f6dfb7' if i==0 else 'white',outline='#c34a3f',width=1)
            a,b,d,e=geo.bounds; c.create_text(*xy((a+d)/2,(b+e)/2),text=part.name,width=max(20,(d-a)*z-4),font=('Segoe UI',9),fill='#3c4655')
    def rotate(self,e):
        if self.drag:
            x,y,yaw,pitch=self.drag; self.yaw=yaw+(e.x-x)*.01; self.pitch=max(.12,min(1.45,pitch+(e.y-y)*.008)); self.draw_3d()
    def draw_3d(self):
        c=self.three; c.delete('all')
        if not self.result: return
        lines=[]; projected=[]
        def project(point):
            x,y,z=point; a=math.cos(self.yaw)*x-math.sin(self.yaw)*y
            b=math.sin(self.yaw)*x+math.cos(self.yaw)*y
            return a,math.sin(self.pitch)*b-math.cos(self.pitch)*z
        for part in self.result.parts:
            geo=part.nominal.simplify(.25,preserve_topology=True)
            offset=0.
            if self.explode.get():
                step=max(self.result.outer)*.06
                offset=-step if part.role=='base' else step*(part.origin[2]/max(1,part.thickness)*.25+1) if part.plane=='xy' else (-step if (part.origin[1] if part.plane=='xz' else part.origin[0])==0 else step)
            for ring in [geo.exterior,*geo.interiors]:
                first=[project(part.point3(x,y,offset)) for x,y in ring.coords]
                last=[project(part.point3(x,y,part.thickness+offset)) for x,y in ring.coords]
                lines.extend([first,last]); projected.extend(first+last)
                for a,b in zip(first,last): lines.append([a,b])
        if not projected: return
        a=min(x for x,y in projected); b=min(y for x,y in projected); d=max(x for x,y in projected); e=max(y for x,y in projected)
        z=max(.01,min((c.winfo_width()-60)/max(1,d-a),(c.winfo_height()-60)/max(1,e-b)))
        for line in lines: c.create_line(*[n for x,y in line for n in (30+(x-a)*z,30+(y-b)*z)],fill='#8b6541',width=1)
        c.create_text(12,12,anchor='nw',text='3D-Schema · nominale Geometrie, ohne Schnittspalt',fill='#53657d')
    def export(self,kind):
        self.refresh_preview()
        if not self.result or not self.placements: return
        path=filedialog.asksaveasfilename(parent=self,defaultextension='.'+kind,filetypes=[(kind.upper(),'*.'+kind)],initialfile=f'Steburn-Box-Platte-{self.current_page()+1}.{kind}')
        if path:
            try: export_page(path,self.result,self.placements,self.app.p.width,self.app.p.height,self.current_page(),kind)
            except Exception as ex: messagebox.showerror('Export',str(ex))
    def apply(self):
        self.refresh_preview()
        if not self.result or not self.placements: return
        if self.model_id and not messagebox.askokcancel('Modell neu erzeugen','Alle Schnittteile dieses Boxmodells werden ersetzt. Nachträgliche Konturänderungen an diesen Teilen gehen verloren. Andere Projektobjekte bleiben erhalten.'): return
        try:
            p,mid,lid=into_project(self.app.p,self.result,self.placements,self.model_id)
            self.app.active_layer=lid; self.app.selection={s.id for s in p.shapes if s.layer==lid}; self.app.selected=next(iter(self.app.selection),None)
            self.app.commit(p); self.app.set_tool('select'); self.app.fit()
            messagebox.showinfo('Box übernommen','Jede Schnittplatte liegt in einer eigenen Ebene. Ausgabe AUS und Leistung 0, bis du die Parameter geprüft hast.\n\nTeile sind gruppiert. Für einzelne Änderungen Gruppierung aufheben. Boxparameter bleiben gespeichert; Rechtsklick auf ein Teil → Boxparameter bearbeiten.'); self.close()
        except Exception as ex: messagebox.showerror('Boxen',str(ex))
    def close(self):
        if self.timer: self.after_cancel(self.timer)
        self.destroy()
