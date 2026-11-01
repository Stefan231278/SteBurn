import unittest
from unittest.mock import Mock,patch
from dataclasses import replace
from steburn.devices.grbl import GrblSession
from steburn.core.model import Project,Shape,Layer
from steburn.core.processing import resolve,area_paths
from steburn.core.planner import build_plan,Plan,Segment
from steburn.core.jobs import snapshot,resume_index,DryRun
from steburn.platform.power import Awake,battery_status

class FakeSerial:
    is_open=True
    def __init__(self,lines): self.lines=iter(lines); self.writes=[]
    def write(self,data): self.writes.append(data)
    def readline(self): return next(self.lines,b'')

class SafetyTests(unittest.TestCase):
    def device(self,lines):
        d=GrblSession(); d.serial=FakeSerial(lines); d.homed=True; d.origin_confirmed=True
        d.settings={13:0,20:1,21:1,22:1,30:1000,32:1,130:400,131:400}
        return d
    def test_reset_idle_zero_cannot_rearm(self):
        d=self.device([b"Grbl 1.1h ['$' for help]\n",b'<Idle|MPos:0,0,0|FS:0,0>\n'])
        with self.assertRaises(ValueError): d.status()
        self.assertFalse(d.homed); self.assertFalse(d.origin_confirmed)
        self.assertEqual(d.status()['state'],'Idle')
        with self.assertRaises(ValueError): d.ready(400,400)
    def test_reset_before_ok_fails_command(self):
        d=self.device([b'Grbl 1.1h\n',b'ok\n'])
        with self.assertRaises(ValueError): d.command('M5')
        self.assertFalse(d.homed)
    def test_alarm_before_status_latches(self):
        d=self.device([b'ALARM:3\n',b'<Idle|MPos:0,0,0>\n'])
        with self.assertRaises(ValueError): d.status()
        self.assertFalse(d.origin_confirmed)
    def test_timeout_invalidates(self):
        d=self.device([])
        with patch('steburn.devices.grbl.time.monotonic',side_effect=[0,3]):
            with self.assertRaises(TimeoutError): d.status()
        self.assertFalse(d.homed)
    def test_manual_confirmation_not_enough(self):
        d=self.device([]); d.homed=False
        with self.assertRaises(ValueError): d.ready(400,400)
    def test_softlimits_required(self):
        d=self.device([]); d.settings[20]=0
        with self.assertRaises(ValueError): d.ready(400,400)
    def test_target_inset_blocks_all_four_edges(self):
        d=self.device([])
        for pt in [(4,20),(396,20),(20,4),(20,396),(float('nan'),20)]:
            with self.assertRaises(ValueError): d.check_targets([pt],400,400)
        d.check_targets([(5,5),(395,395)],400,400)
        self.assertFalse(d.serial.writes)
    def test_home_requires_fresh_zero_idle(self):
        d=self.device([]); d.command=Mock(return_value=[]); d.status=lambda:{'state':'Idle','MPos':'44,0,0'}
        with self.assertRaises(ValueError): d.home()
        self.assertFalse(d.homed)
    def test_home_confirms_verified_zero_automatically(self):
        d=self.device([]); d.command=Mock(return_value=[]); d.status=lambda:{'state':'Idle','MPos':'0,0,0'}
        d.read_work_offset=lambda:[0,0,0]
        d.home(); self.assertTrue(d.homed); self.assertTrue(d.origin_confirmed)
    def test_direct_realtime_bytes(self):
        d=self.device([])
        for byte in (0x21,0x7e,0x91,0x90,0x9a,0x99): d.realtime(byte)
        self.assertEqual(d.serial.writes,[b'!',b'~',b'\x91',b'\x90',b'\x9a',b'\x99'])
    def test_reset_invalidates_before_write(self):
        d=self.device([]); d.emergency_stop()
        self.assertFalse(d.homed); self.assertTrue(d.cancelled.is_set()); self.assertEqual(d.serial.writes,[b'\x18'])

