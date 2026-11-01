"""Live job cockpit built on the existing serialized job runner."""
import tkinter as tk
from tkinter import ttk
import queue,time,threading,json
from pathlib import Path
from copy import deepcopy
from steburn.ui.job_window import JobWindow
from steburn.core.planner import build_plan,Plan
from steburn.core.jobs import snapshot
from steburn.core.streaming import JobRun
from steburn.core.job_errors import remedy
from steburn.core.order import move_layer,layer_for_segment
from steburn.ui.layer_order import LayerOrder
from steburn.platform.power import battery_status

class Cockpit(JobWindow):
    def __init__(self,app,project=None):
        tk.Toplevel.__init__(self,app)
        self.app=app; self.project_override=deepcopy(project) if project is not None else None
        self.project=deepcopy(project if project is not None else app.p)
        self.fixed_parameters=bool(self.project.extensions.get('material_test'))
        self.ui_events=[]; self.last_stats={}; self.control_events={}; self.report_data=None; self.report_path=None; self.final_event=False
        self.title('SteBurn · Job-Cockpit'); self.geometry(f'1100x620+{max(0,app.winfo_rootx()+10)}+{max(0,app.winfo_rooty()+10)}'); self.minsize(760,480)
        self.after_idle(self.fit_monitor)
        self.runner=None; self.events=queue.Queue(); self.started=None; self.done=0
        self.current_status={}; self.after_id=None; self.paused_at=None; self.pause_time=0.; self.last_state=None; self.drawn=0
        self.info=tk.StringVar(value='Bereit · Auftrag vor dem Start prüfen'); self.failure_hint=tk.StringVar(); self.last_error=None
        self.timing=tk.StringVar(value='Noch nicht gestartet'); self.battery=tk.StringVar()
        self.configure(bg='#f3f5f9')
        header=ttk.Frame(self,style='Studio.Dark.TFrame',padding=(20,12)); header.pack(fill='x')
        ttk.Label(header,text='JOB-COCKPIT',style='Studio.Dark.TLabel',font=('Segoe UI',17,'bold')).pack(side='left')
        ttk.Button(header,text='05 Gerät / Verbindung',command=self.open_device,style='Compact.TButton').pack(side='right',padx=(12,0))
        ttk.Label(header,text=self.project.title,style='Studio.Dark.TLabel').pack(side='right')
        # Reserve action row before the expanding content so Stop stays visible.
        actions=ttk.Frame(self,padding=(16,10)); actions.pack(side='bottom',fill='x')
        self.start_button=ttk.Button(actions,text='Auftrag starten · Lasern',style='Accent.TButton',command=self.start); self.start_button.pack(side='left')
        self.pause_button=ttk.Button(actions,text='Pause',command=self.toggle_pause,state='disabled'); self.pause_button.pack(side='left',padx=6)
        self.resume_button=self.pause_button
        self.stop_button=ttk.Button(actions,text='Abbrechen + Referenzposition',style='Danger.TButton',command=self.stop,state='disabled'); self.stop_button.pack(side='right')
        ttk.Button(actions,text='Notstopp / Reset',command=self.emergency).pack(side='right',padx=8)
        ttk.Button(actions,text='Statistik / Ereignisse',command=self.show_statistics).pack(side='right',padx=8)
        ttk.Label(self,textvariable=self.battery,padding=(16,3)).pack(side='bottom',fill='x')
        ttk.Label(self,textvariable=self.timing,padding=(16,3)).pack(side='bottom',fill='x')
        self.progress=ttk.Progressbar(self,maximum=100); self.progress.pack(side='bottom',fill='x',padx=16,pady=6)
        ttk.Label(self,textvariable=self.info,padding=(16,5),wraplength=1050).pack(side='bottom',fill='x')
        ttk.Label(self,textvariable=self.failure_hint,padding=(16,2),wraplength=1050,foreground='#dc493b').pack(side='bottom',fill='x')
        stats=ttk.Frame(self,padding=(16,10)); stats.pack(fill='x')
        self.metrics={}
        for i,(key,title,value) in enumerate([('state','CONTROLLER','—'),('position','POSITION / mm','—'),('feed','VORSCHUB / mm/s','—'),('power','LEISTUNG / %','—')]):
            card=ttk.Frame(stats,style='Studio.Card.TFrame',padding=(14,9)); card.grid(row=0,column=i,sticky='nsew',padx=(0,8)); stats.columnconfigure(i,weight=1)
            ttk.Label(card,text=title,style='Studio.Muted.TLabel',font=('Segoe UI',8,'bold')).pack(anchor='w')
            var=tk.StringVar(value=value); self.metrics[key]=var
            ttk.Label(card,textvariable=var,style='Studio.Card.TLabel',font=('Segoe UI',15,'bold')).pack(anchor='w',pady=(4,0))
        self.order_widget=LayerOrder(self,lambda:self.project,self.change_order); self.order_widget.pack(fill='x',padx=8)
        body=ttk.Frame(self,padding=(16,0)); body.pack(fill='both',expand=True)
        body.columnconfigure(0,weight=1); body.columnconfigure(1,weight=0); body.rowconfigure(0,weight=1)
        preview=ttk.LabelFrame(body,text='Live-Werkzeugweg',padding=8); preview.grid(row=0,column=0,sticky='nsew',padx=(0,12))
        self.canvas=tk.Canvas(preview,bg='#e8edf5',highlightthickness=0); self.canvas.pack(fill='both',expand=True)
        side=ttk.Frame(body,width=290); side.grid(row=0,column=1,sticky='ns')
        live=ttk.LabelFrame(side,text='Parameter im Lauf',padding=8); live.pack(fill='x')
        self.feed_target=tk.DoubleVar(value=20); self.power_target=tk.DoubleVar(value=20); self.override_timer=None; self.initializing=True; self.manual_parameters=False
        self.speed_display=tk.StringVar(); self.power_display=tk.StringVar()
        self.confirmed=tk.StringVar(value='Ist: Vorschub — · Leistung —')
        for key,label in [('speed','Vorschub · Schritte 250 mm/min'),('power','Leistung · Schritte 5 %')]:
            ttk.Label(live,text=label).pack(anchor='w')
            row=ttk.Frame(live); row.pack(fill='x',pady=(4,6))
            ttk.Button(row,text='−250' if key=='speed' else '−5',width=5,style='Compact.TButton',command=lambda k=key:self.step_parameter(k,-1),state='disabled' if self.fixed_parameters else 'normal').pack(side='left')
            ttk.Label(row,textvariable=self.speed_display if key=='speed' else self.power_display,anchor='center',width=18).pack(side='left',fill='x',expand=True,padx=4)
            ttk.Button(row,text='+250' if key=='speed' else '+5',width=5,style='Compact.TButton',command=lambda k=key:self.step_parameter(k,1),state='disabled' if self.fixed_parameters else 'normal').pack(side='right')
        row=ttk.Frame(live); row.pack(fill='x')
        ttk.Button(row,text='Planwerte wiederherstellen',style='Compact.TButton',command=self.reset_overrides,state='disabled' if self.fixed_parameters else 'normal').pack(fill='x')
        ttk.Label(live,textvariable=self.confirmed,wraplength=245).pack(fill='x',pady=(5,0))
        ttk.Label(live,text='Materialtest: feste Matrixwerte für reproduzierbare Ergebnisse.' if self.fixed_parameters else 'Sofortige Übermittlung; Bestätigung von Annahme und aktivem Bahnabschnitt. Der Bewegungspuffer kann kurz nachlaufen.',wraplength=245,style='Studio.Muted.TLabel').pack(fill='x',pady=5)
        log=ttk.LabelFrame(side,text='Job-Ereignisse',padding=8); log.pack(fill='both',expand=True,pady=(12,0))
        self.log=tk.Text(log,width=32,height=4,bg='#ffffff',fg='#334155',relief='flat',font=('Segoe UI',9),state='disabled',wrap='word')
        scroll=ttk.Scrollbar(log,command=self.log.yview); scroll.pack(side='right',fill='y'); self.log.configure(yscrollcommand=scroll.set); self.log.pack(fill='both',expand=True)
        self.percent=tk.StringVar(value='0')
        try: self.plan=build_plan(self.project,preview=False)
        except Exception as ex: self.plan=Plan([],[]); self.info.set(str(ex))
        self.load_plan_values(); self.initializing=False
        self.feed_target.trace_add('write',self.queue_overrides); self.power_target.trace_add('write',self.queue_overrides)
        self.canvas.bind('<Configure>',lambda e:self.draw()); self.protocol('WM_DELETE_WINDOW',self.close)
        if app.appearance: app.appearance.present(self)
        self.write_log('Cockpit bereit. Start löst die Bearbeitung aus.')
        self.tick()
    def fit_monitor(self):
        try: self.state('zoomed')
        except tk.TclError:
            self.geometry(f'{self.winfo_screenwidth()-40}x{self.winfo_screenheight()-100}+10+10')
    def change_order(self,lid,step):
        if self.app.busy or self.runner and self.runner.state not in ('ready','finished','failed','aborted'):
            self.info.set('Ebenenfolge während des Auftrags gesperrt; erst nach Ende ändern.'); return
        candidate=move_layer(self.project,lid,step)
        try: plan=build_plan(candidate,preview=False)
        except ValueError as ex: self.info.set(str(ex)); return
        if self.project_override is not None: self.project_override=deepcopy(candidate)
        else:
            project=deepcopy(self.app.p); table={l.id:l for l in project.layers}
            if set(table)!={l.id for l in candidate.layers}: self.info.set('Ebenen haben sich im Editor geändert. Cockpit erneut öffnen.'); return
            project.layers=[table[l.id] for l in candidate.layers]; self.app.commit(project)
        self.project=candidate; self.plan=plan; self.done=0; self.drawn=0; self.current_status={}; self.runner=None; self.draw(); self.order_widget.refresh(lid)
        self.progress['value']=0
        if not self.manual_parameters:
            self.initializing=True
            try: self.load_plan_values()
            finally: self.initializing=False
        self.info.set('Ebenenfolge aktualisiert; der nächste Start verwendet den neuen Plan.')
    def load_plan_values(self):
        segment=next((s for s in self.plan.segments if s.power>0),None)
        if segment:
            self.feed_target.set(segment.speed/60); self.power_target.set(segment.nominal_power or segment.power)
        self.update_parameter_display()
    def update_parameter_display(self):
        self.speed_display.set(f'{self.feed_target.get()*60:.0f} mm/min\n{self.feed_target.get():.2f} mm/s')
        self.power_display.set(f'{self.power_target.get():g} %')
    def step_parameter(self,key,direction):
        if self.fixed_parameters: return
        self.initializing=True
        try:
            if key=='speed': self.feed_target.set(max(6,min(30000,self.feed_target.get()*60+direction*250))/60)
            else: self.power_target.set(max(0,min(100,self.power_target.get()+direction*5)))
            self.manual_parameters=True; self.update_parameter_display()
        finally: self.initializing=False
        value=self.feed_target.get() if key=='speed' else self.power_target.get()
        if self.runner and self.runner.state in ('running','paused','pausing','resuming'):
            self.runner.request((key,value))
            self.confirmed.set('Änderung angefordert …')
        else: self.info.set('Startwerte angepasst')
    def toggle_pause(self):
        self.request('resume' if self.runner and self.runner.state=='paused' else 'pause')
    def request(self,action):
        if self.runner and self.runner.state in ('running','paused','pausing','resuming'): self.runner.request(action)
    def stop(self):
        if self.runner:
            self.app.device.realtime(0x21); self.runner.request('stop')
            self.info.set('Hält an · anschließend automatische Referenzfahrt')
    def emergency(self):
        self.app.device.emergency_stop(); self.info.set('Notstopp / Reset · Position ungültig; neu referenzieren')
    def xy(self,pt):
        z=min(max(1,self.canvas.winfo_width()-50)/self.project.width,max(1,self.canvas.winfo_height()-40)/self.project.height)
        return (self.canvas.winfo_width()-self.project.width*z)/2+pt[0]*z,20+(self.project.height-pt[1])*z
    def write_log(self,text):
        self.ui_events.append(dict(seconds=max(0,time.monotonic()-self.started) if self.started else 0,message=text))
        self.log.configure(state='normal'); self.log.insert('end',time.strftime('%H:%M:%S')+'  '+text+'\n'); self.log.see('end'); self.log.configure(state='disabled')
    def start(self):
        if self.app.busy: self.info.set('Ein Geräteauftrag läuft bereits.'); return
        self.failure_hint.set(''); self.last_error=None
        try:
            if not self.app.device.connected: raise ValueError('Kein Gerät verbunden.')
            if not self.app.device.homed or not self.app.device.origin_confirmed: raise ValueError('Referenzfahrt erforderlich: '+self.app.device.safety_reason)
            if hasattr(self.app,'flush_auto'): self.app.flush_auto()
            self.project=deepcopy(self.project_override if self.project_override is not None else self.app.p); self.plan=build_plan(self.project,preview=False); job=snapshot(self.plan)
            self.order_widget.refresh(); self.order_widget.set_enabled(False)
            watts=self.app.optical_watts() if hasattr(self.app,'optical_watts') else None
            self.runner=JobRun(self.app.device,job,self.project.width,self.project.height,self.events.put,nominal_watts=watts)
            self.started=time.monotonic(); self.done=0; self.drawn=0; self.last_state=None
            self.ui_events=[]; self.control_events={}; self.final_event=False; self.report_data=None; self.report_path=None
            if not self.manual_parameters:
                self.initializing=True; self.load_plan_values(); self.initializing=False
            else:
                self.runner.feed_target=self.feed_target.get()*60; self.runner.power_target=self.power_target.get()
                if not .1<=self.runner.feed_target/60<=500 or not 0<=self.runner.power_target<=100: raise ValueError('Ungültige Startparameter.')
                self.runner.change_parameter('speed',self.runner.feed_target,origin='start_values'); self.runner.change_parameter('power',self.runner.power_target,origin='start_values')
            self.app.busy=True; self.start_button.configure(state='disabled'); self.stop_button.configure(state='normal')
            def worker():
                try:
                    with self.app.device.io_lock: self.runner.run()
                finally: self.events.put({'worker_done':True})
            threading.Thread(target=worker,daemon=True).start(); self.draw(); self.write_log('Auftrag gestartet · kontinuierliches Streaming')
        except Exception as ex:
            self.info.set('Start gesperrt: '+str(ex)); self.show_failure(ex)
    def show_failure(self,error):
        self.last_error=dict(reason=str(error),recommendation=remedy(error,self.app.device))
        self.failure_hint.set('Ursache: '+str(error)+'\nEmpfehlung: '+self.last_error['recommendation'])
        self.write_log('Fehler: '+str(error)); self.write_log('Empfehlung: '+self.last_error['recommendation'])
    def open_device(self):
        self.app.switch_workspace('machine'); self.app.lift(); self.app.focus_force()
    def queue_overrides(self,*args):
        if self.initializing: return
        self.update_parameter_display()
        self.manual_parameters=True
        if self.override_timer: self.after_cancel(self.override_timer)
        self.override_timer=self.after_idle(self.apply_overrides)
    def apply_overrides(self):
        if self.override_timer: self.after_cancel(self.override_timer)
        self.override_timer=None
        try:
            feed,power=self.feed_target.get(),self.power_target.get()
            if not .1<=feed<=500 or not 0<=power<=100: raise ValueError('Geschwindigkeit 0,1–500 mm/s; Leistung 0–100 %.')
            if not self.runner or self.runner.state not in {'running','paused','pausing','resuming'}:
                self.info.set(f'Startwerte eingestellt · {feed:.1f} mm/s · {power:.1f} %'); return
            self.runner.request(('speed',feed)); self.runner.request(('power',power))
            self.write_log(f'Parameter · {feed:.1f} mm/s · maximal {power:.1f} %')
        except (ValueError,tk.TclError) as ex: self.info.set(str(ex))
    def reset_overrides(self):
        if self.fixed_parameters: return
        if self.override_timer: self.after_cancel(self.override_timer); self.override_timer=None
        self.manual_parameters=False
        self.initializing=True; self.load_plan_values(); self.initializing=False
        if self.runner: self.runner.request(('defaults',0))
    def draw(self):
        super().draw(); self.drawn=0
        if hasattr(self.app,'theme'): self.app.theme.style_canvas(self.canvas)
    def tick(self):
        try:
            while True:
                event=self.events.get_nowait()
                if 'control_event' in event:
                    record=event['control_event']; self.control_events[record['id']]=record
                    stage={'requested':'angefordert','transmitted':'übermittelt','accepted':'vom Controller angenommen','active':'im Bahnablauf bestätigt','not_applied':'nicht angewendet','unconfirmed':'Wirksamkeit nicht bestätigt'}[record['state']]
                    what='Vorschub' if record['key']=='speed' else 'Leistung' if record['key']=='power' else 'Planwerte'
                    message=f'#{record["id"]} {what}'+(f': {record["value"]:g} {record["unit"]}' if record['key']!='defaults' else '')+f' · {stage}'
                    if record['id']==max(self.control_events): self.confirmed.set(message)
                    self.write_log(message); continue
                if event.get('worker_done'):
                    self.app.busy=False; self.start_button.configure(state='normal'); self.stop_button.configure(state='disabled'); self.pause_button.configure(state='disabled'); continue
                self.current_status=event.get('status',self.current_status); self.done=event.get('completed',self.done)
                state=event.get('state','ready'); stats=event.get('stats',{})
                if event.get('error'): self.show_failure(event['error'])
                if state in ('finished','aborted','failed'): self.final_event=True
                self.progress['value']=event.get('progress',self.done/max(1,len(self.plan.segments))*100)
                self.pause_button.configure(text='Fortsetzen' if state=='paused' else 'Pause',state='normal' if state in ('running','paused') else 'disabled')
                self.stop_button.configure(state='normal' if state in ('running','paused','pausing','resuming') else 'disabled')
                labels={'running':'Läuft','paused':'Pausiert','pausing':'Hält an','resuming':'Setzt fort','returning':'Rückfahrt / Referenzposition','stopping':'Bricht ab','finished':'Fertig · Nullposition erreicht','aborted':'Abgebrochen · neu referenziert','failed':'Fehler · Position prüfen'}
                self.info.set(labels.get(state,state)+((' · '+event['error']) if 'error' in event else '')+f' · {event.get("accepted",0)}/{len(self.plan.segments)} Segmente angenommen')
                if stats:
                    self.last_stats=stats
                    energy=f'≈ {stats["energy_j"]:.1f} J / {stats["energy_j"]/3600:.4f} Wh' if stats.get('energy_j') is not None else 'Nennleistung unter Gerät eintragen'
                    self.timing.set(f'Zeit {stats.get("seconds",0):.1f} s · Pause {stats.get("pause_seconds",0):.1f} s · Fahrweg ≈ {stats.get("distance_mm",0):.1f} mm · {len(stats.get("adjustments",[]))} Parameteränderungen\nEnergie (Schätzung): {energy}')
                self.head()
        except queue.Empty: pass
        status=self.current_status
        self.metrics['state'].set(status.get('state','—'))
        coords=status.get('WPos',status.get('MPos',''))
        if coords:
            try: self.metrics['position'].set(' / '.join(f'{float(v):.1f}' for v in coords.split(',')[:2]))
            except ValueError: pass
        fs=status.get('FS','').split(',')
        if len(fs)==2:
            self.metrics['feed'].set(f'{float(fs[0])/60:.2f}')
            maximum=self.app.device.settings.get(30,1000); self.metrics['power'].set(f'{float(fs[1])/maximum*100:.1f}')
        if self.runner:
            if self.runner.state!=self.last_state:
                self.last_state=self.runner.state; self.write_log({'running':'Bearbeitung läuft','paused':'Vollständig pausiert','returning':'Rückfahrt / Referenzposition','aborted':'Abgebrochen · neu referenziert','finished':'Auftrag abgeschlossen','failed':'Auftrag abgebrochen / Fehler'}.get(self.last_state,self.last_state))
            for segment in self.plan.segments[self.drawn:self.done]:
                self.canvas.create_line(*self.xy(segment.start),*self.xy(segment.end),fill='#0d9488' if segment.power else '#94a3b8',tags='completed')
            self.drawn=self.done; self.canvas.tag_raise('head')
            if self.final_event and self.report_data is None: self.save_job_report()
        battery=battery_status()
        self.battery.set(('Netzbetrieb' if battery.ac else 'Akkubetrieb' if battery.ac is False else 'Stromversorgung unbekannt')+(f' · Akku {battery.percent} %' if battery.percent is not None else '')+' · Wachhalten während Auftrag / Pause')
        active=bool(self.app.busy or self.runner and self.runner.state not in ('ready','finished','failed','aborted'))
        self.order_widget.set_enabled(not active)
        if self.plan.segments:
            segment=self.plan.segments[min(self.done,len(self.plan.segments)-1)]
            self.order_widget.set_current(layer_for_segment(self.project,segment),bool(self.runner and self.runner.state=='finished'))
            if self.runner is None: self.order_widget.current.set(self.order_widget.current.get().replace('Aktuell:','Als Erstes:'))
        self.after_id=self.after(100,self.tick)
    def save_job_report(self):
        self.report_data=dict(version=1,title=self.project.title,state=self.runner.state,fingerprint=self.runner.job.fingerprint,statistics=self.last_stats,events=list(self.ui_events),error=self.last_error,material_test=self.project.extensions.get('material_test'))
        try:
            folder=Path(getattr(self.app,'report_directory',Path(__file__).resolve().parents[2]/'user-data'/'job-reports')); folder.mkdir(parents=True,exist_ok=True)
            self.report_path=folder/f'job-{time.time_ns()}.json'; self.report_path.write_text(json.dumps(self.report_data,ensure_ascii=False,indent=2),encoding='utf-8')
            self.app.last_job_report=str(self.report_path); self.write_log('Jobbericht gespeichert: '+self.report_path.name)
        except OSError as ex: self.write_log('Jobbericht konnte nicht gespeichert werden: '+str(ex))
    def show_statistics(self):
        window=tk.Toplevel(self); window.title('Jobstatistik · Parameterereignisse'); window.geometry('1060x500')
        ttk.Label(window,text=self.timing.get(),padding=12,wraplength=1000).pack(fill='x')
        columns=('id','parameter','value','requested','accepted','active','state')
        tree=ttk.Treeview(window,columns=columns,show='headings',height=12)
        for key,label,width in [('id','#',40),('parameter','Parameter',110),('value','Wert',125),('requested','Angefordert / s',130),('accepted','Controller / s',125),('active','Bahn aktiv / s',130),('state','Status',220)]: tree.heading(key,text=label); tree.column(key,width=width)
        tree.pack(fill='both',expand=True,padx=12,pady=8)
        for r in self.last_stats.get('adjustments',[]):
            stamp=lambda key:f'{r[key]:.2f}' if key in r else '—'
            tree.insert('','end',values=(r['id'],r['key'],f'{r["value"]:g} {r["unit"]}',stamp('requested_at'),stamp('accepted_at'),stamp('active_at'),r['state']))
        ttk.Label(window,text=str(self.report_path or 'Jobbericht wird nach Abschluss gespeichert.'),padding=12,wraplength=1000).pack(fill='x')
        if self.app.appearance: self.app.appearance.present(window)
    def close(self):
        if self.app.busy and self.runner and self.runner.state not in ('finished','failed','aborted'):
            self.info.set('Zuerst Auftrag beenden oder abbrechen.'); return
        if self.after_id: self.after_cancel(self.after_id)
        if self.override_timer: self.after_cancel(self.override_timer)
        self.destroy()
