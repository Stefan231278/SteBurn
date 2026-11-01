"""Calibration coupon preview, isolated job and measured result notebook."""
import tkinter as tk
from tkinter import ttk,filedialog
from dataclasses import asdict
from pathlib import Path
import json,math,queue
from steburn.core.material_test import TestSpec,generate,save_session,export_results,label_project,export_assignment
from steburn.core.paths import shape_paths
from steburn.core.planner import build_plan

class MaterialTestWindow(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app); self.app=app; self.project=None; self.session=None; self.session_path=None
        self.loading=False; self.result_timer=None; self.editing_cell=None
        self.motion_events=queue.Queue(); self.motion_poll=None; self.pointer_position=None
        self.title('Materialtest · Schnitt & Gravur'); self.geometry(f'1160x700+{max(0,app.winfo_rootx()+10)}+{max(0,app.winfo_rooty()+10)}'); self.minsize(960,620)
        header=ttk.Frame(self,style='Studio.Dark.TFrame',padding=(14,10)); header.pack(fill='x')
        ttk.Label(header,text='MATERIALTEST  /  SCHNITT & GRAVUR',style='Studio.Dark.TLabel',font=('Segoe UI',15,'bold')).pack(side='left')
        self.info=tk.StringVar(value='15 Schnittfelder + 15 Gravurfelder. Ergebnisse werden nach dem Versuch am Material beurteilt.')
        footer=ttk.Frame(self,padding=10); footer.pack(side='bottom',fill='x')
        ttk.Button(footer,text='Schließen',style='Compact.TButton',command=self.close).pack(side='left')
        ttk.Button(footer,text='Ergebnisse als CSV',style='Compact.TButton',command=self.export_csv).pack(side='left',padx=5)
        ttk.Button(footer,text='Zuordnung als Bild …',style='Compact.TButton',command=self.export_map).pack(side='left',padx=5)
        ttk.Button(footer,text='Nur Beschriftung testen',style='Compact.TButton',command=self.test_labels).pack(side='left',padx=5)
        self.cockpit_button=ttk.Button(footer,text='Prüfmuster im Cockpit öffnen',style='Accent.TButton',command=self.open_cockpit,state='disabled'); self.cockpit_button.pack(side='right')
        ttk.Label(self,textvariable=self.info,wraplength=1100,padding=(12,5)).pack(side='bottom',fill='x')
        tabs=ttk.Notebook(self); tabs.pack(fill='both',expand=True,padx=10,pady=8); self.tabs=tabs
        preview=ttk.Frame(tabs); results=ttk.Frame(tabs); tabs.add(preview,text='Prüfmuster & Werte'); tabs.add(results,text='Gemessene Ergebnisse')
        preview.columnconfigure(1,weight=1); preview.rowconfigure(0,weight=1)
        controls=ttk.LabelFrame(preview,text='Versuchsparameter',padding=10); controls.grid(row=0,column=0,sticky='ns',padx=(0,10))
        layer=next(l for l in app.p.layers if l.id==app.active_layer)
        def existing(key,default):
            value=app.material_vars[key].get().strip() if hasattr(app,'material_vars') and key in app.material_vars else ''
            return value or default
        try: maximum=float(existing('power',str(layer.power))); maximum=maximum if maximum>0 else layer.power or 20
        except ValueError: maximum=layer.power or 20
        powers='; '.join(f'{maximum*i/5:g}' for i in range(1,6))
        speed=layer.speed
        self.vars={key:tk.StringVar(value=value) for key,value in dict(material=existing('material','Materialprobe'),thickness=existing('thickness','0'),powers=powers,cut_speeds='; '.join(f'{speed*i:g}' for i in (.5,1,1.5)),engrave_speeds='; '.join(f'{speed*i:g}' for i in (1,1.5,2)),cut_passes='1',engrave_passes='1',interval='.2',x='20',y='20',size='50',label_power='20',label_speed='600').items()}
        fields=[('material','Material'),('thickness','Dicke (mm; 0 unbekannt)'),('powers','5 Leistungen (%) · ; getrennt'),('cut_speeds','3 Schnittvorschübe (mm/min)'),('engrave_speeds','3 Gravurvorschübe (mm/min)'),('cut_passes','Durchgänge Schnitt'),('engrave_passes','Durchgänge Gravur'),('interval','Gravurabstand (mm)'),('x','Position X (mm)'),('y','Position Y (mm)'),('size','Testgröße (mm; 50–300)'),('label_power','Beschriftung (%)'),('label_speed','Beschriftung (mm/min)')]
        for row,(key,label) in enumerate(fields):
            ttk.Label(controls,text=label).grid(row=row,column=0,sticky='w',padx=(0,8),pady=2)
            ttk.Entry(controls,textvariable=self.vars[key],width=24).grid(row=row,column=1,sticky='ew',pady=2)
        ttk.Button(controls,text='Neues Prüfmuster erzeugen',style='Compact.TButton',command=self.generate).grid(row=len(fields),column=0,columnspan=2,sticky='ew',pady=10)
        ttk.Label(controls,text='Beschriftung vorab separat testen (materialabhängig).\nSchrift: konstante Leistung; Schnitt zuletzt.\nTiefe und Schnittqualität selbst messen.',wraplength=360,style='Studio.Muted.TLabel').grid(row=len(fields)+1,column=0,columnspan=2,sticky='ew')
        self.canvas=tk.Canvas(preview,bg='#e6ebf3',highlightthickness=0); self.canvas.grid(row=0,column=1,sticky='nsew'); self.canvas.bind('<Configure>',lambda e:self.draw()); self.canvas.bind('<Button-1>',self.click_preview)
        self.build_results(results)
        position=ttk.Frame(tabs); tabs.add(position,text='Position auf Werkstück'); self.build_position(position)
        self.protocol('WM_DELETE_WINDOW',self.close)
        if app.appearance: app.appearance.present(self)
        self.after_idle(self.fit_monitor)
        self.after_idle(self.generate)
        self.poll_motion()
    def fit_monitor(self):
        try: self.state('zoomed')
        except tk.TclError: self.geometry(f'{self.winfo_screenwidth()-40}x{self.winfo_screenheight()-100}+10+10')
    @staticmethod
    def parse_values(value): return tuple(float(v.strip().replace(',','.')) for v in value.split(';') if v.strip())
    def form(self):
        number=lambda key:float(self.vars[key].get().replace(',','.'))
        return TestSpec(material=self.vars['material'].get().strip(),thickness=number('thickness'),powers=self.parse_values(self.vars['powers'].get()),cut_speeds=self.parse_values(self.vars['cut_speeds'].get()),engrave_speeds=self.parse_values(self.vars['engrave_speeds'].get()),cut_passes=int(self.vars['cut_passes'].get()),engrave_passes=int(self.vars['engrave_passes'].get()),interval=number('interval'),x=number('x'),y=number('y'),size=number('size'),label_power=number('label_power'),label_speed=number('label_speed'))
    def generate(self):
        try:
            self.save_result(); self.save()
            if self.project is not None and json.dumps(asdict(self.form()),sort_keys=True)==json.dumps(asdict(TestSpec(**self.session['test']['spec'])),sort_keys=True):
                self.draw(); self.draw_position(); return True
            project=generate(self.form(),self.app.p.width,self.app.p.height); test=project.extensions['material_test']
            self.project=project; self.session=dict(version=1,test=test,observations={})
            self.session_path=Path(self.app.library.path).parent/'material-tests'/f'{test["id"]}.json'
            self.save(); self.populate_results(); self.draw(); self.draw_position(); self.cockpit_button.configure(state='normal')
            plan=build_plan(project,preview=False)
            size=test['size_mm'][0]; self.info.set(f'{size:g} × {size:g} mm bei X {test["spec"]["x"]:g} / Y {test["spec"]["y"]:g} · 30 Felder · ca. {plan.duration/60:.1f} min. Eigenständiger Testjob; vorhandene Zeichnung bleibt erhalten.')
            return True
        except (ValueError,OSError) as ex: self.info.set(str(ex)); return False
    def draw(self):
        c=self.canvas; c.delete('all')
        if not self.project: return
        spec=self.project.extensions['material_test']['spec']; x,y=spec['x'],spec['y']; size=spec.get('size',50)
        scale=max(.1,min((c.winfo_width()-50)/size,(c.winfo_height()-50)/size)); ox=(c.winfo_width()-size*scale)/2; oy=(c.winfo_height()-size*scale)/2
        self.preview_transform=(ox,oy,scale,x,y,size)
        xy=lambda point:(ox+(point[0]-x)*scale,oy+(size-(point[1]-y))*scale)
        c.create_rectangle(ox,oy,ox+size*scale,oy+size*scale,fill='white',outline='#cbd5e1')
        for s in self.project.shapes:
            color='#df493b' if s.extra.get('processing',{}).get('operation')=='cut' else '#1878d1' if s.extra.get('processing',{}).get('operation')=='engrave' else '#64748b'
            if s.kind=='rect' and s.extra.get('processing',{}).get('operation')=='engrave':
                fill='#294869' if getattr(getattr(self.app,'theme',None),'dark',False) else '#dbeafe'
                c.create_rectangle(*xy((s.x,s.y+s.h)),*xy((s.x+s.w,s.y)),fill=fill,outline='')
            for path in shape_paths(s): c.create_line(*[v for point in path for v in xy(point)],fill=color,width=1.4)
        c.create_text(ox,oy-12,text=f'{size:g} mm · Schnitt oben / Gravur unten',anchor='w',fill='#64748b')
        if hasattr(self.app,'theme'): self.app.theme.style_canvas(c)
    def click_preview(self,e):
        if not self.session or not hasattr(self,'preview_transform'): return
        ox,oy,scale,x,y,size=self.preview_transform; px=x+(e.x-ox)/scale; py=y+size-(e.y-oy)/scale
        for cell in self.session['test']['cells']:
            if cell['x']<=px<=cell['x']+cell['w'] and cell['y']<=py<=cell['y']+cell['h']:
                self.tree.selection_set(cell['id']); self.tree.see(cell['id']); self.tabs.select(1); return
    def build_position(self,parent):
        bar=ttk.Frame(parent,padding=8); bar.pack(fill='x')
        for key,label in [('x','X'),('y','Y'),('size','Größe')]:
            ttk.Label(bar,text=label+' (mm)').pack(side='left',padx=(8,3)); ttk.Entry(bar,textvariable=self.vars[key],width=8).pack(side='left')
            self.vars[key].trace_add('write',lambda *args:self.draw_position())
        ttk.Button(bar,text='Position übernehmen',command=self.generate,style='Compact.TButton').pack(side='left',padx=8)
        ttk.Button(bar,text='Testfläche rahmen',command=self.frame_test,style='Compact.TButton').pack(side='left')
        ttk.Button(bar,text='Rahmen stoppen',command=self.app.stop_frame,style='Compact.TButton').pack(side='left',padx=5)
        pointer=ttk.Frame(parent,padding=8); pointer.pack(fill='x')
        self.position_mode=tk.StringVar(value='place')
        ttk.Radiobutton(pointer,text='Testfläche verschieben',variable=self.position_mode,value='place').pack(side='left')
        ttk.Radiobutton(pointer,text='Mausfahrt / Pointer (Klick fährt Kopf)',variable=self.position_mode,value='pointer').pack(side='left',padx=10)
        ttk.Checkbutton(pointer,text='Pointerlicht am Ziel (0,15 s)',variable=self.app.pointer_light_var).pack(side='left',padx=8)
        ttk.Spinbox(pointer,from_=.01,to=.5,increment=.01,textvariable=self.app.pointer_power,width=6).pack(side='left')
        ttk.Label(pointer,text='% · max. 0,5 % · kann Spuren erzeugen').pack(side='left',padx=6)
        work=ttk.Frame(parent,padding=(8,0)); work.pack(fill='x')
        ttk.Label(work,text='Werkstück (nur Orientierung):').pack(side='left')
        self.workpiece={k:tk.StringVar(value=str(v)) for k,v in dict(x=5,y=5,w=self.app.p.width-10,h=self.app.p.height-10).items()}
        for key,label in [('x','X'),('y','Y'),('w','Breite'),('h','Höhe')]:
            ttk.Label(work,text=label).pack(side='left',padx=(8,3)); ttk.Entry(work,textvariable=self.workpiece[key],width=7).pack(side='left')
            self.workpiece[key].trace_add('write',lambda *args:self.draw_position())
        ttk.Label(parent,text='Werkstückmaße und Lage am Gerät eingeben. Orange Testfläche ziehen oder zum Platzieren klicken. X/Y = linke untere Ecke; kein Nullpunkt wird verändert. Grau: vorhandene Zeichnung, wird nicht mitgelasert.',wraplength=1050,padding=8).pack(fill='x')
        self.position_canvas=tk.Canvas(parent,bg='#e6ebf3',highlightthickness=0); self.position_canvas.pack(fill='both',expand=True,padx=8,pady=8)
        self.position_canvas.bind('<Configure>',lambda e:self.draw_position()); self.position_canvas.bind('<Button-1>',self.position_press)
        self.position_canvas.bind('<B1-Motion>',self.position_drag); self.position_canvas.bind('<ButtonRelease-1>',self.position_release)
        self.drag_offset=None
    def draw_position(self):
        if not hasattr(self,'position_canvas'): return
        c=self.position_canvas; c.delete('all'); width,height=self.app.p.width,self.app.p.height
        scale=max(.01,min((c.winfo_width()-60)/width,(c.winfo_height()-50)/height)); ox=(c.winfo_width()-width*scale)/2; oy=22
        self.bed_transform=(ox,oy,scale,height)
        xy=lambda x,y:(ox+x*scale,oy+(height-y)*scale)
        c.create_rectangle(*xy(0,height),*xy(width,0),fill='white',outline='#64748b')
        for x in range(0,int(width)+1,50): c.create_line(*xy(x,0),*xy(x,height),fill='#e2e8f0'); c.create_text(*xy(x,0),text=str(x),anchor='n',fill='#64748b')
        for y in range(0,int(height)+1,50): c.create_line(*xy(0,y),*xy(width,y),fill='#e2e8f0'); c.create_text(ox-5,oy+(height-y)*scale,text=str(y),anchor='e',fill='#64748b')
        for shape in self.app.p.shapes[:1000]:
            for path in shape_paths(shape):
                if len(path)>1: c.create_line(*[v for x,y in path for v in xy(x,y)],fill='#94a3b8')
        try:
            work={k:float(v.get().replace(',','.')) for k,v in self.workpiece.items()}
            if all(math.isfinite(v) for v in work.values()) and work['w']>0 and work['h']>0:
                c.create_rectangle(*xy(work['x'],work['y']+work['h']),*xy(work['x']+work['w'],work['y']),outline='#239461',width=2,dash=(6,3))
            x,y,size=(float(self.vars[k].get().replace(',','.')) for k in ('x','y','size'))
            if not all(math.isfinite(v) for v in (x,y,size)) or size<=0: return
            valid=50<=size<=300 and 5<=x<=width-size-5 and 5<=y<=height-size-5
            fits=work['x']<=x and work['y']<=y and x+size<=work['x']+work['w'] and y+size<=work['y']+work['h']
            c.create_rectangle(*xy(x,y+size),*xy(x+size,y),outline='#ed861f' if valid and fits else '#dc2626',width=3,fill='#ffe4c4',stipple='gray25')
            c.create_text(*xy(x+size/2,y+size/2),text=f'TEST\n{size:g} × {size:g} mm\nX {x:g} / Y {y:g}',fill='#a54e09',font=('Segoe UI',10,'bold'))
            c.create_text(10,10,text='Maschinenfläche · Raster 50 mm'+(' · Test liegt außerhalb des Werkstücks' if not fits else ''),anchor='nw',fill='#64748b' if fits else '#dc2626')
        except ValueError: pass
        if self.pointer_position is not None and self.app.device.homed and self.app.device.origin_confirmed:
            px,py=xy(*self.pointer_position)
            c.create_line(px-10,py,px+10,py,fill='#b038ba',width=2); c.create_line(px,py-10,px,py+10,fill='#b038ba',width=2)
            c.create_oval(px-7,py-7,px+7,py+7,outline='#b038ba',width=2)
        if hasattr(self.app,'theme'): self.app.theme.style_canvas(c)
    def bed_point(self,e):
        ox,oy,scale,height=self.bed_transform; return (e.x-ox)/scale,height-(e.y-oy)/scale
    def position_press(self,e):
        if self.position_mode.get()=='pointer': self.pointer_to(self.bed_point(e)); return
        try:
            px,py=self.bed_point(e); x,y,size=(float(self.vars[k].get().replace(',','.')) for k in ('x','y','size'))
            self.drag_offset=(px-x,py-y) if x<=px<=x+size and y<=py<=y+size else (size/2,size/2)
            self.position_drag(e)
        except (ValueError,AttributeError): self.drag_offset=None
    def position_drag(self,e):
        if self.drag_offset is None: return
        try:
            px,py=self.bed_point(e); size=float(self.vars['size'].get().replace(',','.'))
            if not math.isfinite(size) or not 50<=size<=min(300,self.app.p.width-10,self.app.p.height-10): return
            x=max(5,min(self.app.p.width-size-5,px-self.drag_offset[0])); y=max(5,min(self.app.p.height-size-5,py-self.drag_offset[1]))
            self.vars['x'].set(f'{x:.1f}'); self.vars['y'].set(f'{y:.1f}')
        except ValueError: pass
    def position_release(self,e):
        if self.drag_offset is not None: self.position_drag(e); self.drag_offset=None; self.generate()
    def pointer_to(self,point):
        if self.app.busy: self.info.set('Zuerst die aktive Fahrt stoppen oder den Job beenden.'); return
        from steburn.core.job_errors import remedy
        try:
            self.app.device.check_targets([point],self.app.p.width,self.app.p.height)
            visible=self.app.pointer_light_var.get(); power=float(self.app.pointer_power.get().replace(',','.'))
            if not self.app.device.connected or not self.app.device.homed or not self.app.device.origin_confirmed: raise ValueError('Nicht verbunden' if not self.app.device.connected else 'Referenzfahrt erforderlich: '+self.app.device.safety_reason)
            self.app.frame_active=True
            def run():
                try:
                    result=self.app.device.pointer_move(point,self.app.p.width,self.app.p.height,visible,power)
                    self.motion_events.put((True,result,self.app.device.last_position)); return result
                except Exception as ex: self.motion_events.put((False,str(ex),None)); raise
                finally: self.app.frame_active=False
            self.app.run_device(run); self.info.set(f'Pointer fährt nach X {point[0]:.2f} / Y {point[1]:.2f} mm …')
        except (ValueError,OSError) as ex: self.info.set(str(ex)+' · '+remedy(ex,self.app.device))
    def poll_motion(self):
        from steburn.core.job_errors import remedy
        try:
            while True:
                ok,message,position=self.motion_events.get_nowait()
                if ok: self.pointer_position=position; self.info.set(message); self.draw_position()
                else: self.info.set(message+' · '+remedy(message,self.app.device))
        except queue.Empty: pass
        self.motion_poll=self.after(100,self.poll_motion)
    def frame_test(self):
        if self.app.busy: self.info.set('Zuerst den laufenden Geräteauftrag beenden.'); return
        if not self.ensure_project(): return
        from steburn.core.job_errors import remedy
        if not self.app.device.connected or not self.app.device.homed or not self.app.device.origin_confirmed:
            reason='Kein Gerät verbunden.' if not self.app.device.connected else 'Referenzfahrt erforderlich: '+self.app.device.safety_reason
            self.info.set(reason+' '+remedy(reason,self.app.device)); return
        spec=self.session['test']['spec']; x,y,size=spec['x'],spec['y'],spec.get('size',50)
        points=[(x,y),(x+size,y),(x+size,y+size),(x,y+size),(x,y)]
        self.app.frame_active=True
        def run():
            try:
                result=self.app.device.frame_loop(points,self.app.p.width,self.app.p.height); self.motion_events.put((True,result,self.app.device.last_position)); return result
            except Exception as ex: self.motion_events.put((False,str(ex),None)); raise
            finally: self.app.frame_active=False
        self.app.run_device(run); self.info.set('Testfläche wird wiederholt gerahmt. Mit „Rahmen stoppen“ beenden. Rahmenlicht wie unter Vorbereitung eingestellt.')
    def build_results(self,parent):
        parent.columnconfigure(0,weight=1); parent.rowconfigure(0,weight=1)
        columns=('id','operation','power','speed','passes','depth','cut','quality')
        self.tree=ttk.Treeview(parent,columns=columns,show='headings',selectmode='browse')
        for key,label,width in [('id','Feld',55),('operation','Art',85),('power','%',50),('speed','mm/min',80),('passes','x',35),('depth','Tiefe mm',75),('cut','Durch',65),('quality','Bewertung',130)]: self.tree.heading(key,text=label); self.tree.column(key,width=width)
        self.tree.grid(row=0,column=0,sticky='nsew',padx=(0,8)); self.tree.bind('<<TreeviewSelect>>',self.select_cell)
        bar=ttk.Scrollbar(parent,command=self.tree.yview); bar.grid(row=0,column=1,sticky='ns'); self.tree.configure(yscrollcommand=bar.set)
        form=ttk.LabelFrame(parent,text='Am Werkstück beurteilen',padding=12); form.grid(row=0,column=2,sticky='ns',padx=8)
        self.selected_info=tk.StringVar(value='Feld auswählen'); ttk.Label(form,textvariable=self.selected_info,wraplength=280,font=('Segoe UI',10,'bold')).pack(fill='x',pady=5)
        self.depth=tk.StringVar(); self.through=tk.StringVar(value='Ungeprüft'); self.quality=tk.StringVar(value='Unbewertet'); self.notes=tk.StringVar()
        for label,var in [('Gemessene Tiefe (mm)',self.depth),('Notizen',self.notes)]: ttk.Label(form,text=label).pack(anchor='w',pady=(10,2)); ttk.Entry(form,textvariable=var,width=31).pack(fill='x')
        ttk.Label(form,text='Vollständig durchgeschnitten?').pack(anchor='w',pady=(10,2))
        ttk.Combobox(form,textvariable=self.through,values=['Ungeprüft','Ja','Nein'],state='readonly').pack(fill='x')
        ttk.Label(form,text='Bearbeitungsqualität').pack(anchor='w',pady=(10,2))
        ttk.Combobox(form,textvariable=self.quality,values=['Unbewertet','Gut','Zu schwach','Zu stark','Verbrannt'],state='readonly').pack(fill='x')
        ttk.Label(form,text='Keine automatische Tiefenmessung.\nBeobachtungen werden je Feld gespeichert.',wraplength=280,style='Studio.Muted.TLabel').pack(fill='x',pady=12)
        ttk.Button(form,text='Feld als Materialprofil speichern',style='Accent.TButton',command=self.store_profile).pack(fill='x',pady=5)
        ttk.Button(form,text='Gespeicherten Versuch laden …',style='Compact.TButton',command=self.load_session).pack(fill='x',pady=5)
        for var in (self.depth,self.through,self.quality,self.notes): var.trace_add('write',self.schedule_result)
    def populate_results(self):
        self.loading=True; self.editing_cell=None; self.tree.delete(*self.tree.get_children())
        for cell in self.session['test']['cells']:
            self.tree.insert('','end',iid=cell['id'],values=self.row_values(cell))
        self.loading=False
    def row_values(self,cell):
        result=self.session.get('observations',{}).get(cell['id'],{})
        return (cell['id'],'Schnitt' if cell['operation']=='cut' else 'Gravur',f'{cell["power"]:g}',f'{cell["speed"]:g}',cell['passes'],result.get('depth_mm','') if result.get('depth_mm') is not None else '',{'True':'Ja','False':'Nein'}.get(str(result.get('cut_through')),'—'),result.get('quality','Unbewertet'))
    def select_cell(self,e=None):
        rows=self.tree.selection()
        if self.loading or not rows: return
        if self.editing_cell==rows[0]: return
        self.save_result()
        self.loading=True
        self.editing_cell=rows[0]
        result=self.session['observations'].get(rows[0],{}); cell=next(c for c in self.session['test']['cells'] if c['id']==rows[0])
        self.selected_info.set(f'{cell["id"]} · {cell["power"]:g} % / {cell["speed"]:g} mm/min / {cell["passes"]}×')
        self.depth.set('' if result.get('depth_mm') is None else str(result['depth_mm'])); self.through.set({True:'Ja',False:'Nein'}.get(result.get('cut_through'),'Ungeprüft')); self.quality.set(result.get('quality','Unbewertet')); self.notes.set(result.get('notes',''))
        self.loading=False
    def schedule_result(self,*args):
        if self.loading: return
        if self.result_timer: self.after_cancel(self.result_timer)
        self.result_timer=self.after(300,self.save_result)
    def save_result(self):
        if self.result_timer: self.after_cancel(self.result_timer); self.result_timer=None
        if self.loading or not self.session or self.editing_cell is None: return
        try:
            value=self.depth.get().strip(); depth=float(value.replace(',','.')) if value else None
            if depth is not None and (not math.isfinite(depth) or depth<0): raise ValueError('Tiefe muss eine nichtnegative Zahl sein.')
            identifier=self.editing_cell
            self.session['observations'][identifier]=dict(depth_mm=depth,cut_through={'Ja':True,'Nein':False}.get(self.through.get()),quality=self.quality.get(),notes=self.notes.get())
            cell=next(c for c in self.session['test']['cells'] if c['id']==identifier); self.tree.item(identifier,values=self.row_values(cell)); self.save()
        except (ValueError,OSError) as ex: self.info.set(str(ex))
    def save(self):
        if not self.session: return
        if hasattr(self,'workpiece'): self.session['workpiece']={key:var.get() for key,var in self.workpiece.items()}
        report=getattr(self.app,'last_job_report',None)
        if report:
            try:
                data=json.loads(Path(report).read_text(encoding='utf-8'))
                if (data.get('material_test') or {}).get('id')==self.session['test']['id'] and (data.get('material_test') or {}).get('phase')!='labels_only': self.session['job_report']=report
            except (OSError,ValueError): pass
        save_session(self.session_path,self.session)
    def ensure_project(self):
        try:
            if self.project is None or json.dumps(asdict(self.form()),sort_keys=True)!=json.dumps(asdict(TestSpec(**self.session['test']['spec'])),sort_keys=True):
                return self.generate()
            return True
        except (ValueError,OSError) as ex: self.info.set(str(ex)); return False
    def open_cockpit(self):
        if self.app.busy: self.info.set('Zuerst den laufenden Geräteauftrag beenden.'); return
        try:
            if not self.ensure_project(): return
            if self.project is None: return
            if self.app.job_window and self.app.job_window.winfo_exists(): self.app.job_window.close()
            from steburn.ui.cockpit import Cockpit
            self.app.job_window=Cockpit(self.app,project=self.project)
        except (ValueError,OSError) as ex: self.info.set(str(ex))
    def test_labels(self):
        if self.app.busy: self.info.set('Zuerst den laufenden Geräteauftrag beenden.'); return
        if not self.ensure_project(): return
        self.save()
        if self.app.job_window and self.app.job_window.winfo_exists(): self.app.job_window.close()
        from steburn.ui.cockpit import Cockpit
        self.app.job_window=Cockpit(self.app,project=label_project(self.project))
    def export_map(self):
        if not self.ensure_project(): return
        path=filedialog.asksaveasfilename(parent=self,defaultextension='.png',filetypes=[('Zuordnung','*.png')])
        if path:
            try: export_assignment(path,self.session); self.info.set('Zuordnung gespeichert: '+path)
            except (OSError,ValueError) as ex: self.info.set(str(ex))
    def store_profile(self):
        self.save_result()
        if not self.session or not self.tree.selection(): return
        identifier=self.tree.selection()[0]; result=self.session['observations'].get(identifier,{})
        if result.get('depth_mm') is None and result.get('cut_through') is None and result.get('quality','Unbewertet')=='Unbewertet' and not result.get('notes'): self.info.set('Feld zuerst am Material beurteilen.'); return
        cell=next(c for c in self.session['test']['cells'] if c['id']==identifier); spec=self.session['test']['spec']
        preset=dict(name=f'{spec["material"]} · {spec["thickness"]:g} mm · {identifier} · {cell["power"]:g}%/{cell["speed"]:g}',material=spec['material'],thickness=spec['thickness'],operation=cell['operation'],mode='Fläche' if cell['operation']=='engrave' else 'Kontur',speed=cell['speed'],power=cell['power'],passes=cell['passes'],interval=spec['interval'],air=False,test_id=self.session['test']['id'],cell_id=identifier,observation=result)
        try:
            library=self.app.library.read(); library[preset['name']]=preset; self.app.library.write(library); self.app.refresh_materials(); self.info.set('Erprobtes Feld als Materialprofil gespeichert: '+preset['name'])
        except (ValueError,OSError) as ex: self.info.set(str(ex))
    def export_csv(self):
        self.save_result()
        if not self.session: return
        path=filedialog.asksaveasfilename(parent=self,defaultextension='.csv',filetypes=[('Ergebnisse','*.csv')])
        if path:
            try: export_results(path,self.session); self.info.set('Ergebnisse exportiert: '+path)
            except OSError as ex: self.info.set(str(ex))
    def load_session(self):
        self.save_result()
        path=filedialog.askopenfilename(parent=self,initialdir=Path(self.app.library.path).parent/'material-tests',filetypes=[('Materialversuch','*.json')])
        if not path: return
        try:
            data=json.loads(Path(path).read_text(encoding='utf-8')); spec=TestSpec(**data['test']['spec'])
            project=generate(spec,self.app.p.width,self.app.p.height,pattern_version=data['test'].get('pattern_version',1))
            check=project.extensions['material_test']
            if data['test'].get('pattern_hash')!=check['pattern_hash'] or data['test'].get('cells')!=check['cells']: raise ValueError('Versuchsdaten passen nicht zum reproduzierbaren Prüfmuster.')
            project.extensions['material_test']=data['test']
            for shape in project.shapes: shape.extra['group']=data['test']['id']
            self.project=project; self.session=data; self.session_path=Path(path)
            for key,var in self.vars.items():
                value=getattr(spec,key); var.set('; '.join(f'{v:g}' for v in value) if isinstance(value,(list,tuple)) else str(value))
            for key,value in data.get('workpiece',{}).items():
                if key in self.workpiece: self.workpiece[key].set(str(value))
            self.populate_results(); self.draw(); self.draw_position(); self.cockpit_button.configure(state='normal'); self.info.set('Gespeicherter Versuch geladen.')
        except (OSError,ValueError,KeyError,TypeError) as ex: self.info.set(str(ex))
    def close(self):
        if self.motion_poll: self.after_cancel(self.motion_poll)
        self.save_result(); self.save(); self.destroy()
