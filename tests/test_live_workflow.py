import unittest
from unittest.mock import Mock,patch
from steburn.devices.grbl import GrblSession
from steburn.core.jobs import DryRun,snapshot
from steburn.core.planner import Plan,Segment
from contextlib import nullcontext

class WorkflowTests(unittest.TestCase):
    def test_connect_homes_after_identification(self):
        d=GrblSession(); calls=[]
        d.connect=lambda *args:calls.append('connect')
        d.home=lambda:calls.append('home')
        d.connect_and_home('COM5',115200)
        self.assertEqual(calls,['connect','home'])
    def test_home_sets_and_verifies_zero(self):
        d=GrblSession(); d.settings={22:1}; d.command=Mock(return_value=[])
        d.status=lambda:{'state':'Idle','MPos':'0,0,0'}
        d.read_work_offset=lambda:[0,0,0]
        d.home()
        self.assertTrue(d.homed and d.origin_confirmed)
        self.assertIn(unittest.mock.call('G10 L2 P1 X0 Y0 Z0'),d.command.call_args_list)
    def test_bad_offset_prevents_release(self):
        d=GrblSession(); d.settings={22:1}; d.command=Mock()
        d.status=lambda:{'state':'Idle','MPos':'0,0,0'}
        d.read_work_offset=lambda:[5,0,0]
        with self.assertRaises(ValueError): d.home()
        self.assertFalse(d.origin_confirmed)
    def test_frame_repeats_until_stopped_without_beam(self):
        d=GrblSession(); calls=[]
        d.ready=Mock(return_value=[0,0]); d.read_work_offset=lambda:[0,0,0]; d.realtime=Mock()
        position=[10,10]
        d.status=lambda:{'state':'Idle','MPos':f'{position[0]},{position[1]},0'}
        def command(line):
            calls.append(line)
            if line.startswith('$J='):
                import re
                position[:]=[float(re.search(axis+r'([-+\d.]+)',line)[1]) for axis in ('X','Y')]
            if sum(v.startswith('$J=') for v in calls)==15: d.frame_stop.set()
            return []
        d.command=command
        d.frame_loop([(10,10),(20,10),(20,20),(10,20),(10,10)],400,400)
        self.assertEqual(sum(v.startswith('$J=') for v in calls),15)
        self.assertFalse(any(v.startswith(('M3','M4')) for v in calls))
    def test_laser_power_scaling_and_travel_off(self):
        d=Mock(); d.settings={30:1000}; d.read_work_offset.return_value=[0,0,0]
        d.command.side_effect=lambda line:['[GC:G0 G54 G21 G90]'] if line=='$G' else []
        d.status.side_effect=[{'state':'Idle','MPos':'10,10,0'},{'state':'Idle','MPos':'20,10,0'}]
        plan=Plan([Segment((0,0),(10,10),3000,0,'a'),Segment((10,10),(20,10),1200,25,'a')],[])
        runner=DryRun(d,snapshot(plan),400,400,lambda _:None,awake_factory=nullcontext,laser_enabled=True)
        runner.run()
        self.assertEqual(runner.state,'finished')
        commands=[c.args[0] for c in d.command.call_args_list]
        self.assertIn('M4 S0',commands)
        self.assertIn('G1 X10.0000 Y10.0000 F3000.000 S0',commands)
        self.assertIn('G1 X20.0000 Y10.0000 F1200.000 S250',commands)
        self.assertEqual(commands[-1],'M5')
