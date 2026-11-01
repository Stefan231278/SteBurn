import unittest
from steburn.devices.grbl import GrblSession
class OffsetTests(unittest.TestCase):
    def device(self,modal='[GC:G0 G54 G17 G21 G90 G94 M5 M9 T0 F0 S0]',offset='[G54:0.000,0.000,0.000]',g92='[G92:0.000,0.000,0.000]'):
        dev=GrblSession(); dev.origin_confirmed=True; dev.homed=True; dev.settings={20:1,21:1,22:1,13:0,30:1000,32:1,130:400,131:400}
        dev.status=lambda:{'state':'Idle','MPos':'0.000,0.000,0.000'}
        dev.command=lambda cmd:[modal] if cmd=='$G' else [offset,g92]
        return dev
    def test_actual_atomstack_response(self): self.assertEqual(self.device().ready(400,400),[0,0])
    def test_active_wcs_and_g92(self):
        dev=self.device('[GC:G0 G55 G17 G21 G90]', '[G55:10,20,0]', '[G92:1,2,0]'); dev.status=lambda:{'state':'Idle','MPos':'16,27,0'}
        self.assertEqual(dev.ready(400,400),[5,5])
    def test_missing_offset_blocks(self):
        dev=self.device(offset='[G55:0,0,0]')
        with self.assertRaises(ValueError): dev.ready(400,400)
    def test_unknown_active_wcs_blocks(self):
        dev=self.device(modal='[GC:G0 G54.1 G21]')
        with self.assertRaises(ValueError): dev.ready(400,400)
    def test_nonfinite_blocks(self):
        dev=self.device(offset='[G54:nan,0,0]')
        with self.assertRaises(ValueError): dev.ready(400,400)
    def test_fresh_status_required(self):
        dev=self.device(); statuses=iter([{'state':'Idle','MPos':'0,0,0'},{'state':'Run','MPos':'0,0,0'}]); dev.status=lambda:next(statuses)
        with self.assertRaises(ValueError): dev.ready(400,400)
