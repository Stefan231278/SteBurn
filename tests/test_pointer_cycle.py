import unittest
from contextlib import nullcontext
from test_streaming import Firmware,device
from steburn.core.model import Project,Shape
from steburn.core.planner import build_plan
from steburn.core.jobs import snapshot
from steburn.core.streaming import JobRun

class DeceleratingFirmware(Firmware):
    """Models non-instant JogCancel and rejects premature normal G-code."""
    def __init__(self): super().__init__(); self.remaining=0; self.cancels=0; self.premature=[]
    def write(self,data):
        if data==b'\x85':
            self.writes.append(data); self.cancels+=1; self.remaining=3; self.state='Jog'; return
        if data==b'?' and self.remaining:
            self.remaining-=1; self.state='Jog' if self.remaining else 'Idle'
        if self.state=='Jog' and data.startswith((b'M5',b'S0',b'G1',b'$G',b'$#')):
            self.premature.append(data); self.writes.append(data); self.push('error:9'); return
        super().write(data)
        if data.startswith(b'$J='): self.state='Jog'; self.remaining=2

class PointerCycleTests(unittest.TestCase):
    def test_two_repositioned_frames_then_job_without_homing_or_reset(self):
        d=device(); d.serial=DeceleratingFirmware()
        d.serial.on_jog=d.stop_frame
        for x in (20,100):
            d.frame_loop([(x,20),(x+50,20),(x+50,70),(x,70),(x,20)],400,400)
            self.assertTrue(d.homed and d.origin_confirmed)
        self.assertEqual(d.serial.cancels,2); self.assertEqual(d.serial.premature,[])
        p=Project(); p.shapes=[Shape('rect',100,20,50,50,p.layers[1].id)]
        r=JobRun(d,snapshot(build_plan(p,preview=False)),400,400,lambda e:None,awake_factory=nullcontext); r.run()
        self.assertEqual(r.state,'finished'); self.assertEqual(d.serial.homes,0); self.assertNotIn(b'\x18',d.serial.writes)
    def test_stop_request_does_not_write_from_ui_thread(self):
        d=device(); d.stop_frame(); self.assertTrue(d.frame_stop.is_set()); self.assertEqual(d.serial.writes,[])
    def test_pointer_light_is_finite_pulse_and_last_position_confirmed(self):
        d=device(); d.settings[31]=0
        d.pointer_move((80,120),400,400,visible=True,power=.1)
        self.assertIn(b'M3 S1\nG4 P0.15\nM5\n',d.serial.writes)
        self.assertEqual(d.last_position,(80,120)); self.assertTrue(d.homed and d.origin_confirmed)
        self.assertEqual(d.serial.power,0)
    def test_pointer_without_light_never_sends_m3(self):
        d=device(); d.pointer_move((80,120),400,400)
        self.assertNotIn(b'M3',b''.join(d.serial.writes)); self.assertEqual(d.last_position,(80,120))
    def test_pointer_rejects_high_power_and_outside_target_without_motion(self):
        for point,power in (((80,120),1),((0,0),.1)):
            d=device(); d.settings[31]=0
            with self.assertRaises(ValueError): d.pointer_move(point,400,400,visible=True,power=power)
            self.assertFalse(any(b'$J=' in line or b'M3' in line for line in d.serial.writes))
