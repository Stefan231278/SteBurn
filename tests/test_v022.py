import unittest,math
from PIL import Image
from steburn.core.model import Project,Shape
from steburn.core.paths import bounds
from steburn.core.resize import resize_shape
from steburn.core.fonts import installed_fonts
from steburn.core.planner import build_plan,LIMIT,raster_paths
from steburn.io.importers import image_shape
class ResizePreviewTests(unittest.TestCase):
    def image(self): return image_shape(Image.new('RGB',(330,200),'grey'),'layer','Beil',width=100)
    def test_resize_corner_ratio(self):
        s=self.image(); t=resize_shape(s,'ne',(s.x+200,s.y+130),True)
        self.assertAlmostEqual(t.w/t.h,s.w/s.h); self.assertEqual((t.x,t.y),(s.x,s.y))
    def test_resize_corner_free(self):
        s=self.image(); t=resize_shape(s,'ne',(s.x+200,s.y+130),False); self.assertEqual((t.w,t.h),(200,130))
    def test_opposite_corner_fixed(self):
        s=self.image(); t=resize_shape(s,'sw',(s.x-20,s.y-40),False)
        self.assertAlmostEqual(t.x+t.w,s.x+s.w); self.assertAlmostEqual(t.y+t.h,s.y+s.h)
    def test_resize_side_center(self):
        s=self.image(); t=resize_shape(s,'e',(s.x+200,s.y),True); self.assertAlmostEqual(t.y+t.h/2,s.y+s.h/2)
    def test_resize_copy_preserves_original(self):
        s=self.image(); old=s.to_dict() if hasattr(s,'to_dict') else (s.x,s.y,s.w,s.h); resize_shape(s,'ne',(200,200),True); self.assertEqual((s.x,s.y,s.w,s.h),old)
    def test_vector_resize(self):
        s=Shape('rect',10,20,30,40); t=resize_shape(s,'ne',(70,100),False); self.assertEqual(bounds([t]),(10,20,70,100))
    def test_text_free_resize(self):
        s=Shape('text',10,20,70,12,text='Steburn'); a,b,c,d=bounds([s]); t=resize_shape(s,'ne',(a+100,b+40),False); x0,y0,x1,y1=bounds([t]); self.assertAlmostEqual(x1-x0,100); self.assertAlmostEqual(y1-y0,40)
    def test_screenshot_size_simulates(self):
        p=Project(); s=self.image(); s.layer=p.layers[0].id; p.shapes=[s]; old=p.to_dict(); plan=build_plan(p); self.assertTrue(plan.segments); self.assertLess(len(plan.segments),LIMIT); self.assertTrue(any('vereinfachte' in w for w in plan.warnings)); self.assertEqual(old,p.to_dict())
    def test_exact_large_plan_still_explicit(self):
        p=Project(); s=self.image(); s.layer=p.layers[0].id; p.shapes=[s]
        with self.assertRaises(ValueError): build_plan(p,preview=False)
    def test_multiple_images_pass_budget(self):
        p=Project(); p.layers[0].passes=3
        for i in range(3):
            s=self.image(); s.layer=p.layers[0].id; s.x=i*110; p.shapes.append(s)
        plan=build_plan(p); self.assertLess(len(plan.segments),LIMIT)
    def test_white_pixels_are_laser_off(self):
        s=image_shape(Image.new('RGB',(10,10),'white'),'layer','white',width=2); self.assertTrue(all(power==0 for path,power in raster_paths(s,.2)))
    def test_font_discovery(self):
        faces=installed_fonts(); self.assertTrue(faces); self.assertTrue(all(f.path and f.label for f in faces)); self.assertEqual(len(faces),len({f.label for f in faces}))