class ProcessingTests(unittest.TestCase):
    def shape(self):
        p=Project(); s=Shape('rect',10,10,20,20,p.layers[0].id); p.shapes=[s]; return p,s
    def test_object_override_does_not_change_sibling(self):
        p,s=self.shape(); other=Shape('rect',40,10,20,20,s.layer)
        s.extra['processing']={'operation':'engrave','power':37}
        self.assertEqual(resolve(s,p.layers[0]).power,37)
        self.assertEqual(resolve(other,p.layers[0]).power,20)
    def test_holes_remain_unfilled_with_rotation(self):
        from shapely.geometry import LineString,Point
        p,s=self.shape(); s.kind='polygon'; s.extra['contours']=[[(0,0),(20,0),(20,20),(0,20),(0,0)],[(5,5),(15,5),(15,15),(5,15),(5,5)]]
        s.extra['processing']={'operation':'engrave','angle':37,'interval':1}
        paths=area_paths(s,resolve(s,p.layers[0]))
        hole=Point(20,20).buffer(3)
        self.assertTrue(paths)
        self.assertFalse(any(LineString(path).intersects(hole) for path in paths))
    def test_open_shape_cannot_be_filled(self):
        p,s=self.shape(); s.kind='line'; s.extra['processing']={'operation':'engrave'}
        with self.assertRaises(ValueError): build_plan(p)
    def test_cross_has_more_paths(self):
        p,s=self.shape(); v=resolve(s,p.layers[0]); v=replace(v,operation='engrave',interval=1)
        self.assertEqual(len(area_paths(s,replace(v,fill='cross'))),2*len(area_paths(s,v)))
    def test_dots_are_short_paths(self):
        p,s=self.shape(); v=replace(resolve(s,p.layers[0]),operation='engrave',fill='dots',interval=1)
        import math
        self.assertTrue(all(math.dist(path[0],path[-1])<=.081 for path in area_paths(s,v)))
    def test_invalid_override_rejected_on_load(self):
        p,s=self.shape(); s.extra['processing']={'power':float('nan')}
        with self.assertRaises(ValueError): Project.from_dict(p.to_dict())
    def test_new_schema_preserves_overrides(self):
        p,s=self.shape(); s.extra['processing']={'operation':'engrave','fill':'cross','power':35}
        q=Project.from_dict(p.to_dict()); self.assertEqual(q.schema,4); self.assertEqual(q.shapes[0].extra,s.extra)
    def test_bitmap_cannot_silently_cut_frame(self):
        from PIL import Image
        from steburn.io.importers import image_shape
        p=Project(); s=image_shape(Image.new('RGB',(3,3)),p.layers[0].id,'image'); s.extra['processing']={'operation':'cut'}; p.shapes=[s]
        with self.assertRaises(ValueError): build_plan(p)
    def test_output_disabled_not_planned(self):
        p,s=self.shape(); p.layers[0].output=False; self.assertFalse(build_plan(p).segments)

