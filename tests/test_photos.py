import unittest
from dataclasses import asdict
from PIL import Image
from steburn.core.photos import PhotoSettings,render_photo,encode_image,decode_image,processed_shape,raster_size,cropped_size,settings_from
from steburn.core.model import Project
from steburn.core.planner import build_plan
from steburn.io.importers import image_shape

class PhotoTests(unittest.TestCase):
    def source(self):
        image=Image.new('RGB',(32,24)); image.putdata([(x*8,y*10,120) for y in range(24) for x in range(32)])
        return encode_image(image)
    def test_dither_is_binary_and_deterministic(self):
        for mode in ('floyd','atkinson','threshold'):
            a=render_photo(self.source(),{'mode':mode},(32,24)); b=render_photo(self.source(),{'mode':mode},(32,24))
            self.assertTrue(set(a.tobytes())<={0,255}); self.assertEqual(a.tobytes(),b.tobytes())
    def test_whites_never_gain_dark_pixels(self):
        for mode in ('gray','floyd','atkinson','threshold'):
            a=render_photo(Image.new('RGB',(10,10),'white'),{'mode':mode},(10,10))
            self.assertEqual(set(a.tobytes()),{255})
    def test_brightness_gamma_and_inversion(self):
        image=Image.new('RGB',(4,4),(100,100,100))
        normal=render_photo(image,{'mode':'gray'}).getpixel((0,0))
        brighter=render_photo(image,{'mode':'gray','brightness':1.5}).getpixel((0,0)); self.assertGreater(brighter,normal)
        gamma=render_photo(image,{'mode':'gray','gamma':2}).getpixel((0,0)); self.assertGreater(gamma,normal)
        inverse=render_photo(image,{'mode':'gray','invert':True}).getpixel((0,0)); self.assertEqual(inverse,255-normal)
    def test_crop_rotate_and_output_dimensions(self):
        settings=asdict(PhotoSettings(crop=(0,.25,1,.75),rotate=90,mode='gray'))
        self.assertEqual(cropped_size((80,40),settings),(20,80))
        self.assertEqual(render_photo(Image.new('RGB',(80,40)),settings).size,(20,80))
    def test_corrections_are_reversible_and_embedded(self):
        p=Project(); shape=image_shape(decode_image(self.source()),p.layers[0].id,'Test',width=20)
        changed=processed_shape(shape,{'mode':'gray','contrast':2},20,15,1,20,1200,1)
        restored=processed_shape(changed,{'mode':'gray'},20,15,1,20,1200,1)
        direct=processed_shape(shape,{'mode':'gray'},20,15,1,20,1200,1)
        self.assertEqual(restored.extra['image'],direct.extra['image']); self.assertEqual(restored.extra['image_original'],shape.extra['image'])
        p.shapes=[restored]; q=Project.from_dict(p.to_dict()); self.assertEqual(q.shapes[0].extra,restored.extra)
    def test_processed_pixels_reach_laser_plan(self):
        p=Project(); shape=image_shape(Image.new('RGB',(8,8),'black'),p.layers[0].id,'Test',width=10)
        shape=processed_shape(shape,{'mode':'threshold'},10,10,1,30,1200,1); p.shapes=[shape]
        plan=build_plan(p,preview=False); self.assertTrue(any(s.power==30 for s in plan.segments))
        shape=processed_shape(shape,{'mode':'threshold','invert':True},10,10,1,30,1200,1); p.shapes=[shape]
        self.assertFalse(any(s.power>0 for s in build_plan(p,preview=False).segments))
    def test_bad_settings_and_large_rasters_rejected(self):
        for values in ({'gamma':float('nan')},{'black':200,'white':100},{'crop':[0,0,0,1]},{'mode':'unknown'}):
            with self.assertRaises(ValueError): settings_from(values)
        with self.assertRaises(ValueError): raster_size(100,100,.05)
    def test_resized_dither_is_recomputed_from_original(self):
        p=Project(); shape=image_shape(decode_image(self.source()),p.layers[0].id,'Test',width=10)
        shape=processed_shape(shape,{'mode':'floyd'},10,10,1,30,1200,1)
        shape.w=17; shape.h=13; p.shapes=[shape]
        powers={segment.power for segment in build_plan(p,preview=False).segments}
        self.assertTrue(powers<={0,30}); self.assertIn(30,powers)
    def test_invalid_guides_rejected(self):
        p=Project(); p.extensions['guides']=[['z',10]]
        with self.assertRaises(ValueError): p.validate()
