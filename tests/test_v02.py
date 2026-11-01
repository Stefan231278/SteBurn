import unittest,tempfile,math
from pathlib import Path
from copy import deepcopy
from PIL import Image
from steburn.core.model import Project,Shape,Layer
from steburn.core.paths import shape_paths,bounds,transform,as_paths_shape,polygon_geometry
from steburn.core.planner import build_plan,fill_paths,rectangle_plan
from steburn.io.importers import import_file,export_svg,image_shape
from steburn.devices.grbl import GrblSession

class V02Tests(unittest.TestCase):
    def p(self):
        p=Project(); p.shapes=[Shape('rect',10,20,30,40,p.layers[0].id,'Test')]; return p
    def test_three_layers(self): self.assertEqual(len(Project().layers),3)
    def test_migrate_top_left(self):
        p=self.p(); d=p.to_dict(); d['schema']=1; q=Project.from_dict(d); self.assertEqual(q.shapes[0].y,340); self.assertEqual(q.schema,4)
    def test_migrate_line(self):
        d=self.p().to_dict(); d['schema']=1; d['shapes'][0]['kind']='line'; s=Project.from_dict(d).shapes[0]; self.assertEqual(shape_paths(s)[0],[(10,380),(40,340)])
    def test_migrate_polygon(self):
        d=self.p().to_dict(); d['schema']=1; d['shapes'][0]['kind']='polygon'; d['shapes'][0]['points']=[[0,0],[10,0],[0,10],[0,0]]
        s=Project.from_dict(d).shapes[0]; self.assertEqual(shape_paths(s)[0][2],(10,370))
    def test_roundtrip_schema2(self):
        p=self.p()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'p.steburn'; p.save(path); self.assertEqual(p.to_dict(),Project.load(path).to_dict())
    def test_plan_and_passes(self):
        p=self.p(); a=build_plan(p); p.layers[0].passes=2; b=build_plan(p)
        self.assertEqual(sum(s.duration for s in b.segments if s.power),2*sum(s.duration for s in a.segments if s.power))
    def test_hidden_output_still_planned(self):
        p=self.p(); p.layers[0].visible=False; self.assertTrue(build_plan(p).segments)
    def test_output_off(self):
        p=self.p(); p.layers[0].output=False; self.assertFalse(build_plan(p).segments)
    def test_out_of_bounds_warning(self):
        p=self.p(); p.shapes[0].x=390; self.assertTrue(any('außerhalb' in w for w in build_plan(p).warnings))
    def test_no_out_of_bounds_frame(self):
        p=self.p(); p.shapes[0].x=390
        with self.assertRaises(ValueError): rectangle_plan(p,p.shapes)
    def test_frame_rectangle(self):
        p=self.p(); self.assertEqual(rectangle_plan(p,p.shapes),[(10,20),(40,20),(40,60),(10,60),(10,20)])
    def test_fill_hole(self):
        s=as_paths_shape(Shape('polygon'),[[(0,0),(10,0),(10,10),(0,10),(0,0)],[(3,3),(7,3),(7,7),(3,7),(3,3)]])
        lines=fill_paths(s,1)
        self.assertTrue(lines); self.assertFalse(any(3.01<sum(pt[0] for pt in p)/len(p)<6.99 and 3< p[0][1]<7 for p in lines))
    def test_text_paths(self):
        s=Shape('text',10,20,80,12,text='Danke!'); paths=shape_paths(s); self.assertTrue(paths); self.assertTrue(all(p[0]==p[-1] for p in paths)); self.assertGreater(bounds([s])[2],10)
    def test_rotation(self):
        s=self.p().shapes[0]; transform(s,'cw'); a,b,c,d=bounds([s]); self.assertAlmostEqual(c-a,40); self.assertAlmostEqual(d-b,30)
    def test_mirror_twice(self):
        s=self.p().shapes[0]; old=bounds([s]); transform(s,'mirror_x'); transform(s,'mirror_x'); self.assertEqual(old,bounds([s]))
    def test_boolean(self):
        a=self.p().shapes[0]; b=deepcopy(a); b.x+=10; self.assertAlmostEqual(polygon_geometry(a).union(polygon_geometry(b)).area,1600)
    def test_bitmap_formats(self):
        with tempfile.TemporaryDirectory() as d:
            for ext,fmt in [('png','PNG'),('bmp','BMP'),('jpg','JPEG'),('gif','GIF'),('tif','TIFF'),('tga','TGA'),('webp','WEBP')]:
                path=Path(d)/('image.'+ext); Image.new('RGB',(10,20),'black').save(path,format=fmt); s=import_file(path,'x').shapes[0]; self.assertEqual((s.w,s.h),(100,200)); self.assertEqual(s.kind,'image')
    def test_image_plan(self):
        p=self.p(); p.shapes=[image_shape(Image.new('RGB',(2,2),'black'),p.layers[0].id,'Bitmap',width=2)]; plan=build_plan(p); self.assertTrue(any(s.power for s in plan.segments))
    def test_svg_bottom_left_roundtrip(self):
        p=self.p()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'shape.svg'; export_svg(p,path); imported=import_file(path,p.layers[0].id); self.assertEqual(bounds(imported.shapes),bounds(p.shapes))
    def test_svg_curves(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'shape.svg'; path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="100mm" viewBox="0 0 100 100"><path d="M10 10 C10 50 50 50 50 10 Z"/></svg>'); result=import_file(path,'x'); self.assertTrue(len(shape_paths(result.shapes[0])[0])>10)
    def test_pdf_raster(self):
        import fitz
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.pdf'; doc=fitz.open(); doc.new_page(width=72,height=144); doc.save(path); doc.close(); result=import_file(path,'x'); self.assertAlmostEqual(result.shapes[0].w,25.4)
    def test_dxf(self):
        import ezdxf
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.dxf'; doc=ezdxf.new(); doc.header['$INSUNITS']=4; doc.modelspace().add_line((10,20),(30,40)); doc.saveas(path); result=import_file(path,'x'); self.assertEqual(bounds(result.shapes),(10,20,30,40))
    def test_hpgl(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.plt'; path.write_text('IN;PA;PU400,800;PD1200,1600;PU;'); result=import_file(path,'x'); self.assertEqual(bounds(result.shapes),(10,20,30,40))
    def test_gcode_never_executes(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.gcode'; path.write_text('G21\nG90\nG0 X10 Y20\nM4 S100\nG1 X30 Y40 F1200\nM5'); result=import_file(path,'x'); self.assertEqual(bounds(result.shapes),(10,20,30,40))
    def test_gcode_unsupported_atomic(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.nc'; path.write_text('G2 X10 Y20 I5 J5')
            with self.assertRaises(ValueError): import_file(path,'x')
    def test_proprietary_rejected(self):
        with self.assertRaises(ValueError): import_file('test.lbrn2','x')
    def test_unverified_device_blocked(self):
        dev=GrblSession()
        with self.assertRaises(ValueError): dev.align([(1,1)],400,400)
    def test_out_of_bounds_device_blocked(self):
        dev=GrblSession()
        with self.assertRaises(ValueError): dev.align([(401,1)],400,400)
    def test_low_power_requires_calibration(self):
        dev=GrblSession(); dev.ready=lambda w,h:(0,0); dev.settings={30:1000}
        with self.assertRaises(ValueError): dev.align([(1,1)],400,400,visible=True)
    def test_alignment_command_sequence(self):
        dev=GrblSession(); dev.ready=lambda w,h:(0,0); dev.settings={30:1000}; dev.wait_idle=lambda:None
        commands=[]; dev.read_work_offset=lambda:[0,0,0]
        dev.command=lambda cmd: ['[GC:G0 G54 G21 G90]'] if cmd=='$G' else commands.append(cmd)
        dev.align([(10,20),(30,20),(30,40)],400,400,visible=False)
        self.assertEqual(commands[0],'M5'); self.assertEqual(commands[-1],'M5'); self.assertFalse(any(c.startswith(('M3','M4')) for c in commands))
    def test_visible_frame_dynamic_power(self):
        dev=GrblSession(); dev.ready=lambda w,h:(0,0); dev.settings={30:1000}; dev.wait_idle=lambda:None; dev.low_power_confirmed=True; dev.low_power=.1
        commands=[]; dev.read_work_offset=lambda:[0,0,0]; dev.command=lambda cmd: ['[GC:G0 G54 G21 G90]'] if cmd=='$G' else commands.append(cmd); dev.align([(10,20),(30,20)],400,400,visible=True)
        self.assertIn('M4 S1',commands); self.assertEqual(commands[-1],'M5')
    def test_failed_alignment_resets(self):
        dev=GrblSession(); dev.ready=lambda w,h:(0,0); dev.settings={30:1000}; dev.command=lambda cmd:(_ for _ in ()).throw(TimeoutError())
        with self.assertRaises(TimeoutError): dev.align([(10,20)],400,400)
        self.assertTrue(dev.cancelled.is_set())
if __name__=='__main__': unittest.main()
