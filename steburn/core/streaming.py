"""Single-reader GRBL character-counting stream with controlled lifecycle."""
from collections import deque
import math,queue,time
from steburn.platform.power import Awake,battery_status

class JobRun:
    def __init__(self,device,job,width,height,notify,nominal_watts=None,awake_factory=Awake):
        self.device=device; self.job=job; self.width=width; self.height=height; self.notify=notify
        self.nominal_watts=nominal_watts; self.awake_factory=awake_factory
        self.requests=queue.Queue(); self.state='ready'; self.done=0; self.index=0
        self.feed_target=None; self.power_target=None; self.pending_resume=False
        self.last_status={}; self.started=None; self.pause_seconds=0.; self.paused_since=None
        self.distance=0.; self.equivalent_seconds=0.; self.last_pos=None; self.last_sample=None
        self.last_power=0.; self.aborted=False; self.sent=0; self.accepted=0
        self.stats={}; self.started_motion=False; self._finish_time=None
        self.completed_fraction=0.; self.initial_position=None
        self.rx_peak=0
        self.control_history=[]; self.latest_control={}; self.control_markers=deque(maxlen=512); self.last_sent_point=None
    def control_update(self,record,state,**details):
        if record['state']==state: return
        stamp=time.monotonic(); now=max(0,stamp-(self.started if self.started is not None else stamp))
        record.update(state=state,**details); record[state+'_at']=now
        self.notify({'control_event':dict(record)})
    def change_parameter(self,key,value,origin='live'):
        stamp=time.monotonic()
        record=dict(id=len(self.control_history)+1,key=key,value=value,origin=origin,unit='mm/min' if key=='speed' else '%' if key=='power' else 'Planwerte',requested_at=max(0,stamp-(self.started if self.started is not None else stamp)),state='new')
        self.control_history.append(record); self.latest_control[key]=record['id']; self.control_update(record,'requested')
    def parameters(self,segment):
        speed=self.feed_target or segment.speed; nominal=segment.nominal_power or segment.power
        ratio=segment.power/nominal if nominal>0 else 0
        power=(self.power_target*ratio if self.power_target is not None else segment.power) if segment.operation!='travel' else 0
        return speed,math.floor(self.device.settings[30]*power/100),ratio
    def active_control_ids(self,segment):
        ids=[]
        for key,identifier in self.latest_control.items():
            record=self.control_history[identifier-1]
            if record['state']=='active': continue
            if key=='power' and (segment.operation=='travel' or segment.power<=0): continue
            ids.append(identifier)
        return ids
    def confirm_controls(self,pos,status):
        match=None
        for i,marker in enumerate(self.control_markers):
            a,b=marker['start'],marker['end']; dx,dy=b[0]-a[0],b[1]-a[1]; length2=dx*dx+dy*dy
            if not length2: continue
            t=((pos[0]-a[0])*dx+(pos[1]-a[1])*dy)/length2
            if .001<t<=1.001 and math.dist(pos,(a[0]+dx*min(1,t),a[1]+dy*min(1,t)))<=.03: match=i; break
        if match is None: return
        for _ in range(match+1):
            marker=self.control_markers.popleft()
            for identifier in marker['ids']:
                record=self.control_history[identifier-1]
                if record['state']!='active': self.control_update(record,'active',evidence='position_status',reported_fs=status.get('FS'),programmed_feed=marker['feed'],programmed_s=marker['s'])
    def finish_controls(self,completed):
        for record in self.control_history:
            if record['state']=='active': continue
            if completed and record['state']=='accepted': self.control_update(record,'active',evidence='program_completed')
            else: self.control_update(record,'unconfirmed' if record['state'] in ('transmitted','accepted') else 'not_applied',evidence='job_ended')
    def request(self,action): self.requests.put(action)
    def sample(self,status):
        now=time.monotonic()
        if self.last_sample is not None:
            self.equivalent_seconds+=self.last_power*max(0,now-self.last_sample)
        self.last_sample=now
        pos=self.device.position(status)
        self.confirm_controls(pos,status)
        if self.last_pos is not None: self.distance+=math.dist(pos,self.last_pos)
        self.last_pos=pos
        candidates=[]
        for i in range(self.done,min(len(self.job.segments),self.accepted+2,self.done+128)):
            segment=self.job.segments[i]; a=self.initial_position if i==0 and self.initial_position else segment.start; b=segment.end
            dx,dy=b[0]-a[0],b[1]-a[1]; length2=dx*dx+dy*dy
            t=max(0,min(1,((pos[0]-a[0])*dx+(pos[1]-a[1])*dy)/length2)) if length2 else 1
            error=math.dist(pos,(a[0]+dx*t,a[1]+dy*t))
            if error<=.03: candidates.append((error,i,t))
        if candidates:
            error,i,t=min(candidates,key=lambda item:(round(item[0],4),item[1]))
            self.completed_fraction=max(self.completed_fraction,i+t)
            self.done=max(self.done,i+(1 if t>=.999999 else 0))
        fs=status.get('FS','0,0').split(',')
        self.last_power=max(0,min(1,float(fs[1])/self.device.settings[30])) if len(fs)==2 and status['state']=='Run' else 0.
        self.last_status=status
        if status['state']=='Hold:0':
            if self.paused_since is None: self.paused_since=now
            self.state='paused'
        elif status['state']=='Hold:1': self.state='pausing'
        elif status['state']=='Run':
            if self.paused_since is not None: self.pause_seconds+=now-self.paused_since; self.paused_since=None
            if self.state not in ('stopping','returning'): self.state='running'
        elif self.paused_since is not None:
            self.pause_seconds+=now-self.paused_since; self.paused_since=None
    def emit(self,error=None):
        event=dict(state=self.state,completed=self.done,progress=min(100,self.completed_fraction/max(1,len(self.job.segments))*100),total=len(self.job.segments),sent=self.sent,accepted=self.accepted,status=self.last_status,stats=self.statistics())
        if error: event['error']=str(error)
        self.notify(event)
    def statistics(self):
        now=self._finish_time or time.monotonic()
        pauses=self.pause_seconds+(now-self.paused_since if self.paused_since is not None else 0)
        seconds=max(0,now-self.started) if self.started is not None else 0
        energy=self.equivalent_seconds*self.nominal_watts if self.nominal_watts else None
        return dict(seconds=seconds,pause_seconds=pauses,distance_mm=self.distance,energy_j=energy,equivalent_seconds=self.equivalent_seconds,aborted=self.aborted,adjustments=[dict(record) for record in self.control_history])
    def controls(self):
        while not self.requests.empty():
            action=self.requests.get_nowait()
            if action=='stop':
                self.aborted=True; self.state='stopping'; self.device.realtime(0x21)
            elif action=='pause' and self.state in ('running','resuming'):
                self.device.realtime(0x21); self.state='pausing'
            elif action=='resume': self.pending_resume=True
            elif isinstance(action,tuple):
                key,value=action
                if type(value) not in (int,float) or not math.isfinite(value): continue
                if key=='speed' and .1<=value<=500:
                    self.feed_target=value*60; self.change_parameter('speed',value*60)
                if key=='power' and 0<=value<=100:
                    self.power_target=value; self.change_parameter('power',value)
                if key=='defaults':
                    self.feed_target=None; self.power_target=None
                    self.latest_control={}; self.change_parameter('defaults',0)
        if self.pending_resume and not self.aborted and self.last_status.get('state')=='Hold:0':
            self.device.realtime(0x7e); self.pending_resume=False; self.state='resuming'
        elif self.pending_resume and not self.aborted and self.last_status.get('state')=='Idle' and self.state=='paused':
            self.pending_resume=False; self.state='running'
    def chunks(self,start):
        position=start
        for i,s in enumerate(self.job.segments):
            origin=position; distance=math.dist(origin,s.end); fraction=0.
            while fraction<1-1e-10:
                speed=self.feed_target or s.speed
                # Limit buffered adjustment latency without stopping the path.
                fraction=min(1.,fraction+max(.00001,speed/60*.05)/max(distance,1e-12))
                end=tuple(a+(b-a)*fraction for a,b in zip(origin,s.end))
                nominal=s.nominal_power or s.power
                ratio=s.power/nominal if nominal>0 else 0
                power=(self.power_target*ratio if self.power_target is not None else s.power) if s.operation!='travel' else 0
                mode='M3' if s.operation=='cut' or s.constant_power else 'M4'
                sval=math.floor(self.device.settings[30]*power/100)
                yield i,fraction,end,mode,sval,speed
            position=s.end
    @staticmethod
    def parse_status(line):
        parts=line[1:-1].split('|'); result={'state':parts[0]}
        for part in parts[1:]:
            if ':' in part:
                key,value=part.split(':',1); result[key]=value
        return result
    def run(self):
        d=self.device; inflight=deque(); used=0; pending=None; exhausted=False; mode=None
        try:
            d.check_targets([s.end for s in self.job.segments],self.width,self.height)
            start=tuple(d.ready(self.width,self.height))
            if any(abs(v)>.001 for v in d.read_work_offset()): raise ValueError('Auftrag benötigt Nullversatz.')
            with self.awake_factory():
                self.started=time.monotonic(); self.last_pos=start; self.last_sent_point=start; self.initial_position=start; self.state='running'
                d.command('M5'); d.command('S0'); d.command('G21 G90 G94 G54')
                d.realtime(0x90); d.realtime(0x99)
                generator=self.chunks(start); last_report=0.; last_response=time.monotonic(); last_emit=0.; last_ack=time.monotonic()
                while True:
                    self.controls(); now=time.monotonic()
                    if self.aborted and self.last_status.get('state') in ('Hold:0','Idle'):
                        # A cancelled G-code program needs a planner reset. Re-home
                        # after controlled stop rather than asserting stale position.
                        d.emergency_stop(); self.state='returning'; self.emit(); d.home()
                        self.last_status=d.status(); self.sample(self.last_status)
                        break
                    if not self.aborted and self.state not in ('pausing','paused'):
                        while used<96 and (not exhausted or pending is not None):
                            if pending is None:
                                try:
                                    i,fraction,end,new_mode,power,speed=next(generator)
                                    switch=(new_mode+' S0\n') if new_mode!=mode else ''
                                    pending=(f'{switch}G1 X{end[0]:.4f} Y{end[1]:.4f} F{speed:.3f} S{power}\n',i,fraction,new_mode,end)
                                except StopIteration:
                                    pending=('M5\n',None,None,mode,None); exhausted=True
                            text,i,fraction,new_mode,end=pending; marker=None
                            if i is not None:
                                segment=self.job.segments[i]; speed,power,ratio=self.parameters(segment)
                                switch=(new_mode+' S0\n') if new_mode!=mode else ''
                                text=f'{switch}G1 X{end[0]:.4f} Y{end[1]:.4f} F{speed:.3f} S{power}\n'
                                marker=dict(ids=self.active_control_ids(segment),start=self.last_sent_point,end=end,feed=speed,s=power)
                            encoded=text.encode('ascii')
                            if used+len(encoded)>96: break
                            # A mode switch and its motion each require their own ack.
                            for line in encoded.splitlines(keepends=True):
                                is_motion=line.startswith(b'G1')
                                inflight.append((len(line),i if is_motion else None,fraction if is_motion else None,marker if is_motion else None))
                            d.serial.write(encoded); self.started_motion=True; used+=len(encoded); self.rx_peak=max(self.rx_peak,used); mode=new_mode; pending=None
                            if i is not None:
                                self.sent=max(self.sent,i+1); self.last_sent_point=end
                                for identifier in marker['ids']:
                                    record=self.control_history[identifier-1]
                                    if record['state']=='requested': self.control_update(record,'transmitted',programmed_feed=speed,programmed_s=power)
                    if now-last_report>=.1:
                        d.serial.write(b'?'); last_report=now
                    line=d.serial.readline().decode(errors='replace').strip()
                    if line:
                        d.observe(line); last_response=time.monotonic()
                        if line=='ok':
                            if not inflight: raise ValueError('Unerwartete GRBL-Bestätigung.')
                            length,i,fraction,marker=inflight.popleft(); used-=length
                            last_ack=time.monotonic()
                            if marker and marker['ids']:
                                self.control_markers.append(marker)
                                for identifier in marker['ids']:
                                    record=self.control_history[identifier-1]
                                    if record['state'] in ('requested','transmitted'): self.control_update(record,'accepted')
                            if i is not None and fraction>=1: self.accepted=max(self.accepted,i+1)
                        elif line.startswith('error:'): raise ValueError(line)
                        elif line.startswith('<') and line.endswith('>'):
                            status=self.parse_status(line); self.sample(status)
                            if status['state'] not in ('Run','Idle','Hold:0','Hold:1'): raise ValueError('Unerwarteter Zustand: '+status['state'])
                            # Accepted commands are not reported as physically complete.
                            if status['state']=='Idle' and self.state=='pausing' and not inflight: self.state='paused'
                            self.controls()
                    if exhausted and pending is not None and not inflight:
                        # Tail M5 could not fit in the previous receive window.
                        continue
                    if exhausted and pending is None and not inflight and not self.aborted:
                        status=d.status(); self.sample(status)
                        if status['state']=='Idle':
                            if math.dist(d.position(status),self.job.segments[-1].end)>.05: raise ValueError('Auftragsziel nicht bestätigt.')
                            self.done=len(self.job.segments); self.completed_fraction=self.done
                            # All geometry completed; status sampling undercounts curved paths.
                            self.distance=math.dist(start,self.job.segments[0].end)+sum(math.dist(s.start,s.end) for s in self.job.segments[1:])
                            self.state='returning'; self.emit()
                            d.return_to_origin(self.sample)
                            break
                    if now-last_emit>=.15: self.emit(); last_emit=now
                    if time.monotonic()-last_response>4: raise TimeoutError('Keine Controllerantwort während des Auftrags.')
                    if self.state in ('paused','pausing','resuming'): last_ack=time.monotonic()
                    elif inflight and time.monotonic()-last_ack>20: raise TimeoutError('GRBL bestätigt keine weiteren Befehle.')
                    battery=battery_status()
                    if battery.ac is False and battery.percent is not None and battery.percent<=15 and self.state=='running': self.request('pause')
                self.finish_controls(not self.aborted)
                self.last_power=0.; self._finish_time=time.monotonic()
                self.state='aborted' if self.aborted else 'finished'; self.emit()
        except Exception as ex:
            if self.started_motion: d.emergency_stop()
            self.finish_controls(False)
            self.last_power=0.; self._finish_time=time.monotonic(); self.state='failed'; self.emit(ex)
