"""Laser job monitor with explicit start, pause and reset controls."""
import tkinter as tk
from tkinter import ttk,messagebox
import queue,threading,time,bisect
from steburn.core.planner import build_plan,Plan,Segment
from steburn.core.jobs import snapshot,DryRun,resume_index
from steburn.platform.power import battery_status

class JobWindow(tk.Toplevel):
    def __init__(self,app):
        super().__init__(app); self.app=app; self.title('Steburn · Lasern'); self.geometry('860x690')
        self.runner=None; self.events=queue.Queue(); self.started=None; self.done=0; self.current_status={}; self.after_id=None; self.paused_at=None; self.pause_time=0.
        self.info=tk.StringVar(value='Bereit · Laserauftrag bereit'); self.timing=tk.StringVar(value='Zeit: —'); self.battery=tk.StringVar(value='')
        ttk.Label(self,text='Lasern',font=('Segoe UI',18,'bold')).pack(anchor='w',padx=18,pady=(15,5))
        ttk.Label(self,text='Auftrag verwendet die eingestellte Leistung und Geschwindigkeit. Rahmenfahrt bleibt ohne Strahl.',wraplength=810,foreground='#a33f24').pack(fill='x',padx=18)
        self.canvas=tk.Canvas(self,bg='#e0e6ee',highlightthickness=0); self.canvas.pack(fill='both',expand=True,padx=18,pady=12)
        ttk.Label(self,textvariable=self.info).pack(fill='x',padx=18)
        self.progress=ttk.Progressbar(self,maximum=100); self.progress.pack(fill='x',padx=18,pady=6)
        ttk.Label(self,textvariable=self.timing).pack(fill='x',padx=18)
        ttk.Label(self,textvariable=self.battery).pack(fill='x',padx=18,pady=4)
        bar=ttk.Frame(self); bar.pack(fill='x',padx=18,pady=8)
        self.start_button=ttk.Button(bar,text='Auftrag starten · Lasern',command=self.start); self.start_button.pack(side='left')
        self.pause_button=ttk.Button(bar,text='Pause',command=lambda:self.request('pause'),state='disabled'); self.pause_button.pack(side='left',padx=5)
        self.resume_button=ttk.Button(bar,text='Fortsetzen',command=lambda:self.request('resume'),state='disabled'); self.resume_button.pack(side='left')
        self.stop_button=ttk.Button(bar,text='Abbrechen / Reset',command=self.stop,state='disabled'); self.stop_button.pack(side='right')
        controls=ttk.Frame(self); controls.pack(fill='x',padx=18,pady=4)
        for label,actions in [('Geschwindigkeit', [('−10 %','f-'),('100 %','f0'),('+10 %','f+')]),('Leistungs-Override', [('−10 %','p-'),('100 %','p0'),('+10 %','p+')])]:
            group=ttk.LabelFrame(controls,text=label,padding=4); group.pack(side='left',padx=(0,10))
            for text,action in actions: ttk.Button(group,text=text,command=lambda a=action:self.request(a)).pack(side='left')
        preview=ttk.Frame(self); preview.pack(fill='x',padx=18,pady=8)
        ttk.Label(preview,text='Ab Prozent (nur Simulations-Einstieg):').pack(side='left')
        self.percent=tk.StringVar(value='0'); ttk.Entry(preview,textvariable=self.percent,width=8).pack(side='left',padx=5)
        ttk.Button(preview,text='Vorschau ab hier',command=self.resume_preview).pack(side='left')
        self.canvas.bind('<Configure>',lambda e:self.draw())
        self.protocol('WM_DELETE_WINDOW',self.close)
        try: self.plan=build_plan(app.p); self.draw()
        except Exception as ex: self.plan=Plan([],[]); self.info.set(str(ex))
        if getattr(app,'appearance',None): app.appearance.present(self)
        self.start_button.configure(style='Accent.TButton'); self.stop_button.configure(style='Danger.TButton')
        self.tick()
    def xy(self,pt):
        z=min(max(1,self.canvas.winfo_width()-50)/self.app.p.width,max(1,self.canvas.winfo_height()-40)/self.app.p.height)
        return 25+pt[0]*z,20+(self.app.p.height-pt[1])*z
    def draw(self):
        if not hasattr(self,'plan'): return
        self.canvas.delete('all')
        self.canvas.create_rectangle(*self.xy((0,self.app.p.height)),*self.xy((self.app.p.width,0)),fill='white',outline='#8895a4')
        stride=max(1,len(self.plan.segments)//4000)
        for s in self.plan.segments[::stride]: self.canvas.create_line(*self.xy(s.start),*self.xy(s.end),fill='#a9bacb')
        self.head()
    def head(self):
        text=self.current_status.get('MPos')
        if not text: return
        try:
            x,y,*_=map(float,text.split(',')); a,b=self.xy((x,y)); self.canvas.delete('head')
            self.canvas.create_oval(a-5,b-5,a+5,b+5,fill='#e47723',tags='head')
        except ValueError: pass
    def start(self):
        if self.app.busy: self.info.set('Ein Geräteauftrag läuft. Kurz warten.'); return
        try:
            if not self.app.device.connected: raise ValueError('Zuerst im Gerätebereich verbinden und referenzieren.')
            self.plan=build_plan(self.app.p,preview=False)
            job=snapshot(self.plan)
            self.app.device.check_targets([s.end for s in job.segments],self.app.p.width,self.app.p.height)
            self.runner=DryRun(self.app.device,job,self.app.p.width,self.app.p.height,self.events.put,laser_enabled=True)
            self.started=time.monotonic(); self.pause_time=0.; self.paused_at=None; self.done=0
            self.app.busy=True; self.start_button.configure(state='disabled'); self.stop_button.configure(state='normal')
            def worker():
                try:
                    with self.app.device.io_lock: self.runner.run()
                finally: self.events.put({'worker_done':True})
            threading.Thread(target=worker,daemon=True).start(); self.draw()
        except Exception as ex: self.info.set('Start gesperrt: '+str(ex))
    def request(self,action):
        if self.runner and self.runner.state not in {'finished','failed','ready'}:
            self.runner.request(action)
            if action=='resume': self.resume_button.configure(state='disabled')
    def stop(self):
        # Raw reset must remain available even if a read is waiting for a timeout.
        self.app.device.emergency_stop()
        if self.runner: self.runner.request('stop')
        self.info.set('Reset angefordert · Position unbekannt · neu referenzieren')
    def tick(self):
        try:
            while True:
                event=self.events.get_nowait()
                if event.get('worker_done'):
                    self.app.busy=False; self.start_button.configure(state='normal'); self.stop_button.configure(state='disabled')
                    self.pause_button.configure(state='disabled'); self.resume_button.configure(state='disabled'); continue
                if 'battery_warning' in event: self.info.set('Akku niedrig: Pause angefordert. Netzteil anschließen.'); continue
                state=event.get('state','unknown'); self.current_status=event.get('status',self.current_status)
                self.done=event.get('completed',self.done); total=event.get('total',len(self.plan.segments))
                self.progress['value']=100*self.done/max(1,total)
                labels={'running':'Läuft','pausing':'Hält an','paused':'Pausiert','resuming':'Fortsetzen angefordert','finished':'Fertig','failed':'Abgebrochen / Position prüfen'}
                self.info.set(f'{labels.get(state,state)} · {self.done}/{total} abgeschlossene Segmente · Vorschub {event.get("feed",100)} % · Leistungs-Override {event.get("power",100)} % · Laserauftrag'+(' · '+event['error'] if 'error' in event else ''))
                self.pause_button.configure(state='normal' if state=='running' else 'disabled')
                self.resume_button.configure(state='normal' if state=='paused' else 'disabled')
                if state=='paused' and self.paused_at is None: self.paused_at=time.monotonic()
                if state=='running' and self.paused_at is not None: self.pause_time+=time.monotonic()-self.paused_at; self.paused_at=None
                self.head()
        except queue.Empty: pass
        if self.started:
            elapsed=time.monotonic()-self.started
            remaining=sum(s.duration for s in self.plan.segments[self.done:])
            feed=self.runner.feed if self.runner else 100
            self.timing.set(f'Vergangen {elapsed:.0f} s · Rest grob {remaining*100/max(10,feed):.0f} s · Pausen/Übertragung und Beschleunigung verändern die Schätzung')
            if self.runner and self.runner.state in {'finished','failed'}: self.started=None
        battery=battery_status(); self.battery.set(('Netzbetrieb' if battery.ac is True else 'Akkubetrieb' if battery.ac is False else 'Stromversorgung unbekannt')+(f' · Akku {battery.percent} %' if battery.percent is not None else '')+' · Wachhalten aktiv nur während physischem Auftrag (Windows)')
        self.after_id=self.after(150,self.tick)
    def resume_preview(self):
        from steburn.ui.simulation import Simulation
        try:
            job=snapshot(build_plan(self.app.p,preview=False)); i,actual=resume_index(job,float(self.percent.get().replace(',','.')))
            messagebox.showinfo('Wiederaufnahme-Vorschau',f'Einstieg am Segmentanfang bei {actual:.2f} % der geschätzten Planzeit.\nKeine physische Wiederaufnahme nach Ausfall freigegeben.')
            Simulation(self.app,Plan(list(job.segments[i:]),['Vorschau eines Wiedereinstiegs; reale Position und Material nicht geprüft.']))
        except Exception as ex: messagebox.showerror('Vorschau',str(ex))
    def close(self):
        if self.app.busy and self.runner and self.runner.state not in {'finished','failed'}:
            messagebox.showinfo('Auftrag läuft','Zuerst Auftrag beenden oder abbrechen.'); return
        if self.after_id: self.after_cancel(self.after_id)
        self.destroy()
