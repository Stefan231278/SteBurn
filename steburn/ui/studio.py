"""Task-oriented native workspace: design, prepare, materials and machine."""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from copy import deepcopy
import math
from steburn.ui.workbench import App as Workbench
from steburn.ui.widgets import ScrollPanel
from steburn.core.model import Shape
from steburn.core.paths import shape_paths,bounds,as_paths_shape
from steburn.core.design import set_bezier,split_cubic
from steburn.core.materials import MaterialLibrary,validate_preset,apply_preset
from steburn.core.planner import build_plan
from steburn.core.processing import resolve

class App(Workbench):
    def __init__(self):
        self.studio_ready=False; self.curve_clicks=[]; self.node_selection=None
        self.summary_timer=None; self.workspace='design'; self.material_items={}
        self.library=MaterialLibrary(Path(__file__).resolve().parents[2]/'user-data'/'materials.json')
        super().__init__()
    def build(self):
        super().build()
        self.title('SteBurn 0.6 · Studio')
        self.install_studio_style(); self.build_studio_header(); self.build_studio_tools()
        self.build_text_panel(); self.build_vector_panel(); self.build_material_panel(); self.build_preparation_panel()
        self.notebook.tab(self.page_tabs['props'],text='Maße & Position')
        self.notebook.tab(self.page_tabs['layers'],text='Ebenen')
        self.notebook.tab(self.processing_tab,text='Bearbeitung')
        self.notebook.tab(self.page_tabs['machine'],text='Verbindung')
        self.notebook.tab(self.page_tabs['materials'],text='Materialprofile')
        self.studio_ready=True
        self.notebook.bind('<<NotebookTabChanged>>',self.on_tab_changed,add='+')
        self.switch_workspace('design'); self.refresh()
        self.after(350,self.set_initial_columns)
    def set_initial_columns(self):
        self.main_pane.sashpos(0,220)
        self.main_pane.sashpos(1,max(450,self.main_pane.winfo_width()-390))
    def on_tab_changed(self,e=None):
        if not self.studio_ready: return
        selected=self.notebook.select()
        key='machine' if selected==str(self.page_tabs['machine']) else 'materials' if selected==str(self.page_tabs['materials']) else 'prepare' if selected in (str(self.processing_tab),str(self.prepare_tab)) else 'design' if selected in (str(self.page_tabs['props']),str(self.text_tab),str(self.vector_tab)) else self.workspace
        if key!=self.workspace:
            self.switch_workspace(key); self.notebook.select(selected)
    def fit(self):
        super().fit()
        self.ox=(self.canvas.winfo_width()-self.p.width*self.scale)/2
        self.oy=(self.canvas.winfo_height()-self.p.height*self.scale)/2
        self.render()
    def bind_shortcuts(self):
        super().bind_shortcuts()
        def editing():
            widget=self.focus_get()
            return bool(widget and widget.winfo_class() in ('Text','Entry','TEntry','TCombobox','TSpinbox','Spinbox'))
        for sequence,command in [('<Delete>',self.delete),('<Control-d>',self.duplicate),('<Control-z>',self.undo),('<Control-y>',self.redo),('<Control-a>',self.select_all)]:
            self.bind(sequence,lambda e,c=command:None if editing() else c())
        for sequence,tool in [('<Control-r>','rect'),('<Control-e>','ellipse'),('<Control-l>','line'),('<Control-t>','text')]:
            self.bind(sequence,lambda e,t=tool:None if editing() else self.set_tool(t))
    def delete(self):
        if self.tool=='nodes' and self.node_selection: self.delete_node()
        else: super().delete()
    def install_studio_style(self):
        style=ttk.Style(self)
        style.configure('.',font=('Segoe UI',9),background='#f3f5f9',foreground='#25334a')
        style.configure('TFrame',background='#f3f5f9'); style.configure('TLabel',background='#f3f5f9')
        style.configure('Studio.Dark.TFrame',background='#172338')
        style.configure('Studio.Dark.TLabel',background='#172338',foreground='#f1f5f9')
        style.configure('Studio.Card.TFrame',background='#ffffff')
        style.configure('Studio.Card.TLabel',background='#ffffff',foreground='#172338')
        style.configure('Studio.Muted.TLabel',foreground='#64748b')
        style.configure('TLabelframe',background='#f3f5f9',bordercolor='#d9e1ec')
        style.configure('TLabelframe.Label',background='#f3f5f9',foreground='#334155',font=('Segoe UI',9,'bold'))
        style.configure('Treeview',rowheight=25,font=('Segoe UI',9))
        style.configure('Treeview.Heading',font=('Segoe UI',9,'bold'))
        style.configure('TNotebook.Tab',padding=(9,7))
        for name in ('TButton','Selected.TButton','Accent.TButton','Danger.TButton'):
            style.configure(name,padding=(8,4),font=('Segoe UI',9))
        # The old 40px image surfaces forced every button to a tall minimum.
        for name in ('Compact.TButton','Nav.TButton','NavSelected.TButton'):
            style.layout(name,[('Button.border',{'sticky':'nswe','children':[('Button.padding',{'sticky':'nswe','children':[('Button.label',{'sticky':'nswe'})]})]})])
            style.configure(name,padding=(10,7),background='#ffffff',foreground='#334155',relief='flat',font=('Segoe UI',9))
        style.configure('Nav.TButton',background='#26354c',foreground='#dce6f4')
        style.configure('NavSelected.TButton',background='#dbeafe',foreground='#1d4ed8',font=('Segoe UI',9,'bold'))
        self.canvas.configure(bg='#e6ebf3')
    def build_studio_header(self):
        for child in self.header.winfo_children(): child.pack_forget()
        self.header.configure(style='Studio.Dark.TFrame',padding=(12,9))
        self.header_brand.configure(style='Studio.Dark.TLabel',text='SteBurn',font=('Segoe UI',17,'bold'))
        self.header_brand.pack(side='left',padx=(0,22))
        self.nav_buttons={}
        for key,label in [('design','01 Gestaltung'),('prepare','02 Vorbereitung'),('materials','03 Materialien'),('laser','04 Lasern'),('machine','05 Gerät')]:
            button=ttk.Button(self.header,text=label,style='Nav.TButton',command=lambda k=key:self.switch_workspace(k))
            button.pack(side='left',padx=3); self.nav_buttons[key]=button
        self.connection_dot.configure(bg='#172338'); self.connection_dot.pack(side='right',padx=8)
        self.connection_caption=ttk.Label(self.header,text='OFFLINE',style='Studio.Dark.TLabel'); self.connection_caption.pack(side='right')
        files=ttk.Frame(self.header,style='Studio.Dark.TFrame'); files.pack(side='right',padx=12)
        for label,fn in [('Öffnen',self.open),('Speichern',self.save),('Import',self.import_file)]:
            ttk.Button(files,text=label,style='Nav.TButton',command=fn).pack(side='left',padx=2)
        self.canvas_actions=ttk.Frame(self.canvas.master,padding=(8,6))
        self.canvas_actions.pack(fill='x',before=self.canvas)
        self.section_title=ttk.Label(self.canvas_actions,text='Gestaltung',font=('Segoe UI',11,'bold')); self.section_title.pack(side='left')
        self.stage_actions=ttk.Frame(self.canvas_actions); self.stage_actions.pack(side='right')
    def reflow_header(self):
        if not self.studio_ready: return
        # Workspace navigation stays fixed. File commands are also in the menu.
        self._toolbar_timer=None
    def build_studio_tools(self):
        left=self.tree.master
        for child in list(left.winfo_children()):
            if child!=self.tree: child.destroy()
        self.tree.pack_forget()
        title=ttk.Frame(left,padding=(8,10)); title.pack(fill='x')
        ttk.Label(title,text='WERKZEUGE',font=('Segoe UI',9,'bold')).pack(side='left')
        self.tool_buttons={}
        groups=[('Zeichnen',[('Auswahl','select'),('Rechteck','rect'),('Ellipse','ellipse'),('Linie','line'),('Bézier','bezier'),('Vieleck','polygon')]),('Bearbeiten',[('Knoten','nodes'),('Text','text'),('Messen','measure'),('Laserziel','position')])]
        for title,tools in groups:
            card=ttk.LabelFrame(left,text=title,padding=6); card.pack(fill='x',padx=8,pady=(0,8))
            for i,(label,tool) in enumerate(tools):
                b=ttk.Button(card,text=label,style='Compact.TButton',command=lambda t=tool:self.set_tool(t)); b.grid(row=i//2,column=i%2,sticky='ew',padx=2,pady=2)
                self.tool_buttons[tool]=b
            card.columnconfigure((0,1),weight=1)
        ttk.Checkbutton(left,text='Werkzeug feststellen',variable=self.pinned).pack(fill='x',padx=10,pady=3)
        edit=ttk.Frame(left); edit.pack(fill='x',padx=8,pady=5)
        for text,fn in [('Kopie',self.duplicate),('Löschen',self.delete),('↶',self.undo),('↷',self.redo)]:
            ttk.Button(edit,text=text,width=7 if text=='Löschen' else 5 if text=='Kopie' else 2,style='Compact.TButton',command=fn).pack(side='left',fill='x',expand=True,padx=1)
        ttk.Label(left,text='OBJEKTE & AUSWAHL',font=('Segoe UI',9,'bold'),padding=(10,8)).pack(fill='x')
        self.tree.pack(fill='both',expand=True,padx=8,pady=(0,8))
        left.configure(width=220)
    def card(self,parent,title):
        frame=ttk.LabelFrame(parent,text=title,padding=10); frame.pack(fill='x',padx=8,pady=(8,0)); return frame
    def field(self,parent,label,var,row):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky='w',padx=(0,10),pady=2)
        entry=ttk.Entry(parent,textvariable=var,width=14); entry.grid(row=row,column=1,sticky='ew',pady=2); parent.columnconfigure(1,weight=1); return entry
    def build_text_panel(self):
        self.text_tab=ScrollPanel(self.notebook); self.notebook.add(self.text_tab,text='Text & Schrift')
        parent=self.text_tab.content
        card=self.card(parent,'Textinhalt')
        self.text_content=tk.Text(card,height=4,wrap='word',font=('Segoe UI',11),relief='flat',bd=1,highlightthickness=1,highlightbackground='#cbd5e1',undo=True); self.text_content.pack(fill='x')
        self.text_content.bind('<Control-Return>',lambda e:(self.apply_text(),'break')[1])
        self.text_content.bind('<Control-a>',lambda e:(self.text_content.tag_add('sel','1.0','end-1c'),'break')[1])
        row=ttk.Frame(card); row.pack(fill='x',pady=(6,0))
        ttk.Button(row,text='Neuen Text erstellen',style='Compact.TButton',command=self.create_text).pack(side='left')
        ttk.Button(row,text='Text übernehmen',style='Compact.TButton',command=self.apply_text).pack(side='right')
        card=self.card(parent,'Schrift & Satz')
        self.fontbox=ttk.Combobox(card,state='normal',postcommand=self.post_fonts); self.fontbox.pack(fill='x',pady=3)
        self.fontbox.bind('<<ComboboxSelected>>',self.system_font_selected); self.fontbox.bind('<KeyRelease>',self.filter_fonts)
        self.text_size=tk.StringVar(value='12'); self.tracking=tk.StringVar(value='0'); self.line_spacing=tk.StringVar(value='1.3'); self.text_alignment=tk.StringVar(value='Links')
        fields=ttk.Frame(card); fields.pack(fill='x')
        for row,(label,var) in enumerate([('Schriftgröße (mm)',self.text_size),('Laufweite (mm)',self.tracking),('Zeilenabstand (Faktor)',self.line_spacing)]): self.field(fields,label,var,row)
        ttk.Combobox(card,textvariable=self.text_alignment,values=['Links','Zentriert','Rechts'],state='readonly').pack(fill='x',pady=4)
        ttk.Button(card,text='Schriftdatei wählen …',style='Compact.TButton',command=self.choose_font).pack(fill='x',pady=3)
        ttk.Button(card,text='Text in Pfade umwandeln',style='Compact.TButton',command=self.text_to_paths).pack(fill='x',pady=3)
        ttk.Label(parent,text='Schriftschnitt über die Systemschrift wählen. Text bleibt bis zur Pfadumwandlung editierbar.',wraplength=335,style='Studio.Muted.TLabel',padding=10).pack(fill='x')
        # Typography now has one dedicated home; preserve geometry variables.
        props=self.pages['props']
        for child in props.winfo_children():
            if isinstance(child,ttk.Frame) and child!=getattr(self,'unused',None):
                if any(isinstance(w,ttk.Combobox) for w in child.winfo_children()): child.grid_remove()
            if isinstance(child,ttk.Label) and str(child.cget('text'))=='Text': child.grid_remove()
            if isinstance(child,ttk.Entry) and str(child.cget('textvariable'))==str(self.vars['text']): child.grid_remove()
    def build_vector_panel(self):
        self.vector_tab=ScrollPanel(self.notebook); self.notebook.add(self.vector_tab,text='Pfade & Radien')
        parent=self.vector_tab.content
        card=self.card(parent,'Ecken & Konturen')
        self.radius=tk.StringVar(value='0'); fields=ttk.Frame(card); fields.pack(fill='x'); self.field(fields,'Rechteckradius (mm)',self.radius,0)
        ttk.Button(card,text='Radius auf Auswahl anwenden',style='Compact.TButton',command=self.apply_radius).pack(fill='x',pady=4)
        row=ttk.Frame(card); row.pack(fill='x')
        for label,fn in [('In Pfad umwandeln',self.convert_paths),('Bézier zeichnen',lambda:self.set_tool('bezier'))]: ttk.Button(row,text=label,style='Compact.TButton',command=fn).pack(side='left',fill='x',expand=True,padx=1)
        card=self.card(parent,'Knoten & Tangenten')
        self.node_tree=ttk.Treeview(card,columns=('role','x','y'),show='headings',height=4,selectmode='browse')
        for key,title,width in [('role','Punkt',105),('x','X / mm',85),('y','Y / mm',85)]: self.node_tree.heading(key,text=title); self.node_tree.column(key,width=width,stretch=True)
        self.node_tree.pack(fill='x'); self.node_tree.bind('<<TreeviewSelect>>',self.select_node_row)
        fields=ttk.Frame(card); fields.pack(fill='x'); self.node_x=tk.StringVar(); self.node_y=tk.StringVar()
        self.field(fields,'X (mm)',self.node_x,0); self.field(fields,'Y (mm)',self.node_y,1)
        ttk.Button(card,text='Knotenposition übernehmen',style='Compact.TButton',command=self.apply_node).pack(fill='x',pady=3)
        row=ttk.Frame(card); row.pack(fill='x')
        for label,fn in [('Teilen / Einfügen',self.insert_node),('Knoten löschen',self.delete_node)]: ttk.Button(row,text=label,style='Compact.TButton',command=fn).pack(side='left',fill='x',expand=True,padx=1)
        self.smooth=tk.BooleanVar(value=False)
        ttk.Checkbutton(card,text='Bézier-Tangenten spiegeln',variable=self.smooth,command=self.set_smooth).pack(anchor='w',pady=4)
        ttk.Label(parent,text='Bézier: Start, zwei Kontrollpunkte und Ende anklicken. Im Knotenmodus Anker und Griffe direkt ziehen; Anker bewegen ihre angrenzenden Griffe mit.',wraplength=335,style='Studio.Muted.TLabel',padding=10).pack(fill='x')
    def build_preparation_panel(self):
        self.prepare_tab=ScrollPanel(self.notebook); self.notebook.add(self.prepare_tab,text='Auftragsübersicht')
        parent=self.prepare_tab.content
        card=self.card(parent,'1 · Auftrag prüfen')
        self.plan_summary=tk.StringVar(value='Noch kein Auftrag')
        ttk.Label(card,textvariable=self.plan_summary,wraplength=315,justify='left').pack(fill='x')
        self.layer_summary=ttk.Treeview(card,columns=('name','speed','power'),show='headings',height=4)
        for key,label,width in [('name','Ausgabeebene',125),('speed','mm/min',80),('power','%',55)]: self.layer_summary.heading(key,text=label); self.layer_summary.column(key,width=width)
        self.layer_summary.pack(fill='x',pady=8)
        row=ttk.Frame(card); row.pack(fill='x')
        for label,step in [('Ebene ↑',-1),('Ebene ↓',1)]: ttk.Button(row,text=label,style='Compact.TButton',command=lambda s=step:self.reorder_preparation(s)).pack(side='left',padx=2)
        ttk.Button(card,text='Prüfung aktualisieren',style='Compact.TButton',command=self.update_summary).pack(fill='x')
        card=self.card(parent,'Hinweise zur Ausgabe')
        ttk.Label(card,text='Objektwerte haben Vorrang vor Ebenenwerten.\n\nLeistung, Vorschub und Durchgänge im Register Bearbeitung einstellen. Zeitwerte sind geometrische Schätzungen.\n\nDie Bahnsimulation bewegt keine Maschine. Die Rahmenfahrt bewegt die Achsen ohne Strahl.',wraplength=315).pack(fill='x')
        self.prepare_stage=ttk.Frame(self.canvas.master,padding=(10,0,10,10))
        bar=ttk.Frame(self.prepare_stage); bar.pack(fill='x',pady=(0,8))
        for label,fn in [('Simulation',self.simulate),('Nur Auswahl',self.simulate_selection),('Rahmen fahren',self.frame),('Stopp',self.stop_frame)]:
            ttk.Button(bar,text=label,style='Compact.TButton',command=fn).pack(side='left',padx=2)
        card=ttk.LabelFrame(self.prepare_stage,text='Werkzeugwege · Rot: Bearbeitung · Blau: Leerfahrt',padding=8); card.pack(fill='both',expand=True)
        self.preparation_canvas=tk.Canvas(card,bg='#e6ebf3',highlightthickness=0); self.preparation_canvas.pack(fill='both',expand=True)
        self.preparation_canvas.bind('<Configure>',lambda e:self.draw_preparation())
        footer=ttk.Frame(self.prepare_stage); footer.pack(fill='x',pady=(8,0))
        ttk.Label(footer,text='Prüfen → simulieren → ausrichten → Auftrag starten',style='Studio.Muted.TLabel').pack(side='left')
        ttk.Button(footer,text='Weiter zum Job-Cockpit',style='Accent.TButton',command=self.open_job).pack(side='right')
    def switch_workspace(self,key):
        if not self.studio_ready: return
        if key=='laser':
            self.open_job()
            for name,b in self.nav_buttons.items(): b.configure(style='NavSelected.TButton' if name=='laser' else 'Nav.TButton')
            return
        self.workspace=key
        groups={'design':[self.page_tabs['props'],self.text_tab,self.vector_tab,self.page_tabs['layers']],
                'prepare':[self.prepare_tab,self.processing_tab,self.page_tabs['layers']],
                'materials':[self.page_tabs['materials']], 'machine':[self.page_tabs['machine']]}
        for tab in self.notebook.tabs(): self.notebook.hide(tab)
        for tab in groups[key]: self.notebook.add(tab); self.notebook.insert('end',tab)
        self.notebook.select(groups[key][0])
        self.canvas.pack_forget(); self.prepare_stage.pack_forget(); self.material_stage.pack_forget()
        active=self.material_stage if key=='materials' else self.prepare_stage if key=='prepare' else self.canvas
        active.pack(fill='both',expand=True)
        for name,b in self.nav_buttons.items(): b.configure(style='NavSelected.TButton' if name==key else 'Nav.TButton')
        labels={'design':'Gestaltung · Formen, Text & Pfade','prepare':'Vorbereitung · Prüfen, simulieren & ausrichten','materials':'Materialien · Eigene erprobte Profile','machine':'Gerät · Verbindung, Referenzierung & Diagnose'}
        self.section_title.configure(text=labels[key])
        for child in self.stage_actions.winfo_children(): child.destroy()
        actions={'design':[('Einpassen',self.fit),('Gruppieren',self.group)],'prepare':[('Simulation',self.simulate),('Cockpit',self.open_job)],'materials':[('Neues Profil',self.new_material)],'machine':[('Verbinden + Referenzfahrt',self.connect_device)]}
        for label,fn in actions[key]: ttk.Button(self.stage_actions,text=label,style='Compact.TButton',command=fn).pack(side='left',padx=3)
        if key=='prepare': self.update_summary()
    def set_tool(self,tool):
        if tool!='bezier': self.curve_clicks=[]
        super().set_tool(tool)
        if self.studio_ready:
            self.switch_workspace('design')
            if tool=='text': self.notebook.select(self.text_tab)
            if tool in ('nodes','bezier'): self.notebook.select(self.vector_tab)
            for key,b in self.tool_buttons.items(): b.configure(style='NavSelected.TButton' if key==tool else 'Compact.TButton')
    def refresh(self):
        super().refresh()
        if not self.studio_ready: return
        s=self.current()
        if s and s.kind=='text':
            self.text_content.delete('1.0','end'); self.text_content.insert('1.0',s.text)
            self.text_size.set(f'{s.h:g}'); self.tracking.set(str(s.extra.get('tracking',0))); self.line_spacing.set(str(s.extra.get('line_spacing',1.3)))
            self.text_alignment.set({'left':'Links','center':'Zentriert','right':'Rechts'}[s.extra.get('text_align','left')])
        self.radius.set(str(s.extra.get('corner_radius',0)) if s else '0')
        self.smooth.set(bool(s and s.extra.get('curve_smooth')))
        self.refresh_nodes(); self.refresh_materials()
        if self.summary_timer: self.after_cancel(self.summary_timer); self.summary_timer=None
        if self.workspace=='prepare': self.summary_timer=self.after(300,self.update_summary)
    def poll(self):
        super().poll()
        if self.studio_ready:
            self.connection_caption.configure(text='VERBUNDEN' if self.device.connected and self.device.link_ok else 'OFFLINE')
    def update_summary(self):
        self.summary_timer=None
        if not hasattr(self,'plan_summary'): return
        self.layer_summary.delete(*self.layer_summary.get_children())
        for i,layer in enumerate(self.p.layers):
            self.layer_summary.insert('','end',iid=layer.id,values=(f'{i+1:02} · {layer.name}'+(' [aus]' if not layer.output else ''),f'{layer.speed:g}',f'{layer.power:g}'))
        try:
            plan=build_plan(self.p)
            n=sum(1 for s in plan.segments if s.power>0)
            warnings='\n'.join(plan.warnings[:3])
            overrides=sum('processing' in s.extra for s in self.p.shapes)
            self.plan_summary.set(f'{len(self.p.shapes)} Objekte · {len(plan.segments):,} Segmente\n{n:,} Bearbeitungssegmente · ca. {plan.duration/60:.1f} min\n'+('Exakter Plan' if plan.exact else 'Vereinfachte Vorschau; exakter Startplan wird separat geprüft')+f'\n{overrides} Objekte mit eigenen Bearbeitungswerten'+ ('\n'+warnings if warnings else ''))
            self.preparation_plan=plan
            self.draw_preparation()
        except Exception as ex:
            self.preparation_plan=None; self.draw_preparation()
            self.plan_summary.set('Plan noch nicht ausführbar: '+str(ex))
    def draw_preparation(self):
        if not hasattr(self,'preparation_canvas'): return
        c=self.preparation_canvas; c.delete('all')
        z=max(.01,min((c.winfo_width()-50)/self.p.width,(c.winfo_height()-45)/self.p.height))
        xy=lambda pt:((c.winfo_width()-self.p.width*z)/2+pt[0]*z,20+(self.p.height-pt[1])*z)
        c.create_rectangle(*xy((0,self.p.height)),*xy((self.p.width,0)),fill='white',outline='#cbd5e1')
        plan=getattr(self,'preparation_plan',None)
        if not plan:
            if hasattr(self,'theme'): self.theme.style_canvas(c)
            return
        stride=max(1,len(plan.segments)//7000)
        for s in plan.segments[::stride]: c.create_line(*xy(s.start),*xy(s.end),fill='#f08b7e' if s.power else '#94b3da',dash=() if s.power else (3,3))
        if stride>1: c.create_text(30,25,anchor='nw',text='Hintergrunddarstellung reduziert',fill='#64748b')
        if hasattr(self,'theme'): self.theme.style_canvas(c)
    def open_job(self):
        if self.job_window and self.job_window.winfo_exists(): self.job_window.lift(); return
        from steburn.ui.cockpit import Cockpit
        self.job_window=Cockpit(self)
    def create_text(self):
        text=self.text_content.get('1.0','end-1c').strip() or 'Neuer Text'
        try:
            p=deepcopy(self.p); s=Shape('text',30,30,80,12,self.active_layer,'Text',text); p.shapes.append(s)
            self.selection={s.id}; self.selected=s.id; self.commit(p)
            self.switch_workspace('design'); self.notebook.select(self.text_tab)
        except Exception as ex: self.status.set(str(ex))
    def apply_text(self):
        s=self.current()
        if not s or s.kind!='text' or s.extra.get('locked'): self.status.set('Bitte einen entsperrten Text auswählen.'); return
        try:
            p=deepcopy(self.p); t=next(v for v in p.shapes if v.id==s.id)
            t.text=self.text_content.get('1.0','end-1c'); t.h=float(self.text_size.get().replace(',','.'))
            if not t.text.strip(): raise ValueError('Text darf nicht leer sein.')
            t.extra.update(tracking=float(self.tracking.get().replace(',','.')),line_spacing=float(self.line_spacing.get().replace(',','.')),text_align={'Links':'left','Zentriert':'center','Rechts':'right'}[self.text_alignment.get()])
            p.validate(); a,b,c,d=bounds([t]); t.w=c-a; self.commit(p); self.status.set('Text und Satz übernommen')
        except Exception as ex: self.status.set(str(ex))
    def apply_radius(self):
        try:
            radius=float(self.radius.get().replace(',','.'))
            if not math.isfinite(radius) or radius<0: raise ValueError('Radius muss mindestens 0 mm sein.')
            p=deepcopy(self.p); changed=0
            for s in p.shapes:
                if s.id in self.selection and s.kind=='rect' and not s.extra.get('locked'):
                    s.extra['corner_radius']=min(radius,s.w/2,s.h/2); changed+=1
            if not changed: raise ValueError('Bitte ein entsperrtes Rechteck auswählen.')
            self.commit(p); self.status.set(f'Radius auf {changed} Rechtecke angewendet')
        except Exception as ex: self.status.set(str(ex))
    def convert_paths(self):
        try:
            p=deepcopy(self.p)
            for s in p.shapes:
                if s.id in self.selection and not s.extra.get('locked') and s.kind!='image': as_paths_shape(s,shape_paths(s))
            self.commit(p); self.set_tool('nodes')
        except Exception as ex: self.status.set(str(ex))
    def render(self):
        super().render()
        if not hasattr(self,'canvas'): return
        if self.curve_clicks:
            if len(self.curve_clicks)>1: self.canvas.create_line(*[v for pt in self.curve_clicks for v in self.screen(*pt)],fill='#7c3aed',dash=(3,3),tags='curve-preview')
            for pt in self.curve_clicks:
                x,y=self.screen(*pt); self.canvas.create_oval(x-4,y-4,x+4,y+4,fill='#7c3aed',outline='white',tags='curve-preview')
        if self.tool!='nodes': return
        for s in self.chosen():
            if 'bezier' not in s.extra: continue
            for item in self.canvas.find_all():
                if any(t.startswith('node:'+s.id+':') for t in self.canvas.gettags(item)): self.canvas.delete(item)
            nodes=[(s.x+x,s.y+y) for x,y in s.extra['bezier']]
            for i in range(0,len(nodes)-1,3):
                for a,b in [(nodes[i],nodes[i+1]),(nodes[i+2],nodes[i+3])]: self.canvas.create_line(*self.screen(*a),*self.screen(*b),fill='#a78bfa',dash=(3,3))
            for i,pt in enumerate(nodes):
                x,y=self.screen(*pt); r=5 if i%3==0 else 4; tag=f'curve:{s.id}:{i}'
                color='#f59e0b' if self.node_selection==(s.id,0,i) else '#7c3aed' if i%3==0 else '#ffffff'
                self.canvas.create_oval(x-r,y-r,x+r,y+r,fill=color,outline='#7c3aed',width=2,tags=tag)
    def press(self,e):
        if self.tool=='bezier':
            self.curve_clicks.append(self.coords(e))
            if len(self.curve_clicks)==4:
                p=deepcopy(self.p); s=set_bezier(Shape('polyline',layer=self.active_layer,name='Bézierkurve'),self.curve_clicks)
                s.extra['processing']={'operation':'cut' if resolve(s,next(l for l in p.layers if l.id==s.layer)).operation=='cut' else 'mark'}; p.shapes.append(s); self.curve_clicks=[]; self.selection={s.id}; self.selected=s.id; self.commit(p); self.set_tool('nodes')
            else: self.render(); self.status.set(f'Bézier · Punkt {len(self.curve_clicks)}/4 gesetzt · Esc bricht ab')
            return
        if self.tool=='text':
            x,y=self.coords(e); p=deepcopy(self.p); s=Shape('text',x,y,80,12,self.active_layer,'Text','Neuer Text'); p.shapes.append(s)
            self.selection={s.id}; self.selected=s.id; self.commit(p); self.one_shot(); self.notebook.select(self.text_tab); return
        if self.tool=='nodes':
            for item in reversed(self.canvas.find_overlapping(e.x-7,e.y-7,e.x+7,e.y+7)):
                for tag in self.canvas.gettags(item):
                    if tag.startswith('curve:'):
                        _,sid,index=tag.split(':'); s=next(s for s in self.p.shapes if s.id==sid)
                        if s.extra.get('locked'): return
                        self.selected=sid; self.node_selection=(sid,0,int(index)); self.checkpoint()
                        self.drag=('curve',sid,int(index),[(s.x+x,s.y+y) for x,y in s.extra['bezier']]); self.refresh_nodes(); return
                    if tag.startswith('node:'):
                        _,sid,contour,index=tag.split(':'); self.selected=sid; self.node_selection=(sid,int(contour),int(index)); self.refresh_nodes()
        super().press(e)
    def motion(self,e):
        if self.drag and self.drag[0]=='curve':
            _,sid,index,original=self.drag; s=next(s for s in self.p.shapes if s.id==sid)
            self.move_curve_node(s,original,index,self.coords(e)); self.render(); return
        super().motion(e)
    def move_curve_node(self,s,nodes,index,target):
        nodes=deepcopy(nodes); dx,dy=target[0]-nodes[index][0],target[1]-nodes[index][1]; nodes[index]=list(target)
        if index%3==0:
            for adjacent in (index-1,index+1):
                if 0<=adjacent<len(nodes): nodes[adjacent]=[nodes[adjacent][0]+dx,nodes[adjacent][1]+dy]
        elif s.extra.get('curve_smooth'):
            anchor=index-1 if index%3==1 else index+1; opposite=2*anchor-index
            if 0<=opposite<len(nodes): nodes[opposite]=[2*nodes[anchor][0]-target[0],2*nodes[anchor][1]-target[1]]
        set_bezier(s,nodes)
    def release(self,e):
        if self.drag and self.drag[0]=='curve': self.drag=None; self.changed(); self.refresh(); return
        super().release(e)
    def escape(self,e=None):
        self.curve_clicks=[]; return super().escape(e)
    def refresh_nodes(self):
        if not hasattr(self,'node_tree'): return
        self.node_tree.delete(*self.node_tree.get_children()); s=self.current()
        if not s or s.kind not in ('polyline','polygon'): return
        paths=[s.extra['bezier']] if 'bezier' in s.extra else s.extra.get('contours',[s.points])
        for contour,path in enumerate(paths):
            # Sampled paths can be dense; the canvas remains fully editable.
            for i,(x,y) in enumerate(path[:500]):
                role=f'Anker {i//3+1}' if 'bezier' in s.extra and i%3==0 else f'Griff {i}' if 'bezier' in s.extra else f'Knoten {contour+1}.{i+1}'
                iid=f'{contour}:{i}'; self.node_tree.insert('','end',iid=iid,values=(role,f'{s.x+x:.3f}',f'{s.y+y:.3f}'))
                if self.node_selection==(s.id,contour,i): self.node_tree.selection_set(iid); self.node_x.set(f'{s.x+x:.4f}'); self.node_y.set(f'{s.y+y:.4f}')
    def select_node_row(self,e=None):
        items=self.node_tree.selection(); s=self.current()
        if items and s:
            contour,index=map(int,items[0].split(':')); self.node_selection=(s.id,contour,index)
            points=[s.extra['bezier']] if 'bezier' in s.extra else s.extra.get('contours',[s.points])
            if contour>=len(points) or index>=len(points[contour]): return
            x,y=points[contour][index]; self.node_x.set(f'{s.x+x:.6f}'); self.node_y.set(f'{s.y+y:.6f}'); self.render()
    def node_edit(self,callback):
        s=self.current()
        if not s or not self.node_selection or self.node_selection[0]!=s.id or s.extra.get('locked'):
            self.status.set('Bitte im Knotenmodus einen entsperrten Knoten auswählen.'); return
        try:
            p=deepcopy(self.p); target=next(v for v in p.shapes if v.id==s.id); callback(target,*self.node_selection[1:]); self.commit(p)
        except Exception as ex: self.status.set(str(ex))
    def apply_node(self):
        def change(s,contour,index):
            target=(float(self.node_x.get().replace(',','.')),float(self.node_y.get().replace(',','.')))
            if not all(math.isfinite(v) for v in target): raise ValueError('Ungültige Position')
            if 'bezier' in s.extra: self.move_curve_node(s,[(s.x+x,s.y+y) for x,y in s.extra['bezier']],index,target)
            else:
                paths=shape_paths(s); closed=paths[contour][0]==paths[contour][-1]; paths[contour][index]=target
                if closed and index in (0,len(paths[contour])-1): paths[contour][0]=paths[contour][-1]=target
                as_paths_shape(s,paths)
        self.node_edit(change)
    def insert_node(self):
        def change(s,contour,index):
            if 'bezier' in s.extra:
                nodes=[(s.x+x,s.y+y) for x,y in s.extra['bezier']]; segment=min(index//3,(len(nodes)-4)//3); set_bezier(s,split_cubic(nodes,segment))
            else:
                paths=shape_paths(s); path=paths[contour]; i=min(index,len(path)-2); path.insert(i+1,tuple((a+b)/2 for a,b in zip(path[i],path[i+1]))); as_paths_shape(s,paths)
        self.node_edit(change)
    def delete_node(self):
        def change(s,contour,index):
            if 'bezier' in s.extra:
                nodes=[(s.x+x,s.y+y) for x,y in s.extra['bezier']]
                if index%3 or index==0 or index==len(nodes)-1: raise ValueError('Nur innere Bézier-Anker können gelöscht werden.')
                del nodes[index-1:index+2]; set_bezier(s,nodes)
            else:
                paths=shape_paths(s); path=paths[contour]; closed=path[0]==path[-1]
                if len(path)<=(4 if closed else 2): raise ValueError('Pfad benötigt mehr Knoten.')
                if closed:
                    path.pop(); del path[index%len(path)]; path.append(path[0])
                else: del path[index]
                as_paths_shape(s,paths)
            self.node_selection=None
        self.node_edit(change)
    def set_smooth(self):
        s=self.current()
        if not s or 'bezier' not in s.extra or s.extra.get('locked'): return
        p=deepcopy(self.p); next(v for v in p.shapes if v.id==s.id).extra['curve_smooth']=self.smooth.get(); self.commit(p)
    def reorder_preparation(self,step):
        if self.busy: self.status.set('Reihenfolge erst nach Ende des Geräteauftrags ändern.'); return
        from steburn.core.order import move_layer
        rows=self.layer_summary.selection(); lid=rows[0] if rows else self.active_layer
        self.commit(move_layer(self.p,lid,step)); self.layer_summary.selection_set(lid)
        self.status.set('Ebenenfolge aktualisiert · Simulation und nächste Aufträge verwenden diese Reihenfolge.')
    def build_material_panel(self):
        parent=self.pages['materials']
        for child in parent.winfo_children(): child.destroy()
        self.material_stage=ttk.Frame(self.canvas.master,padding=(10,0,10,10))
        self.material_stage.columnconfigure(0,weight=1); self.material_stage.columnconfigure(1,weight=2); self.material_stage.rowconfigure(0,weight=1)
        card=ttk.LabelFrame(self.material_stage,text='Materialbibliothek',padding=10); card.grid(row=0,column=0,sticky='nsew',padx=(0,10))
        self.materialbox=ttk.Combobox(card,state='readonly'); self.materialbox.pack(fill='x'); self.materialbox.bind('<<ComboboxSelected>>',self.load_material)
        self.material_list=ttk.Treeview(card,columns=('material','thickness'),show='tree headings',height=7,selectmode='browse')
        self.material_list.heading('#0',text='Profil'); self.material_list.column('#0',width=100,minwidth=70)
        self.material_list.heading('material',text='Material'); self.material_list.column('material',width=70,minwidth=50)
        self.material_list.heading('thickness',text='mm'); self.material_list.column('thickness',width=40,minwidth=30)
        self.material_list.pack(fill='both',expand=True,pady=8); self.material_list.bind('<<TreeviewSelect>>',self.select_material_row)
        row=ttk.Frame(card); row.pack(fill='x',pady=5)
        for label,fn in [('Neu',self.new_material),('Entfernen',self.remove_material)]: ttk.Button(row,text=label,style='Compact.TButton',command=fn).pack(side='left',fill='x',expand=True,padx=1)
        ttk.Label(card,text='Eigene erprobte Werte speichern und in weiteren Projekten wiederverwenden.',wraplength=220,style='Studio.Muted.TLabel').pack(fill='x',pady=8)
        card=ttk.LabelFrame(self.material_stage,text='Profil bearbeiten',padding=12); card.grid(row=0,column=1,sticky='nsew'); self.material_vars={}
        specs=[('name','Profilname',''),('material','Material',''),('thickness','Stärke (mm)','0'),('speed','Vorschub (mm/min)','1200'),('power','Leistung (%)','0'),('passes','Durchgänge','1'),('interval','Linienabstand (mm)','0.2')]
        for i,(key,label,value) in enumerate(specs): var=tk.StringVar(value=value); self.material_vars[key]=var; self.field(card,label,var,i)
        self.material_op=tk.StringVar(value='Schneiden'); self.material_air=tk.BooleanVar(value=False)
        ttk.Combobox(card,textvariable=self.material_op,values=['Schneiden','Gravieren','Markieren'],state='readonly').grid(row=7,column=0,columnspan=2,sticky='ew',pady=4)
        ttk.Checkbutton(card,text='Air Assist als Profilparameter',variable=self.material_air).grid(row=8,column=0,columnspan=2,sticky='w')
        ttk.Label(card,text='Neue Profile starten mit 0 % Leistung. Material und Stärke sind Angaben zur Wiedererkennung; sie bestimmen keine automatischen Leistungswerte.',wraplength=280,style='Studio.Muted.TLabel').grid(row=9,column=0,columnspan=2,sticky='ew',pady=12)
        ttk.Button(card,text='Profil speichern',style='Accent.TButton',command=self.save_material).grid(row=10,column=0,columnspan=2,sticky='ew',pady=4)
        card=self.card(parent,'Im Projekt verwenden')
        self.material_target=tk.StringVar(); ttk.Label(card,textvariable=self.material_target,wraplength=315,font=('Segoe UI',10,'bold')).pack(fill='x',pady=(0,10))
        self.material_scope=tk.StringVar(value='layer')
        row=ttk.Frame(card); row.pack(fill='x')
        ttk.Radiobutton(row,text='Aktive Ebene',variable=self.material_scope,value='layer').pack(side='left'); ttk.Radiobutton(row,text='Objektauswahl',variable=self.material_scope,value='selection').pack(side='left',padx=8)
        ttk.Button(card,text='Profil anwenden',style='Accent.TButton',command=self.apply_material).pack(fill='x',pady=5)
        ttk.Label(card,text='Eigene Objektwerte haben Vorrang vor Ebenenwerten.\n\nAktive Ebene unten über ihren Farbreiter wählen.\n\nVerwendete Profile werden im Projekt mitgespeichert. Air Assist wird als Parameter gespeichert.',wraplength=325,style='Studio.Muted.TLabel').pack(fill='x',pady=8)
    def refresh_materials(self):
        try: values=self.library.read()
        except (ValueError,OSError) as ex: values={}; self.status.set('Materialbibliothek: '+str(ex))
        values.update(self.p.extensions.get('materials',{})); self.material_items=values
        self.materialbox['values']=list(values)
        self.material_list.delete(*self.material_list.get_children())
        for i,(name,preset) in enumerate(values.items()): self.material_list.insert('','end',iid=str(i),text=name,values=(preset.get('material',''),preset.get('thickness','')))
        layer=next(l for l in self.p.layers if l.id==self.active_layer)
        assigned=self.p.extensions.get('material_assignments',{}).get(layer.id,'Noch kein Materialprofil zugewiesen')
        self.material_target.set('Aktive Ebene: '+layer.name+'\n'+assigned)
    def select_material_row(self,e=None):
        rows=self.material_list.selection()
        if rows:
            self.materialbox.set(self.material_list.item(rows[0],'text')); self.load_material()
    def new_material(self):
        self.materialbox.set('')
        for key,value in dict(name='',material='',thickness='0',speed='1200',power='0',passes='1',interval='0.2').items(): self.material_vars[key].set(value)
        self.material_op.set('Schneiden'); self.material_air.set(False)
    def load_material(self,e=None):
        preset=self.material_items.get(self.materialbox.get())
        if not preset: return
        defaults=dict(name=self.materialbox.get(),material='',thickness=0,speed=1200,power=0,passes=1,interval=.2)
        for key,var in self.material_vars.items(): var.set(str(preset.get(key,defaults[key])))
        self.material_op.set({'cut':'Schneiden','engrave':'Gravieren','mark':'Markieren'}.get(preset.get('operation','engrave' if preset.get('mode')=='Fläche' else 'cut'),'Schneiden'))
        self.material_air.set(bool(preset.get('air')))
    def material_form(self):
        values={key:var.get().strip() for key,var in self.material_vars.items()}
        for key in ('thickness','speed','power','interval'): values[key]=float(values[key].replace(',','.'))
        values['passes']=int(values['passes']); values['air']=self.material_air.get(); values['operation']={'Schneiden':'cut','Gravieren':'engrave','Markieren':'mark'}[self.material_op.get()]
        values['mode']='Fläche' if values['operation']=='engrave' else 'Kontur'
        return validate_preset(values)
    def save_material(self):
        try:
            preset=self.material_form(); values=self.library.read(); values[preset['name']]=preset; self.library.write(values)
            p=deepcopy(self.p); p.extensions.setdefault('materials',{})[preset['name']]=preset; self.commit(p); self.materialbox.set(preset['name']); self.status.set('Materialprofil gespeichert')
        except Exception as ex: self.status.set(str(ex))
    def remove_material(self):
        name=self.materialbox.get()
        if not name: return
        try:
            values=self.library.read(); values.pop(name,None); self.library.write(values)
            p=deepcopy(self.p); p.extensions.get('materials',{}).pop(name,None); self.commit(p); self.new_material(); self.status.set('Profil entfernt; angewendete Bearbeitungswerte bleiben erhalten')
        except Exception as ex: self.status.set(str(ex))
    def apply_material(self):
        try:
            preset=self.material_form(); ids=set(self.selection) if self.material_scope.get()=='selection' else None
            if self.material_scope.get()=='selection' and not ids: raise ValueError('Bitte zuerst Objekte auswählen.')
            self.commit(apply_preset(self.p,preset,self.active_layer,ids)); self.materialbox.set(preset['name']); self.status.set('Materialprofil auf '+('Auswahl' if ids else 'aktive Ebene')+' angewendet')
        except Exception as ex: self.status.set(str(ex))
