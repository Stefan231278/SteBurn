"""Geometric, assembly, layout and persistence checks for independently built boxes."""
import unittest,tempfile,math,random
from pathlib import Path
from dataclasses import replace
from shapely.geometry import Point,Polygon
from steburn.modules.boxes import BoxSpec,generate,arrange,placed_geometry,into_project,export_page
from steburn.core.model import Project,Shape
from steburn.core.planner import build_plan
from steburn.io.importers import import_file

class BoxTests(unittest.TestCase):
    def spec(self,**kw): return replace(BoxSpec(),**kw)
    def test_all_forms_and_closures(self):
        for style in ('rect','round','polygon','rounded'):
            for closure in ('open','closed','loose'):
                r=generate(self.spec(style=style,closure=closure))
                self.assertTrue(all(p.geometry.is_valid and p.geometry.geom_type=='Polygon' for p in r.parts))
                self.assertEqual(sum(p.role=='lid' for p in r.parts),int(closure!='open'))
    def test_inner_outer_conversion_rect(self):
        r=generate(self.spec(dimensions='inner',closure='closed'))
        self.assertEqual(r.inner,(120,80,60)); self.assertEqual(r.outer,(126,86,66))
    def test_open_inner_height(self):
        r=generate(self.spec(dimensions='inner',closure='open'))
        self.assertEqual(r.inner,(120,80,60)); self.assertEqual(r.outer,(126,86,63))
    def test_loose_lid_outer_height_includes_lid(self):
        r=generate(self.spec(closure='loose')); lid=next(p for p in r.parts if p.role=='lid')
        self.assertEqual(lid.origin[2]+lid.thickness,r.outer[2])
    def test_finger_shell_has_no_overlap_or_holes(self):
        rng=random.Random(412)
        for closure in ('open','closed','loose'):
            r=generate(self.spec(width=90,depth=60,height=45,closure=closure))
            W,D,H=r.outer; t=r.spec.thickness
            # Include all 8 triple corners and edge strips, then independent interior samples.
            points=[(x,y,z) for x in (t/2,W-t/2) for y in (t/2,D-t/2) for z in (t/2,H-t/2)]
            points += [(rng.uniform(.01,W-.01),rng.uniform(.01,D-.01),rng.uniform(.01,H-.01)) for _ in range(1000)]
            for x,y,z in points:
                shell=(x<t or x>W-t or y<t or y>D-t or z<t or (closure!='open' and z>H-t))
                n=sum(p.contains3(x,y,z) for p in r.parts)
                self.assertEqual(n,int(shell),(closure,(x,y,z),n))
    def test_finger_edge_pair_every_segment(self):
        r=generate(self.spec(width=90,depth=60,height=45,closure='closed'))
        t=r.spec.thickness
        # Along all 12 edges at non-boundary sample points: each unit volume belongs to one face.
        for axis,length in enumerate(r.outer):
            others=[a for a in range(3) if a!=axis]
            for i in range(1,251):
                for sideA in (False,True):
                    for sideB in (False,True):
                        p=[0.,0.,0.]; p[axis]=(i-.371)*length/251
                        p[others[0]]=r.outer[others[0]]-t/2 if sideA else t/2
                        p[others[1]]=r.outer[others[1]]-t/2 if sideB else t/2
                        self.assertEqual(sum(part.contains3(*p) for part in r.parts),1,(axis,p))
    def test_butt_shell_volume(self):
        r=generate(self.spec(joint='butt',closure='closed'))
        volume=sum(p.nominal.area*p.thickness for p in r.parts)
        self.assertAlmostEqual(volume,math.prod(r.outer)-math.prod(r.inner))
    def test_finger_shell_volume(self):
        r=generate(self.spec(closure='closed'))
        self.assertAlmostEqual(sum(p.nominal.area*p.thickness for p in r.parts),math.prod(r.outer)-math.prod(r.inner))
    def test_divider_cross_laps_do_not_collide(self):
        r=generate(self.spec(rows=3,columns=4)); div=[p for p in r.parts if p.role=='divider']
        self.assertEqual(len(div),5)
        for a in [p for p in div if p.plane=='xz']:
            for b in [p for p in div if p.plane=='yz']:
                x=b.origin[0]+b.thickness/2; y=a.origin[1]+a.thickness/2
                for z in (8,18,28,38,48): self.assertLessEqual(sum(p.contains3(x,y,z) for p in (a,b)),1)
    def test_kerf_increases_exterior_and_shrinks_holes(self):
        a=generate(self.spec(style='round',height=15)); b=generate(self.spec(style='round',height=15,kerf=.2))
        ra=next(p for p in a.parts if p.role=='ring'); rb=next(p for p in b.parts if p.role=='ring')
        self.assertGreater(rb.geometry.area,ra.geometry.area)
        self.assertLess(Polygon(rb.geometry.interiors[0]).area,Polygon(ra.geometry.interiors[0]).area)
    def test_lamination_rounds_height_explicitly(self):
        r=generate(self.spec(style='round',height=20,thickness=3))
        self.assertEqual(r.outer[2],21); self.assertTrue(any('aufgerundet' in w for w in r.warnings))
    def test_sides_and_thickness_change_geometry(self):
        a=generate(self.spec(style='polygon',height=15,sides=5)); b=generate(self.spec(style='polygon',height=15,sides=8,thickness=4))
        self.assertNotEqual(a.parts[0].nominal.area,b.parts[0].nominal.area)
        self.assertNotEqual(len(a.parts),len(b.parts))
    def test_invalid_values(self):
        for kwargs in ({'width':float('nan')},{'thickness':0},{'kerf':-1},{'sides':2},{'columns':100},{'radius':1000,'style':'rounded'},{'style':'polygon','rows':2}):
            with self.assertRaises(ValueError): generate(self.spec(**kwargs))
    def test_too_thick_or_short_finger_box_rejected(self):
        with self.assertRaises(ValueError): generate(self.spec(width=10,depth=10,height=10,thickness=3))
    def test_oversize_part_not_scaled(self):
        r=generate(self.spec(width=600,depth=500))
        with self.assertRaises(ValueError): arrange(r)
    def test_layout_inside_margin_no_overlap(self):
        for style in ('rect','round','polygon','rounded'):
            r=generate(self.spec(style=style,height=30,kerf=.2)); places=arrange(r,300,250)
            for place in places:
                geo=placed_geometry(r.parts[place.part],place); a,b,c,d=geo.bounds
                self.assertGreaterEqual(a,5-1e-7); self.assertGreaterEqual(b,5-1e-7)
                self.assertLessEqual(c,295+1e-7); self.assertLessEqual(d,245+1e-7)
            for i,p in enumerate(places):
                for q in places[i+1:]:
                    if p.page==q.page: self.assertFalse(placed_geometry(r.parts[p.part],p).intersects(placed_geometry(r.parts[q.part],q)))
    def test_multisheet_no_missing_parts(self):
        r=generate(self.spec(style='round')); places=arrange(r)
        self.assertEqual({p.part for p in places},set(range(len(r.parts))))
        self.assertGreater(max(p.page for p in places),0)
    def test_project_parameters_roundtrip_and_no_live_output(self):
        p=Project(); r=generate(self.spec()); places=arrange(r)
        q,mid,lid=into_project(p,r,places); q=Project.from_dict(q.to_dict())
        self.assertEqual(q.extensions['box_models'][mid]['parameters']['width'],120)
        self.assertTrue(all(not l.output and l.power==0 for l in q.layers if l.id in q.extensions['box_models'][mid]['layers']))
        self.assertFalse(build_plan(q).segments)
    def test_regenerate_preserves_unrelated_objects(self):
        p=Project(); original=Shape('rect',10,10,20,20,p.layers[0].id); p.shapes.append(original)
        r=generate(self.spec()); q,mid,lid=into_project(p,r,arrange(r))
        s=Shape('rect',300,300,10,10,lid); q.shapes.append(s)
        r2=generate(self.spec(width=130)); new,mid2,_=into_project(q,r2,arrange(r2),mid)
        self.assertEqual(mid,mid2); self.assertTrue(any(v.id==original.id for v in new.shapes)); self.assertTrue(any(v.id==s.id for v in new.shapes))
        self.assertEqual(len([v for v in new.shapes if v.extra.get('box_model')==mid]),5)
        self.assertEqual(len(p.shapes),1)
    def test_svg_export_reimport_keeps_holes(self):
        r=generate(self.spec(style='round',height=12)); places=arrange(r)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'box.svg'; export_page(path,r,places,400,400)
            data=import_file(path,'layer'); self.assertTrue(data.shapes)
            self.assertTrue(any(len(s.extra.get('contours',[]))>1 for s in data.shapes))
    def test_dxf_export_is_mm_closed_polylines(self):
        import ezdxf
        r=generate(self.spec()); places=arrange(r)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'box.dxf'; export_page(path,r,places,400,400,kind='dxf')
            doc=ezdxf.readfile(path); self.assertEqual(doc.header['$INSUNITS'],4)
            self.assertTrue(all(e.closed for e in doc.modelspace().query('LWPOLYLINE')))
    def test_only_first_sheet_visible(self):
        r=generate(self.spec(style='round')); p,mid,lid=into_project(Project(),r,arrange(r))
        lids=p.extensions['box_models'][mid]['layers']
        self.assertEqual(sum(l.visible for l in p.layers if l.id in lids),1)

