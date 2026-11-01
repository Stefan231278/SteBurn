"""Photo import queue and reversible, pixel-aligned laser image preparation."""
import tkinter as tk
from tkinter import ttk,filedialog
from pathlib import Path
from dataclasses import asdict
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import queue,math
from PIL import Image,ImageTk
from steburn.ui.widgets import ScrollPanel
from steburn.core.photos import PhotoSettings,settings_from,decode_image,render_photo,cropped_size,raster_size,recommended_interval,processed_shape
from steburn.core.processing import resolve
from steburn.io.importers import import_file,BITMAPS

MODE_LABELS={'Graustufen · variable Leistung':'gray','Floyd-Steinberg · Rasterpunkte':'floyd','Atkinson · Rasterpunkte':'atkinson','Schwarzweiß · Schwellwert':'threshold'}

class ImageStudio(tk.Toplevel):
    def __init__(self,app,shape=None):
        super().__init__(app); self.app=app; self.edit_id=shape.id if shape else None
        self.title('SteBurn · Bildstudio & Import'); self.geometry(f'{min(1320,self.winfo_screenwidth()-50)}x{min(740,self.winfo_screenheight()-110)}'); self.minsize(1040,590)
        self.records=[]; self.index=None; self.loading=False; self.timer=None; self.poll_id=None; self.closed=False
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='SteBurn-Bild'); self.results=queue.Queue(); self.generation=0; self.future=None
        self.photos=[]; self.images={}; self.rects={}; self.info=tk.StringVar(value='Bilder hinzufügen oder eine bestehende Bildauswahl bearbeiten.')
        header=ttk.Frame(self,style='Studio.Dark.TFrame',padding=(16,10)); header.pack(fill='x')
        ttk.Label(header,text='BILDSTUDIO',style='Studio.Dark.TLabel',font=('Segoe UI',16,'bold')).pack(side='left')
        ttk.Label(header,text='Import → Bildkorrektur → Raster → Projekt',style='Studio.Dark.TLabel').pack(side='right')
        footer=ttk.Frame(self,padding=(12,8)); footer.pack(side='bottom',fill='x')
        ttk.Button(footer,text='Schließen',style='Compact.TButton',command=self.close).pack(side='left')
        self.apply_button=ttk.Button(footer,text='Änderungen übernehmen' if shape else 'Bilder ins Projekt übernehmen',style='Accent.TButton',command=self.apply); self.apply_button.pack(side='right')
        ttk.Label(self,textvariable=self.info,padding=(12,5),wraplength=1200).pack(side='bottom',fill='x')
        body=ttk.Frame(self,padding=10); body.pack(fill='both',expand=True)
        body.columnconfigure(1,weight=1); body.rowconfigure(0,weight=1)
        left=ttk.Frame(body,width=160); left.grid(row=0,column=0,sticky='ns',padx=(0,10))
        for label,fn in [('＋ Bilder hinzufügen',self.choose_files),('Vektor / PDF importieren',self.import_vectors)]: ttk.Button(left,text=label,style='Compact.TButton',state='disabled' if shape else 'normal',command=fn).pack(fill='x',pady=3)
        ttk.Label(left,text='IMPORTLISTE',font=('Segoe UI',8,'bold')).pack(anchor='w',pady=(12,5))
        self.file_list=tk.Listbox(left,width=23,height=7,exportselection=False,relief='flat',highlightthickness=1,highlightbackground='#d5deea',font=('Segoe UI',9)); self.file_list.pack(fill='both',expand=True); self.file_list.bind('<<ListboxSelect>>',self.select_record)
        ttk.Button(left,text='Aus Liste entfernen',style='Compact.TButton',state='disabled' if shape else 'normal',command=self.remove_record).pack(fill='x',pady=5)
        ttk.Label(left,text='Einstellungen gelten pro Bild. Alle Bilder der Liste werden gemeinsam übernommen.',wraplength=155,style='Studio.Muted.TLabel').pack(fill='x',pady=6)
        center=ttk.Frame(body); center.grid(row=0,column=1,sticky='nsew',padx=(0,10)); center.columnconfigure((0,1),weight=1); center.rowconfigure(1,weight=1)
        for i,(key,label) in enumerate([('original','Original · zum Zuschneiden ziehen'),('processed','Laserbild · geplantes Raster')]):
            ttk.Label(center,text=label,font=('Segoe UI',9,'bold')).grid(row=0,column=i,sticky='w',pady=5)
            canvas=tk.Canvas(center,bg='#e4eaf2',highlightthickness=0,width=220); canvas.grid(row=1,column=i,sticky='nsew',padx=(0,5)); self.images[key]=canvas
            canvas.bind('<Configure>',lambda e:self.paint())
        original=self.images['original']; original.bind('<ButtonPress-1>',self.crop_press); original.bind('<B1-Motion>',self.crop_motion); original.bind('<ButtonRelease-1>',self.crop_release)
        self.details=tk.StringVar(value='Original bleibt im Projekt erhalten. Vorschau und Ausgabe verwenden dieselbe Bildberechnung.')
        ttk.Label(center,textvariable=self.details,wraplength=620,padding=(0,8),style='Studio.Muted.TLabel').grid(row=2,column=0,columnspan=2,sticky='ew')
        tabs=ttk.Notebook(body); tabs.grid(row=0,column=2,sticky='ns'); self.tabs=tabs
        self.pages={name:ScrollPanel(tabs) for name in ('Bild','Zuschnitt','Laser')}
        for label,page in self.pages.items(): tabs.add(page,text=label)
        self.vars={}
        for name,value in asdict(PhotoSettings()).items():
            if name=='crop': continue
            self.vars[name]=tk.BooleanVar(value=value) if type(value) is bool else tk.StringVar(value=str(value))
        self.vars['mode']=tk.StringVar(value=next(iter(MODE_LABELS)))
        self.crop_vars=[tk.StringVar(value=v) for v in ('0','0','100','100')]
        self.width=tk.StringVar(value='100'); self.height=tk.StringVar(value='100'); self.interval=tk.StringVar(value='.3')
        self.power=tk.StringVar(value='20'); self.speed=tk.StringVar(value='1200'); self.passes=tk.StringVar(value='1'); self.keep_ratio=tk.BooleanVar(value=True)
        self.build_adjustments(); self.build_crop(); self.build_laser()
        for var in [*self.vars.values(),*self.crop_vars,self.width,self.height,self.interval,self.power,self.speed,self.passes,self.keep_ratio]: var.trace_add('write',self.schedule_preview)
        self.protocol('WM_DELETE_WINDOW',self.close)
        if app.appearance: app.appearance.present(self)
        if shape: self.add_shape(shape)
        self.poll()
    def group(self,page,title):
        group=ttk.LabelFrame(self.pages[page].content,text=title,padding=7); group.pack(fill='x',padx=7,pady=4); return group
    def entry(self,parent,label,var,row):
        ttk.Label(parent,text=label).grid(row=row,column=0,sticky='w',pady=3,padx=(0,8))
        entry=ttk.Entry(parent,textvariable=var,width=10); entry.grid(row=row,column=1,sticky='ew',pady=3); parent.columnconfigure(1,weight=1); return entry
    def build_adjustments(self):
        group=self.group('Bild','Tonwerte & Details')
        for key,label,lo,hi in [('brightness','Helligkeit',.1,3),('contrast','Kontrast',.1,4),('gamma','Gamma / Mitteltöne',.2,3),('sharpness','Schärfe',0,4)]:
            row=ttk.Frame(group); row.pack(fill='x',pady=3); ttk.Label(row,text=label).pack(anchor='w')
            line=ttk.Frame(row); line.pack(fill='x'); ttk.Scale(line,from_=lo,to=hi,variable=self.vars[key]).pack(side='left',fill='x',expand=True); ttk.Entry(line,textvariable=self.vars[key],width=6).pack(side='right',padx=(5,0))
        row=ttk.Frame(group); row.pack(fill='x',pady=5)
        self.entry(row,'Schwarzpunkt',self.vars['black'],0); self.entry(row,'Weißpunkt',self.vars['white'],1)
        ttk.Checkbutton(group,text='Tonwerte automatisch spreizen',variable=self.vars['autocontrast']).pack(anchor='w',pady=3)
        ttk.Checkbutton(group,text='Invertieren / Negativ',variable=self.vars['invert']).pack(anchor='w',pady=3)
        ttk.Button(group,text='Bildkorrekturen zurücksetzen',style='Compact.TButton',command=self.reset_adjustments).pack(fill='x',pady=5)
    def build_crop(self):
        group=self.group('Zuschnitt','Zuschnitt in Prozent')
        for i,(label,var) in enumerate(zip(('Links','Oben','Rechts','Unten'),self.crop_vars)): self.entry(group,label,var,i)
        ttk.Label(group,text='Alternativ auf dem Original einen Ausschnitt aufziehen.',wraplength=235,style='Studio.Muted.TLabel').grid(row=4,column=0,columnspan=2,sticky='ew',pady=8)
        ttk.Button(group,text='Gesamtes Bild',style='Compact.TButton',command=self.reset_crop).grid(row=5,column=0,columnspan=2,sticky='ew')
        group=self.group('Zuschnitt','Ausrichtung')
        ttk.Combobox(group,textvariable=self.vars['rotate'],values=['0','90','180','270'],state='readonly').pack(fill='x',pady=4)
        ttk.Label(group,text='Drehung im Uhrzeigersinn (°)').pack(anchor='w')
        ttk.Checkbutton(group,text='Horizontal spiegeln',variable=self.vars['mirror']).pack(anchor='w',pady=5)
    def build_laser(self):
        group=self.group('Laser','Bildverfahren')
        ttk.Combobox(group,textvariable=self.vars['mode'],values=list(MODE_LABELS),state='readonly',width=28).pack(fill='x',pady=4)
        row=ttk.Frame(group); row.pack(fill='x'); self.threshold_entry=self.entry(row,'Schwellwert (0–255)',self.vars['threshold'],0)
        ttk.Label(group,text='Graustufen modulieren die Leistung. Rasterverfahren erzeugen Schwarzweißpunkte.',wraplength=235,style='Studio.Muted.TLabel').pack(fill='x',pady=5)
        group=self.group('Laser','Maße & Raster')
        for i,(label,var) in enumerate([('Breite (mm)',self.width),('Höhe (mm)',self.height),('Rasterabstand (mm)',self.interval)]):
            entry=self.entry(group,label,var,i)
            if var is self.height: self.height_entry=entry
        ttk.Checkbutton(group,text='Seitenverhältnis erhalten',variable=self.keep_ratio).grid(row=3,column=0,columnspan=2,sticky='w',pady=4)
        ttk.Button(group,text='Raster an Planlimit anpassen',style='Compact.TButton',command=self.fit_raster).grid(row=4,column=0,columnspan=2,sticky='ew',pady=4)
        group=self.group('Laser','Bearbeitungswerte')
        for i,(label,var) in enumerate([('Max. Leistung (%)',self.power),('Vorschub (mm/min)',self.speed),('Durchgänge',self.passes)]): self.entry(group,label,var,i)
    def choose_files(self):
        paths=filedialog.askopenfilenames(parent=self,title='Fotos und Bilder hinzufügen',filetypes=[('Bilder','*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.gif *.tga'),('Alle Dateien','*.*')])
        self.add_files(paths)
    def add_files(self,paths):
        messages=[]
        for path in paths:
            try:
                if Path(path).suffix.lower() not in BITMAPS: raise ValueError('Für Vektor/PDF bitte den separaten Import verwenden.')
                result=import_file(path,self.app.active_layer)
                self.add_shape(result.shapes[0],select=False)
                messages.extend(result.warnings)
            except Exception as ex: messages.append(Path(path).name+': '+str(ex))
        if self.index is None and self.records: self.load_record(0)
        if messages: self.info.set(' · '.join(messages))
    def add_shape(self,shape,select=True):
        source=shape.extra.get('image_original',shape.extra['image']); original=decode_image(source); source_size=original.size
        original.thumbnail((1400,1400),Image.Resampling.LANCZOS)
        layer=next(l for l in self.app.p.layers if l.id==shape.layer); process=resolve(shape,layer)
        values=shape.extra.get('image_adjustments',asdict(PhotoSettings()))
        interval=process.interval if self.edit_id else recommended_interval(shape.w,shape.h,process.passes)
        cw,ch=cropped_size(source_size,values)
        keep=not self.edit_id or abs(shape.h/shape.w-ch/cw)<.001
        self.records.append(dict(shape=deepcopy(shape),source=source,size=source_size,original=original,settings=deepcopy(values),width=shape.w,height=shape.h,interval=interval,power=process.power,speed=process.speed,passes=process.passes,keep=keep))
        self.file_list.insert('end',shape.name)
        if select: self.load_record(len(self.records)-1)
    def select_record(self,e=None):
        selection=self.file_list.curselection()
        if not selection or self.loading: return
        index=selection[0]
        if self.index is not None and index!=self.index:
            try: self.save_form()
            except Exception as ex:
                self.info.set(str(ex)); self.file_list.selection_clear(0,'end'); self.file_list.selection_set(self.index); return
        self.load_record(index)
    def load_record(self,index):
        self.loading=True; self.index=index; record=self.records[index]; values=asdict(settings_from(record['settings']))
        for key,var in self.vars.items(): var.set(next(label for label,value in MODE_LABELS.items() if value==values[key]) if key=='mode' else values[key])
        for var,value in zip(self.crop_vars,values['crop']): var.set(f'{value*100:g}')
        for key in ('width','height','interval','power','speed','passes'): getattr(self,key).set(str(record[key]))
        self.keep_ratio.set(record.get('keep',True)); self.file_list.selection_clear(0,'end'); self.file_list.selection_set(index)
        self.original_image=record['original']; self.processed_image=None
        self.loading=False; self.schedule_preview(); self.paint()
    def form(self):
        values={key:var.get() for key,var in self.vars.items()}; values['mode']=MODE_LABELS[values['mode']]
        for key in ('brightness','contrast','gamma','sharpness'): values[key]=float(str(values[key]).replace(',','.'))
        for key in ('black','white','threshold','rotate'): values[key]=int(float(values[key]))
        values['crop']=tuple(float(v.get().replace(',','.'))/100 for v in self.crop_vars)
        settings=asdict(settings_from(values))
        width=float(self.width.get().replace(',','.')); height=float(self.height.get().replace(',','.'))
        if self.keep_ratio.get() and self.index is not None:
            w,h=cropped_size(self.records[self.index]['size'],settings); height=width*h/w
        interval=float(self.interval.get().replace(',','.')); power=float(self.power.get().replace(',','.')); speed=float(self.speed.get().replace(',','.')); passes=int(self.passes.get())
        if not all(math.isfinite(v) for v in (width,height,interval,power,speed)) or not 0<width<=10000 or not 0<height<=10000 or not 0<=power<=100 or not 0<speed<=30000 or not 1<=passes<=1000: raise ValueError('Ungültige Maße oder Laserparameter.')
        return dict(settings=settings,width=width,height=height,interval=interval,power=power,speed=speed,passes=passes,keep=self.keep_ratio.get())
    def save_form(self):
        if self.index is None: return
        self.records[self.index].update(self.form())
    def schedule_preview(self,*args):
        if self.loading or self.closed or self.index is None: return
        self.generation+=1
        self.height_entry.configure(state='readonly' if self.keep_ratio.get() else 'normal')
        self.threshold_entry.configure(state='normal' if MODE_LABELS[self.vars['mode'].get()] in ('threshold','atkinson') else 'disabled')
        if self.timer: self.after_cancel(self.timer)
        self.timer=self.after(180,self.request_preview)
    def request_preview(self):
        self.timer=None
        try:
            record=self.records[self.index]; form=self.form(); size=raster_size(form['width'],form['height'],form['interval'],form['passes'])
            if self.keep_ratio.get():
                self.loading=True; self.height.set(f'{form["height"]:.3f}'); self.loading=False
            self.generation+=1; generation=self.generation
            if self.future: self.future.cancel()
            def work(): return render_photo(record['source'],form['settings'],size)
            self.future=self.pool.submit(work)
            self.future.add_done_callback(lambda future:self.preview_done(future,generation,form,size))
            self.info.set('Vorschau wird berechnet …')
        except Exception as ex: self.loading=False; self.info.set(str(ex))
    def preview_done(self,future,generation,form,size):
        if future.cancelled(): return
        try: self.results.put(('preview',generation,future.result(),form,size))
        except Exception as ex: self.results.put(('error',generation,str(ex)))
    def poll(self):
        if self.closed: return
        try:
            while True:
                result=self.results.get_nowait(); kind=result[0]
                if kind=='applied':
                    self.finish_apply(result[1])
                    if self.closed: return
                    continue
                if kind=='apply_error': self.apply_button.configure(state='normal'); self.info.set(result[1]); continue
                if result[1]!=self.generation: continue
                if kind=='error': self.info.set(result[2]); continue
                _,_,self.processed_image,form,size=result
                coverage=sum((255-v)*count for v,count in enumerate(self.processed_image.histogram()))/(255*size[0]*size[1])*100
                self.details.set(f'{size[0]} × {size[1]} Rasterpixel · {25.4/form["interval"]:.1f} dpi · {form["width"]:.1f} × {form["height"]:.1f} mm\nDunkelanteil {coverage:.1f} % · Vorschau zeigt den berechneten Rasterinhalt, verkleinert auf den Bildschirm.')
                self.info.set('Vorschau aktuell · Original bleibt erhalten'); self.paint()
        except queue.Empty: pass
        self.poll_id=self.after(80,self.poll)
    def paint(self):
        self.photos=[]
        for key,image in [('original',getattr(self,'original_image',None)),('processed',getattr(self,'processed_image',None))]:
            canvas=self.images[key]; canvas.delete('all')
            if image is None:
                canvas.create_text(max(10,canvas.winfo_width()/2),max(10,canvas.winfo_height()/2),text='Bild hinzufügen' if key=='original' else 'Laserbild-Vorschau',fill='#64748b'); continue
            width,height=max(1,canvas.winfo_width()-20),max(1,canvas.winfo_height()-20)
            scale=min(width/image.width,height/image.height); size=(max(1,int(image.width*scale)),max(1,int(image.height*scale)))
            preview=image.resize(size,Image.Resampling.NEAREST if key=='processed' else Image.Resampling.LANCZOS)
            photo=ImageTk.PhotoImage(preview,master=self); self.photos.append(photo)
            x=(canvas.winfo_width()-size[0])/2; y=(canvas.winfo_height()-size[1])/2; self.rects[key]=(x,y,size[0],size[1])
            canvas.create_image(x,y,anchor='nw',image=photo)
            if key=='original':
                try:
                    a,b,c,d=[float(v.get())/100 for v in self.crop_vars]
                    canvas.create_rectangle(x+a*size[0],y+b*size[1],x+c*size[0],y+d*size[1],outline='#0d9488',dash=(4,3),width=2)
                except ValueError: pass
        if hasattr(self.app,'theme'):
            for canvas in self.images.values(): self.app.theme.style_canvas(canvas)
    def crop_press(self,e):
        if 'original' not in self.rects: return
        self.crop_start=(e.x,e.y)
    def crop_motion(self,e):
        if not hasattr(self,'crop_start'): return
        canvas=self.images['original']; canvas.delete('crop-ghost'); canvas.create_rectangle(*self.crop_start,e.x,e.y,outline='#0d9488',width=2,tags='crop-ghost')
    def crop_release(self,e):
        if not hasattr(self,'crop_start') or 'original' not in self.rects: return
        x,y,w,h=self.rects['original']; a,b=self.crop_start; del self.crop_start
        left,right=sorted((max(0,min(1,(a-x)/w)),max(0,min(1,(e.x-x)/w))))
        top,bottom=sorted((max(0,min(1,(b-y)/h)),max(0,min(1,(e.y-y)/h))))
        if right-left<.01 or bottom-top<.01: return
        self.loading=True
        for var,value in zip(self.crop_vars,(left,top,right,bottom)): var.set(f'{value*100:.3f}')
        self.loading=False; self.schedule_preview(); self.paint()
    def reset_crop(self):
        for var,value in zip(self.crop_vars,('0','0','100','100')): var.set(value)
    def reset_adjustments(self):
        defaults=asdict(PhotoSettings()); self.loading=True
        for key in ('brightness','contrast','gamma','sharpness','black','white','threshold','invert','autocontrast'): self.vars[key].set(defaults[key])
        self.loading=False; self.schedule_preview()
    def fit_raster(self):
        try:
            form=self.form(); self.interval.set(str(recommended_interval(form['width'],form['height'],form['passes'])))
        except Exception as ex: self.info.set(str(ex))
    def remove_record(self):
        if self.index is None: return
        self.generation+=1; self.records.pop(self.index); self.file_list.delete(self.index); self.index=None
        if self.records: self.load_record(0)
        else: self.original_image=None; self.processed_image=None; self.paint()
    def import_vectors(self):
        self.app.import_vector_file()
        if not self.records: self.close()
    def apply(self):
        if not self.records: self.info.set('Bitte zuerst Bilder hinzufügen.'); return
        try:
            self.save_form(); records=deepcopy([{k:v for k,v in r.items() if k!='original'} for r in self.records])
            for r in records: raster_size(r['width'],r['height'],r['interval'],r['passes'])
            self.apply_button.configure(state='disabled'); self.info.set('Laserbilder werden berechnet …')
            def work():
                try:
                    shapes=[processed_shape(r['shape'],r['settings'],r['width'],r['height'],r['interval'],r['power'],r['speed'],r['passes']) for r in records]
                    self.results.put(('applied',shapes))
                except Exception as ex: self.results.put(('apply_error',str(ex)))
            self.pool.submit(work)
        except Exception as ex: self.info.set(str(ex))
    def finish_apply(self,shapes):
        try:
            p=deepcopy(self.app.p)
            if self.edit_id:
                current=next((s for s in p.shapes if s.id==self.edit_id),None)
                if current is None or current.extra.get('locked'): raise ValueError('Das Bild wurde entfernt oder gesperrt.')
                source=current.extra.get('image_original',current.extra['image'])
                if source!=self.records[0]['source']: raise ValueError('Das Original wurde inzwischen geändert. Bildstudio erneut öffnen.')
                current.extra.update(shapes[0].extra); current.w=shapes[0].w; current.h=shapes[0].h
                for shape in shapes[1:]: p.shapes.append(shape)
            else:
                for i,shape in enumerate(shapes): shape.x+=i*8; shape.y+=i*8; p.shapes.append(shape)
            self.app.selection={s.id for s in shapes}; self.app.selected=shapes[0].id; self.app.commit(p)
            self.app.switch_workspace('design'); self.app.status.set(f'{len(shapes)} Laserbilder übernommen · Originale und Korrekturen gespeichert')
            self.close()
        except Exception as ex: self.apply_button.configure(state='normal'); self.info.set(str(ex))
    def close(self):
        self.closed=True
        if self.timer: self.after_cancel(self.timer)
        if self.poll_id: self.after_cancel(self.poll_id)
        self.pool.shutdown(wait=False,cancel_futures=True); self.destroy()
