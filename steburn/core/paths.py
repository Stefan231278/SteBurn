"""Geometry in bottom-left coordinates, independent of UI and device transport."""
from pathlib import Path
import math
from functools import lru_cache
from steburn.core.geometry import outline

@lru_cache(maxsize=16)
def font_path(requested=''):
    if requested:
        if Path(requested).is_file(): return requested
        raise ValueError('Projekt-Schriftdatei fehlt. Schrift erneut auswählen oder Text zuvor in Pfade umwandeln.')
    candidates=[Path('C:/Windows/Fonts/arial.ttf'),Path('C:/Windows/Fonts/segoeui.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    for p in candidates:
        if p.is_file(): return str(p)
    raise ValueError('Keine TrueType-Schrift gefunden. Schriftdatei im Textwerkzeug wählen.')

@lru_cache(maxsize=128)
def text_paths(text,height,requested='',font_index=0,tracking=0.,line_spacing=1.3,align='left'):
    from fontTools.ttLib import TTFont
    from fontTools.pens.basePen import BasePen
    font=TTFont(font_path(requested),fontNumber=font_index); glyphs=font.getGlyphSet(); cmap=font.getBestCmap(); scale=height/font['head'].unitsPerEm
    result=[]
    class Pen(BasePen):
        def __init__(self): super().__init__(glyphs); self.current=[]
        def _moveTo(self,p): self.current=[p]
        def _lineTo(self,p): self.current.append(p)
        def _curveToOne(self,a,b,c):
            p=self.current[-1]
            for i in range(1,17):
                t=i/16; u=1-t; self.current.append((u**3*p[0]+3*u*u*t*a[0]+3*u*t*t*b[0]+t**3*c[0],u**3*p[1]+3*u*u*t*a[1]+3*u*t*t*b[1]+t**3*c[1]))
        def _qCurveToOne(self,a,b):
            p=self.current[-1]
            for i in range(1,13):
                t=i/12; u=1-t; self.current.append((u*u*p[0]+2*u*t*a[0]+t*t*b[0],u*u*p[1]+2*u*t*a[1]+t*t*b[1]))
        def _closePath(self):
            if self.current: self.current.append(self.current[0]); result.append(self.current)
            self.current=[]
        def _endPath(self):
            if self.current: result.append(self.current)
            self.current=[]
    output=[]; lines=[]
    try:
        for row,line in enumerate(text.split('\n')):
            advance=0.; contours=[]
            for ch in line:
                if ord(ch) not in cmap: raise ValueError(f'Schrift unterstützt Zeichen {ch!r} nicht.')
                name=cmap[ord(ch)]; result.clear(); pen=Pen(); glyphs[name].draw(pen)
                contours.extend([[(advance+x*scale,y*scale-row*height*line_spacing) for x,y in contour] for contour in result])
                advance+=font['hmtx'][name][0]*scale+tracking
            lines.append((contours,max(0,advance-tracking)))
        width=max((w for _,w in lines),default=0)
        for contours,w in lines:
            shift=(width-w)/2 if align=='center' else width-w if align=='right' else 0
            output.extend([[(x+shift,y) for x,y in path] for path in contours])
    finally: font.close()
    if not output: return ()
    minx=min(x for p in output for x,y in p); miny=min(y for p in output for x,y in p)
    return tuple(tuple((x-minx,y-miny) for x,y in p) for p in output)

def shape_paths(s):
    if s.kind=='text': return [[(s.x+x*s.extra.get('text_scale_x',1.),s.y+y) for x,y in p] for p in text_paths(s.text,s.h,s.extra.get('font',''),s.extra.get('font_index',0),s.extra.get('tracking',0.),s.extra.get('line_spacing',1.3),s.extra.get('text_align','left'))]
    if 'bezier' in s.extra:
        from steburn.core.design import cubic_points
        return [[(s.x+x,s.y+y) for x,y in cubic_points(s.extra['bezier'])]]
    if s.kind=='rect' and s.extra.get('corner_radius',0):
        from steburn.core.design import rounded_rectangle
        return [[(s.x+x,s.y+y) for x,y in rounded_rectangle(s.w,s.h,s.extra['corner_radius'])]]
    if s.kind=='image': return [[(s.x,s.y),(s.x+s.w,s.y),(s.x+s.w,s.y+s.h),(s.x,s.y+s.h),(s.x,s.y)]]
    paths=s.extra.get('contours')
    if paths is not None: return [[(s.x+x,s.y+y) for x,y in p] for p in paths]
    return [outline(s)]

def bounds(shapes):
    pts=[pt for s in shapes for path in shape_paths(s) for pt in path]
    if not pts: raise ValueError('Keine Geometrie ausgewählt.')
    return min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)

def as_paths_shape(s,paths):
    s.kind='polygon' if all(p[0]==p[-1] for p in paths) else 'polyline'
    s.extra={k:v for k,v in s.extra.items() if k not in ('contours','image','font','bezier','corner_radius')}
    minx=min(x for p in paths for x,y in p); miny=min(y for p in paths for x,y in p)
    s.x=minx; s.y=miny; s.w=max(x for p in paths for x,y in p)-minx; s.h=max(y for p in paths for x,y in p)-miny
    local=[[[x-minx,y-miny] for x,y in p] for p in paths]
    s.points=local[0]; s.extra['contours']=local
    return s

def transform(s,operation,center=None):
    if s.kind=='image': raise ValueError('Bildtransformationen folgen später; Bild kann verschoben und skaliert werden.')
    paths=shape_paths(s); x0,y0,x1,y1=bounds([s]); cx,cy=center or ((x0+x1)/2,(y0+y1)/2)
    def point(x,y):
        if operation=='mirror_x': return 2*cx-x,y
        if operation=='mirror_y': return x,2*cy-y
        if operation=='cw': return cx+y-cy,cy-x+cx
        return cx-y+cy,cy+x-cx
    if 'bezier' in s.extra:
        from steburn.core.design import set_bezier
        return set_bezier(s,[point(s.x+x,s.y+y) for x,y in s.extra['bezier']])
    return as_paths_shape(s,[[point(x,y) for x,y in p] for p in paths])

def polygon_geometry(s):
    from shapely.geometry import Polygon
    geometry=Polygon()
    for path in shape_paths(s):
        if len(path)<4 or path[0]!=path[-1]: raise ValueError('Operation benötigt geschlossene Konturen.')
        part=Polygon(path)
        if not part.is_valid: raise ValueError('Kontur überschneidet sich selbst.')
        geometry=geometry.symmetric_difference(part)
    return geometry

def geometry_paths(geo):
    if geo.is_empty: return []
    polys=list(geo.geoms) if geo.geom_type=='MultiPolygon' else [geo]
    if any(p.geom_type!='Polygon' for p in polys): raise ValueError('Ergebnis enthält nicht unterstützte Geometrie.')
    return [list(r.coords) for p in polys for r in [p.exterior,*p.interiors]]
