import unittest,tempfile,math
from pathlib import Path
from copy import deepcopy
from unittest.mock import Mock
from steburn.core.model import Project,Shape
from steburn.core.paths import shape_paths,bounds,transform,text_paths
from steburn.core.design import set_bezier,cubic_points,split_cubic
from steburn.core.resize import resize_shape
from steburn.core.materials import MaterialLibrary,apply_preset,validate_preset
from steburn.core.jobs import DryRun,snapshot
from steburn.core.planner import build_plan,Plan,Segment

class DesignTests(unittest.TestCase):
    def curve(self):
        return set_bezier(Shape('polyline',layer='l'),[(10,10),(10,40),(40,40),(40,10)])
    def test_cubic_endpoints_and_midpoint(self):
        points=cubic_points([(0,0),(0,30),(30,30),(30,0)])
        self.assertEqual(points[0],(0,0)); self.assertEqual(points[-1],(30,0))
        self.assertTrue(any(math.dist(p,(15,22.5))<1e-10 for p in points))
    def test_split_preserves_curve(self):
        nodes=[(0,0),(0,30),(30,30),(30,0)]
        split=split_cubic(nodes,0)
        from shapely.geometry import LineString
        self.assertLess(LineString(cubic_points(nodes)).hausdorff_distance(LineString(cubic_points(split))),.041)
        self.assertEqual(len(split),7)
    def test_rounded_rect_changes_toolpath_and_bounds(self):
        p=Project(); s=Shape('rect',10,10,40,20,p.layers[1].id,extra={'corner_radius':4}); p.shapes=[s]
        pts=shape_paths(s)[0]; self.assertGreater(len(pts),12)
        self.assertEqual(pts[0],pts[-1]); self.assertNotIn((10,10),pts)
        self.assertEqual(bounds([s]),(10,10,50,30)); self.assertTrue(build_plan(p).segments)
    def test_curve_roundtrip_and_resize_keep_controls(self):
        p=Project(); s=self.curve(); s.layer=p.layers[1].id; p.shapes=[s]
        q=Project.from_dict(p.to_dict()); self.assertEqual(shape_paths(s),shape_paths(q.shapes[0]))
        r=resize_shape(s,'ne',(70,70),False); self.assertIn('bezier',r.extra)
        transform(r,'mirror_x'); self.assertIn('bezier',r.extra)
    def test_invalid_design_data_rejected(self):
        p=Project(); s=Shape('rect',layer=p.layers[0].id); p.shapes=[s]
        s.extra['corner_radius']=float('nan')
        with self.assertRaises(ValueError): p.validate()
        s.extra={'bezier':[[0,0]]}
        with self.assertRaises(ValueError): p.validate()
    def test_multiline_tracking_and_alignment(self):
        original=text_paths('AB',12)
        tracked=text_paths('AB',12,tracking=2)
        extent=lambda paths:max(x for p in paths for x,y in p)-min(x for p in paths for x,y in p)
        self.assertAlmostEqual(extent(tracked)-extent(original),2)
        lines=text_paths('AB\nA',12,align='right')
        self.assertGreater(max(y for p in lines for x,y in p),12)
        left=text_paths('AB\nA',12,align='left'); self.assertNotEqual(lines,left)

class MaterialTests(unittest.TestCase):
    def preset(self): return dict(name='Eigene Probe 3 mm',material='Holz',thickness=3,speed=900,power=25,passes=2,interval=.15,air=True,mode='Kontur',operation='cut')
    def test_library_persists_and_project_embeds_preset(self):
        with tempfile.TemporaryDirectory() as tmp:
            library=MaterialLibrary(Path(tmp)/'materials.json'); preset=self.preset()
            library.write({preset['name']:preset}); self.assertEqual(library.read()[preset['name']],preset)
            p=Project(); q=apply_preset(p,preset,p.layers[0].id)
            self.assertEqual(q.layers[0].speed,900); self.assertEqual(p.layers[0].speed,1200)
            r=Project.from_dict(q.to_dict()); self.assertEqual(r.extensions['materials'][preset['name']],preset)
    def test_selection_scope_and_locked_objects(self):
        p=Project(); a=Shape('rect',10,10,10,10,p.layers[0].id); b=deepcopy(a); b.id='b'; b.extra['locked']=True; p.shapes=[a,b]
        q=apply_preset(p,self.preset(),p.layers[0].id,{a.id,b.id})
        self.assertEqual(q.shapes[0].extra['processing']['power'],25)
        self.assertNotIn('processing',q.shapes[1].extra); self.assertEqual(q.layers[0].power,20)
    def test_invalid_profile_rejected(self):
        p=self.preset(); p['power']=101
        with self.assertRaises(ValueError): validate_preset(p)

class CockpitOverrideTests(unittest.TestCase):
    def runner(self):
        d=Mock(); plan=Plan([Segment((0,0),(10,10),1200,20,'a')],[])
        return d,DryRun(d,snapshot(plan),400,400,lambda _:None)
    def test_absolute_override_uses_confirmed_status(self):
        d,r=self.runner(); r.request(('feed',125)); r.request(('power',85)); r.controls({'Ov':'110,100,100'})
        values=[c.args[0] for c in d.realtime.call_args_list]
        self.assertEqual(values,[0x91]+[0x93]*5+[0x9b]+[0x9d]*5)
    def test_out_of_range_override_sends_nothing(self):
        d,r=self.runner()
        for target in (0,201,float('nan')): r.request(('feed',target))
        r.controls({}); d.realtime.assert_not_called()
