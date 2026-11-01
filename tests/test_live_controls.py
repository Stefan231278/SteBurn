import unittest
from contextlib import nullcontext
from test_streaming import device
from steburn.core.model import Project,Shape
from steburn.core.jobs import snapshot
from steburn.core.planner import build_plan
from steburn.core.streaming import JobRun

class LiveControlTests(unittest.TestCase):
    def runner(self):
        p=Project(); p.shapes=[Shape('rect',20,20,15,15,p.layers[1].id)]
        d=device(); events=[]; r=JobRun(d,snapshot(build_plan(p,preview=False)),400,400,events.append,awake_factory=nullcontext)
        return d,r,events
    def test_changes_have_ack_and_execution_confirmation(self):
        d,r,events=self.runner(); r.request(('speed',1450/60)); r.request(('power',65)); r.run()
        self.assertEqual(r.state,'finished')
        records=r.statistics()['adjustments']; self.assertEqual(len(records),2)
        for record in records:
            self.assertEqual(record['state'],'active'); self.assertLessEqual(record['requested_at'],record['transmitted_at']); self.assertLessEqual(record['transmitted_at'],record['accepted_at']); self.assertLessEqual(record['accepted_at'],record['active_at'])
        self.assertTrue(any(b'F1450.000 S650' in data for data in d.serial.writes))
        self.assertTrue(any(e.get('control_event',{}).get('state')=='accepted' for e in events))
    def test_ack_alone_is_not_reported_as_active(self):
        d,r,events=self.runner(); r.change_parameter('power',65)
        record=r.control_history[0]; r.control_update(record,'transmitted'); r.control_update(record,'accepted')
        self.assertEqual(record['state'],'accepted'); self.assertNotIn('active_at',record)
        r.finish_controls(False); self.assertEqual(record['state'],'unconfirmed')
    def test_superseded_unsent_requests_are_not_falsely_confirmed(self):
        d,r,events=self.runner(); r.request(('power',65)); r.request(('power',70)); r.run()
        self.assertEqual(r.control_history[0]['state'],'not_applied'); self.assertEqual(r.control_history[1]['state'],'active')
    def test_visible_frame_is_m4_low_power_and_off_at_end(self):
        d=device(); d.settings[31]=0; n=[0]
        def stop():
            n[0]+=1
            if n[0]==3: d.stop_frame()
        d.serial.on_jog=stop
        d.frame_loop([(10,10),(30,10),(30,30),(10,30),(10,10)],400,400,visible=True,low_power=.1)
        output=b''.join(d.serial.writes)
        self.assertIn(b'G1 M4 S1\n',output); self.assertNotIn(b'M3',output)
        self.assertEqual(d.serial.power,0); self.assertTrue(d.homed and d.origin_confirmed)
        self.assertLess(output.index(b'$J='),output.index(b'G1 M4'))
    def test_visible_frame_never_automatically_boosts_unrepresentable_power(self):
        d=device(); d.settings[31]=0; d.settings[30]=255
        with self.assertRaises(ValueError): d.frame_loop([(10,10),(30,10)],400,400,visible=True,low_power=.1)
        self.assertNotIn(b'M4',b''.join(d.serial.writes))
        with self.assertRaises(ValueError): d.configure_frame_light(True,.51)
    def test_frame_light_can_be_switched_off_without_reference_loss(self):
        d=device(); d.settings[31]=0; n=[0]; powers=[]
        def change():
            n[0]+=1; powers.append(d.serial.power)
            if n[0]==2: d.configure_frame_light(False,.1)
            if n[0]==4: d.stop_frame()
        d.serial.on_jog=change
        d.frame_loop([(10,10),(30,10),(30,30),(10,30),(10,10)],400,400,visible=True,low_power=.1)
        self.assertEqual(powers[:3],[0,1,0]); self.assertTrue(d.homed and d.origin_confirmed)
        self.assertNotIn(b'\x18',d.serial.writes)
