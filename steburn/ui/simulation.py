import tkinter as tk
from tkinter import ttk
import time,bisect
from copy import deepcopy
from steburn.core.planner import build_plan,Plan,Segment
from steburn.core.order import move_layer,layer_for_segment
from steburn.ui.layer_order import LayerOrder

class Simulation(tk.Toplevel):
    def __init__(self,app,plan=None,label='Bearbeitungssimulation'):
        super().__init__(app); self.title('Steburn · '+label); self.geometry(f'{min(1100,self.winfo_screenwidth()-80)}x{min(720,self.winfo_screenheight()-140)}')
        self.app=app; self.plan=plan or build_plan(app.p); self.project=deepcopy(app.p); self.elapsed=0.; self.playing=False; self.tick_id=None
        self.plan_ids={s.shape_id for s in self.plan.segments}; self.order_editable=bool(self.plan_ids) and self.plan_ids<={s.id for s in self.project.shapes}
        self.cumulative=[0.]
        for segment in self.plan.segments: self.cumulative.append(self.cumulative[-1]+segment.duration)
        self.total=self.cumulative[-1]; self.last=time.monotonic()
        bar=ttk.Frame(self); bar.pack(fill='x',padx=8,pady=8)
        for name,fn in [('Start / Fortsetzen',self.play),('Pause',self.pause),('Zurücksetzen',self.reset)]: ttk.Button(bar,text=name,command=fn).pack(side='left',padx=4)
        self.speed=tk.StringVar(value='10'); ttk.Label(bar,text='Tempo ×').pack(side='left',padx=(12,4)); ttk.Combobox(bar,textvariable=self.speed,values=['1','5','10','50','100'],width=5,state='readonly').pack(side='left')
        self.info=tk.StringVar(); ttk.Label(self,textvariable=self.info,padding=8).pack(fill='x')
        self.order_widget=LayerOrder(self,lambda:self.project,self.change_order); self.order_widget.pack(fill='x',padx=8); self.order_widget.set_enabled(self.order_editable)
        self.canvas=tk.Canvas(self,bg='#e5e9ef',highlightthickness=0); self.canvas.pack(fill='both',expand=True,padx=8)
        self.slider=ttk.Scale(self,from_=0,to=max(self.total,.001),command=self.seek); self.slider.pack(fill='x',padx=12,pady=8)
        details='\n'.join(self.plan.warnings[:8]) or 'Keine Auffälligkeiten im berechneten Weg.'
        ttk.Label(self,text='Rot: Bearbeitung · Blau gestrichelt: Leerfahrt · Gelb: virtuelle Laserposition\n'+details+'\nZeit ist ein geometrischer Schätzwert ohne Beschleunigung. Keine Vorhersage von Brand, Tiefe oder Schnittqualität.',wraplength=960,padding=8).pack(fill='x')
        self.canvas.bind('<Configure>',lambda e:self.draw()); self.protocol('WM_DELETE_WINDOW',self.close); self.after(60,self.draw)
        if getattr(app,'appearance',None): app.appearance.present(self)
    def xy(self,pt): return self.ox+pt[0]*self.scale,self.oy+(self.project.height-pt[1])*self.scale
    def change_order(self,lid,step):
        if self.app.busy: self.info.set('Reihenfolge während eines Geräteauftrags gesperrt.'); return
        candidate=move_layer(self.project,lid,step)
        try: plan=build_plan(candidate,ids=self.plan_ids)
        except ValueError as ex: self.info.set(str(ex)); return
        self.pause(); self.project=candidate; self.plan=plan; self.cumulative=[0.]
        for segment in plan.segments: self.cumulative.append(self.cumulative[-1]+segment.duration)
        self.total=self.cumulative[-1]; self.elapsed=0.; self.slider.configure(to=max(self.total,.001)); self.slider.set(0)
        if {l.id for l in self.app.p.layers}=={l.id for l in candidate.layers}:
            project=deepcopy(self.app.p); table={l.id:l for l in project.layers}; project.layers=[table[l.id] for l in candidate.layers]; self.app.commit(project)
        self.order_widget.refresh(lid); self.draw()
    def draw(self):
        c=self.canvas; c.delete('all'); self.scale=max(.1,min((c.winfo_width()-70)/self.project.width,(c.winfo_height()-60)/self.project.height)); self.ox=40; self.oy=25
        c.create_rectangle(*self.xy((0,self.project.height)),*self.xy((self.project.width,0)),fill='white',outline='#8997a5')
        for n in range(0,int(self.project.width)+1,50): c.create_text(*self.xy((n,0)),text=str(n),anchor='n',font=('Segoe UI',8))
        for n in range(0,int(self.project.height)+1,50): c.create_text(*self.xy((0,n)),text=str(n),anchor='e',font=('Segoe UI',8))
        stride=max(1,len(self.plan.segments)//6000)
        for s in self.plan.segments[::stride]: c.create_line(*self.xy(s.start),*self.xy(s.end),fill='#e7a19a' if s.power else '#8fb2da',dash=() if s.power else (3,3))
        if stride>1: c.create_text(50,30,anchor='nw',text='Dichte Wege: Hintergrunddarstellung reduziert; Zeitablauf vollständig.',fill='#666')
        self.update_head()
        if hasattr(self.master,'theme'): self.master.theme.style_canvas(c)
    def update_head(self):
        if not self.plan.segments:
            self.info.set('Keine Segmente'); return
        i=min(len(self.plan.segments)-1,max(0,bisect.bisect_right(self.cumulative,self.elapsed)-1)); s=self.plan.segments[i]
        self.order_widget.set_current(layer_for_segment(self.project,s),self.elapsed>=self.total)
        t=min(1,max(0,(self.elapsed-self.cumulative[i])/max(s.duration,1e-12)))
        pt=tuple(a+(b-a)*t for a,b in zip(s.start,s.end)); x,y=self.xy(pt); self.canvas.delete('head')
        self.canvas.create_oval(x-6,y-6,x+6,y+6,fill='#ffd34e',outline='#573f10',width=2,tags='head')
        self.info.set(f'{self.elapsed:.1f} / {self.total:.1f} s · X {pt[0]:.1f} · Y {pt[1]:.1f} mm · '+(f'Bearbeitung {s.power:.2f} %' if s.power else 'Laser aus / Leerfahrt'))
    def seek(self,value): self.elapsed=float(value); self.last=time.monotonic(); self.update_head()
    def play(self):
        if self.elapsed>=self.total: self.elapsed=0.
        self.playing=True; self.last=time.monotonic(); self.tick()
    def tick(self):
        if self.tick_id: self.after_cancel(self.tick_id); self.tick_id=None
        if not self.playing: return
        now=time.monotonic(); self.elapsed=min(self.total,self.elapsed+(now-self.last)*float(self.speed.get())); self.last=now
        self.slider.set(self.elapsed); self.update_head()
        if self.elapsed>=self.total: self.playing=False
        else: self.tick_id=self.after(30,self.tick)
    def pause(self): self.playing=False
    def reset(self): self.pause(); self.elapsed=0.; self.slider.set(0); self.update_head()
    def close(self):
        self.pause()
        if self.tick_id: self.after_cancel(self.tick_id)
        self.destroy()
