import unittest,re
from unittest.mock import patch
from collections import deque
from contextlib import nullcontext
from steburn.devices.grbl import GrblSession
from steburn.core.streaming import JobRun
from steburn.core.jobs import snapshot
from steburn.core.planner import build_plan
from steburn.core.model import Project,Shape

class Firmware:
    is_open=True
    def __init__(self):
        self.lines=deque(); self.writes=[]; self.position=[0.,0.]; self.state='Idle'; self.power=0; self.feed=1200; self.queries=0; self.homes=0; self.on_motion=None; self.on_jog=None
    def reset_input_buffer(self): self.lines.clear()
    def readline(self): return self.lines.popleft() if self.lines else b''
    def push(self,value): self.lines.append((value+'\n').encode())
    def write(self,data):
        self.writes.append(data)
        if data==b'?':
            self.queries+=1; self.push(f'<{self.state}|MPos:{self.position[0]},{self.position[1]},0|WCO:0,0,0|FS:{self.feed},{self.power}>'); return
        if data==b'!': self.state='Hold:0'; return
        if data==b'~': self.state='Run'; return
        if data==b'\x18': self.state='Idle'; self.power=0; self.lines.clear(); self.push('Grbl 1.1h'); return
        if data==b'\x85': self.state='Idle'; return
        if len(data)==1 and data[0]>=0x80: return
        for line in data.decode().splitlines():
            if line=='$G': self.push('[GC:G1 G54 G21 G90 G94 M5]')
            elif line=='$#': self.push('[G54:0,0,0]'); self.push('[G92:0,0,0]')
            elif line=='$H': self.homes+=1; self.position=[0.,0.]; self.state='Idle'
            elif line.startswith('M5'): self.power=0; self.state='Idle'
            elif line.startswith(('G1 ','G53 G1 ','$J=')):
                for key,i in [('X',0),('Y',1)]:
                    match=re.search(key+r'([-+\d.]+)',line)
                    if match: self.position[i]=float(match[1])
                match=re.search(r'S([\d.]+)',line)
                if match: self.power=float(match[1])
                match=re.search(r'F([\d.]+)',line)
                if match: self.feed=float(match[1])
                if line.startswith('$J=') and self.on_jog: self.on_jog()
                elif self.on_motion: self.on_motion()
            self.push('ok')

def device():
    d=GrblSession(); d.serial=Firmware(); d.homed=True; d.origin_confirmed=True
    d.settings={13:0,20:1,21:1,22:1,30:1000,32:1,130:400,131:400}
    return d

class StreamingTests(unittest.TestCase):
    def setup_job(self):
        p=Project(); s=Shape('text',20,20,80,12,p.layers[1].id,'Text','ABC'); p.shapes=[s]
        d=device(); events=[]; r=JobRun(d,snapshot(build_plan(p,preview=False)),400,400,events.append,awake_factory=nullcontext)
        return d,r,events
    def test_cut_text_streams_constant_power_and_returns_zero(self):
        d,r,events=self.setup_job(); r.run()
        self.assertEqual(r.state,'finished',events[-1]); self.assertEqual(d.serial.position,[0,0]); self.assertTrue(d.homed)
        lines=[line for data in d.serial.writes if data not in (b'?',b'\x90',b'\x99') for line in data.decode().splitlines()]
        self.assertTrue(any(line.startswith('M3') for line in lines))
        self.assertTrue(any(data.count(b'\n')>=2 for data in d.serial.writes))
        self.assertGreater(r.statistics()['distance_mm'],0)
        self.assertFalse(any(data==b'\x18' for data in d.serial.writes))
    def test_frame_stop_keeps_reference_and_position(self):
        d=device(); n=[0]
        def stop():
            n[0]+=1
            if n[0]==3: d.stop_frame()
        d.serial.on_jog=stop
        d.frame_loop([(10,10),(30,10),(30,30),(10,30),(10,10)],400,400)
        self.assertTrue(d.homed and d.origin_confirmed); self.assertEqual(d.last_position,(30,30))
        self.assertIn(b'\x85',d.serial.writes); self.assertNotIn(b'\x18',d.serial.writes)
        d.ready(400,400)
    def test_pause_resume_is_retained_until_fully_held(self):
        d,r,_=self.setup_job(); r.state='running'; r.last_status={'state':'Hold:1'}
        r.request('resume'); r.controls(); self.assertTrue(r.pending_resume)
        self.assertNotIn(b'~',d.serial.writes)
        r.last_status={'state':'Hold:0'}; r.controls(); self.assertIn(b'~',d.serial.writes); self.assertEqual(r.state,'resuming')
        self.assertEqual(d.serial.homes,0)
    def test_absolute_settings_include_zero_and_full_power(self):
        d,r,_=self.setup_job(); r.request(('speed',12.5)); r.request(('power',100)); r.controls()
        self.assertEqual(r.feed_target,750); self.assertEqual(r.power_target,100)
        chunks=r.chunks((0,0)); beam=next(c for c in chunks if c[4]>0); self.assertEqual(beam[4],1000)
        r.request(('power',0)); r.controls(); self.assertTrue(all(c[4]==0 for _,c in zip(range(40),chunks)))
    def test_abort_stops_then_homes_without_reconnect(self):
        d,r,events=self.setup_job(); triggered=[False]
        def stop():
            if not triggered[0]: triggered[0]=True; r.request('stop')
        d.serial.on_motion=stop; r.run()
        self.assertEqual(r.state,'aborted',events[-1]); self.assertEqual(d.serial.homes,1)
        self.assertTrue(d.homed and d.origin_confirmed); self.assertEqual(d.serial.position,[0,0])
    def test_new_home_recovers_cancelled_session_on_same_port(self):
        d=device(); serial=d.serial; d.emergency_stop(); d.home()
        self.assertIs(d.serial,serial); self.assertTrue(d.homed and d.origin_confirmed)
    def test_full_stream_pause_and_resume_completes(self):
        d,r,events=self.setup_job(); requested=[False]
        def pause():
            if not requested[0]: requested[0]=True; r.request('pause')
        def report(event):
            events.append(event)
            if event['state']=='paused': r.request('resume')
        d.serial.on_motion=pause; r.notify=report; r.run()
        self.assertEqual(r.state,'finished',events[-1]); self.assertIn(b'~',d.serial.writes)
        self.assertEqual(d.serial.homes,0)
    def test_alarm_never_automatically_returns_or_homes(self):
        d,r,events=self.setup_job(); fired=[False]
        def alarm():
            if not fired[0]: fired[0]=True; d.serial.push('ALARM:1')
        d.serial.on_motion=alarm; r.run()
        self.assertEqual(r.state,'failed'); self.assertEqual(d.serial.homes,0); self.assertFalse(d.homed)
    def test_energy_estimate_excludes_pause(self):
        d,r,_=self.setup_job(); r.nominal_watts=40; r.started=0
        with patch('steburn.core.streaming.time.monotonic',side_effect=[0,2,5]):
            r.sample({'state':'Run','MPos':'10,10,0','FS':'1200,500'})
            r.sample({'state':'Hold:0','MPos':'10,10,0','FS':'0,500'})
            stats=r.statistics()
        self.assertEqual(stats['energy_j'],40); self.assertEqual(stats['pause_seconds'],3)
    def test_receive_window_is_bounded(self):
        d,r,_=self.setup_job(); r.run(); self.assertLessEqual(r.rx_peak,96); self.assertGreater(r.rx_peak,50)