class BoxRobustnessTests(unittest.TestCase):
    def test_fractional_dimensions_shell_volume(self):
        rng=random.Random(681)
        for _ in range(40):
            t=rng.uniform(.7,8)
            spec=BoxSpec(width=rng.uniform(7,30)*t,depth=rng.uniform(7,30)*t,height=rng.uniform(7,30)*t,thickness=t,finger=3*t,closure='closed')
            result=generate(spec)
            self.assertAlmostEqual(sum(p.nominal.area*t for p in result.parts),math.prod(result.outer)-math.prod(result.inner),places=5)
    def test_unit_converted_dimensions_stay_connected(self):
        # PowerShell/GUI-style decimal formatting can slightly perturb exact nominal dimensions.
        t=float(f'{3/25.4:.8g}')*25.4
        w=float(f'{120/25.4:.8g}')*25.4
        d=float(f'{80/25.4:.8g}')*25.4
        h=float(f'{60/25.4:.8g}')*25.4
        spec=BoxSpec(width=w,depth=d,height=h,thickness=t,finger=9)
        result=generate(spec)
        self.assertTrue(all(p.geometry.geom_type=='Polygon' for p in result.parts))

    def test_kerf_cannot_erase_thin_joint_features(self):
        with self.assertRaises(ValueError): generate(BoxSpec(thickness=.5,finger=1.5,kerf=.8))