class JobTests(unittest.TestCase):
    def plan(self): return Plan([Segment((0,0),(10,0),60,20,'a'),Segment((10,0),(20,0),60,20,'a')],[])
    def test_preview_not_executable(self):
        p=self.plan(); p.exact=False
        with self.assertRaises(ValueError): snapshot(p)
    def test_hash_changes_with_power(self):
        a=self.plan(); b=self.plan(); b.segments[0]=replace(b.segments[0],power=10)
        self.assertNotEqual(snapshot(a).fingerprint,snapshot(b).fingerprint)
    def test_percent_maps_back_to_segment_start(self): self.assertEqual(resume_index(snapshot(self.plan()),56),(1,50))
    def test_percent_invalid(self):
        for value in (-1,100,float('nan')):
            with self.assertRaises(ValueError): resume_index(snapshot(self.plan()),value)
    def test_resume_only_fully_held(self):
        device=Mock(); runner=DryRun(device,snapshot(self.plan()),400,400,lambda _:None)
        runner.request('resume'); runner.controls({'state':'Hold:1'}); device.realtime.assert_not_called()
        runner.request('resume'); runner.controls({'state':'Hold:0'}); device.realtime.assert_called_once_with(0x7e)
    def test_preflight_failure_does_not_reset_machine(self):
        device=Mock(); device.check_targets.side_effect=ValueError('out of bounds')
        events=[]; runner=DryRun(device,snapshot(self.plan()),400,400,events.append); runner.run()
        device.emergency_stop.assert_not_called(); self.assertEqual(events[-1]['state'],'failed')
    def test_wake_release_on_exception(self):
        kernel=Mock(); kernel.SetThreadExecutionState.return_value=1
        with self.assertRaises(ValueError):
            with Awake(kernel): raise ValueError('abort')
        self.assertEqual([v.args[0] for v in kernel.SetThreadExecutionState.call_args_list],[0x80000001,0x80000000])
    def test_wake_failure_blocks_start(self):
        kernel=Mock(); kernel.SetThreadExecutionState.return_value=0
        with self.assertRaises(OSError): Awake(kernel).acquire()
    def test_power_unknown_is_not_zero_battery(self):
        kernel=Mock()
        def fill(ptr):
            ptr._obj.ACLineStatus=255; ptr._obj.BatteryLifePercent=255; return 1
        kernel.GetSystemPowerStatus.side_effect=fill
        result=battery_status(kernel); self.assertIsNone(result.ac); self.assertIsNone(result.percent)

class RunnerIntegrationTests(unittest.TestCase):
    def runner(self,statuses):
        d=GrblSession(); d.serial=FakeSerial([]); d.ready=Mock(return_value=[0,0]); d.read_work_offset=lambda:[0,0,0]
        commands=[]
        def command(line):
            commands.append(line)
            return ['[GC:G0 G54 G21 G90]'] if line=='$G' else []
        d.command=command; values=iter(statuses); d.status=lambda:next(values)
        plan=Plan([Segment((0,0),(10,10),1200,50,'a')],[])
        kernel=Mock(); kernel.SetThreadExecutionState.return_value=1
        events=[]; run=DryRun(d,snapshot(plan),400,400,events.append,awake_factory=lambda:Awake(kernel))
        return run,d,commands,events,kernel
    def test_dryrun_never_enables_emission(self):
        run,d,commands,events,kernel=self.runner([{'state':'Run','MPos':'5,5,0','Ov':'110,100,110'},{'state':'Idle','MPos':'10,10,0'}])
        with patch('steburn.core.jobs.time.sleep'): run.run()
        self.assertEqual(run.state,'finished'); self.assertEqual(run.done,1)
        self.assertTrue(any('F600.000 S0' in c for c in commands))
        self.assertFalse(any(c.startswith(('M3','M4')) for c in commands))
        self.assertEqual(kernel.SetThreadExecutionState.call_args_list[-1].args,(0x80000000,))
    def test_disconnect_during_run_resets_and_releases_awake(self):
        run,d,commands,events,kernel=self.runner([])
        d.status=Mock(side_effect=OSError('USB getrennt'))
        run.run()
        self.assertEqual(run.state,'failed'); self.assertFalse(d.homed)
        self.assertIn(b'\x18',d.serial.writes)
        self.assertEqual(kernel.SetThreadExecutionState.call_args_list[-1].args,(0x80000000,))
    def test_failed_awake_prevents_movement(self):
        run,d,commands,events,kernel=self.runner([]); kernel.SetThreadExecutionState.return_value=0
        run.run()
        self.assertEqual(run.state,'failed'); self.assertFalse(any(c.startswith('G1 ') for c in commands))
    def test_low_battery_requests_hold(self):
        from steburn.platform.power import PowerStatus
        run,d,commands,events,kernel=self.runner([{'state':'Run','MPos':'5,5,0'},{'state':'Hold:0','MPos':'5,5,0'}])
        def notify(event):
            events.append(event)
            if event.get('state')=='paused': run.request('stop')
        run.notify=notify
        with patch('steburn.core.jobs.battery_status',return_value=PowerStatus(False,10)),patch('steburn.core.jobs.time.sleep'):
            run.run()
        self.assertIn(b'!',d.serial.writes); self.assertEqual(run.state,'failed')
