import unittest, tempfile
from pathlib import Path
from steburn.core.model import Project,Shape,History
from steburn.core.geometry import checks
from steburn.io.svg import export_svg,import_svg
from steburn.core.extensions import Registry,Command
class CoreTests(unittest.TestCase):
    def project(self):
        p=Project(); p.shapes.append(Shape('rect',10,20,30,40,p.layers[0].id)); return p
    def test_roundtrip(self):
        p=self.project(); p.extensions['future']={'arbitrary':[1,2]}; p.shapes[0].extra={'future':True}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.steburn'; p.save(path); self.assertEqual(p.to_dict(),Project.load(path).to_dict())
    def test_invalid_numbers(self):
        p=self.project(); p.shapes[0].x=float('nan')
        with self.assertRaises(ValueError): p.validate()
    def test_power(self):
        p=self.project(); p.layers[0].power=101
        with self.assertRaises(ValueError): p.validate()
    def test_future_schema(self):
        d=self.project().to_dict(); d['schema']=99
        with self.assertRaises(ValueError): Project.from_dict(d)
    def test_undo_redo(self):
        p=self.project(); h=History(); h.checkpoint(p); p.shapes[0].x=50; p=h.undo(p); self.assertEqual(p.shapes[0].x,10); p=h.redo(p); self.assertEqual(p.shapes[0].x,50)
    def test_new_change_clears_redo(self):
        p=self.project(); h=History(); h.checkpoint(p); p=h.undo(p); h.checkpoint(p); self.assertFalse(h.redo_stack)
    def test_bounds(self):
        p=self.project(); p.shapes[0].x=390; self.assertTrue(any('außerhalb' in s for s in checks(p)))
    def test_duplicate(self):
        p=self.project(); p.shapes.append(Shape('rect',10,20,30,40,p.layers[0].id)); self.assertTrue(any('mehrfach' in s for s in checks(p)))
    def test_svg_scale(self):
        p=self.project()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.svg'; export_svg(p,path); s=import_svg(path,p.layers[0].id)[0]; self.assertEqual((s.x,s.y,s.w,s.h),(10,20,30,40))
    def test_svg_rejects_path(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.svg'; path.write_text('<svg width="10mm" height="10mm" viewBox="0 0 10 10"><path d="M0 0L1 1"/></svg>')
            with self.assertRaises(ValueError): import_svg(path,'x')
    def test_svg_rejects_transforms(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.svg'; path.write_text('<svg width="10mm" height="10mm" viewBox="0 0 10 10"><g transform="scale(2)"/></svg>')
            with self.assertRaises(ValueError): import_svg(path,'x')
    def test_registry(self):
        r=Registry(); c=Command('a','A',lambda:None); r.register(c)
        with self.assertRaises(ValueError): r.register(c)
if __name__=='__main__': unittest.main()
