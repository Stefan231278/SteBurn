import unittest,math
from steburn.core.model import Shape,Project
from steburn.core.paths import as_paths_shape,shape_paths
from steburn.core.nodes import paths,transform_nodes,delete_nodes
from steburn.core.connect import join,endpoints
from steburn.core.order import move_layer,layer_for_segment
from steburn.core.planner import build_plan

def line(points): return as_paths_shape(Shape('polyline'),[points])

class ConnectionTests(unittest.TestCase):
    def test_straight_join_preserves_both_paths_and_closes_same_contour(self):
        a=line([(10,10),(20,10)]); b=line([(30,10),(40,20)])
        result=join(a,b,1,0); self.assertEqual(shape_paths(result)[0],[(10,10),(20,10),(30,10),(40,20)])
        result=join(result,result,1,0); self.assertEqual(shape_paths(result)[0][0],shape_paths(result)[0][-1])
    def test_coincident_ends_do_not_create_duplicate_segment(self):
        a=line([(10,10),(20,10)]); b=line([(20,10),(30,20)])
        self.assertEqual(len(shape_paths(join(a,b,1,0))[0]),3)
    def test_tangent_join_and_edit_preserve_g1_directions(self):
        a=line([(10,10),(20,10)]); b=line([(30,20),(30,40)])
        result=join(a,b,1,0,True,True)
        def check(shape):
            p=paths(shape)[0]
            for i in (3,6):
                u=(p[i][0]-p[i-1][0],p[i][1]-p[i-1][1]); v=(p[i+1][0]-p[i][0],p[i+1][1]-p[i][1])
                self.assertAlmostEqual(u[0]*v[1]-u[1]*v[0],0,places=7); self.assertGreater(u[0]*v[0]+u[1]*v[1],0)
        check(result); self.assertEqual(result.extra['tangent_anchors'],[3,6])
        changed=transform_nodes(result,{(0,4)},lambda x,y:(x,y+2)); check(changed)
        check(transform_nodes(result,{(0,2),(0,4)},lambda x,y:(x+1,y+2)))
        self.assertEqual(endpoints(changed)[0],(10,10)); self.assertEqual(endpoints(changed)[1],(30,40))
    def test_tangent_requires_curve_and_nonzero_handles(self):
        a=line([(10,10),(20,10)]); b=line([(30,20),(30,40)])
        with self.assertRaises(ValueError): join(a,b,1,0,False,True)
    def test_delete_multiple_closed_nodes_preserves_closure(self):
        a=line([(0,0),(10,0),(20,10),(20,20),(10,30),(0,20),(0,0)])
        result=delete_nodes(a,{(0,0),(0,2)})
        self.assertEqual(len(shape_paths(result)[0]),5); self.assertEqual(shape_paths(result)[0][0],shape_paths(result)[0][-1])
    def test_delete_all_nodes_removes_shape(self):
        a=line([(10,10),(20,10)]); self.assertIsNone(delete_nodes(a,{(0,0),(0,1)}))
    def test_delete_cubic_anchor_preserves_valid_chain(self):
        a=line([(10,10),(20,10)]); b=line([(30,20),(30,40)]); joined=join(a,b,1,0,True,True)
        result=delete_nodes(joined,{(0,3)}); self.assertEqual((len(paths(result)[0])-1)%3,0)
        self.assertEqual(result.extra['tangent_anchors'],[3])
    def test_layer_reorder_rebuilds_actual_plan_order(self):
        project=Project(); project.shapes=[Shape('rect',10+i*40,10,10,10,l.id) for i,l in enumerate(project.layers)]
        changed=move_layer(project,project.layers[0].id,1); plan=build_plan(changed,preview=False)
        active=[layer_for_segment(changed,s) for s in plan.segments if s.power]
        self.assertEqual(active[0],project.layers[1].id); self.assertEqual(project.layers[0].name,'Gravur')
    def test_all_endpoint_orientations(self):
        a=line([(10,10),(20,10)]); b=line([(30,20),(40,20)])
        for i in (0,1):
            for j in (0,1):
                result=shape_paths(join(a,b,i,j))[0]
                self.assertEqual(result,[endpoints(a)[1-i],endpoints(a)[i],endpoints(b)[j],endpoints(b)[1-j]])
    def test_tangent_closing_curve_preserves_both_seam_tangents(self):
        a=line([(10,10),(30,10),(30,30)]); result=join(a,a,1,0,True,True); p=paths(result)[0]
        self.assertEqual(p[0],p[-1]); self.assertIn(0,result.extra['tangent_anchors']); self.assertIn(6,result.extra['tangent_anchors'])
        incoming=(p[-1][0]-p[-2][0],p[-1][1]-p[-2][1]); outgoing=(p[1][0]-p[0][0],p[1][1]-p[0][1])
        self.assertAlmostEqual(incoming[0]*outgoing[1]-incoming[1]*outgoing[0],0)
    def test_closed_cubic_can_retain_two_anchors_after_deletion(self):
        a=line([(10,10),(30,10),(30,30)]); result=join(a,a,1,0,True,True)
        changed=delete_nodes(result,{(0,3)}); p=paths(changed)[0]
        self.assertEqual(len(p),7); self.assertEqual(p[0],p[-1])
    def test_dimensions_persist_without_entering_laser_plan(self):
        from steburn.core.jobs import snapshot
        project=Project(); project.shapes=[Shape('rect',20,20,30,30,project.layers[1].id)]
        before=snapshot(build_plan(project,preview=False)).fingerprint
        project.extensions['measurements']=[[(10,10),(90,100)]]
        restored=Project.from_dict(project.to_dict())
        self.assertEqual(snapshot(build_plan(restored,preview=False)).fingerprint,before)
        self.assertTrue(restored.extensions['measurements'])
    def test_first_contour_is_base_and_join_creates_group(self):
        a=line([(10,10),(20,10)]); a.name='Basis'; a.layer='base-layer'; a.extra['processing']={'operation':'cut','power':71,'speed':650}
        b=line([(30,20),(40,20)]); b.layer='other-layer'
        result=join(a,b,1,0)
        self.assertEqual((result.id,result.name,result.layer),(a.id,'Basis','base-layer'))
        self.assertEqual(result.extra['processing'],a.extra['processing']); self.assertTrue(result.extra['group'])
        self.assertNotIn('group',a.extra); self.assertNotIn('group',b.extra)
    def test_existing_base_group_is_retained(self):
        a=line([(10,10),(20,10)]); b=line([(30,20),(40,20)])
        a.extra['group']='first-group'; b.extra['group']='second-group'
        self.assertEqual(join(a,b,1,0).extra['group'],'first-group')
