import unittest,tempfile,csv,json
from pathlib import Path
from dataclasses import replace
from steburn.core.material_test import TestSpec,generate,save_session,export_results,label_project,export_assignment
from steburn.core.paths import bounds,shape_paths
from steburn.core.planner import build_plan

class MaterialCalibrationTests(unittest.TestCase):
    def spec(self): return TestSpec('Eigene Probe',3,(5,10,15,20,25),(500,1000,1500),(1000,1500,2000))
    def test_exact_fifty_mm_outline_and_thirty_cells(self):
        p=generate(self.spec()); self.assertEqual(bounds(p.shapes),(20,20,70,70))
        cells=p.extensions['material_test']['cells']; self.assertEqual(len(cells),30)
        self.assertEqual(sum(c['operation']=='cut' for c in cells),15)
        self.assertEqual(sum(c['operation']=='engrave' for c in cells),15)
    def test_repeatable_geometry_and_unique_experiment_id(self):
        a,b=generate(self.spec()),generate(self.spec())
        self.assertEqual([shape_paths(s) for s in a.shapes],[shape_paths(s) for s in b.shapes])
        self.assertEqual(a.extensions['material_test']['pattern_hash'],b.extensions['material_test']['pattern_hash'])
        self.assertNotEqual(a.extensions['material_test']['id'],b.extensions['material_test']['id'])
    def test_grid_values_match_each_generated_shape(self):
        p=generate(self.spec()); spec=p.extensions['material_test']
        for cell in spec['cells']:
            s=next(s for s in p.shapes if s.extra.get('material_cell')==cell['id'])
            for key in ('power','speed','passes','operation'): self.assertEqual(s.extra['processing'][key],cell[key])
    def test_engraving_before_cutting_and_outline_not_cut(self):
        p=generate(self.spec()); plan=build_plan(p,preview=False)
        operations=[s.operation for s in plan.segments if s.power>0]
        self.assertLess(operations.index('engrave'),operations.index('cut'))
        self.assertTrue(all(op=='cut' for op in operations[operations.index('cut'):]))
        self.assertEqual(p.shapes[0].extra['processing']['operation'],'mark')
    def test_invalid_ranges_and_position_rejected(self):
        for s in (replace(self.spec(),powers=(10,20)),replace(self.spec(),cut_speeds=(1,2,3)),replace(self.spec(),x=0),replace(self.spec(),powers=(5,10,15,20,101))):
            with self.assertRaises(ValueError): generate(s)
    def test_measured_results_persist_and_export(self):
        p=generate(self.spec()); session={'test':p.extensions['material_test'],'observations':{'C01':dict(depth_mm=1.25,cut_through=False,quality='Zu schwach',notes='gemessen')}}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'result.json'; save_session(path,session); self.assertEqual(json.loads(path.read_text())['observations']['C01']['depth_mm'],1.25)
            csvpath=Path(tmp)/'result.csv'; export_results(csvpath,session)
            with csvpath.open(encoding='utf-8-sig') as file: rows=list(csv.DictReader(file,delimiter=';'))
            self.assertEqual(len(rows),30); self.assertEqual(next(r for r in rows if r['id']=='C01')['depth_mm'],'1.25')
    def test_scaled_and_positioned_coupon_matches_matrix_geometry(self):
        original=generate(self.spec()); p=generate(replace(self.spec(),x=100,y=150,size=100))
        self.assertEqual(bounds(p.shapes),(100,150,200,250))
        self.assertEqual(p.extensions['material_test']['size_mm'],[100,100])
        for a,b in zip(original.extensions['material_test']['cells'],p.extensions['material_test']['cells']):
            self.assertAlmostEqual(b['x'],100+2*(a['x']-20)); self.assertAlmostEqual(b['y'],150+2*(a['y']-20))
            self.assertEqual(b['w'],a['w']*2); self.assertEqual(b['power'],a['power']); self.assertEqual(b['speed'],a['speed'])
        for cell in p.extensions['material_test']['cells']:
            shape=next(s for s in p.shapes if s.extra.get('material_cell')==cell['id'])
            self.assertEqual(bounds([shape]),(cell['x'],cell['y'],cell['x']+cell['w'],cell['y']+cell['h']))
    def test_readable_labels_larger_and_legacy_pattern_still_reproducible(self):
        new=generate(self.spec()); old=generate(self.spec(),pattern_version=1)
        label=lambda p:next(s for s in p.shapes if s.name=='cut Vorschub 500')
        self.assertAlmostEqual(label(new).h,1.8); self.assertAlmostEqual(label(old).h,1.25)
        self.assertNotEqual(shape_paths(label(new)),shape_paths(label(old)))
        self.assertNotIn('size',old.extensions['material_test']['spec'])
        self.assertEqual(old.extensions['material_test']['pattern_version'],1)
    def test_size_and_scaled_boundary_rejected(self):
        for spec in (replace(self.spec(),size=49),replace(self.spec(),size=301),replace(self.spec(),size=100,x=300)):
            with self.assertRaises(ValueError): generate(spec)
    def test_label_probe_only_contains_labels_and_constant_power(self):
        p=generate(self.spec()); probe=label_project(p)
        self.assertEqual(probe.extensions['material_test']['phase'],'labels_only')
        self.assertNotIn('phase',p.extensions['material_test'])
        self.assertFalse(any(s.extra.get('material_cell') for s in probe.shapes))
        plan=build_plan(probe,preview=False)
        lettering=[s for s in plan.segments if s.power>0 and s.constant_power]
        self.assertTrue(lettering); self.assertTrue(all(s.operation=='mark' for s in lettering))
        self.assertTrue(all(s.power==self.spec().label_power for s in lettering))
    def test_historical_patterns_retain_dynamic_marking(self):
        for version in (1,2):
            plan=build_plan(generate(self.spec(),pattern_version=version),preview=False)
            self.assertFalse(any(s.constant_power for s in plan.segments))
    def test_assignment_can_be_exported_for_existing_unlabelled_test(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'map.png'; export_assignment(path,{'test':generate(self.spec(),pattern_version=2).extensions['material_test']})
            with Image.open(path) as image: self.assertEqual(image.size,(1400,1550))
