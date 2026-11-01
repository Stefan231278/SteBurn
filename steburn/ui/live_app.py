"""Automatic document edits and non-blocking device status polling."""
import tkinter as tk
from tkinter import ttk
from copy import deepcopy
from pathlib import Path
import json,math,queue,threading
from steburn.ui.workspace import App as Workspace
from steburn.ui.drawing import Drawing
from steburn.ui.workbench import OP_LABELS,FILL_LABELS
from steburn.core.paths import bounds,shape_paths,as_paths_shape

class App(Drawing,Workspace):
    def __init__(self):
        self.auto_ready=False; self.auto_suspended=0; self.auto_busy=False; self.pending_edits={}; self.auto_timer=None
        self.telemetry=queue.Queue(); self.telemetry_pending=False
        super().__init__()
    def build(self):
        super().build()
        self.auto_ready=True
        for var in self.vars.values(): var.trace_add('write',lambda *args:self.schedule_edit('object'))
        for var in self.lvars.values(): var.trace_add('write',lambda *args:self.schedule_edit('layer'))
        for var in (self.mode,self.visible,self.output,self.air): var.trace_add('write',lambda *args:self.schedule_edit('layer'))
        self.object_layer.bind('<<ComboboxSelected>>',lambda e:self.schedule_edit('object'),add='+')
        for var in (self.text_size,self.tracking,self.line_spacing,self.text_alignment): var.trace_add('write',lambda *args:self.schedule_edit('text'))
        self.text_content.bind('<<Modified>>',self.text_modified,add='+'); self.text_content.edit_modified(False)
        for var in (self.process_op,self.process_fill,self.process_power,self.process_speed,self.process_interval,self.process_angle,self.process_passes): var.trace_add('write',lambda *args:self.schedule_edit('processing'))
        self.radius.trace_add('write',lambda *args:self.schedule_edit('radius'))
        self.rotation.trace_add('write',lambda *args:self.schedule_edit('rotation'))
        for var in (self.node_x,self.node_y): var.trace_add('write',lambda *args:self.schedule_edit('node'))
        self.watts_var.trace_add('write',self.save_watts)
        self.bind('<FocusOut>',self.focus_edit,add='+'); self.hide_apply_buttons()
    def build_material_panel(self):
        super().build_material_panel()
        parent=self.pages['materials']
        card=self.card(parent,'Material kalibrieren')
        ttk.Label(card,text='Schnitt- und Gravurtest auf dem Werkstück positionieren, Größe wählen und gemessene Ergebnisse je Feld speichern.',wraplength=285).pack(fill='x',pady=4)
        ttk.Button(card,text='Materialtest …',style='Accent.TButton',command=self.open_material_test).pack(fill='x',pady=6)
    def open_material_test(self):
        from steburn.ui.material_test import MaterialTestWindow
        self.material_test_window=MaterialTestWindow(self)
    def build_machine_panel(self):
        super().build_machine_panel()
        settings=Path(__file__).resolve().parents[2]/'user-data'/'settings.json'
        try: watts=json.loads(settings.read_text(encoding='utf-8')).get('optical_watts','')
        except (OSError,ValueError): watts=''
        self.watts_var=tk.StringVar(value=str(watts) if watts else '')
        page=self.pages['machine']
        ttk.Label(page,text='Optische Nennleistung (W) · optional').pack(fill='x',pady=(8,0))
        ttk.Entry(page,textvariable=self.watts_var).pack(fill='x')
        ttk.Label(page,text='Für die geschätzte Energie im Jobbericht. Keine elektrische Leistungsmessung.',wraplength=290).pack(fill='x',pady=4)
    def build_preparation_panel(self):
        super().build_preparation_panel()
        self.frame_light_var=tk.BooleanVar(value=False); self.frame_light_percent=tk.StringVar(value='0.1')
        row=ttk.Frame(self.prepare_stage); row.pack(fill='x',before=self.prepare_stage.winfo_children()[1],pady=(0,7))
        ttk.Checkbutton(row,text='Schwaches Rahmenlicht',variable=self.frame_light_var,command=self.update_frame_light).pack(side='left')
        ttk.Label(row,text='Leistung (%)').pack(side='left',padx=(12,4))
        ttk.Spinbox(row,from_=.01,to=.5,increment=.01,textvariable=self.frame_light_percent,width=6).pack(side='left')
        ttk.Label(row,text='Max. 0,5 % · kann materialabhängig Spuren erzeugen',style='Studio.Muted.TLabel').pack(side='left',padx=8)
        self.frame_light_percent.trace_add('write',self.update_frame_light)
        pointer=ttk.Frame(self.prepare_stage); pointer.pack(fill='x',before=row,pady=(0,5))
        ttk.Button(pointer,text='Mausfahrt / Pointer',command=self.activate_pointer,style='Compact.TButton').pack(side='left')
        self.pointer_light_var=tk.BooleanVar(value=False); self.pointer_power=tk.StringVar(value='0.1')
        ttk.Checkbutton(pointer,text='Pointerlicht am Ziel (0,15 s)',variable=self.pointer_light_var).pack(side='left',padx=8)
        ttk.Spinbox(pointer,from_=.01,to=.5,increment=.01,textvariable=self.pointer_power,width=6).pack(side='left')
        ttk.Label(pointer,text='% · max. 0,5 % · kann Spuren erzeugen',style='Studio.Muted.TLabel').pack(side='left',padx=6)
    def activate_pointer(self):
        self.switch_workspace('design'); self.set_tool('position'); self.status.set('Mausfahrt: Klick fährt den Kopf direkt zum Ziel. Pointerlicht nur bei aktivierter Option, als kurzer Impuls.')
    def position_target(self,point):
        if self.busy: self.status.set('Zuerst die aktive Fahrt stoppen oder den Job beenden.'); return
        try:
            visible=self.pointer_light_var.get(); power=float(self.pointer_power.get().replace(',','.'))
            self.device.check_targets([point],self.p.width,self.p.height)
            self.frame_active=True
            def run():
                try: return self.device.pointer_move(point,self.p.width,self.p.height,visible,power)
                finally: self.frame_active=False
            self.run_device(run)
        except (ValueError,OSError) as ex: self.status.set(str(ex))
    def update_frame_light(self,*args):
        try: self.device.configure_frame_light(self.frame_light_var.get(),float(self.frame_light_percent.get().replace(',','.')))
        except ValueError as ex:
            self.frame_light_var.set(False); self.device.configure_frame_light(False,.1); self.status.set(str(ex))
    def optical_watts(self):
        try:
            value=float(self.watts_var.get().replace(',','.'))
            return value if math.isfinite(value) and 0<value<=10000 else None
        except ValueError: return None
    def save_watts(self,*args):
        if not hasattr(self,'theme'): return
        if self.watts_var.get().strip() and self.optical_watts() is None: return
        try:
            path=self.theme.path
            try: data=json.loads(path.read_text(encoding='utf-8'))
            except (OSError,ValueError): data={}
            data['optical_watts']=self.optical_watts(); path.parent.mkdir(parents=True,exist_ok=True)
            from steburn.core.materials import MaterialLibrary
            import os,tempfile
            fd,tmp=tempfile.mkstemp(dir=path.parent,suffix='.tmp')
            try:
                with os.fdopen(fd,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)
                os.replace(tmp,path)
            finally:
                if os.path.exists(tmp): os.unlink(tmp)
        except OSError as ex: self.status.set(str(ex))
    def hide_apply_buttons(self,parent=None):
        parent=parent or self
        labels={'Änderungen übernehmen','Text übernehmen','Ebene übernehmen','Auf Auswahl anwenden','Knotenposition übernehmen','Übernehmen','✓','Runden','Drehen'}
        for child in parent.winfo_children():
            if isinstance(child,ttk.Button) and str(child.cget('text')) in labels:
                if child.winfo_manager()=='grid': child.grid_remove()
                elif child.winfo_manager()=='pack': child.pack_forget()
            if not isinstance(child,tk.Toplevel): self.hide_apply_buttons(child)
    def update_context(self,force=False):
        super().update_context(force)
        if self.auto_ready: self.hide_apply_buttons(self.context_content)
    def refresh(self):
        self.auto_suspended+=1
        try:
            super().refresh()
            if self.auto_ready:
                self.text_content.edit_modified(False); self.hide_apply_buttons()
                s=self.current(); self.rotation.set(str(s.extra.get('rotation_angle',0)) if s else '0')
        finally: self.auto_suspended-=1
    def select_node_row(self,e=None):
        self.auto_suspended+=1
        try: super().select_node_row(e)
        finally: self.auto_suspended-=1
    def layer_selected(self):
        if self.auto_ready and not self.auto_suspended: self.flush_auto()
        self.auto_suspended+=1
        try: super().layer_selected()
        finally: self.auto_suspended-=1
    def remove_layer(self,lid=None):
        self.flush_auto(); return super().remove_layer(lid)
    def text_modified(self,e=None):
        if not self.text_content.edit_modified(): return
        self.text_content.edit_modified(False); self.schedule_edit('text')
    def focus_edit(self,e=None):
        if self.pending_edits and not self.auto_busy: self.after_idle(self.flush_auto)
    def schedule_edit(self,kind):
        if not self.auto_ready or self.auto_suspended or self.auto_busy or self.loading or self.drag: return
        s=self.current(); context=dict(ids=set(self.selection),sid=s.id if s else None,layer=self.active_layer)
        if kind=='object':
            context.update(values={k:v.get() for k,v in self.vars.items()},baseline=dict(self.property_baseline),keep=self.keep_ratio.get(),object_layer=self.object_layer.current())
        elif kind=='layer': context.update(values={k:v.get() for k,v in self.lvars.items()},mode=self.mode.get(),visible=self.visible.get(),output=self.output.get(),air=self.air.get())
        elif kind=='text': context.update(text=self.text_content.get('1.0','end-1c'),size=self.text_size.get(),tracking=self.tracking.get(),spacing=self.line_spacing.get(),align=self.text_alignment.get())
        elif kind=='processing': context.update(op=self.process_op.get(),fill=self.process_fill.get(),power=self.process_power.get(),speed=self.process_speed.get(),interval=self.process_interval.get(),angle=self.process_angle.get(),passes=self.process_passes.get())
        elif kind=='radius': context['radius']=self.radius.get()
        elif kind=='rotation': context['angle']=self.rotation.get()
        elif kind=='node': context.update(node=self.node_selection,x=self.node_x.get(),y=self.node_y.get())
        self.pending_edits[kind]=context
        if self.auto_timer: self.after_cancel(self.auto_timer)
        self.auto_timer=self.after(350,self.flush_auto)
    @staticmethod
    def number(value):
        value=str(value).strip().replace(',','.')
        if not value or value.endswith('.') or value in ('-','+'): raise ValueError('Eingabe noch unvollständig')
        result=float(value)
        if not math.isfinite(result): raise ValueError('Ungültige Zahl')
        return result
    def flush_auto(self):
        if self.auto_busy or not self.auto_ready: return
        if self.auto_timer: self.after_cancel(self.auto_timer); self.auto_timer=None
        pending,self.pending_edits=self.pending_edits,{}
        if not pending: return
        focus=self.focus_get(); caret=None; value=None
        try:
            if isinstance(focus,tk.Text): caret=focus.index('insert')
            elif isinstance(focus,ttk.Entry): caret=focus.index('insert'); value=focus.get()
        except tk.TclError: pass
        self.auto_busy=True
        try:
            for kind,context in pending.items():
                try:
                    p=self.edit_project(kind,context); p.validate()
                    if p.to_dict()!=self.p.to_dict(): self.commit(p); self.status.set('Änderung übernommen')
                except (ValueError,KeyError,IndexError,StopIteration) as ex: self.status.set(str(ex))
        finally:
            self.auto_busy=False; self.auto_suspended+=1
            try:
                if focus and focus.winfo_exists() and caret is not None:
                    if isinstance(focus,tk.Text): focus.mark_set('insert',caret)
                    elif isinstance(focus,ttk.Entry):
                        if value is not None and str(focus.cget('state'))!='readonly': focus.delete(0,'end'); focus.insert(0,value)
                        focus.icursor(caret)
            except tk.TclError: pass
            finally: self.auto_suspended-=1
    def edit_project(self,kind,c):
        p=deepcopy(self.p); s=next((s for s in p.shapes if s.id==c['sid']),None)
        if kind in ('object','text','radius','node') and (s is None or s.extra.get('locked')): return p
        if kind=='object':
            oldw,oldh=s.w,s.h; edited=set()
            for key in ('x','y','w','h'):
                if c['values'][key]!=c['baseline'].get(key): setattr(s,key,self.number(c['values'][key])); edited.add(key)
            if c['keep'] and oldw>0 and oldh>0:
                if 'w' in edited and 'h' not in edited: s.h=oldh*s.w/oldw
                elif 'h' in edited and 'w' not in edited: s.w=oldw*s.h/oldh
            s.name=c['values']['name']
            if c['object_layer']>=0: s.layer=p.layers[c['object_layer']].id
            if s.kind in ('polygon','polyline') and (s.w!=oldw or s.h!=oldh):
                if oldw<=0 or oldh<=0: raise ValueError('Linien mit Nullbreite/-höhe über Knoten bearbeiten.')
                s.extra['contours']=[[[x*s.w/oldw,y*s.h/oldh] for x,y in path] for path in s.extra.get('contours',[s.points])]; s.points=s.extra['contours'][0]
                if 'bezier' in s.extra: s.extra['bezier']=[[x*s.w/oldw,y*s.h/oldh] for x,y in s.extra['bezier']]
            if s.kind=='text':
                if 'w' in edited and oldw>0: s.extra['text_scale_x']=s.extra.get('text_scale_x',1.)*(s.w/oldw)/(s.h/oldh)
                a,b,d,e=bounds([s]); s.w=d-a
        elif kind=='text' and s.kind=='text':
            if not c['text'].strip(): raise ValueError('Text darf nicht leer sein.')
            s.text=c['text']; s.h=self.number(c['size'])
            s.extra.update(tracking=self.number(c['tracking']),line_spacing=self.number(c['spacing']),text_align={'Links':'left','Zentriert':'center','Rechts':'right'}[c['align']])
            p.validate(); a,b,d,e=bounds([s]); s.w=d-a
        elif kind=='layer':
            layer=next(l for l in p.layers if l.id==c['layer']); layer.name=c['values']['name']
            for key in ('speed','power','interval'): setattr(layer,key,self.number(c['values'][key]))
            layer.passes=int(c['values']['passes']); layer.mode=c['mode']; layer.visible=c['visible']; layer.output=c['output']; layer.air=c['air']
            layer.operation='engrave' if layer.mode=='Fläche' else 'cut' if layer.operation=='cut' or layer.name.casefold() in ('schnitt','schneiden','cut') else 'mark'
        elif kind=='processing':
            values=dict(operation=OP_LABELS[c['op']],fill=FILL_LABELS[c['fill']],power=self.number(c['power']),speed=self.number(c['speed']),interval=self.number(c['interval']),angle=self.number(c['angle']),passes=int(c['passes']))
            from steburn.core.processing import resolve
            for target in p.shapes:
                if target.id in c['ids'] and not target.extra.get('locked'):
                    target.extra['processing']=dict(values); settings=resolve(target,next(l for l in p.layers if l.id==target.layer))
                    if settings.operation=='engrave' and target.kind!='image' and any(path[0]!=path[-1] for path in shape_paths(target)): raise ValueError('Offene Linien als Schnitt oder Markierung bearbeiten.')
                    if target.kind=='image' and settings.operation!='engrave': raise ValueError('Bilder benötigen Gravur oder vorherige Vektorisierung.')
        elif kind=='radius':
            radius=self.number(c['radius'])
            if radius<0: raise ValueError('Radius muss mindestens 0 sein.')
            for target in p.shapes:
                if target.id in c['ids'] and target.kind=='rect' and not target.extra.get('locked'): target.extra['corner_radius']=min(radius,target.w/2,target.h/2)
        elif kind=='rotation':
            from steburn.core.design import rotate_shape
            angle=self.number(c['angle'])
            if abs(angle)>3600: raise ValueError('Drehwinkel außerhalb des Bereichs.')
            for i,target in enumerate(p.shapes):
                if target.id in c['ids'] and target.kind not in ('image','text') and not target.extra.get('locked'):
                    delta=angle-target.extra.get('rotation_angle',0)
                    if abs(delta)>1e-9:
                        p.shapes[i]=rotate_shape(target,delta); p.shapes[i].extra['rotation_angle']=angle
        elif kind=='node' and c['node'] and c['node'][0]==s.id:
            from steburn.core.nodes import paths,transform_nodes
            _,contour,index=c['node']; point=(self.number(c['x']),self.number(c['y'])); old=paths(s)[contour][index]
            dx,dy=point[0]-old[0],point[1]-old[1]; keys=getattr(self,'node_keys',set()) or {c['node']}
            for i,shape in enumerate(p.shapes):
                selected={(ci,j) for sid,ci,j in keys if sid==shape.id}
                if selected and not shape.extra.get('locked'): p.shapes[i]=transform_nodes(shape,selected,lambda x,y:(x+dx,y+dy))
        return p
    def quick_layer(self,lid,assign=True):
        self.flush_auto(); self.active_layer=lid
        if assign and self.selection:
            p=deepcopy(self.p); layer=next(l for l in p.layers if l.id==lid)
            from steburn.core.processing import resolve
            for s in p.shapes:
                if s.id in self.selection and not s.extra.get('locked'):
                    if s.kind=='image' and layer.mode!='Fläche': self.status.set('Bilder zuerst vektorisieren.'); return
                    s.layer=lid; s.extra.pop('processing',None); s.extra.pop('material',None)
            self.commit(p)
        else: self.refresh()
    def press(self,e): self.flush_auto(); super().press(e)
    def tree_selected(self,e):
        desired=self.tree.selection(); self.flush_auto()
        if desired!=self.tree.selection(): self.tree.selection_set(desired)
        super().tree_selected(e)
    def switch_workspace(self,key):
        self.flush_auto(); super().switch_workspace(key)
    def save(self,as_new=False): self.flush_auto(); return super().save(as_new)
    def confirm(self): self.flush_auto(); return super().confirm()
    def undo(self): self.flush_auto(); super().undo()
    def redo(self): self.flush_auto(); super().redo()
    def idle_device_poll(self):
        if self.device.connected and not self.busy and not self.telemetry_pending:
            self.telemetry_pending=True
            def read():
                if not self.device.io_lock.acquire(blocking=False): self.telemetry.put(None); return
                try:
                    if not self.busy: self.device.status()
                    self.telemetry.put(None)
                except Exception as ex: self.device.link_ok=False; self.telemetry.put(str(ex))
                finally: self.device.io_lock.release()
            threading.Thread(target=read,daemon=True).start()
        self.after(2000,self.idle_device_poll)
    def poll(self):
        super().poll()
        if hasattr(self,'canvas'):
            self.canvas.delete('pointer-position')
            if self.tool=='position' and self.device.homed and self.device.last_position is not None:
                x,y=self.screen(*self.device.last_position)
                self.canvas.create_line(x-9,y,x+9,y,fill='#ed861f',width=2,tags='pointer-position'); self.canvas.create_line(x,y-9,x,y+9,fill='#ed861f',width=2,tags='pointer-position')
                self.canvas.create_text(x+12,y-12,text=f'Bestätigt {self.device.last_position[0]:.1f} / {self.device.last_position[1]:.1f}',anchor='w',fill='#ed861f',tags='pointer-position')
        try:
            while True:
                error=self.telemetry.get_nowait(); self.telemetry_pending=False
                if error: self.connection.set(error)
        except queue.Empty: pass
