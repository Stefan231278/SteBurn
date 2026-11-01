import unittest
from steburn.core.model import Shape
from steburn.core.paths import shape_paths,as_paths_shape,bounds
from steburn.core.resize import resize_shape
from steburn.core.nodes import paths,transform_nodes
from steburn.core.design import set_bezier

class NodeTests(unittest.TestCase):
    def test_side_handle_ignores_aspect_lock(self):
        for kind in ('rect','ellipse'):
            s=Shape(kind,20,30,40,20)
            result=resize_shape(s,'e',(80,40),True)
            self.assertEqual((result.x,result.y,result.w,result.h),(20,30,60,20))
            result=resize_shape(s,'n',(40,70),True)
            self.assertEqual((result.x,result.y,result.w,result.h),(20,30,40,40))
    def test_corner_still_preserves_aspect_lock(self):
        s=Shape('rect',20,30,40,20); r=resize_shape(s,'ne',(100,60),True)
        self.assertEqual(r.w/r.h,2)
    def test_editing_primitive_seam_keeps_contour_closed(self):
        s=Shape('rect',20,30,40,20); r=transform_nodes(s,{(0,0)},lambda x,y:(x-5,y+3))
        self.assertEqual(shape_paths(r)[0][0],shape_paths(r)[0][-1]); self.assertEqual(shape_paths(r)[0][0],(15,33))
        self.assertEqual(s.kind,'rect')
    def test_multi_node_stretch_preserves_hole_and_seams(self):
        s=as_paths_shape(Shape('polygon'),[[(10,10),(40,10),(40,40),(10,40),(10,10)],[(20,20),(30,20),(30,30),(20,30),(20,20)]])
        r=transform_nodes(s,{(0,0),(0,1)},lambda x,y:(x*2,y))
        self.assertEqual(shape_paths(r)[1],shape_paths(s)[1])
        self.assertEqual(shape_paths(r)[0][0],shape_paths(r)[0][-1])
    def test_closed_bezier_anchor_moves_both_adjacent_handles(self):
        s=set_bezier(Shape('polyline'),[(10,10),(20,10),(30,20),(30,30),(20,40),(10,20),(10,10)])
        old=paths(s)[0]; r=transform_nodes(s,{(0,0)},lambda x,y:(x+5,y+2)); new=paths(r)[0]
        for i in (0,1,5,6): self.assertEqual(new[i],(old[i][0]+5,old[i][1]+2))
        self.assertEqual(new[0],new[-1])
    def test_closed_bezier_smooth_handle_mirrors_across_seam(self):
        s=set_bezier(Shape('polyline'),[(10,10),(20,10),(30,20),(30,30),(20,40),(10,20),(10,10)]); s.extra['curve_smooth']=True
        r=transform_nodes(s,{(0,1)},lambda x,y:(x+2,y+3)); new=paths(r)[0]
        self.assertEqual(new[5],(2*new[0][0]-new[1][0],2*new[0][1]-new[1][1]))
