"""Extended editor; device tasks run off the Tk thread, results via queue."""
import tkinter as tk
from tkinter import ttk,filedialog,simpledialog,messagebox,colorchooser
from copy import deepcopy
from pathlib import Path
import math,base64,io,threading,queue
from uuid import uuid4
from steburn.ui.app import App as Foundation
from steburn.core.model import Project,Shape,Layer,History
from steburn.core.paths import shape_paths,bounds,as_paths_shape,transform,polygon_geometry,geometry_paths
from steburn.core.planner import build_plan,rectangle_plan,Plan,Segment
from steburn.io.importers import import_file,export_svg,ALL_EXTENSIONS
from steburn.ui.simulation import Simulation
from steburn.devices.grbl import GrblSession
from steburn.core.resize import resize_shape
from steburn.core.fonts import installed_fonts

COLORS=['#1878d1','#df493b','#239461','#8a4cb8','#d68b16','#169eae','#cc4b91','#48546d']
class App(Foundation):
    def __init__(self):
        self.keep_ratio=None; self.font_faces=(); self.property_baseline={}; self.selection=set(); self.image_cache={}; self.poly_points=[]; self.hover=(0.,0.); self.measuring=None
        self.device=GrblSession(); self.events=queue.Queue(); self.busy=False
        super().__init__(); self.after(100,self.poll)
    def build(self):
        super().build()
        tools=tk.Menu(self.menubar,tearoff=False); self.menubar.insert_cascade(2,label='Werkzeuge',menu=tools)
        for label,fn in [('Auswählen',lambda:self.set_tool('select')),('Linien zeichnen',lambda:self.set_tool('line')),('Rechteck',lambda:self.set_tool('rect')),('Ellipse',lambda:self.set_tool('ellipse')),('Vieleck zeichnen',lambda:self.set_tool('polygon')),('Regelmäßiges Vieleck',self.regular_polygon),('Knoten bearbeiten',lambda:self.set_tool('nodes')),('Text bearbeiten',lambda:self.set_tool('text')),('Laser positionieren',lambda:self.set_tool('position')),('Messen',lambda:self.set_tool('measure')),('QR-Code erzeugen',self.qrcode),('Versatz-Formen',self.offset),('Formen verschweißen',lambda:self.boolean('union')),('Boolesche Differenz',lambda:self.boolean('difference')),('Boolescher Schnitt',lambda:self.boolean('intersection')),('Bild anpassen',self.adjust_image),('Text in Pfade umwandeln',self.text_to_paths)]: tools.add_command(label=label,command=fn)
        for label in ['Bild nachzeichnen','Pfad auf Text anwenden','Maske auf Bild','Warp / Deform']: tools.add_command(label=label+' (folgt)',state='disabled')
        arrange=tk.Menu(self.menubar,tearoff=False); self.menubar.insert_cascade(3,label='Anordnen',menu=arrange)
        for label,fn in [('Gruppieren',self.group),('Gruppierung aufheben',self.ungroup),('Horizontal spiegeln',lambda:self.transform_selection('mirror_x')),('Vertikal spiegeln',lambda:self.transform_selection('mirror_y')),('90° im Uhrzeigersinn',lambda:self.transform_selection('cw')),('90° gegen Uhrzeigersinn',lambda:self.transform_selection('ccw')),('Links ausrichten',lambda:self.align_many('left')),('Rechts ausrichten',lambda:self.align_many('right')),('Oben ausrichten',lambda:self.align_many('top')),('Unten ausrichten',lambda:self.align_many('bottom')),('Horizontal zentrieren',lambda:self.align_many('center_x')),('Vertikal zentrieren',lambda:self.align_many('center_y')),('Horizontal verteilen',lambda:self.distribute('x')),('Vertikal verteilen',lambda:self.distribute('y')),('Raster / Anordnung',self.array),('Kreisförmige Anordnung',self.circle_array),('Rechteck-Schachtelung',self.nest),('Nach vorne',lambda:self.reorder(True)),('Nach hinten',lambda:self.reorder(False)),('Auswahl sperren',lambda:self.lock(True)),('Auswahl entsperren',lambda:self.lock(False))]: arrange.add_command(label=label,command=fn)
        laser=tk.Menu(self.menubar,tearoff=False); self.menubar.insert_cascade(4,label='Laserwerkzeuge',menu=laser)
        for label,fn in [('Simulation',self.simulate),('Physisch zur Mausposition',lambda:self.set_tool('position')),('Physisch Rahmen fahren',self.frame),('Geräteprofil / Verbindung',lambda:self.notebook.select(self.page_tabs['machine']))]: laser.add_command(label=label,command=fn)
        # Add accessible buttons next to the canvas modes.
        top=self.canvas.master.winfo_children()[0]
        top.winfo_children()[1].configure(text='Simulation')
        ttk.Button(top,text='Rahmen',command=self.simulate_frame).pack(side='left',padx=2)
        left=self.tree.master
        before=next(w for w in left.winfo_children() if isinstance(w,ttk.Button) and w.cget('text')=='Duplizieren')
        extra_tools=ttk.Frame(left); extra_tools.pack(fill='x',padx=6,pady=6,before=before)
        for i,(label,tool) in enumerate([('Vieleck','polygon'),('Knoten','nodes'),('Messen','measure'),('Laserziel','position')]):
            ttk.Button(extra_tools,text=label,command=lambda t=tool:self.set_tool(t)).grid(row=i//2,column=i%2,sticky='ew',padx=1,pady=1)
        extra_tools.columnconfigure(0,weight=1); extra_tools.columnconfigure(1,weight=1)
        self.header_status=next(w for bar in self.winfo_children() if isinstance(bar,ttk.Frame) for w in bar.winfo_children() if isinstance(w,ttk.Label) and 'OFFLINE' in str(w.cget('text')))
        self.tree.configure(selectmode='extended')
        self.canvas.bind('<Motion>',self.mouse_move); self.canvas.bind('<Double-Button-1>',self.finish_polygon)
        self.bind('<Return>',lambda e:self.finish_polygon() if self.tool=='polygon' else None)
        status_widget=self.winfo_children()[-1]
        self.palette=ttk.Frame(self)
        self.main_pane.pack_forget(); status_widget.pack_forget()
        status_widget.pack(side='bottom',fill='x')
        self.palette.pack(side='bottom',fill='x',padx=8,pady=4)
        self.main_pane.pack(fill='both',expand=True,padx=8)
        for child in self.pages['layers'].winfo_children(): child.destroy()
        self.build_layer_panel(); self.build_machine_panel()
        ttk.Label(self.pages['props'],text='X/Y: links unten am Objekt\nStrg+Klick: Mehrfachauswahl\nDoppelklick/Enter: Vieleck beenden',wraplength=230).pack(fill='x',padx=8,pady=8)
        props=self.pages['props']
        self.keep_ratio=tk.BooleanVar(value=True)
        controls=ttk.Frame(props)
        first=props.winfo_children()[0]
        controls.pack(fill='x',padx=8,pady=6,before=first)
        ttk.Checkbutton(controls,text='Seitenverhältnis beibehalten',variable=self.keep_ratio).pack(anchor='w')
        ttk.Label(controls,text='Rahmen-Griffe ziehen · Shift kehrt Verhältnis um',wraplength=230).pack(anchor='w')
        typography=ttk.Frame(props); text_label=next(w for w in props.winfo_children() if isinstance(w,ttk.Label) and w.cget('text')=='Text'); typography.pack(fill='x',padx=8,pady=8,before=text_label)
        ttk.Label(typography,text='Systemschriftart').pack(anchor='w')
        self.fontbox=ttk.Combobox(typography,state='normal',postcommand=self.post_fonts)
        self.fontbox.pack(fill='x'); self.fontbox.bind('<<ComboboxSelected>>',self.system_font_selected)
        self.fontbox.bind('<KeyRelease>',self.filter_fonts)
        ttk.Button(typography,text='Schriftdatei wählen …',command=self.choose_font).pack(fill='x',pady=4)
        self.refresh()
    def build_layer_panel(self):
        frame=self.pages['layers']; self.layerbox=ttk.Combobox(frame,state='readonly'); self.layerbox.pack(fill='x',padx=8,pady=8); self.layerbox.bind('<<ComboboxSelected>>',lambda e:self.layer_selected())
        bar=ttk.Frame(frame); bar.pack(fill='x',padx=8)
        self.layerbox.bind('<Button-3>',lambda e:self.layer_context(e,self.active_layer))
        for i,(label,fn) in enumerate([('+',self.add_layer),('−',self.remove_layer),('Name',self.rename_layer),('Farbe',self.layer_color),('Vor',lambda:self.move_layer(-1)),('Nach',lambda:self.move_layer(1))]):
            ttk.Button(bar,text=label,width=5,command=fn).grid(row=i//3,column=i%3,sticky='ew',padx=1,pady=1)
        for i in range(3): bar.columnconfigure(i,weight=1)
        self.lvars={}
        for key,label in [('name','Ebenenname'),('speed','Geschwindigkeit (mm/min)'),('power','Leistung (%)'),('passes','Durchgänge'),('interval','Linienintervall (mm)')]:
            ttk.Label(frame,text=label).pack(anchor='w',padx=8,pady=(8,0)); v=tk.StringVar(); self.lvars[key]=v; ttk.Entry(frame,textvariable=v).pack(fill='x',padx=8)
        self.mode=tk.StringVar(value='Kontur'); ttk.Combobox(frame,textvariable=self.mode,values=['Kontur','Fläche'],state='readonly').pack(fill='x',padx=8,pady=8)
        self.visible=tk.BooleanVar(value=True); self.output=tk.BooleanVar(value=True); self.air=tk.BooleanVar(value=False)
        for label,v in [('Anzeigen',self.visible),('In Simulation / Ausgabe einbeziehen',self.output),('Air Assist (Parameter)',self.air)]: ttk.Checkbutton(frame,text=label,variable=v).pack(anchor='w',padx=8)
        ttk.Button(frame,text='Ebene übernehmen',command=self.apply_layer).pack(fill='x',padx=8,pady=8)
        ttk.Label(frame,text='Ebenenreihenfolge = Bearbeitungsreihenfolge.\nEin Klick auf einen Farbreiter aktiviert die Ebene.\nRechtsklick: Auswahl ausdrücklich zuordnen.\nDoppelklick: umbenennen.',wraplength=240).pack(fill='x',padx=8,pady=8)
    def build_machine_panel(self):
        page=self.pages['machine']
        for child in page.winfo_children(): child.destroy()
        ttk.Label(page,text='A40 Pro · GRBL-Ausrichtung',font=('Segoe UI',11,'bold')).pack(anchor='w',padx=8,pady=8)
        self.port=tk.StringVar(value='COM4'); self.baud=tk.StringVar(value='115200'); self.connection=tk.StringVar(value='Nicht verbunden / unbestätigt')
        ttk.Entry(page,textvariable=self.port).pack(fill='x',padx=8); ttk.Label(page,text='COM-Port, z. B. COM3').pack(anchor='w',padx=8)
        ttk.Combobox(page,textvariable=self.baud,values=['9600','115200','230400','460800'],state='readonly').pack(fill='x',padx=8,pady=4)
        ttk.Button(page,text='Ports suchen',command=self.ports).pack(fill='x',padx=8,pady=2)
        ttk.Button(page,text='Verbinden / $I und $$ lesen',command=self.connect_device).pack(fill='x',padx=8,pady=2)
        ttk.Button(page,text='Position / Versätze nur lesen',command=lambda:self.run_device(self.device.diagnostics)).pack(fill='x',padx=8,pady=2)
        ttk.Label(page,textvariable=self.connection,wraplength=240).pack(fill='x',padx=8,pady=8)
        ttk.Button(page,text='Nullpunkt / Homing bestätigen',command=self.confirm_origin).pack(fill='x',padx=8,pady=2)
        self.low_power=tk.StringVar(value='0'); self.visible_align=tk.BooleanVar(value=False)
        ttk.Label(page,text='Getestete Ausrichtleistung (%) · max. 0.5').pack(anchor='w',padx=8,pady=(8,0)); ttk.Entry(page,textvariable=self.low_power).pack(fill='x',padx=8)
        ttk.Checkbutton(page,text='Sichtbaren Strahl ausdrücklich verwenden',variable=self.visible_align).pack(anchor='w',padx=8)
        ttk.Button(page,text='Mausziel per Klick wählen',command=lambda:self.set_tool('position')).pack(fill='x',padx=8,pady=2)
        ttk.Button(page,text='Rechteck physisch abfahren',command=self.frame).pack(fill='x',padx=8,pady=2)
        tk.Button(page,text='ABBRUCH / Controller-Reset',bg='#c5443b',fg='white',command=self.stop_device).pack(fill='x',padx=8,pady=8)
        ttk.Button(page,text='Trennen',command=self.disconnect_device).pack(fill='x',padx=8)
        ttk.Label(page,text='Keine Schneid-/Gravurstarts in 0.3.\nAusrichtung standardmäßig Laser AUS.\nEin sichtbarer Strahl kann Material markieren.\nReset ersetzt keinen Hardware-Notaus.',wraplength=240).pack(fill='x',padx=8,pady=8)
    def bind_shortcuts(self):
        super().bind_shortcuts()
        for seq,tool in [('<Control-r>','rect'),('<Control-e>','ellipse'),('<Control-l>','line'),('<Control-t>','text'),('<Alt-m>','measure'),('<Alt-l>','position')]: self.bind(seq,lambda e,t=tool:self.set_tool(t))
    def chosen(self):
        ids=self.selection or ({self.selected} if self.selected else set())
        return [s for s in self.p.shapes if s.id in ids]
    def commit(self,p):
        p.validate(); self.checkpoint(); self.p=p; self.image_cache.clear(); self.changed(); self.refresh()
    def coords(self,e): return ((e.x-self.ox)/self.scale,self.p.height-(e.y-self.oy)/self.scale)
    def screen(self,x,y): return self.ox+x*self.scale,self.oy+(self.p.height-y)*self.scale
    def set_tool(self,t):
        self.poly_points=[]; self.measuring=None; super().set_tool(t)
        self.canvas.configure(cursor='crosshair' if t!='select' else 'arrow')
        if t=='polygon': self.status.set('Vieleck: Punkte klicken, mit Enter oder Doppelklick schließen.')
        if t=='position': self.status.set('Mausfahrt: Klick fährt den Kopf direkt zum Ziel. Optionales kurzes Pointerlicht unter Vorbereitung.')
    def mouse_move(self,e):
        self.hover=self.coords(e)
        self.status.set(f'{self.tool} · X {self.hover[0]:.1f} · Y {self.hover[1]:.1f} mm · '+('Gerät verbunden' if self.device.connected else 'Offline'))
    def press(self,e):
        if self.preview: return
        x,y=self.coords(e); self.hover=(x,y)
        if self.tool=='position': self.position_target((x,y)); return
        if self.tool=='measure':
            if self.measuring is None: self.measuring=(x,y)
            else:
                a,b=self.measuring; self.canvas.create_line(*self.screen(a,b),*self.screen(x,y),fill='#7649ac',dash=(3,3),tags='measure'); messagebox.showinfo('Abstand',f'{math.hypot(x-a,y-b):.1f} mm\nΔX {x-a:.1f} · ΔY {y-b:.1f}'); self.measuring=None
            return
        if self.tool=='polygon':
            if not self.poly_points or math.dist(self.poly_points[-1],(x,y))>.2: self.poly_points.append((x,y))
            self.render(); return
        if self.tool=='nodes':
            ids=self.canvas.find_overlapping(e.x-7,e.y-7,e.x+7,e.y+7)
            for i in reversed(ids):
                for tag in self.canvas.gettags(i):
                    if tag.startswith('node:'):
                        _,sid,contour,index=tag.split(':'); s=next(s for s in self.p.shapes if s.id==sid)
                        if s.extra.get('locked'): return
                        self.checkpoint(); self.drag=('node',sid,int(contour),int(index)); return
            return
        if self.tool=='text':
            text=simpledialog.askstring('Text','Beschriftung:',parent=self)
            if text:
                s=Shape('text',x,y,100,12,self.active_layer,'Text',text); x0,y0,x1,y1=bounds([s]); s.w=x1-x0
                p=deepcopy(self.p); p.shapes.append(s); self.selection={s.id}; self.selected=s.id; self.commit(p)
            return
        if self.tool=='select':
            handles=self.canvas.find_overlapping(e.x-5,e.y-5,e.x+5,e.y+5)
            for item in reversed(handles):
                for tag in self.canvas.gettags(item):
                    if tag.startswith('resize:'):
                        _,sid,handle=tag.split(':'); original=next(s for s in self.p.shapes if s.id==sid)
                        if original.extra.get('locked'): return
                        self.checkpoint(); self.drag=('resize',deepcopy(original),handle,bool(self.keep_ratio.get()) != bool(e.state & 1)); return
            items=self.canvas.find_overlapping(e.x-4,e.y-4,e.x+4,e.y+4)
            sid=next((tag[2:] for i in reversed(items) for tag in self.canvas.gettags(i) if tag.startswith('s:')),None)
            if sid is None:
                for shape in reversed(self.p.shapes):
                    layer=next(l for l in self.p.layers if l.id==shape.layer)
                    if not layer.visible: continue
                    try:
                        a,b,c,d=bounds([shape])
                        if a<=x<=c and b<=y<=d: sid=shape.id; break
                    except ValueError: continue
            if e.state & 4:
                if sid in self.selection: self.selection.remove(sid)
                elif sid: self.selection.add(sid)
            else:
                if sid not in self.selection: self.selection={sid} if sid else set()
            if sid:
                s=next(s for s in self.p.shapes if s.id==sid); group=s.extra.get('group')
                if group: self.selection.update(s.id for s in self.p.shapes if s.extra.get('group')==group)
            self.selected=sid or next(iter(self.selection),None)
            originals=[deepcopy(s) for s in self.chosen() if not s.extra.get('locked')]
            if originals: self.drag=('move_many',x,y,originals); self.checkpoint()
            self.refresh(); return
        self.drag=('draw',x,y)
    def motion(self,e):
        if not self.drag: return
        x,y=self.coords(e)
        if self.drag[0]=='resize':
            _,original,handle,keep=self.drag
            try:
                replacement=resize_shape(original,handle,(x,y),keep)
                for i,s in enumerate(self.p.shapes):
                    if s.id==original.id: self.p.shapes[i]=replacement; break
                self.image_cache.clear(); self.render()
                for key in ('x','y','w','h'): self.vars[key].set(f'{getattr(replacement,key):.1f}')
            except ValueError as ex: self.status.set(str(ex))
        elif self.drag[0]=='move_many':
            _,a,b,originals=self.drag
            for old in originals:
                s=next(s for s in self.p.shapes if s.id==old.id); s.x=old.x+x-a; s.y=old.y+y-b
            self.render()
        elif self.drag[0]=='node':
            _,sid,contour,index=self.drag; s=next(s for s in self.p.shapes if s.id==sid)
            paths=s.extra.get('contours',[s.points]); points=paths[contour]; closed=points[0]==points[-1]
            points[index]=[x-s.x,y-s.y]
            if closed and index in (0,len(points)-1): points[0]=points[-1]=[x-s.x,y-s.y]
            s.points=paths[0]; self.render()
        else:
            _,a,b=self.drag; self.canvas.delete('ghost')
            if self.tool=='line': self.canvas.create_line(*self.screen(a,b),*self.screen(x,y),fill='#526678',dash=(4,3),width=2,tags='ghost')
            elif self.tool=='ellipse': self.canvas.create_oval(*self.screen(a,b),*self.screen(x,y),outline='#526678',dash=(4,3),tags='ghost')
            else: self.canvas.create_rectangle(*self.screen(a,b),*self.screen(x,y),outline='#526678',dash=(4,3),tags='ghost')
    def release(self,e):
        if not self.drag: return
        kind,*data=self.drag; self.drag=None; x,y=self.coords(e)
        if kind=='draw':
            a,b=data
            if abs(x-a)+abs(y-b)<.5: self.render(); return
            if self.tool=='line':
                from steburn.core.processing import resolve
                s=as_paths_shape(Shape('polyline',layer=self.active_layer,name='Linie'),[[(a,b),(x,y)]])
                s.extra['processing']={'operation':'cut' if resolve(s,next(l for l in self.p.layers if l.id==s.layer)).operation=='cut' else 'mark'}
            else: s=Shape(self.tool,min(a,x),min(b,y),abs(x-a),abs(y-b),self.active_layer,{'rect':'Rechteck','ellipse':'Ellipse'}.get(self.tool,'Objekt'))
            p=deepcopy(self.p); p.shapes.append(s); self.selected=s.id; self.selection={s.id}; self.commit(p)
        else:
            if kind=='node':
                s=next(s for s in self.p.shapes if s.id==data[0]); as_paths_shape(s,shape_paths(s))
            self.changed(); self.refresh()
    def finish_polygon(self,e=None):
        if self.tool!='polygon' or len(self.poly_points)<3: return
        pts=self.poly_points+[self.poly_points[0]]; s=as_paths_shape(Shape('polygon',layer=self.active_layer,name='Vieleck'),[pts]); p=deepcopy(self.p); p.shapes.append(s); self.poly_points=[]; self.selection={s.id}; self.selected=s.id; self.commit(p)
    def render(self):
        if not hasattr(self,'canvas'): return
        c=self.canvas; c.delete('all'); z=self.scale
        c.create_rectangle(*self.screen(0,self.p.height),*self.screen(self.p.width,0),fill='white',outline='#8795a3',tags='workarea')
        step=10 if z>=2 else 50
        for x in range(0,int(self.p.width)+1,step):
            c.create_line(*self.screen(x,0),*self.screen(x,self.p.height),fill='#edf0f3',tags='grid'); xx,yy=self.screen(x,0); c.create_text(xx,yy+12,text=str(x),font=('Segoe UI',8),fill='#657588',tags='grid-label')
        for y in range(0,int(self.p.height)+1,step):
            c.create_line(*self.screen(0,y),*self.screen(self.p.width,y),fill='#edf0f3',tags='grid'); xx,yy=self.screen(0,y); c.create_text(xx-20,yy,text=str(y),font=('Segoe UI',8),fill='#657588',tags='grid-label')
        c.create_text(*self.screen(0,0),text='0',anchor='ne',fill='#182b40')
        for s in self.p.shapes:
            l=next(l for l in self.p.layers if l.id==s.layer)
            if not l.visible: continue
            tags=('s:'+s.id,); selected=s.id in self.selection or s.id==self.selected
            if s.kind=='image':
                if s.w<=0 or s.h<=0: continue
                from PIL import Image,ImageTk
                key=(s.id,round(z,4),s.w,s.h,hash(s.extra.get('image','')))
                if key not in self.image_cache:
                    if len(self.image_cache)>50: self.image_cache.clear()
                    with Image.open(io.BytesIO(base64.b64decode(s.extra['image']))) as im:
                        self.image_cache[key]=ImageTk.PhotoImage(im.resize((max(1,min(4096,int(s.w*z))),max(1,min(4096,int(s.h*z))))))
                c.create_image(*self.screen(s.x,s.y+s.h),anchor='nw',image=self.image_cache[key],tags=tags)
            else:
                try: paths=shape_paths(s)
                except Exception: paths=[[(s.x,s.y),(s.x+s.w,s.y+s.h)]]
                for ci,path in enumerate(paths):
                    if len(path)>1: c.create_line(*[v for pt in path for v in self.screen(*pt)],fill=l.color,width=2.5 if selected else 1.4,tags=tags)
                    if self.tool=='nodes' and selected and s.kind in {'polygon','polyline'}:
                        for index,pt in enumerate(path[:1000]):
                            a,b=self.screen(*pt); c.create_rectangle(a-3,b-3,a+3,b+3,fill='white',outline='#354d67',tags=(f'node:{s.id}:{ci}:{index}',))
            if selected:
                try:
                    simple_line='bezier' not in s.extra and len(shape_paths(s))==1 and len(shape_paths(s)[0])==2
                    x0,y0,x1,y1=bounds([s])
                    if not simple_line: c.create_rectangle(*self.screen(x0,y1),*self.screen(x1,y0),outline='#354d67',dash=(3,3))
                    elif self.tool=='select':
                        for index,point in enumerate(shape_paths(s)[0]):
                            px,py=self.screen(*point); c.create_oval(px-5,py-5,px+5,py+5,fill='white',outline='#1878d1',width=2,tags=f'line-end:{s.id}:{index}')
                    if not simple_line and self.tool=='select' and len(self.selection)==1 and not s.extra.get('locked') and x1>x0 and y1>y0:
                        positions={'sw':(x0,y0),'s':((x0+x1)/2,y0),'se':(x1,y0),'e':(x1,(y0+y1)/2),'ne':(x1,y1),'n':((x0+x1)/2,y1),'nw':(x0,y1),'w':(x0,(y0+y1)/2)}
                        for handle,pt in positions.items():
                            a,b=self.screen(*pt); c.create_rectangle(a-5,b-5,a+5,b+5,fill='white',outline='#1878d1',width=2,tags=(f'resize:{s.id}:{handle}',))
                except ValueError: pass
        if len(self.poly_points)>1: c.create_line(*[v for pt in self.poly_points for v in self.screen(*pt)],fill='#754bb5',dash=(3,3))
    def refresh(self):
        if not hasattr(self,'layerbox'): return
        valid={s.id for s in self.p.shapes}; self.selection.intersection_update(valid)
        if self.selected not in valid: self.selected=next(iter(self.selection),None)
        if self.selected: self.selection.add(self.selected)
        super().refresh()
        self.loading=True
        if self.selection: self.tree.selection_set(list(self.selection))
        self.loading=False
        s=self.current(); self.property_baseline={}
        if s:
            for key in ('x','y','w','h'):
                self.property_baseline[key]=f'{getattr(s,key):.1f}'; self.vars[key].set(self.property_baseline[key])
            if hasattr(self,'fontbox'):
                path=s.extra.get('font',''); index=s.extra.get('font_index',0)
                match=next((f for f in self.font_faces if f.path==path and f.index==index),None)
                self.fontbox.set(match.label if match else (s.extra.get('font_label') or ('Standardschrift' if s.kind=='text' else '')))
        elif hasattr(self,'fontbox'): self.fontbox.set('')
        if hasattr(self,'palette'):
            for child in self.palette.winfo_children(): child.destroy()
            ttk.Label(self.palette,text='Ebenen:').pack(side='left',padx=(0,6))
            for l in self.p.layers:
                b=tk.Button(self.palette,text=l.name,bg=l.color,fg='white',relief='sunken' if l.id==self.active_layer else 'raised',bd=3 if l.id==self.active_layer else 1,padx=12,pady=5,command=lambda lid=l.id:self.quick_layer(lid))
                b.pack(side='left',padx=2); b.bind('<Double-Button-1>',lambda e,lid=l.id:self.rename_layer(lid))
                b.bind('<Button-3>',lambda e,lid=l.id:self.quick_layer(lid,False))
            ttk.Button(self.palette,text='+',width=3,command=self.add_layer).pack(side='left',padx=5)
            ttk.Button(self.palette,text='−',width=3,command=self.remove_layer,state='normal' if len(self.p.layers)>1 else 'disabled').pack(side='left')
    def tree_selected(self,e):
        if self.loading: return
        ids=set(self.tree.selection())
        if ids!=self.selection: self.selection=ids; self.selected=next(iter(ids),None); self.refresh()
    def apply(self):
        s=self.current()
        if not s or s.extra.get('locked'): return
        try:
            p=deepcopy(self.p); target=next(t for t in p.shapes if t.id==s.id)
            oldw,oldh=target.w,target.h
            edited=set()
            for k in ('x','y','w','h'):
                value=self.vars[k].get()
                if value!=self.property_baseline.get(k):
                    setattr(target,k,float(value.replace(',','.'))); edited.add(k)
            if self.keep_ratio.get() and oldw>0 and oldh>0:
                if 'w' in edited and 'h' not in edited: target.h=oldh*target.w/oldw
                elif 'h' in edited and 'w' not in edited: target.w=oldw*target.h/oldh
            target.name=self.vars['name'].get(); target.text=self.vars['text'].get(); target.layer=p.layers[self.object_layer.current()].id
            if target.kind in {'polygon','polyline'} and (target.w!=oldw or target.h!=oldh):
                if oldw<=0 or oldh<=0: raise ValueError('Nullbreite/-höhe: Linien über Knoten bearbeiten.')
                contours=target.extra.get('contours',[target.points]); target.extra['contours']=[[[x*target.w/oldw,y*target.h/oldh] for x,y in pts] for pts in contours]; target.points=target.extra['contours'][0]
                if 'bezier' in target.extra: target.extra['bezier']=[[x*target.w/oldw,y*target.h/oldh] for x,y in target.extra['bezier']]
            if target.kind=='text':
                if 'w' in edited and oldw>0:
                    target.extra['text_scale_x']=target.extra.get('text_scale_x',1.)*(target.w/oldw)/(target.h/oldh)
                x0,y0,x1,y1=bounds([target]); target.w=x1-x0
            self.commit(p)
        except Exception as ex: messagebox.showerror('Objekt',str(ex))
    def layer_selected(self):
        super().layer_selected()
        if hasattr(self,'output'):
            l=next(l for l in self.p.layers if l.id==self.active_layer); self.output.set(l.output); self.air.set(l.air)
    def apply_layer(self):
        try:
            p=deepcopy(self.p); l=next(l for l in p.layers if l.id==self.active_layer)
            l.name=self.lvars['name'].get()
            for k in ('speed','power','interval'): setattr(l,k,float(self.lvars[k].get()))
            l.passes=int(self.lvars['passes'].get()); l.mode=self.mode.get(); l.visible=self.visible.get(); l.output=self.output.get(); l.air=self.air.get(); self.commit(p)
        except Exception as ex: messagebox.showerror('Ebene',str(ex))
    def quick_layer(self,lid,assign=True):
        self.active_layer=lid
        if assign and self.chosen():
            p=deepcopy(self.p)
            for s in p.shapes:
                if s.id in self.selection and not s.extra.get('locked'): s.layer=lid
            self.commit(p)
        else: self.refresh()
    def rename_layer(self,lid=None):
        lid=lid or self.active_layer; l=next(l for l in self.p.layers if l.id==lid); name=simpledialog.askstring('Ebene umbenennen','Name:',initialvalue=l.name,parent=self)
        if name: p=deepcopy(self.p); next(l for l in p.layers if l.id==lid).name=name; self.commit(p)
    def layer_color(self):
        color=colorchooser.askcolor(parent=self)[1]
        if color: p=deepcopy(self.p); next(l for l in p.layers if l.id==self.active_layer).color=color; self.commit(p)
    def add_layer(self):
        p=deepcopy(self.p); l=Layer('Ebene '+str(len(p.layers)+1),COLORS[len(p.layers)%len(COLORS)]); p.layers.append(l); self.active_layer=l.id; self.commit(p)
    def move_layer(self,direction):
        p=deepcopy(self.p); i=next(i for i,l in enumerate(p.layers) if l.id==self.active_layer); j=i+direction
        if 0<=j<len(p.layers): p.layers[i],p.layers[j]=p.layers[j],p.layers[i]; self.commit(p)
    def remove_layer(self,lid=None):
        from dataclasses import asdict
        from steburn.core.processing import resolve
        if len(self.p.layers)==1: self.status.set('Die letzte Ebene bleibt erhalten.'); return
        p=deepcopy(self.p); index=next(i for i,l in enumerate(p.layers) if l.id==(lid or self.active_layer)); old=p.layers.pop(index)
        target=p.layers[min(index,len(p.layers)-1)]; moved=0
        for shape in p.shapes:
            if shape.layer==old.id:
                shape.extra['processing']=asdict(resolve(shape,old)); shape.layer=target.id; moved+=1
        self.active_layer=target.id; self.commit(p)
        self.status.set(f'Ebene entfernt · {moved} Objekte mit Bearbeitungswerten nach „{target.name}“ verschoben · Strg+Z macht rückgängig.')
    def delete(self):
        ids={s.id for s in self.chosen() if not s.extra.get('locked')}
        if ids: p=deepcopy(self.p); p.shapes=[s for s in p.shapes if s.id not in ids]; self.selection.clear(); self.selected=None; self.commit(p)
    def duplicate(self):
        shapes=self.chosen()
        if not shapes: return
        p=deepcopy(self.p); ids=set(); groups={}
        for s in shapes:
            s=deepcopy(s); s.id=uuid4().hex; s.x+=5; s.y+=5; s.extra.pop('locked',None)
            if 'group' in s.extra: s.extra['group']=groups.setdefault(s.extra['group'],uuid4().hex)
            p.shapes.append(s); ids.add(s.id)
        self.selection=ids; self.selected=next(iter(ids)); self.commit(p)
    def group(self):
        if len(self.chosen())<2: return
        p=deepcopy(self.p); group=uuid4().hex
        for s in p.shapes:
            if s.id in self.selection: s.extra['group']=group
        self.commit(p)
    def ungroup(self):
        p=deepcopy(self.p)
        for s in p.shapes:
            if s.id in self.selection: s.extra.pop('group',None)
        self.commit(p)
    def lock(self,value):
        p=deepcopy(self.p)
        for s in p.shapes:
            if s.id in self.selection: s.extra['locked']=value
        self.commit(p)
    def transform_selection(self,op):
        try:
            p=deepcopy(self.p)
            chosen=[s for s in self.chosen() if not s.extra.get('locked')]
            if not chosen: return
            x0,y0,x1,y1=bounds(chosen); center=((x0+x1)/2,(y0+y1)/2)
            for s in p.shapes:
                if s.id in self.selection and not s.extra.get('locked'): transform(s,op,center)
            self.commit(p)
        except Exception as ex: messagebox.showerror('Transformation',str(ex))
    def load_fonts(self):
        if not self.font_faces:
            self.font_faces=installed_fonts()
        self.fontbox['values']=[f.label for f in self.font_faces]
    def post_fonts(self):
        self.load_fonts(); query=self.fontbox.get().casefold()
        if query and query!='standardschrift' and not any(query==f.label.casefold() for f in self.font_faces):
            self.fontbox['values']=[f.label for f in self.font_faces if query in f.label.casefold()]
    def filter_fonts(self,e=None):
        self.load_fonts(); query=self.fontbox.get().casefold()
        self.fontbox['values']=[f.label for f in self.font_faces if query in f.label.casefold()]
    def system_font_selected(self,e=None):
        s=self.current()
        if not s or s.kind!='text' or s.extra.get('locked'): return
        face=next((f for f in self.font_faces if f.label==self.fontbox.get()),None)
        if face is None: return
        try:
            p=deepcopy(self.p); target=next(t for t in p.shapes if t.id==s.id)
            target.extra.update(font=face.path,font_index=face.index,font_label=face.label)
            a,b,c,d=bounds([target]); target.w=c-a; self.commit(p)
        except Exception as ex: messagebox.showerror('Systemschrift',str(ex))
    def choose_font(self):
        s=self.current()
        if not s or s.kind!='text': return
        path=filedialog.askopenfilename(filetypes=[('TrueType / OpenType','*.ttf *.otf')],initialdir='C:/Windows/Fonts' if Path('C:/Windows/Fonts').exists() else str(Path.home()))
        if path:
            try:
                p=deepcopy(self.p); target=next(t for t in p.shapes if t.id==s.id); target.extra['font']=path; target.extra['font_index']=0; target.extra['font_label']=Path(path).stem; a,b,c,d=bounds([target]); target.w=c-a; self.commit(p)
            except Exception as ex: messagebox.showerror('Schrift',str(ex))
    def text_to_paths(self):
        try:
            p=deepcopy(self.p)
            for s in p.shapes:
                if s.id in self.selection and s.kind=='text' and not s.extra.get('locked'): as_paths_shape(s,shape_paths(s))
            self.commit(p)
        except Exception as ex: messagebox.showerror('Textpfade',str(ex))
    def align(self,axis):
        try:
            p=deepcopy(self.p)
            for s in p.shapes:
                if s.id in self.selection and not s.extra.get('locked'):
                    a,b,c,d=bounds([s]); s.x+=(p.width-(c-a))/2-a if axis=='x' else 0; s.y+=(p.height-(d-b))/2-b if axis=='y' else 0
            self.commit(p)
        except Exception as ex: messagebox.showerror('Ausrichten',str(ex))
    def align_many(self,mode):
        shapes=self.chosen()
        if not shapes: return
        x0,y0,x1,y1=bounds(shapes); p=deepcopy(self.p)
        for s in p.shapes:
            if s.id not in self.selection or s.extra.get('locked'): continue
            a,b,c,d=bounds([s])
            if mode=='left': s.x+=x0-a
            if mode=='right': s.x+=x1-c
            if mode=='bottom': s.y+=y0-b
            if mode=='top': s.y+=y1-d
            if mode=='center_x': s.x+=(x0+x1-a-c)/2
            if mode=='center_y': s.y+=(y0+y1-b-d)/2
        self.commit(p)
    def distribute(self,axis):
        shapes=sorted(self.chosen(),key=lambda s:sum(bounds([s])[i] for i in ((0,2) if axis=='x' else (1,3))))
        if len(shapes)<3: messagebox.showinfo('Verteilen','Mindestens drei Objekte auswählen.'); return
        def center(s): a,b,c,d=bounds([s]); return (a+c)/2 if axis=='x' else (b+d)/2
        first,last=center(shapes[0]),center(shapes[-1]); p=deepcopy(self.p)
        for i,original in enumerate(shapes):
            s=next(s for s in p.shapes if s.id==original.id)
            if not s.extra.get('locked'): setattr(s,axis,getattr(s,axis)+first+(last-first)*i/(len(shapes)-1)-center(original))
        self.commit(p)
    def reorder(self,front):
        p=deepcopy(self.p); chosen=[s for s in p.shapes if s.id in self.selection]; others=[s for s in p.shapes if s.id not in self.selection]; p.shapes=others+chosen if front else chosen+others; self.commit(p)
    def regular_polygon(self):
        n=simpledialog.askinteger('Vieleck','Anzahl Ecken:',initialvalue=6,minvalue=3,maxvalue=100)
        if not n: return
        radius=simpledialog.askfloat('Vieleck','Radius in mm:',initialvalue=20,minvalue=.1,maxvalue=200)
        if radius is None: return
        pts=[(self.p.width/2+radius*math.cos(i*math.tau/n),self.p.height/2+radius*math.sin(i*math.tau/n)) for i in range(n)]; pts.append(pts[0]); s=as_paths_shape(Shape('polygon',layer=self.active_layer,name=f'{n}-Eck'),[pts]); p=deepcopy(self.p); p.shapes.append(s); self.selection={s.id}; self.selected=s.id; self.commit(p)
    def boolean(self,op):
        selected=self.chosen()
        if len(selected)<2: messagebox.showinfo('Boolesche Operation','Mindestens zwei geschlossene Formen auswählen. Bei Differenz ist das erste Objekt der Objektliste die Ausgangsform.'); return
        if any(s.extra.get('locked') or s.kind=='image' for s in selected): return
        try:
            geo=polygon_geometry(selected[0])
            for s in selected[1:]: geo=getattr(geo,op)(polygon_geometry(s))
            paths=geometry_paths(geo)
            if not paths: messagebox.showinfo('Ergebnis','Ergebnis ist leer; Originale unverändert.'); return
            shape=as_paths_shape(Shape('polygon',layer=selected[0].layer,name=op),paths); p=deepcopy(self.p); p.shapes=[s for s in p.shapes if s.id not in self.selection]; p.shapes.append(shape); self.selected=shape.id; self.selection={shape.id}; self.commit(p)
        except Exception as ex: messagebox.showerror('Boolesche Operation',str(ex))
    def offset(self):
        distance=simpledialog.askfloat('Versatz','Abstand in mm (negativ = innen):',initialvalue=1,minvalue=-100,maxvalue=100)
        if distance is None: return
        try:
            p=deepcopy(self.p); ids=set()
            for s in self.chosen():
                paths=geometry_paths(polygon_geometry(s).buffer(distance))
                if paths:
                    shape=as_paths_shape(Shape('polygon',layer=s.layer,name=s.name+' Versatz'),paths); p.shapes.append(shape); ids.add(shape.id)
            self.selection=ids; self.selected=next(iter(ids),None); self.commit(p)
        except Exception as ex: messagebox.showerror('Versatz',str(ex))
    def qrcode(self):
        text=simpledialog.askstring('QR-Code','Text oder URL:',parent=self)
        if not text: return
        try:
            import qrcode
            code=qrcode.QRCode(border=4); code.add_data(text); code.make(fit=True); matrix=code.get_matrix(); cell=.8; n=len(matrix); paths=[]
            for row,data in enumerate(matrix):
                for col,dark in enumerate(data):
                    if dark:
                        x=20+col*cell; y=20+(n-1-row)*cell; paths.append([(x,y),(x+cell,y),(x+cell,y+cell),(x,y+cell),(x,y)])
            s=as_paths_shape(Shape('polygon',layer=self.active_layer,name='QR-Code'),paths); p=deepcopy(self.p); p.shapes.append(s); self.selection={s.id}; self.selected=s.id; self.commit(p)
            messagebox.showinfo('QR-Code','Dunkle Module als Konturen erzeugt. Für ausgefüllte Module Ebene auf Fläche stellen. Ruhezone von vier Modulen freihalten.')
        except Exception as ex: messagebox.showerror('QR-Code',str(ex))
    def array(self):
        shapes=self.chosen()
        if not shapes: return
        cols=simpledialog.askinteger('Raster','Spalten:',initialvalue=3,minvalue=1,maxvalue=30)
        if cols is None: return
        rows=simpledialog.askinteger('Raster','Zeilen:',initialvalue=2,minvalue=1,maxvalue=30)
        if rows is None: return
        gap=simpledialog.askfloat('Raster','Abstand zwischen Begrenzungsrahmen (mm):',initialvalue=5,minvalue=0,maxvalue=100)
        if gap is None: return
        x0,y0,x1,y1=bounds(shapes); p=deepcopy(self.p)
        for row in range(rows):
            for col in range(cols):
                if row==col==0: continue
                group=uuid4().hex
                for original in shapes:
                    s=deepcopy(original); s.id=uuid4().hex; s.x+=col*(x1-x0+gap); s.y+=row*(y1-y0+gap); s.extra['group']=group; p.shapes.append(s)
        self.commit(p)
    def circle_array(self):
        shapes=self.chosen()
        if not shapes: return
        n=simpledialog.askinteger('Kreisanordnung','Anzahl Kopien (inkl. Original):',initialvalue=6,minvalue=2,maxvalue=100)
        if not n: return
        radius=simpledialog.askfloat('Kreisanordnung','Radius (mm):',initialvalue=40,minvalue=1,maxvalue=200)
        if radius is None: return
        p=deepcopy(self.p)
        for i in range(1,n):
            dx=radius*(math.cos(i*math.tau/n)-1); dy=radius*math.sin(i*math.tau/n); group=uuid4().hex
            for original in shapes:
                s=deepcopy(original); s.id=uuid4().hex; s.x+=dx; s.y+=dy; s.extra['group']=group; p.shapes.append(s)
        self.commit(p)
    def nest(self):
        shapes=self.chosen()
        if not shapes: return
        try:
            p=deepcopy(self.p); x=y=5.; rowheight=0.
            for original in sorted(shapes,key=lambda s:bounds([s])[3]-bounds([s])[1],reverse=True):
                s=next(s for s in p.shapes if s.id==original.id)
                if s.extra.get('locked'): raise ValueError('Gesperrte Objekte zuerst entsperren.')
                a,b,c,d=bounds([s]); w=c-a; h=d-b
                if x+w>p.width-5: x=5.; y+=rowheight+5; rowheight=0.
                if x+w>p.width-5 or y+h>p.height-5: raise ValueError('Objekte passen mit 5 mm Abstand nicht auf die Arbeitsfläche.')
                s.x+=x-a; s.y+=y-b; x+=w+5; rowheight=max(rowheight,h)
            self.commit(p)
        except Exception as ex: messagebox.showerror('Rechteck-Schachtelung',str(ex))
    def adjust_image(self):
        selected=[s for s in self.chosen() if s.kind=='image' and not s.extra.get('locked')]
        if not selected: messagebox.showinfo('Bild','Bild auswählen.'); return
        contrast=simpledialog.askfloat('Bildkontrast','Kontrastfaktor:',initialvalue=1.2,minvalue=.1,maxvalue=5)
        if contrast is None: return
        from PIL import Image,ImageEnhance,ImageOps
        p=deepcopy(self.p)
        for original in selected:
            s=next(s for s in p.shapes if s.id==original.id)
            with Image.open(io.BytesIO(base64.b64decode(s.extra['image']))) as im: im=ImageEnhance.Contrast(ImageOps.grayscale(im)).enhance(contrast); buf=io.BytesIO(); im.save(buf,format='PNG'); s.extra['image']=base64.b64encode(buf.getvalue()).decode()
        self.commit(p)
    def simulate(self):
        try: Simulation(self,build_plan(self.p))
        except Exception as ex: messagebox.showerror('Simulation abgebrochen',str(ex))
    def frame_shapes(self):
        return self.chosen() or [s for s in self.p.shapes if next(l for l in self.p.layers if l.id==s.layer).output]
    def simulate_frame(self):
        try:
            shapes=self.frame_shapes(); pts=rectangle_plan(self.p,shapes); segments=[Segment((0,0),pts[0],1200,0,'frame')]+[Segment(a,b,1200,0,'frame') for a,b in zip(pts,pts[1:])]; Simulation(self,Plan(segments,[]),'Rahmensimulation · Laser aus')
        except Exception as ex: messagebox.showerror('Rahmen',str(ex))
    def set_preview(self,value):
        if value: self.simulate()
        else: self.preview=False; self.render()
    def check(self):
        try:
            plan=build_plan(self.p); messagebox.showinfo('Projektprüfung','\n'.join(plan.warnings) if plan.warnings else f'{len(plan.segments)} Segmente, keine geometrischen Auffälligkeiten.\nMaterial und Maschine nicht durch Simulation geprüft.')
        except Exception as ex: messagebox.showerror('Projektprüfung',str(ex))
    def import_file(self):
        pattern=' '.join('*'+e for e in ALL_EXTENSIONS)
        path=filedialog.askopenfilename(filetypes=[('Laser-/Gestaltungsdateien',pattern),('Alle Dateien','*.*')])
        if not path: return
        try:
            result=import_file(path,self.active_layer)
            if result.warnings and not messagebox.askokcancel('Importhinweise','\n'.join(result.warnings)+'\n\nImport übernehmen?'): return
            p=deepcopy(self.p); p.shapes.extend(result.shapes); self.selection={s.id for s in result.shapes}; self.selected=next(iter(self.selection),None); self.commit(p)
        except Exception as ex: messagebox.showerror('Import vollständig abgebrochen',str(ex))
    def export_file(self):
        path=filedialog.asksaveasfilename(defaultextension='.svg',filetypes=[('SVG','*.svg')])
        if path:
            try: export_svg(self.p,path); self.status.set('SVG exportiert · Text als Pfade')
            except Exception as ex: messagebox.showerror('Export',str(ex))
    def store_material(self):
        name=simpledialog.askstring('Materialvorlage','Material / Dicke / Bearbeitung:',parent=self)
        if not name: return
        p=deepcopy(self.p); l=next(l for l in p.layers if l.id==self.active_layer); p.extensions.setdefault('materials',{})[name]={k:getattr(l,k) for k in ('speed','power','passes','mode','interval','air')}; self.commit(p)
    def use_material(self):
        preset=self.p.extensions.get('materials',{}).get(self.materialbox.get())
        if not preset: return
        try:
            p=deepcopy(self.p); l=next(l for l in p.layers if l.id==self.active_layer)
            for k in ('speed','power','passes','mode','interval','air'):
                if k in preset: setattr(l,k,preset[k])
            self.commit(p)
        except Exception as ex: messagebox.showerror('Material',str(ex))
    def new(self):
        if self.busy: return
        if self.confirm(): self.selection.clear(); self.selected=None; self.p=Project(); self.history=History(); self.path=None; self.dirty=False; self.image_cache.clear(); self.refresh(); self.fit(); self.title('Steburn · Unbenannt')
    def open(self):
        if self.busy or not self.confirm(): return
        path=filedialog.askopenfilename(filetypes=[('Steburn Projekt','*.steburn')])
        if path:
            try:
                p=Project.load(path); self.p=p; self.path=path; self.selection.clear(); self.selected=None; self.history=History(); self.dirty=False; self.image_cache.clear(); self.refresh(); self.fit(); self.title('Steburn · '+p.title)
            except Exception as ex: messagebox.showerror('Öffnen',str(ex))
    def ports(self):
        from serial.tools.list_ports import comports
        ports=list(comports()); messagebox.showinfo('COM-Ports','\n'.join(f'{p.device}: {p.description}' for p in ports) or 'Keine Ports erkannt.')
        if len(ports)==1: self.port.set(ports[0].device)
    def run_device(self,task):
        if self.busy: messagebox.showinfo('Gerät','Ein Geräteauftrag läuft bereits.'); return
        self.busy=True
        def worker():
            try: self.events.put(('ok',task()))
            except Exception as ex: self.events.put(('error',str(ex)))
        threading.Thread(target=worker,daemon=True).start()
    def poll(self):
        try:
            while True:
                kind,value=self.events.get_nowait(); self.busy=False
                if kind=='error': self.connection.set(str(value)); self.status.set(str(value))
                else:
                    self.connection.set('Verbunden, Profil noch prüfen' if self.device.connected else 'Nicht verbunden')
                    if value: self.connection.set(str(value)); self.status.set(str(value).splitlines()[-1])
        except queue.Empty: pass
        self.header_status.configure(text='A40 Pro · 400 × 400 mm · '+('VERBUNDEN' if self.device.connected else 'OFFLINE'))
        self.after(100,self.poll)
    def connect_device(self):
        port=self.port.get().strip(); baud=self.baud.get()
        if not port: messagebox.showinfo('Verbindung','COM-Port eintragen.'); return
        self.run_device(lambda:self.device.connect(port,baud))
    def confirm_origin(self):
        if self.busy or not self.device.connected: return
        if messagebox.askyesno('Koordinaten bestätigen','Ist der reale Arbeitsnullpunkt links unten korrekt eingerichtet und die Position durch Homing oder überprüftes manuelles Referenzieren bekannt?\n\nSteburn führt keine Referenzfahrt aus und setzt keinen Nullpunkt. Falsche Bestätigung kann zu falschen Bewegungen führen.'):
            self.device.origin_confirmed=True; self.connection.set('Nullpunkt manuell bestätigt; Status wird vor jeder Bewegung geprüft')
    def prepare_visible(self):
        visible=self.visible_align.get()
        if visible:
            try: value=float(self.low_power.get())
            except ValueError: raise ValueError('Ungültige Ausrichtleistung')
            if not 0<value<=.5: raise ValueError('Ausrichtleistung muss >0 und maximal 0.5 % sein.')
            if not messagebox.askyesno('Sichtbare Ausrichtung','Diese Leistung muss an deinem Laser und Material zuvor getestet sein. Auch sehr geringe Leistung kann einbrennen.\n\nGetestete Leistung verwenden?'): return None
            self.device.low_power=value; self.device.low_power_confirmed=True
        return visible
    def position_target(self,point):
        try:
            if self.busy: return
            if not self.device.connected: messagebox.showinfo('Mausziel',f'Ziel X {point[0]:.1f}, Y {point[1]:.1f} mm.\nKeine physische Bewegung: Gerät nicht verbunden.'); return
            visible=self.prepare_visible()
            if visible is None: return
            if not messagebox.askokcancel('Physische Positionierung',f'Zu X {point[0]:.1f}, Y {point[1]:.1f} mm fahren?\n'+('Danach sichtbarer 0.1-s-Puls.' if visible else 'Laser bleibt aus.')): return
            width,height=self.p.width,self.p.height; self.run_device(lambda:self.device.align([point],width,height,visible,pulse=visible))
        except Exception as ex: messagebox.showerror('Ausrichtung',str(ex))
    def frame(self):
        try:
            if self.busy: return
            pts=rectangle_plan(self.p,self.frame_shapes())
            if not self.device.connected: messagebox.showinfo('Rahmen','Gerät nicht verbunden. Der Rahmen kann bereits simuliert werden.'); return
            visible=self.prepare_visible()
            if visible is None: return
            if not messagebox.askokcancel('Physischer Rahmen',f'Rechteck von {pts[0]} bis {pts[2]} mm abfahren?\n'+('Sichtbarer Strahl aktiviert.' if visible else 'Laser bleibt aus.')): return
            width,height=self.p.width,self.p.height; self.run_device(lambda:self.device.align(pts,width,height,visible))
        except Exception as ex: messagebox.showerror('Rahmen',str(ex))
    def stop_device(self): self.device.emergency_stop(); self.connection.set('Abgebrochen · Reset gesendet · neu verbinden')
    def disconnect_device(self):
        if self.busy: self.stop_device(); return
        self.device.disconnect(); self.connection.set('Nicht verbunden')
    def close(self):
        if self.busy:
            self.stop_device(); messagebox.showinfo('Gerät','Abbruch angefordert. Auf Ende des Geräteauftrags warten, dann schließen.'); return
        if self.confirm(): self.device.disconnect(); self.destroy()
