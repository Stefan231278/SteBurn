"""Immutable plans, laser-off test runs and explicit laser-enabled jobs."""
import hashlib,json,math,queue,time
from dataclasses import dataclass,asdict
from steburn.platform.power import Awake,battery_status

@dataclass(frozen=True)
class JobSnapshot:
    segments: tuple
    fingerprint: str
    duration: float

def snapshot(plan):
    if not plan.exact: raise ValueError('Vereinfachte Vorschau ist kein ausführbarer Plan.')
    if not plan.segments: raise ValueError('Kein Bearbeitungsweg')
    values=[asdict(s) for s in plan.segments]
    for segment in plan.segments:
        if not all(math.isfinite(v) for v in (*segment.start,*segment.end,segment.speed,segment.power)) or segment.speed<=0 or not 0<=segment.power<=100: raise ValueError('Ungültiges Segment')
    raw=json.dumps(values,sort_keys=True,separators=(',',':'),allow_nan=False)
    return JobSnapshot(tuple(plan.segments),hashlib.sha256(raw.encode()).hexdigest(),plan.duration)

def resume_index(job,percent):
    """Explicit time-based segment boundary, never a claim of physical completion."""
    if not math.isfinite(percent) or not 0<=percent<100: raise ValueError('Startprozent muss 0 bis unter 100 betragen')
    target=job.duration*percent/100; elapsed=0.
    for i,s in enumerate(job.segments):
        if elapsed+s.duration>target: return i,100*elapsed/max(job.duration,1e-12)
        elapsed+=s.duration
    return 0,0.

class DryRun:
    """Single reader. UI queues requests; raw bytes are sent by worker only.

    Laser output requires laser_enabled=True; test runs remain laser-off.
    """
    def __init__(self,device,job,width,height,notify,awake_factory=Awake,laser_enabled=False):
        self.device=device; self.job=job; self.width=width; self.height=height
        self.notify=notify; self.requests=queue.Queue(); self.state='ready'
        self.awake_factory=awake_factory; self.feed=100; self.power=100; self.done=0; self.index=0
        self.laser_enabled=laser_enabled
    def request(self,action): self.requests.put(action)
    def emit(self,status=None):
        self.notify({'state':self.state,'completed':self.done,'total':len(self.job.segments),
                     'feed':self.feed,'power':self.power,'status':status or {}})
    def controls(self,status):
        while not self.requests.empty():
            action=self.requests.get_nowait()
            if isinstance(action,tuple) and action[0] in ('feed','power'):
                name,target=action
                if not isinstance(target,(int,float)) or not math.isfinite(target) or not 10<=target<=200:
                    continue
                values=status.get('Ov','').split(',')
                current=int(values[0 if name=='feed' else 2]) if len(values)==3 else getattr(self,name)
                delta=round(target)-current
                coarse,small=divmod(abs(delta),10)
                codes=((0x91,0x93) if delta>0 else (0x92,0x94)) if name=='feed' else ((0x9a,0x9c) if delta>0 else (0x9b,0x9d))
                for _ in range(coarse): self.device.realtime(codes[0])
                for _ in range(small): self.device.realtime(codes[1])
                continue
            if action=='stop': self.device.emergency_stop(); raise ValueError('Auftrag abgebrochen; Referenzfahrt erforderlich')
            if action=='pause': self.device.realtime(0x21); self.state='pausing'
            if action=='resume':
                if status.get('state')!='Hold:0': continue
                self.device.realtime(0x7e); self.state='resuming'
            if action in {'f+','f-','f0','p+','p-','p0'}:
                code={'f+':0x91,'f-':0x92,'f0':0x90,'p+':0x9a,'p-':0x9b,'p0':0x99}[action]
                self.device.realtime(code)
    def run(self):
        d=self.device; engaged=False
        try:
            d.check_targets([s.end for s in self.job.segments],self.width,self.height)
            d.ready(self.width,self.height)
            if any(abs(v)>.001 for v in d.read_work_offset()): raise ValueError('Testlauf benötigt Nullversatz.')
            modal=d.command('$G')
            if not any(' G54 ' in ' '+v+' ' for v in modal): raise ValueError('Testlauf benötigt G54.')
            with self.awake_factory():
                engaged=True
                d.command('M5'); d.command('S0'); d.command('G21 G90 G94')
                d.realtime(0x90); d.realtime(0x99)
                if self.laser_enabled: d.command('M4 S0')
                self.state='running'; self.emit()
                for i,s in enumerate(self.job.segments):
                    self.index=i
                    speed=s.speed if self.laser_enabled else min(s.speed,600.)
                    power=math.floor(d.settings[30]*s.power/100) if self.laser_enabled else 0
                    d.command(f'G1 X{s.end[0]:.4f} Y{s.end[1]:.4f} F{speed:.3f} S{power}')
                    last=time.monotonic(); status={}; idle_since=None
                    while True:
                        self.controls(status)
                        status=d.status(); state=status['state']
                        if 'Ov' in status:
                            ov=[int(v) for v in status['Ov'].split(',')]
                            if len(ov)==3: self.feed,self.power=ov[0],ov[2]
                        if state=='Hold:0': self.state='paused'
                        elif state=='Hold:1': self.state='pausing'
                        elif state=='Run': self.state='running'
                        elif state=='Idle':
                            values=[float(v) for v in status.get('MPos','').split(',') if v]
                            if len(values)<2 or not all(math.isfinite(v) for v in values): raise ValueError('Maschinenposition fehlt')
                            if math.dist(values[:2],s.end)<=.05:
                                self.state='running'; break
                            if idle_since is None: idle_since=time.monotonic()
                            if time.monotonic()-idle_since>2: raise ValueError('Stillstand vor Segmentziel; Position prüfen')
                        else: raise ValueError('Unerwarteter Zustand: '+state)
                        self.emit(status)
                        battery=battery_status()
                        if battery.ac is False and battery.percent is not None and battery.percent<=15 and state=='Run':
                            d.realtime(0x21); self.state='pausing'; self.notify({'battery_warning':battery.percent})
                        # A bounded no-motion response timeout is handled by status().
                        # A segment may be held indefinitely, while the worker keeps Windows awake.
                        if state=='Run' and time.monotonic()-last>max(120,s.duration*20): raise TimeoutError('Bewegung dauert unerwartet lange')
                        if state.startswith('Hold'): last=time.monotonic()
                        time.sleep(.1)
                    self.done=i+1; self.emit(status)
                engaged=True
                d.command('M5'); d.realtime(0x90); d.realtime(0x99)
                self.state='finished'; self.emit()
        except Exception as ex:
            if engaged: d.emergency_stop()
            self.state='failed'; self.notify({'state':'failed','error':str(ex)})
