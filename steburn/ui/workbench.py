"""Steburn workbench: presentation and command routing, independent of geometry."""
import tkinter as tk
from tkinter import ttk,messagebox,simpledialog
from copy import deepcopy
from pathlib import Path
import queue,threading,time
from steburn.ui.editor import App as Editor
from steburn.core.paths import bounds
from steburn.core.processing import resolve,area_paths
from steburn.core.planner import build_plan
from steburn.core.jobs import snapshot,DryRun,resume_index
from steburn.platform.power import battery_status,Awake

OP_LABELS={'Von Ebene':'inherit','Schneiden':'cut','Gravieren':'engrave','Kontur markieren':'mark'}
FILL_LABELS={'Schraffiert':'lines','Kreuzschraffur':'cross','Gepunktet':'dots','Vollflächig':'solid'}
class App(Editor):
    def __init__(self):
        self.appearance=None; self.presentation_ready=False; self.tool_pin=False; self.marquee=None; self.job_window=None; self.fill_cache={}
        super().__init__()
    def build(self):
        super().build()
        style=ttk.Style(self)
        style.configure('.',font=('Segoe UI',10),background='#eef1f5',foreground='#243247')
        style.configure('TButton',padding=(9,6),relief='flat')
        style.map('TButton',background=[('active','#dce5ef')])
        style.configure('Accent.TButton',background='#e47723',foreground='#182438')
        style.configure('Treeview',rowheight=29,background='#ffffff',fieldbackground='#ffffff',borderwidth=0)
        style.map('Treeview',background=[('selected','#dae8fb')],foreground=[('selected','#183754')])
        style.configure('TNotebook.Tab',padding=(10,7))
        self.canvas.configure(bg='#dfe5ed')
        self.theme_font='Segoe UI' if __import__('os').name=='nt' else 'DejaVu Sans'
        style.configure('.',font=(self.theme_font,10))
        style.configure('Dark.TFrame',background='#243247')
        style.configure('Dark.TLabel',background='#243247',foreground='#f5f7fa')
        toolbar=self.canvas.master.winfo_children()[0]
        toolbar.configure(style='Dark.TFrame')
        for child in toolbar.winfo_children():
            if isinstance(child,ttk.Label): child.configure(style='Dark.TLabel')
        self.canvas.bind('<Button-3>',self.context)
        self.tree.bind('<Button-3>',self.tree_context)
        self.bind('<Escape>',self.escape)
        top=self.canvas.master.winfo_children()[0]
        self.pinned=tk.BooleanVar(value=False)
        ttk.Checkbutton(top,text='Werkzeug feststellen',variable=self.pinned).pack(side='left',padx=8)
        self.lasern_button=ttk.Button(top,text='Lasern',command=self.open_job,style='Accent.TButton')
        self.lasern_button.pack(side='left',padx=4)
        self.processing_panel()
        self.notebook.select(self.processing_tab)
        page=self.pages['machine']
        relief=tk.Menu(self.menubar,tearoff=False)
        relief.add_command(label='Relief-Assistent …',command=self.relief)
        relief.insert_command(0,label='Boxen & Gehäuse …',command=self.boxes)
        self.menubar.add_cascade(label='Module',menu=relief)
        self.configure_icon()
        self.set_tool('select'); self.refresh()
        self.presentation_ready=True
        self.appearance.brand_header(self)
        self.appearance.present(self)
        self.layout_workflow()
        self.canvas.bind('<Shift-MouseWheel>',self.wheel)
        self.compact_layout()
        self.after_idle(lambda:self.state('zoomed'))
        self.after(1500,self.idle_device_poll)
    def layout_workflow(self):
        # Recreate workflow controls in the existing header: no second canvas row.
        top=self.canvas.master.winfo_children()[0]
        header=self.header_status.master
        actions=[('Gestalten',lambda:self.set_preview(False)),('Simulation',self.simulate),('Rahmen',self.frame),('Rahmen stoppen',self.stop_frame),('Lasern',self.open_job)]
        self.workflow_buttons=[]
        for label,command in actions:
            button=ttk.Button(header,text=label,command=command,style='Toolbar.Accent.TButton' if label=='Lasern' else 'Toolbar.TButton')
            self.workflow_buttons.append(button)
        self.lasern_button=self.workflow_buttons[-1]
        # Keep the tool pin next to the drawing tools rather than above the canvas.
        left=self.tree.master
        before=next(w for w in left.winfo_children() if isinstance(w,ttk.Label) and str(w.cget('text'))=='OBJEKTE')
        ttk.Checkbutton(left,text='Werkzeug feststellen',variable=self.pinned).pack(fill='x',padx=6,pady=6,before=before)
        top.destroy(); self.canvas.pack_configure(pady=0)
        old_status=next(w for w in self.winfo_children() if isinstance(w,ttk.Label) and str(w.cget('textvariable'))==str(self.status))
        footer=ttk.Frame(self)
        footer.pack(side='bottom',fill='x',before=self.palette)
        ttk.Label(footer,textvariable=self.status,padding=8).pack(side='left',fill='x',expand=True)
        self.header_status.destroy()
        self.header_status=ttk.Label(footer,text='A40 Pro · OFFLINE',padding=8)
        self.header_status.pack(side='right')
        old_status.destroy()
        self.header=header
        self.connection_dot=tk.Label(header,text='●',fg='#d64545',bg='#243247',font=('Segoe UI',14))
        self.header_actions=[w for w in header.winfo_children() if isinstance(w,ttk.Button)]
        self.header_brand=next(w for w in header.winfo_children() if isinstance(w,ttk.Label))
        self.overflow_menu=tk.Menu(header,tearoff=False)
        self.overflow=ttk.Menubutton(header,text='Mehr',menu=self.overflow_menu,style='Toolbar.TButton')
        self._toolbar_timer=None
        header.bind('<Configure>',self.schedule_header,add='+')
        self.after_idle(self.reflow_header)
        self.appearance.present(self)
    def schedule_header(self,e=None):
        if self._toolbar_timer: self.after_cancel(self._toolbar_timer)
        self._toolbar_timer=self.after(70,self.reflow_header)
    def reflow_header(self):
        self._toolbar_timer=None
        self.header.update_idletasks()
        available=self.header.winfo_width()-52
        if available<100: return
        buttons=list(self.header_actions)
        hidden=[]
        need=self.header_brand.winfo_reqwidth()+sum(b.winfo_reqwidth()+6 for b in buttons)+18
        for name in ['Prüfen','Einpassen','Rückgängig','Import','Neu','Öffnen']:
            if need<=available: break
            button=next((b for b in buttons if str(b.cget('text'))==name),None)
            if button:
                buttons.remove(button); hidden.append(button)
                need-=button.winfo_reqwidth()+6
                if len(hidden)==1: need+=self.overflow.winfo_reqwidth()+8
        self.overflow_menu.delete(0,'end')
        for button in hidden: self.overflow_menu.add_command(label=button.cget('text'),command=button.invoke)
        for widget in self.header.winfo_children(): widget.pack_forget()
        self.connection_dot.pack(side='right',padx=6)
        self.header_brand.pack(side='left',padx=(0,8))
        for button in buttons: button.pack(side='left',padx=3,pady=3)
        if hidden: self.overflow.pack(side='left',padx=4,pady=3)
    def configure_icon(self):
        from steburn.ui.presentation import Appearance
        self.appearance=Appearance(self)
    def set_tool(self,t):
        super().set_tool(t)
        if not hasattr(self,'tree'): return
        labels={'Auswählen / bewegen':'select','Rechteck':'rect','Ellipse / Kreis':'ellipse','Linie':'line','Text':'text','Vieleck':'polygon','Knoten':'nodes','Messen':'measure','Laserziel':'position'}
        def visit(parent):
            for child in parent.winfo_children():
                if isinstance(child,ttk.Button) and str(child.cget('text')) in labels:
                    child.configure(style='Selected.TButton' if labels[str(child.cget('text'))]==t else 'TButton')
                visit(child)
        visit(self.tree.master)
    def processing_panel(self):
        from steburn.ui.widgets import ScrollPanel
        self.processing_tab=ScrollPanel(self.notebook)
        self.notebook.insert(0,self.processing_tab,text='Bearbeitung')
        frame=ttk.LabelFrame(self.processing_tab.content,text='Bearbeitung der Auswahl',padding=8)
        frame.pack(fill='x',padx=8,pady=10)
        self.process_op=tk.StringVar(value='Von Ebene'); self.process_fill=tk.StringVar(value='Schraffiert')
        self.process_power=tk.StringVar(value='20'); self.process_speed=tk.StringVar(value='1200')
        self.process_interval=tk.StringVar(value='0.2'); self.process_angle=tk.StringVar(value='0'); self.process_passes=tk.StringVar(value='1')
        ttk.Combobox(frame,values=list(OP_LABELS),textvariable=self.process_op,state='readonly').pack(fill='x',pady=3)
        ttk.Combobox(frame,values=list(FILL_LABELS),textvariable=self.process_fill,state='readonly').pack(fill='x',pady=3)
        self.power_slider=tk.DoubleVar(value=20)
        ttk.Label(frame,text='Laserleistung (%)').pack(anchor='w')
        ttk.Scale(frame,from_=0,to=100,variable=self.power_slider,command=lambda v:self.process_power.set(f'{float(v):.1f}')).pack(fill='x')
        for label,var in [('Leistung (%)',self.process_power),('Geschwindigkeit (mm/min)',self.process_speed),('Durchgänge',self.process_passes),('Linien-/Punktabstand (mm)',self.process_interval),('Winkel (°)',self.process_angle)]:
            ttk.Label(frame,text=label).pack(anchor='w'); ttk.Entry(frame,textvariable=var).pack(fill='x',pady=(0,5))
        ttk.Button(frame,text='Auf Auswahl anwenden',command=self.apply_processing).pack(fill='x',pady=3)
        ttk.Button(frame,text='Alle Werte wieder von Ebene',command=self.clear_processing).pack(fill='x',pady=3)
        ttk.Label(frame,text='Objektwerte haben Vorrang vor Ebenenwerten.\nPunkte = kurze Striche; Vollfläche = dichte Bahnen.\nBitmaps benötigen zum Schneiden Vektorkonturen.',wraplength=230).pack(fill='x',pady=5)
    def refresh(self):
        super().refresh()
        if not hasattr(self,'process_op'): return
        s=self.current()
        if s:
            try:
                settings=resolve(s,next(l for l in self.p.layers if l.id==s.layer)); values=s.extra.get('processing',{})
                self.process_op.set(next(k for k,v in OP_LABELS.items() if v==values.get('operation','inherit')))
                self.process_fill.set(next(k for k,v in FILL_LABELS.items() if v==settings.fill))
                for key,var in [('power',self.process_power),('speed',self.process_speed),('interval',self.process_interval),('angle',self.process_angle),('passes',self.process_passes)]: var.set(f'{getattr(settings,key):g}')
                self.power_slider.set(settings.power)
            except ValueError: pass
        # Layer tabs activate only; assignment is an explicit context action.
        if hasattr(self,'palette'):
            buttons=[w for w in self.palette.winfo_children() if isinstance(w,tk.Button)]
            for button,layer in zip(buttons,self.p.layers):
                button.configure(command=lambda lid=layer.id:self.quick_layer(lid,True),relief='flat',bd=1,padx=14,highlightthickness=2,highlightbackground='#243247' if layer.id==self.active_layer else '#eef1f4')
                button.bind('<Button-3>',lambda e,lid=layer.id:self.layer_context(e,lid))
        if self.presentation_ready:
            from steburn.ui.presentation import attach_help
            attach_help(self)
    def commit(self,p):
        # New open vectors cannot define a filled area; give them explicit contour intent.
        from steburn.core.paths import shape_paths
        for s in p.shapes:
            if s.kind in {'line','polyline'} and 'processing' not in s.extra:
                paths=shape_paths(s)
                if any(path[0]!=path[-1] for path in paths):
                    layer=next(l for l in p.layers if l.id==s.layer)
                    s.extra['processing']={'operation':'cut' if resolve(s,layer).operation=='cut' else 'mark'}
        self.fill_cache.clear(); super().commit(p)
    def apply_processing(self):
        if not self.chosen(): return
        try:
            values={'operation':OP_LABELS[self.process_op.get()],'fill':FILL_LABELS[self.process_fill.get()],
                    'power':float(self.process_power.get().replace(',','.')),'speed':float(self.process_speed.get().replace(',','.')),
                    'interval':float(self.process_interval.get().replace(',','.')),'angle':float(self.process_angle.get().replace(',','.')),
                    'passes':int(self.process_passes.get())}
            p=deepcopy(self.p)
            for s in p.shapes:
                if s.id in self.selection and not s.extra.get('locked'):
                    if s.kind=='image' and values['operation'] in {'cut','mark'}: raise ValueError('Bitmap zuerst vektorisieren. Schneiden des Bildrahmens wird nicht stillschweigend angenommen.')
                    if s.kind=='image' and (values['fill']=='cross' or values['angle']!=0): raise ValueError('Bitmap unterstützt Raster/Graustufen oder Schwarzweiß-Raster; Kreuzschraffur und Winkel folgen später.')
                    s.extra['processing']=values.copy()
                    settings=resolve(s,next(l for l in p.layers if l.id==s.layer))
                    if s.kind!='image' and settings.operation=='engrave': area_paths(s,settings,display=True)
            self.commit(p)
        except Exception as ex: messagebox.showerror('Bearbeitung',str(ex))
    def clear_processing(self):
        p=deepcopy(self.p)
        for s in p.shapes:
            if s.id in self.selection and not s.extra.get('locked'): s.extra.pop('processing',None)
        self.commit(p)
    def set_operation(self,op):
        p=deepcopy(self.p)
        try:
            for s in p.shapes:
                if s.id not in self.selection or s.extra.get('locked'): continue
                if s.kind=='image' and op in {'cut','mark'}: raise ValueError('Bitmap benötigt Vektorkontur.')
                s.extra.setdefault('processing',{})['operation']=op
                settings=resolve(s,next(l for l in p.layers if l.id==s.layer))
                if s.kind!='image' and settings.operation=='engrave': area_paths(s,settings,display=True)
            self.commit(p)
        except Exception as ex: messagebox.showerror('Bearbeitung',str(ex))
    def render(self):
        super().render()
        if not hasattr(self,'canvas'): return
        for s in self.p.shapes:
            layer=next(l for l in self.p.layers if l.id==s.layer)
            if not layer.visible or s.kind=='image': continue
            try:
                settings=resolve(s,layer)
                if settings.operation!='engrave': continue
                key=(repr(s),settings)
                if key not in self.fill_cache:
                    if len(self.fill_cache)>100: self.fill_cache.clear()
                    self.fill_cache[key]=area_paths(s,settings,display=True)
                for path in self.fill_cache[key][:1500]:
                    item=self.canvas.create_line(*[v for pt in path for v in self.screen(*pt)],fill=layer.color,width=1,stipple='gray50',tags=('s:'+s.id,'fill-preview'))
                    self.canvas.tag_lower(item)
                    # Keep fills above the white work surface/grid, below selection handles.
                self.canvas.tag_raise('s:'+s.id)
                self.canvas.tag_raise('resize:'+s.id+':ne')
            except ValueError:
                x,y=self.screen(s.x,s.y)
                self.canvas.create_text(x,y,text='Füllung prüfen',anchor='sw',fill='#b8452d',tags=('s:'+s.id,))
        self.canvas.tag_raise('fill-preview')
        for item in self.canvas.find_all():
            if any(t.startswith('resize:') for t in self.canvas.gettags(item)): self.canvas.tag_raise(item)
    def escape(self,e=None):
        self.drag=None; self.marquee=None; self.set_tool('select'); self.render(); return 'break'
    def one_shot(self):
        if not getattr(self,'pinned',None) or not self.pinned.get(): self.set_tool('select')
    def press(self,e):
        if self.tool=='select':
            items=self.canvas.find_overlapping(e.x-4,e.y-4,e.x+4,e.y+4)
            # Clicking within a visible bounding box selects it, as in the editor.
            x,y=self.coords(e)
            hit=any(any(t.startswith(('s:','resize:')) for t in self.canvas.gettags(i)) for i in items)
            hit=hit or any(next(l for l in self.p.layers if l.id==s.layer).visible and bounds([s])[0]<=x<=bounds([s])[2] and bounds([s])[1]<=y<=bounds([s])[3] for s in self.p.shapes)
            if not hit:
                original=set(self.selection) if e.state & 4 else set()
                self.selection=original; self.selected=next(iter(original),None)
                self.drag=('marquee',x,y,original); self.refresh(); return
        old=self.tool
        super().press(e)
        if old in {'text','position'}: self.one_shot()
    def motion(self,e):
        if self.drag and self.drag[0]=='marquee':
            _,x,y,_=self.drag
            self.canvas.delete('marquee'); self.canvas.create_rectangle(*self.screen(x,y),e.x,e.y,outline='#3278c7',dash=(5,3),tags='marquee'); return
        super().motion(e)
    def release(self,e):
        if self.drag and self.drag[0]=='marquee':
            _,a,b,original=self.drag; x,y=self.coords(e); self.drag=None
            x0,x1=sorted((a,x)); y0,y1=sorted((b,y)); ids=set(original)
            for s in self.p.shapes:
                layer=next(l for l in self.p.layers if l.id==s.layer)
                c,d,f,g=bounds([s])
                if layer.visible and x0<=c and f<=x1 and y0<=d and g<=y1: ids.add(s.id)
            groups={s.extra.get('group') for s in self.p.shapes if s.id in ids}-{None}
            ids.update(s.id for s in self.p.shapes if s.extra.get('group') in groups)
            self.selection=ids; self.selected=next(iter(ids),None); self.refresh(); return
        kind=self.drag[0] if self.drag else None
        super().release(e)
        if kind=='draw': self.one_shot()
    def finish_polygon(self,e=None):
        count=len(self.p.shapes); super().finish_polygon(e)
        if len(self.p.shapes)>count: self.one_shot()
    def import_file(self):
        super().import_file(); self.one_shot()
    def popup(self,menu,e):
        try: menu.tk_popup(e.x_root,e.y_root)
        finally: menu.grab_release()
        return 'break'
    def context(self,e):
        items=self.canvas.find_overlapping(e.x-4,e.y-4,e.x+4,e.y+4)
        sid=next((t[2:] for i in reversed(items) for t in self.canvas.gettags(i) if t.startswith('s:')),None)
        if sid and sid not in self.selection: self.selection={sid}; self.selected=sid; self.refresh()
        menu=self.object_menu() if sid or self.chosen() else tk.Menu(self,tearoff=False)
        if not (sid or self.chosen()):
            menu.add_command(label='Importieren …',command=self.import_file)
            menu.add_command(label='Alles auswählen',command=self.select_all)
            menu.add_command(label='Arbeitsfläche einpassen',command=self.fit)
        return self.popup(menu,e)
    def tree_context(self,e):
        sid=self.tree.identify_row(e.y)
        if sid and sid not in self.selection: self.selection={sid}; self.selected=sid; self.refresh()
        return self.popup(self.object_menu(),e)
    def object_menu(self):
        menu=tk.Menu(self,tearoff=False)
        for label,fn in [('Duplizieren',self.duplicate),('Umbenennen …',self.rename_object),('Gruppieren',self.group),('Gruppierung aufheben',self.ungroup),('Sperren',lambda:self.lock(True)),('Entsperren',lambda:self.lock(False))]: menu.add_command(label=label,command=fn)
        layers=tk.Menu(menu,tearoff=False)
        for l in self.p.layers: layers.add_command(label=l.name,command=lambda lid=l.id:self.quick_layer(lid,True))
        menu.add_cascade(label='Ebene zuweisen',menu=layers)
        operations=tk.Menu(menu,tearoff=False)
        for label,op in OP_LABELS.items(): operations.add_command(label=label,command=lambda v=op:self.set_operation(v))
        menu.add_cascade(label='Bearbeitungsart',menu=operations)
        arrange=tk.Menu(menu,tearoff=False)
        for label,mode in [('Links','left'),('Rechts','right'),('Oben','top'),('Unten','bottom'),('Horizontal mittig','center_x'),('Vertikal mittig','center_y')]: arrange.add_command(label=label,command=lambda m=mode:self.align_many(m))
        menu.add_cascade(label='Ausrichten',menu=arrange)
        chosen=self.chosen()
        if any(s.kind=='image' for s in chosen):
            menu.add_command(label='Bild aufbereiten …',command=self.adjust_image)
            menu.add_command(label='Relief-Assistent …',command=self.relief)
        if any(s.kind=='text' for s in chosen): menu.add_command(label='Text in Pfade',command=self.text_to_paths)
        if any(s.extra.get('box_model') for s in chosen): menu.add_command(label='Boxparameter bearbeiten …',command=self.boxes)
        menu.add_command(label='Auswahl simulieren',command=self.simulate_selection)
        menu.add_separator(); menu.add_command(label='Löschen',command=self.delete)
        return menu
    def layer_context(self,e,lid):
        menu=tk.Menu(self,tearoff=False)
        menu.add_command(label='Aktivieren',command=lambda:self.quick_layer(lid,False))
        menu.add_command(label='Auswahl dieser Ebene zuweisen',command=lambda:self.quick_layer(lid,True))
        menu.add_command(label='Umbenennen …',command=lambda:self.rename_layer(lid))
        def color(): self.active_layer=lid; self.layer_color()
        menu.add_command(label='Farbe …',command=color)
        def toggle():
            p=deepcopy(self.p); l=next(l for l in p.layers if l.id==lid); l.output=not l.output; self.commit(p)
        menu.add_command(label='Ausgabe ein/aus',command=toggle)
        menu.add_separator(); menu.add_command(label='Ebene entfernen (Objekte verschieben)',command=lambda:self.remove_layer(lid),state='normal' if len(self.p.layers)>1 else 'disabled')
        return self.popup(menu,e)
    def select_all(self): self.selection={s.id for s in self.p.shapes}; self.selected=next(iter(self.selection),None); self.refresh()
    def rename_object(self):
        s=self.current()
        if not s or s.extra.get('locked'): return
        name=simpledialog.askstring('Objekt','Name:',initialvalue=s.name,parent=self)
        if name:
            p=deepcopy(self.p); next(v for v in p.shapes if v.id==s.id).name=name; self.commit(p)
    def simulate_selection(self):
        from steburn.ui.simulation import Simulation
        try:
            p=deepcopy(self.p)
            for l in p.layers:
                if any(s.id in self.selection and s.layer==l.id for s in p.shapes): l.output=True
            Simulation(self,build_plan(p,ids=set(self.selection)))
        except Exception as ex: messagebox.showerror('Simulation',str(ex))
    def prepare_visible(self):
        if self.visible_align.get():
            messagebox.showinfo('Strahl gesperrt','Sichtbare Ausrichtung noch nicht am Material geprüft. In dieser Version nur Laser AUS verwenden.')
            return None
        return False
    def home_device(self):
        if self.busy or not self.device.connected: return
        self.run_device(self.device.home)
    def confirm_origin(self):
        if not self.device.homed:
            messagebox.showinfo('Freigabe gesperrt','Zuerst in Steburn die Referenzfahrt ausführen. Ein Neustart hebt diese Freigabe auf.'); return
        if self.busy: return
        if messagebox.askyesno('Sichtprüfung','Steht der Kopf nach der Steburn-Referenzfahrt tatsächlich links vorne und war die Fahrt störungsfrei?'):
            self.device.origin_confirmed=True; self.device.safety_reason='Referenzfahrt und Sichtprüfung bestätigt'
            self.connection.set(self.device.safety_reason)
    def idle_device_poll(self):
        if self.device.connected and not self.busy:
            # status() only runs in the serialized device worker, never on Tk.
            self.run_device(lambda:(self.device.status(),None)[1],keep_awake=False)
        self.after(2000,self.idle_device_poll)
    def poll(self):
        super().poll()
        if hasattr(self,'header_status'):
            label='OFFLINE' if not self.device.connected else ('REFERENZ BESTÄTIGT' if self.device.homed and self.device.origin_confirmed else 'FAHRTEN GESPERRT')
            dark=getattr(getattr(self,'theme',None),'dark',False)
            self.header_status.configure(text='A40 Pro · '+label,foreground=('#6ee7b7' if dark else '#2f705a') if label=='REFERENZ BESTÄTIGT' else ('#fbbf24' if dark else '#9b4826'))
        if hasattr(self,'connection_dot'):
            self.connection_dot.configure(fg='#46cf83' if self.device.connected and self.device.link_ok else '#d64545')
    def run_device(self,task,keep_awake=True):
        def guarded():
            try:
                with self.device.io_lock:
                    if keep_awake:
                        with Awake(): return task()
                    return task()
            except (OSError,TimeoutError) as ex:
                self.device.link_ok=False
                self.device.invalidate('Gerätefehler: '+str(ex)+'; Referenzfreigabe aufgehoben'); raise
            finally:
                try:
                    import json,time
                    from pathlib import Path
                    folder=Path(getattr(self,'device_trace_directory',Path(__file__).resolve().parents[2]/'user-data'/'device-traces')); folder.mkdir(parents=True,exist_ok=True)
                    transport=type(self.device.serial)
                    data=dict(transport=transport.__module__+'.'+transport.__name__,homed=self.device.homed,origin_confirmed=self.device.origin_confirmed,reason=self.device.safety_reason,position=self.device.last_position,log=list(self.device.log)[-500:])
                    (folder/f'device-{time.time_ns()}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
                except OSError: pass
        super().run_device(guarded)
    def build_machine_panel(self):
        page=self.pages['machine']
        for child in page.winfo_children(): child.destroy()
        self.port=tk.StringVar(value='COM5'); self.baud=tk.StringVar(value='115200')
        self.connection=tk.StringVar(value='Nicht verbunden')
        self.low_power=tk.StringVar(value='0'); self.visible_align=tk.BooleanVar(value=False)
        ttk.Label(page,text='A40 Pro · GRBL',font=('Segoe UI',11,'bold')).pack(fill='x')
        for label,var in [('Anschluss',self.port),('Baudrate',self.baud)]:
            ttk.Label(page,text=label).pack(anchor='w'); ttk.Entry(page,textvariable=var).pack(fill='x')
        for label,fn in [('Ports suchen',self.ports),('Verbinden + Referenzfahrt',self.connect_device),('Neu referenzieren',self.home_device),('Position / Versätze nur lesen',lambda:self.run_device(self.device.diagnostics)),('ABBRUCH / Controller-Reset',self.stop_device),('Trennen',self.disconnect_device)]:
            ttk.Button(page,text=label,command=fn,style='Danger.TButton' if 'ABBRUCH' in label else 'TButton').pack(fill='x',pady=2)
        ttk.Label(page,textvariable=self.connection,wraplength=290).pack(fill='x',pady=4)
        ttk.Label(page,text='Verbinden startet automatisch die Referenzfahrt.\nAuftragssteuerung unter 04 Lasern.',wraplength=290).pack(fill='x')
    def connect_device(self):
        port=self.port.get().strip(); baud=self.baud.get()
        if not port: self.status.set('COM-Port eintragen'); return
        self.run_device(lambda:self.device.connect_and_home(port,baud))
    def ports(self):
        from serial.tools.list_ports import comports
        ports=list(comports())
        self.status.set(' · '.join(f'{p.device}: {p.description}' for p in ports) or 'Keine Ports erkannt')
        if len(ports)==1: self.port.set(ports[0].device)
    def frame(self):
        from steburn.core.planner import rectangle_plan
        if self.busy: return
        try:
            if not self.device.connected: raise ValueError('Zuerst verbinden')
            pts=tuple(rectangle_plan(self.p,self.frame_shapes()))
            width,height=self.p.width,self.p.height
            self.status.set('Rahmen läuft wiederholt · Stopptaste beendet die Fahrt')
            self.frame_active=True
            def run_frame():
                try: return self.device.frame_loop(pts,width,height)
                finally: self.frame_active=False
            self.run_device(run_frame)
        except Exception as ex: self.status.set(str(ex))
    def stop_frame(self):
        if getattr(self,'frame_active',False) and self.device.connected:
            self.device.stop_frame(); self.status.set('Rahmen hält an · Position bleibt erhalten')
    def position_target(self,point):
        if self.busy: return
        width,height=self.p.width,self.p.height
        self.run_device(lambda:self.device.align([point],width,height,False))
    def wheel(self,e):
        if e.state & 4: return super().wheel(e)
        if not e.delta: return 'break'
        if e.state & 1: self.ox+=e.delta/120*32
        else: self.oy+=e.delta/120*32
        self.render(); return 'break'
    def compact_layout(self):
        style=ttk.Style(self)
        for name in ('TButton','Accent.TButton','Danger.TButton','Selected.TButton','Toolbar.TButton','Toolbar.Accent.TButton'):
            style.configure(name,padding=(6,3),font=(self.theme_font,9))
        style.configure('TEntry',padding=2); style.configure('TCombobox',padding=2)
        style.configure('TNotebook.Tab',padding=(5,4),font=(self.theme_font,9))
        self.main_pane.panes()
        right=self.notebook.master; right.configure(width=350)
        self.after(250,lambda:self.main_pane.sashpos(1,max(500,self.main_pane.winfo_width()-350)))
        def compact(parent):
            children=list(parent.pack_slaves())
            # Turn label/input pairs into a single row, preserving widget identity.
            if children and all(w.pack_info().get('side')=='top' for w in children):
                for w in children: w.pack_forget()
                row=0; i=0
                parent.columnconfigure(1,weight=1)
                while i<len(children):
                    w=children[i]
                    if isinstance(w,ttk.Label) and i+1<len(children) and isinstance(children[i+1],(ttk.Entry,ttk.Combobox)):
                        w.configure(wraplength=145)
                        w.grid(row=row,column=0,sticky='w',padx=3,pady=0)
                        children[i+1].grid(row=row,column=1,sticky='ew',padx=3,pady=0); i+=2
                    else:
                        w.grid(row=row,column=0,columnspan=2,sticky='ew',padx=3,pady=0); i+=1
                    row+=1
            for child in parent.winfo_children():
                if isinstance(child,(ttk.Frame,ttk.LabelFrame)): compact(child)
        for panel in [*self.pages.values(),self.processing_tab.content]: compact(panel)
        for child in self.tree.master.pack_slaves():
            child.pack_configure(pady=2)
    def boxes(self):
        from steburn.ui.boxes import BoxDialog
        try: BoxDialog(self)
        except Exception as ex: messagebox.showerror('Boxmodul',str(ex))
    def relief(self):
        from steburn.ui.relief import ReliefDialog
        ReliefDialog(self)
    def open_job(self):
        if self.job_window and self.job_window.winfo_exists(): self.job_window.lift(); return
        from steburn.ui.job_window import JobWindow
        self.job_window=JobWindow(self)
