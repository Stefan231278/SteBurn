"""Large canvas, contextual tool options, rulers and collapsible inspectors."""
import tkinter as tk
from tkinter import ttk,filedialog
from copy import deepcopy
from types import SimpleNamespace
import math
from steburn.ui.studio import App as Studio
from steburn.ui.presentation import ToolTip
from steburn.ui.widgets import ScrollPanel
from steburn.core.paths import bounds,as_paths_shape,shape_paths
from steburn.core.design import rotate_shape
from steburn.io.importers import import_file as load_file,ALL_EXTENSIONS,BITMAPS

TOOLS=[('select','↖','Auswahl / bewegen'),('rect','▭','Rechteck'),('ellipse','○','Ellipse'),('line','╱','Linie'),('bezier','⌁','Bézierkurve'),('pencil','✎','Freihand'),('polygon','⬡','Vieleck'),('nodes','◇','Knoten bearbeiten'),('text','T','Text'),('measure','↔','Messen'),('position','⊕','Laserziel')]

class App(Studio):
    def __init__(self):
        self.workspace_ready=False; self.dock_visible=True; self.photo_window=None
        self.context_key=None; self.space_pan=False; self.ruler_drag=None
        super().__init__()
    def build(self):
        super().build()
        from steburn import __version__
        self.title(f'SteBurn {__version__} · Design & Laser')
        self.snap_enabled=tk.BooleanVar(value=False); self.grid_visible=tk.BooleanVar(value=True)
        self.grid_step=tk.StringVar(value='5'); self.draw_radius=tk.StringVar(value='0'); self.zoom_label=tk.StringVar(value='100 %')
        self.freehand_tolerance=tk.StringVar(value='.15'); self.rotation=tk.StringVar(value='0')
        self.left_dock=self.nametowidget(self.main_pane.panes()[0]); self.right_dock=self.notebook.master
        self.build_tool_rail(); self.build_object_dock(); self.build_image_inspector(); self.build_context_bar()
        for tab,text in [(self.page_tabs['props'],'Eigenschaften'),(self.text_tab,'Text'),(self.vector_tab,'Pfade'),(self.page_tabs['layers'],'Ebenen')]: self.notebook.tab(tab,text=text)
        self.canvas.bind('<Double-Button-1>',self.double_click)
        self.canvas.bind('<KeyPress-space>',lambda e:self.pan_key(True)); self.canvas.bind('<KeyRelease-space>',lambda e:self.pan_key(False))
        self.canvas.bind('<FocusOut>',lambda e:self.pan_key(False)); self.canvas.bind('<Home>',lambda e:self.fit())
        view=tk.Menu(self.menubar,tearoff=False); self.menubar.add_cascade(label='Ansicht',menu=view)
        view.add_command(label='Bedienfelder ein-/ausblenden (Tab)',command=self.toggle_dock)
        view.add_command(label='Objekte & Ebenen',command=self.show_objects)
        view.add_checkbutton(label='Raster anzeigen',variable=self.grid_visible,command=self.render)
        view.add_checkbutton(label='Am Raster / an Hilfslinien fangen',variable=self.snap_enabled)
        view.add_command(label='Hilfslinien entfernen',command=self.clear_guides)
        view.add_command(label='Arbeitsfläche einpassen',command=self.fit)
        self.workspace_ready=True; self.switch_workspace('design'); self.refresh()
        self.grid_step.trace_add('write',lambda *args:self.after_idle(self.render))
        from steburn.ui.theme import ThemeManager
        self.theme=ThemeManager(self)
        self.dark_mode=tk.BooleanVar(value=self.theme.dark)
        self.theme_label=tk.StringVar()
        ttk.Button(self.header,textvariable=self.theme_label,style='Nav.TButton',command=self.toggle_theme).pack(side='right',padx=6)
        view.add_separator(); view.add_checkbutton(label='Dunkle Darstellung',variable=self.dark_mode,command=self.set_theme)
        self.set_theme(persist=False)
        self.after(400,self.set_initial_columns)
    def toggle_theme(self):
        self.dark_mode.set(not self.dark_mode.get()); self.set_theme()
    def set_theme(self,persist=True):
        try: self.theme.apply('dark' if self.dark_mode.get() else 'light',persist=persist)
        except OSError as ex: self.status.set('Darstellung aktiv; Einstellung konnte nicht gespeichert werden: '+str(ex))
        self.theme_label.set('◐ Dunkel' if self.theme.dark else '◐ Hell')
    def set_initial_columns(self):
        if not self.workspace_ready: return
        self.main_pane.sashpos(0,66)
        if self.dock_visible: self.main_pane.sashpos(1,max(500,self.main_pane.winfo_width()-345))
        self.fit()
    def build_tool_rail(self):
        for child in list(self.left_dock.winfo_children()):
            if child==self.tree: child.pack_forget()
            else: child.destroy()
        self.left_dock.configure(width=64)
        self.tool_buttons={}; self.rail_actions={}; self._tool_icon_cache={}
        for tool,icon,label in TOOLS:
            if tool in ('rect','nodes','measure'): ttk.Separator(self.left_dock).pack(fill='x',padx=12,pady=3)
            b=ttk.Button(self.left_dock,text=label,compound='none',style='Rail.TButton',command=lambda t=tool:self.set_tool(t))
            b.pack(fill='x',padx=7,pady=1); b.usage_help=ToolTip(b,label+' · Optionen passend zum Werkzeug oben'); self.tool_buttons[tool]=b
        ttk.Separator(self.left_dock).pack(fill='x',padx=12,pady=3)
        for key,label,command in [('import','Fotos, Bilder und Vektoren importieren',self.import_file),('objects','Objektliste und Ebenen öffnen',self.show_objects)]:
            button=ttk.Button(self.left_dock,text=label,compound='none',style='Rail.TButton',command=command); button.pack(fill='x',padx=7,pady=1)
            button.usage_help=ToolTip(button,label); self.rail_actions[key]=button
        self.refresh_tool_icons()
    def refresh_tool_icons(self):
        if not hasattr(self,'rail_actions'): return
        from PIL import ImageTk
        from steburn.ui.tool_icons import draw_icon
        dark=getattr(getattr(self,'theme',None),'dark',False)
        style=ttk.Style(self)
        layout=[('Button.border',{'sticky':'nswe','children':[('Button.padding',{'sticky':'nswe','children':[('Button.label',{'sticky':'nswe'})]})]})]
        for name,selected in [('Rail.TButton',False),('RailSelected.TButton',True)]:
            style.layout(name,layout)
            background=('#174e58' if dark else '#087e8b') if selected else ('#202c3d' if dark else '#f4f7fb')
            border=('#5eead4' if dark else '#087e8b') if selected else background
            style.configure(name,padding=(5,3),anchor='center',background=background,bordercolor=border,lightcolor=border,darkcolor=border,relief='flat')
            hover=('#216370' if dark else '#0a919d') if selected else ('#27465b' if dark else '#e1f1f3')
            style.map(name,background=[('pressed','#1c6c77' if dark else '#086976'),('active',hover)],bordercolor=[('focus','#67d5cc')])
        for key,button in {**self.tool_buttons,**self.rail_actions}.items():
            selected=key==self.tool and key in self.tool_buttons
            cache_key=(key,dark,selected)
            if cache_key not in self._tool_icon_cache: self._tool_icon_cache[cache_key]=ImageTk.PhotoImage(draw_icon(key,dark,selected,size=26),master=self)
            button.configure(image=self._tool_icon_cache[cache_key],style='RailSelected.TButton' if selected else 'Rail.TButton')
    def build_object_dock(self):
        self.objects_tab=ttk.Frame(self.notebook,padding=8); self.notebook.add(self.objects_tab,text='Objekte')
        row=ttk.Frame(self.objects_tab); row.pack(fill='x',pady=(0,6))
        for label,fn in [('Kopie',self.duplicate),('Löschen',lambda:Studio.delete(self)),('Sperren',lambda:self.lock(True))]: ttk.Button(row,text=label,style='Compact.TButton',command=fn).pack(side='left',fill='x',expand=True,padx=1)
        self.tree.destroy()
        self.tree=ttk.Treeview(self.objects_tab,show='tree',selectmode='extended',height=9); self.tree.pack(fill='both',expand=True)
        self.tree.bind('<<TreeviewSelect>>',self.tree_selected); self.tree.bind('<Button-3>',self.tree_context)
        ttk.Label(self.objects_tab,text='Strg: Mehrfachauswahl · Rechtsklick: Objektaktionen',wraplength=295,style='Studio.Muted.TLabel').pack(fill='x',pady=8)
    def build_image_inspector(self):
        self.image_tab=ScrollPanel(self.notebook); self.notebook.add(self.image_tab,text='Bild')
        card=self.card(self.image_tab.content,'Bild & Laser-Raster')
        self.image_info=tk.StringVar(value='Ein Bild auswählen oder importieren.')
        ttk.Label(card,textvariable=self.image_info,wraplength=290).pack(fill='x',pady=6)
        ttk.Button(card,text='Bildstudio öffnen',style='Accent.TButton',command=self.adjust_image).pack(fill='x',pady=5)
        ttk.Button(card,text='Weitere Bilder importieren',style='Compact.TButton',command=self.import_file).pack(fill='x',pady=4)
        ttk.Label(card,text='Original, Zuschnitt und Bildkorrekturen bleiben gespeichert. Helligkeit ist eine Bildkorrektur; die maximale Laserleistung wird separat eingestellt.',wraplength=290,style='Studio.Muted.TLabel').pack(fill='x',pady=10)
    def build_context_bar(self):
        self.context_bar=ttk.Frame(self.canvas.master,padding=(7,6))
        self.context_bar.pack(fill='x',before=self.canvas)
        self.context_content=ttk.Frame(self.context_bar); self.context_content.pack(side='left',fill='x',expand=True)
        controls=ttk.Frame(self.context_bar); controls.pack(side='right')
        for label,fn in [('−',lambda:self.zoom(.85,self.canvas.winfo_width()/2,self.canvas.winfo_height()/2)),('+',lambda:self.zoom(1/.85,self.canvas.winfo_width()/2,self.canvas.winfo_height()/2)),('Einpassen',self.fit),('☷',self.toggle_dock)]: ttk.Button(controls,text=label,width=2 if label in ('−','+','☷') else 8,style='Compact.TButton',command=fn).pack(side='left',padx=1)
        ttk.Label(controls,textvariable=self.zoom_label,width=6).pack(side='left',padx=5)
    def bind_shortcuts(self):
        super().bind_shortcuts()
        self.bind('<Tab>',self.tab_key)
        self.bind('<Control-i>',lambda e:self.import_file())
    def tab_key(self,e=None):
        widget=self.focus_get()
        if widget and widget.winfo_class() in ('Text','Entry','TEntry','TCombobox','TSpinbox'): return
        if self.workspace=='design': self.toggle_dock(); return 'break'
    def pan_key(self,value):
        self.space_pan=value
        if self.workspace_ready: self.canvas.configure(cursor='fleur' if value else '')
    def toggle_dock(self):
        if not self.workspace_ready: return
        if self.dock_visible:
            self.saved_dock_width=self.main_pane.winfo_width()-self.main_pane.sashpos(1)
            self.main_pane.forget(self.right_dock); self.dock_visible=False
        else:
            self.main_pane.add(self.right_dock,weight=0); self.dock_visible=True
            self.after(70,self.restore_dock_width)
        self.after_idle(self.render)
    def restore_dock_width(self):
        if self.dock_visible:
            self.update_idletasks()
            self.main_pane.sashpos(0,66)
            self.main_pane.sashpos(1,max(400,self.main_pane.winfo_width()-getattr(self,'saved_dock_width',345)))
    def show_objects(self):
        if not self.workspace_ready: return
        if self.workspace!='design': self.switch_workspace('design')
        if not self.dock_visible: self.toggle_dock()
        self.notebook.select(self.objects_tab)
    def switch_workspace(self,key):
        super().switch_workspace(key)
        if key=='laser': return
        if not self.workspace_ready: return
        if key!='design' and not self.dock_visible: self.toggle_dock()
        self.context_bar.pack_forget()
        if key=='design':
            self.canvas_actions.pack_forget(); self.context_bar.pack(fill='x',before=self.canvas)
            self.update_inspector(); self.update_context(force=True)
        else:
            active=self.prepare_stage if key=='prepare' else self.material_stage if key=='materials' else self.canvas
            self.canvas_actions.pack_forget(); self.canvas_actions.pack(fill='x',before=active)
    def set_tool(self,tool):
        super().set_tool(tool)
        if self.workspace_ready:
            self.update_context(force=True); self.update_inspector(select=True); self.refresh_tool_icons()
    def refresh(self):
        super().refresh()
        if not self.workspace_ready: return
        if hasattr(self,'theme'): self.theme.style_widgets(self.palette)
        self.update_context(); self.update_inspector()
        s=self.current()
        if s and s.kind=='image':
            from steburn.core.processing import resolve
            process=resolve(s,next(l for l in self.p.layers if l.id==s.layer)); pixels=s.extra.get('pixels',[0,0]); mode=s.extra.get('image_adjustments',{}).get('mode','gray')
            self.image_info.set(f'{s.name}\n{s.w:.1f} × {s.h:.1f} mm · {pixels[0]} × {pixels[1]} px\n{mode} · Abstand {process.interval:g} mm\nMax. {process.power:g} % · {process.speed:g} mm/min')
    def inspector_kind(self):
        s=self.current()
        if self.tool=='nodes' or self.tool=='bezier': return 'path'
        if self.tool=='text' or s and s.kind=='text': return 'text'
        if s and s.kind=='image': return 'image'
        if self.tool=='rect' or s and s.kind=='rect': return 'rect'
        return 'selection'
    def update_inspector(self,select=False):
        if self.workspace!='design': return
        kind=self.inspector_kind()
        context=self.text_tab if kind=='text' else self.vector_tab if kind in ('path','rect') else self.image_tab if kind=='image' else None
        visible=[self.page_tabs['props']]+([context] if context else [])+[self.objects_tab,self.page_tabs['layers']]
        current=self.notebook.select()
        for tab in self.notebook.tabs():
            if tab not in [str(v) for v in visible]: self.notebook.hide(tab)
        for tab in visible: self.notebook.add(tab); self.notebook.insert('end',tab)
        if select and context: self.notebook.select(context)
        elif current not in [str(v) for v in visible]: self.notebook.select(visible[0])
    def update_context(self,force=False):
        kind=self.inspector_kind(); s=self.current(); key=(self.tool,kind,bool(s),s.id if s else None)
        if key==self.context_key and not force: return
        self.context_key=key
        for child in self.context_content.winfo_children(): child.destroy()
        frame=self.context_content
        label=dict((tool,name) for tool,icon,name in TOOLS).get(self.tool,'Auswahl')
        ttk.Label(frame,text=label,font=('Segoe UI',9,'bold')).pack(side='left',padx=(0,12))
        def button(text,fn):
            b=ttk.Button(frame,text=text,style='Compact.TButton',command=fn); b.pack(side='left',padx=2); return b
        def field(text,var,width=6):
            ttk.Label(frame,text=text).pack(side='left',padx=(6,2)); entry=ttk.Entry(frame,textvariable=var,width=width); entry.pack(side='left'); return entry
        if self.tool in ('select','nodes') and s and kind not in ('text','path'):
            for name,label in [('x','X'),('y','Y'),('w','B'),('h','H')]: field(label,self.vars[name],5)
            button('✓',self.apply)
        if kind=='image': button('Bild bearbeiten',self.adjust_image)
        elif kind=='text':
            field('Größe',self.text_size,5); button('Satz & Schrift',lambda:self.open_inspector(self.text_tab)); button('Übernehmen',self.apply_text)
        elif kind=='path':
            button('Knoten / Griffe',lambda:self.open_inspector(self.vector_tab)); button('Teilen',self.insert_node); button('Löschen',self.delete_node)
            ttk.Checkbutton(frame,text='Tangenten spiegeln',variable=self.smooth,command=self.set_smooth).pack(side='left',padx=6)
            if hasattr(self,'join_contours'):
                menu=tk.Menu(frame,tearoff=False)
                for label,c,t in [('Gerade',False,False),('Kurve',True,False),('Tangentiale Kurve',True,True)]: menu.add_command(label=label,command=lambda c=c,t=t:self.join_contours(c,t))
                menu.add_separator(); menu.add_command(label='Tangentialbedingung lösen',command=self.release_tangency)
                ttk.Menubutton(frame,text='Verbinden',menu=menu,style='Compact.TMenubutton').pack(side='left',padx=3)
        elif kind=='rect':
            field('Radius',self.draw_radius if self.tool=='rect' else self.radius,5)
            if self.tool!='rect': button('Runden',self.apply_radius)
        elif self.tool=='pencil': field('Vereinfachen mm',self.freehand_tolerance,5)
        elif self.tool=='select' and s and s.kind not in ('image','text'):
            field('Drehen °',self.rotation,5); button('Drehen',self.rotate_selection)
        if self.tool in ('rect','ellipse','line','bezier','pencil','polygon','text'):
            ttk.Checkbutton(frame,text='Feststellen',variable=self.pinned).pack(side='left',padx=5)
        if self.tool=='measure' and hasattr(self,'clear_measurements'): button('Alle Maße entfernen',self.clear_measurements)
        if self.tool in ('rect','ellipse','line','bezier','pencil','polygon','select','nodes','measure') and (not s or self.tool!='select'):
            ttk.Checkbutton(frame,text='Fangen',variable=self.snap_enabled).pack(side='left',padx=7)
            field('Raster mm',self.grid_step,4)
        ttk.Checkbutton(frame,text='Raster',variable=self.grid_visible,command=self.render).pack(side='left',padx=7)
    def open_inspector(self,tab):
        if not self.dock_visible: self.toggle_dock()
        self.notebook.select(tab)
    def coords(self,e):
        x,y=super().coords(e)
        if not self.workspace_ready or not self.snap_enabled.get() or getattr(e,'state',0)&8: return x,y
        try:
            step=float(self.grid_step.get().replace(',','.'))
            if not math.isfinite(step) or step<=0: return x,y
            sx,sy=round(x/step)*step,round(y/step)*step
            for guide in self.p.extensions.get('guides',[]):
                axis,value=guide
                if axis=='x' and abs(x-value)*self.scale<7: sx=value
                if axis=='y' and abs(y-value)*self.scale<7: sy=value
            return sx,sy
        except (ValueError,TypeError): return x,y
    def render(self):
        super().render()
        if not self.workspace_ready: return
        c=self.canvas; w,h=c.winfo_width(),c.winfo_height()
        c.delete('grid'); c.delete('grid-label')
        if self.grid_visible.get():
            try:
                step=float(self.grid_step.get().replace(',','.'))
                if not math.isfinite(step) or step<=0: raise ValueError()
                display_step=step*max(1,math.ceil(8/max(.0001,step*self.scale)))
                for i in range(1,math.ceil(self.p.width/display_step)):
                    x=i*display_step; c.create_line(*self.screen(x,0),*self.screen(x,self.p.height),fill='#edf1f6',tags='grid')
                for i in range(1,math.ceil(self.p.height/display_step)):
                    y=i*display_step; c.create_line(*self.screen(0,y),*self.screen(self.p.width,y),fill='#edf1f6',tags='grid')
                c.tag_raise('grid','workarea')
            except ValueError: pass
        s=self.current()
        if self.tool=='select' and s and len(self.selection)==1 and s.kind not in ('text','image') and not s.extra.get('locked') and not ('bezier' not in s.extra and len(shape_paths(s))==1 and len(shape_paths(s)[0])==2):
            x0,y0,x1,y1=bounds([s]); px,py=self.screen((x0+x1)/2,y1)
            c.create_line(px,py,px,py-22,fill='#0d9488')
            c.create_oval(px-5,py-27,px+5,py-17,fill='#d1fae5',outline='#0d9488',width=2,tags='rotate:'+s.id)
        for i,(axis,value) in enumerate(self.p.extensions.get('guides',[])):
            if axis=='x': x,_=self.screen(value,0); c.create_line(x,24,x,h,fill='#0d9488',dash=(5,4),tags=f'guide:{i}')
            else: _,y=self.screen(0,value); c.create_line(28,y,w,y,fill='#0d9488',dash=(5,4),tags=f'guide:{i}')
        c.create_rectangle(0,0,w,24,fill='#f4f6fa',outline='#ced7e3'); c.create_rectangle(0,0,28,h,fill='#f4f6fa',outline='#ced7e3')
        step=10 if self.scale>3 else 25 if self.scale>1.5 else 50
        lo=int((-self.ox/self.scale)//step)*step; hi=int((w-self.ox)/self.scale)+step
        for v in range(lo,hi,step):
            x,_=self.screen(v,0)
            if x>30: c.create_line(x,18,x,24,fill='#94a3b8'); c.create_text(x+3,9,text=str(v),anchor='w',font=('Segoe UI',8),fill='#64748b')
        miny=self.p.height-(h-self.oy)/self.scale; maxy=self.p.height+self.oy/self.scale
        for v in range(int(miny//step)*step,int(maxy)+step,step):
            _,y=self.screen(0,v)
            if y>28: c.create_line(22,y,28,y,fill='#94a3b8'); c.create_text(11,y,text=str(v),angle=90,font=('Segoe UI',8),fill='#64748b')
        c.create_text(14,12,text='mm',font=('Segoe UI',7),fill='#64748b')
        self.zoom_label.set(f'{self.scale/1.5*100:.0f} %')
        if hasattr(self,'theme'): self.theme.style_canvas(c)
    def press(self,e):
        if self.workspace_ready:
            self.canvas.focus_set()
            if self.space_pan:
                self.drag=('pan',e.x,e.y); return
            if self.tool=='pencil' and e.x>=28 and e.y>=24:
                self.drag=('pencil',[self.coords(e)]); return
            if e.y<24 or e.x<28:
                self.drag=('guide','y' if e.y<24 else 'x',None); return
            if self.tool=='select':
                for item in reversed(self.canvas.find_overlapping(e.x-4,e.y-4,e.x+4,e.y+4)):
                    for tag in self.canvas.gettags(item):
                        if tag.startswith('rotate:'):
                            s=next(s for s in self.p.shapes if s.id==tag.split(':')[1]); x0,y0,x1,y1=bounds([s]); center=((x0+x1)/2,(y0+y1)/2)
                            x,y=super().coords(e); start=math.atan2(y-center[1],x-center[0]); self.checkpoint(); self.drag=('rotate',deepcopy(s),center,start); return
                        if tag.startswith('guide:'):
                            index=int(tag.split(':')[1]); axis=self.p.extensions['guides'][index][0]; self.drag=('guide',axis,index); return
        super().press(e)
    def motion(self,e):
        if self.drag and self.drag[0]=='pencil':
            points=self.drag[1]; point=self.coords(e)
            if math.dist(point,points[-1])*self.scale>=2 and len(points)<12000: points.append(point)
            self.canvas.delete('pencil-ghost')
            if len(points)>1: self.canvas.create_line(*[v for pt in points for v in self.screen(*pt)],fill='#7c3aed',width=2,tags='pencil-ghost')
            return
        if self.drag and self.drag[0]=='rotate':
            _,original,center,start=self.drag; x,y=super().coords(e); angle=math.degrees(math.atan2(y-center[1],x-center[0])-start)
            if getattr(e,'state',0)&1: angle=round(angle/15)*15
            result=rotate_shape(original,angle,center)
            self.p.shapes=[result if s.id==result.id else s for s in self.p.shapes]; self.render(); self.status.set(f'Drehung {angle:.1f}° · Shift: 15°-Schritte'); return
        if self.drag and self.drag[0]=='pan':
            _,x,y=self.drag; self.ox+=e.x-x; self.oy+=e.y-y; self.drag=('pan',e.x,e.y); self.render(); return
        if self.drag and self.drag[0]=='guide':
            self.render(); self.canvas.create_line(28,e.y,self.canvas.winfo_width(),e.y,fill='#0d9488',width=2) if self.drag[1]=='y' else self.canvas.create_line(e.x,24,e.x,self.canvas.winfo_height(),fill='#0d9488',width=2); return
        super().motion(e)
    def release(self,e):
        if self.drag and self.drag[0]=='pencil':
            from steburn.core.model import Shape
            from shapely.geometry import LineString
            points=self.drag[1]; self.drag=None
            try:
                tolerance=float(self.freehand_tolerance.get().replace(',','.'))
                if not math.isfinite(tolerance) or not 0<=tolerance<=5: raise ValueError('Vereinfachung muss 0–5 mm betragen.')
                if len(points)<2: self.render(); return
                points=list(LineString(points).simplify(tolerance).coords)
                s=as_paths_shape(Shape('polyline',layer=self.active_layer,name='Freihand'),[points])
                from steburn.core.processing import resolve
                s.extra['processing']={'operation':'cut' if resolve(s,next(l for l in self.p.layers if l.id==s.layer)).operation=='cut' else 'mark'}
                p=deepcopy(self.p); p.shapes.append(s); self.selection={s.id}; self.selected=s.id; self.commit(p); self.one_shot()
            except ValueError as ex: self.status.set(str(ex)); self.render()
            return
        if self.drag and self.drag[0]=='rotate': self.drag=None; self.changed(); self.refresh(); return
        if self.drag and self.drag[0]=='pan': self.drag=None; return
        if self.drag and self.drag[0]=='guide':
            _,axis,index=self.drag; self.drag=None; x,y=super().coords(e); value=x if axis=='x' else y
            p=deepcopy(self.p); guides=p.extensions.setdefault('guides',[])
            valid=28<e.x<self.canvas.winfo_width() and 24<e.y<self.canvas.winfo_height()
            if index is not None:
                if valid: guides[index]=[axis,value]
                else: guides.pop(index)
            elif valid: guides.append([axis,value])
            self.commit(p); return
        if self.tool=='rect' and self.drag and self.drag[0]=='draw':
            from steburn.core.model import Shape
            try:
                radius=float(self.draw_radius.get().replace(',','.'))
                if not math.isfinite(radius) or radius<0: raise ValueError('Radius muss mindestens 0 mm sein.')
                _,a,b=self.drag; x,y=self.coords(e); self.drag=None
                if abs(x-a)+abs(y-b)<.5: self.render(); return
                s=Shape('rect',min(a,x),min(b,y),abs(x-a),abs(y-b),self.active_layer,'Rechteck')
                s.extra['corner_radius']=min(radius,s.w/2,s.h/2)
                p=deepcopy(self.p); p.shapes.append(s); self.selection={s.id}; self.selected=s.id
                self.commit(p); self.one_shot(); return
            except ValueError as ex: self.drag=None; self.status.set(str(ex)); self.render(); return
        super().release(e)
    def clear_guides(self):
        p=deepcopy(self.p); p.extensions['guides']=[]; self.commit(p)
    def rotate_selection(self):
        try:
            if not self.selection: raise ValueError('Bitte zuerst Vektorobjekte auswählen.')
            angle=float(self.rotation.get().replace(',','.')); p=deepcopy(self.p)
            p.shapes=[rotate_shape(s,angle) if s.id in self.selection and not s.extra.get('locked') else s for s in p.shapes]
            self.commit(p); self.rotation.set('0')
        except ValueError as ex: self.status.set(str(ex))
    def double_click(self,e):
        if self.tool=='polygon': return self.finish_polygon(e)
        for item in reversed(self.canvas.find_overlapping(e.x-4,e.y-4,e.x+4,e.y+4)):
            for tag in self.canvas.gettags(item):
                if tag.startswith('s:'):
                    self.selected=tag[2:]; self.selection={self.selected}; self.refresh(); s=self.current()
                    if s.kind=='image': self.adjust_image()
                    elif s.kind=='text': self.open_inspector(self.text_tab); self.text_content.focus_set()
                    return 'break'
    def open_image_studio(self,shape=None):
        from steburn.ui.image_studio import ImageStudio
        self.photo_window=ImageStudio(self,shape); return self.photo_window
    def adjust_image(self):
        images=[s for s in self.chosen() if s.kind=='image' and not s.extra.get('locked')]
        if not images: self.status.set('Bitte zuerst ein entsperrtes Bild auswählen oder importieren.'); return
        self.open_image_studio(images[0])
    def import_file(self):
        paths=filedialog.askopenfilenames(parent=self,title='Bilder und Vektoren importieren',filetypes=[('Bilder','*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.gif *.tga'),('Vektoren / PDF','*.svg *.dxf *.pdf *.ai *.plt *.hpgl'),('Alle unterstützten Formate',' '.join('*'+x for x in ALL_EXTENSIONS))])
        if paths: self.import_paths(paths)
    def import_vector_file(self):
        paths=filedialog.askopenfilenames(parent=self,title='Vektoren und PDF importieren',filetypes=[('Vektoren / PDF','*.svg *.dxf *.pdf *.ai *.plt *.hpgl'),('Alle unterstützten Formate',' '.join('*'+x for x in ALL_EXTENSIONS))])
        if paths: self.import_paths(paths)
    def import_paths(self,paths):
        from pathlib import Path
        p=deepcopy(self.p); shapes=[]; images=[]; messages=[]
        try:
            for path in paths:
                result=load_file(path,self.active_layer); messages.extend(result.warnings)
                for shape in result.shapes:
                    if shape.kind=='image': images.append(shape)
                    else: shapes.append(shape)
            if shapes:
                p.shapes.extend(shapes); self.selection={s.id for s in shapes}; self.selected=shapes[0].id; self.commit(p); self.switch_workspace('design')
            if images:
                window=self.open_image_studio()
                for i,shape in enumerate(images): window.add_shape(shape,select=i==0)
            self.status.set(f'{len(shapes)} Vektorobjekte · {len(images)} Bilder im Bildstudio'+(' · '+' · '.join(messages[:2]) if messages else ''))
        except Exception as ex: self.status.set('Import abgebrochen: '+str(ex))
