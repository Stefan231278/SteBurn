"""Optional, lazy-loaded relief preparation; no guessed physical calibration or AI."""
import tkinter as tk
from tkinter import ttk,messagebox
import base64,io
from copy import deepcopy
from PIL import Image,ImageOps,ImageStat,ImageTk
from steburn.io.importers import image_shape

class ReliefDialog(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app); self.app=app; self.title('Steburn · Relief-Assistent'); self.geometry('690x700')
        chosen=[s for s in app.chosen() if s.kind=='image' and not s.extra.get('locked')]
        self.source=deepcopy(chosen[0]) if len(chosen)==1 else None
        ttk.Label(self,text='Relief vorbereiten',font=('Segoe UI',18,'bold')).pack(anchor='w',padx=18,pady=14)
        ttk.Label(self,text='Lokale Bildanalyse und Tiefeninterpretation. Keine KI angeschlossen.\nTiefenwerte sind Gestaltungsziele, kein kalibrierter Materialabtrag.',wraplength=640,foreground='#a33f24').pack(fill='x',padx=18)
        self.preview=ttk.Label(self); self.preview.pack(padx=18,pady=12)
        self.material=tk.StringVar(value='Holz'); self.depth=tk.StringVar(value='1.0'); self.slices=tk.StringVar(value='4'); self.invert=tk.BooleanVar(value=False)
        for label,var in [('Material',self.material),('Zieltiefe (mm, unkalibriert)',self.depth),('Schichten (2–16)',self.slices)]:
            ttk.Label(self,text=label).pack(anchor='w',padx=18); ttk.Entry(self,textvariable=var).pack(fill='x',padx=18,pady=(0,8))
        ttk.Checkbutton(self,text='Tiefenkarte umkehren (standardmäßig dunkel = tief)',variable=self.invert,command=self.show).pack(anchor='w',padx=18)
        self.analysis=tk.StringVar(value='Bitte genau ein Bild im Editor auswählen und den Assistenten neu öffnen.')
        ttk.Label(self,textvariable=self.analysis,wraplength=640).pack(fill='x',padx=18,pady=10)
        ttk.Button(self,text='Schichtvorschau als bearbeitbare Objekte übernehmen',command=self.generate).pack(fill='x',padx=18,pady=10)
        if self.source:
            with Image.open(io.BytesIO(base64.b64decode(self.source.extra['image']))) as image:
                self.gray=ImageOps.grayscale(image).copy()
            contrast=ImageStat.Stat(self.gray).stddev[0]
            suggestion='Geringer Kontrast: Motiv zuerst freistellen oder Kontrast erhöhen.' if contrast<25 else 'Vorschlag: wenige Schichten und weiche Übergänge; Details in Tiefenkarte prüfen.'
            self.analysis.set(f'Bildanalyse: {self.gray.width} × {self.gray.height} Pixel; Grauwert-Streuung {contrast:.1f}.\n{suggestion}\nEine Fotografie beschreibt keine eindeutige 3D-Geometrie. Übernommene Schichten sind zunächst von der Ausgabe ausgeschlossen.')
            self.show()
        if getattr(app,'appearance',None): app.appearance.present(self)
    def show(self):
        if not self.source: return
        image=ImageOps.invert(self.gray) if self.invert.get() else self.gray.copy()
        image.thumbnail((600,200)); self.photo=ImageTk.PhotoImage(image); self.preview.configure(image=self.photo)
    def generate(self):
        if not self.source: return
        try:
            import math
            depth=float(self.depth.get().replace(',','.')); n=int(self.slices.get())
            if not math.isfinite(depth) or not 0<depth<=20 or not 2<=n<=16: raise ValueError('Zieltiefe >0 bis 20 mm; 2 bis 16 Schichten. Keine Aussage zur erreichbaren Tiefe.')
            from steburn.core.model import Layer
            p=deepcopy(self.app.p)
            layer=Layer('Relief-Vorschau (ungeprüft)',color='#8a4cb8',mode='Fläche',output=False,power=10)
            p.layers.append(layer)
            gray=ImageOps.invert(self.gray) if self.invert.get() else self.gray
            for i in range(n):
                threshold=255*(1-(i+.5)/n)
                mask=gray.point(lambda v:0 if v<threshold else 255)
                s=image_shape(mask,layer.id,f'Relief Schicht {i+1}/{n}',width=self.source.w)
                s.x=self.source.x; s.y=self.source.y; s.h=self.source.h
                s.extra['relief']={'source_id':self.source.id,'material':self.material.get(),'target_depth_mm':depth,'slice':i+1,'count':n,'calibrated':False}
                p.shapes.append(s)
            p.extensions.setdefault('relief_preparations',[]).append({'source':self.source.id,'layer':layer.id,'depth_target_mm':depth,'material':self.material.get(),'calibrated':False})
            self.app.active_layer=layer.id; self.app.selection={s.id for s in p.shapes if s.layer==layer.id}; self.app.selected=next(iter(self.app.selection)); self.app.commit(p)
            messagebox.showinfo('Relief übernommen','Schichten liegen deckungsgleich in einer eigenen Ebene, Ausgabe AUS.\nOriginal bleibt erhalten. Original vor einer späteren Bearbeitung separat von der Ausgabe ausschließen.\nEinzelne Schichten über die Objektliste auswählen und simulieren.'); self.destroy()
        except Exception as ex: messagebox.showerror('Relief',str(ex))
