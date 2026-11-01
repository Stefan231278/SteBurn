"""Deterministic path preview, not a physics/thermal simulation."""
from dataclasses import dataclass
import math, base64, io
from steburn.core.paths import shape_paths, polygon_geometry, bounds
from steburn.core.processing import resolve, area_paths

@dataclass(frozen=True)
class Segment:
    start: tuple
    end: tuple
    speed: float
    power: float
    shape_id: str
    operation: str = 'mark'
    nominal_power: float = 0.
    constant_power: bool = False
    @property
    def duration(self): return math.dist(self.start,self.end)/self.speed*60
@dataclass
class Plan:
    segments: list
    warnings: list
    exact: bool = True
    @property
    def duration(self): return sum(s.duration for s in self.segments)

LIMIT=250000

def fill_paths(s,interval):
    from shapely.geometry import LineString
    geo=polygon_geometry(s); x0,y0,x1,y1=geo.bounds; paths=[]; y=y0+interval/2; reverse=False
    while y<y1:
        cut=geo.intersection(LineString([(x0-1,y),(x1+1,y)]))
        lines=list(cut.geoms) if hasattr(cut,'geoms') else [cut]
        pairs=[list(l.coords) for l in lines if l.geom_type=='LineString' and not l.is_empty]
        pairs.sort(key=lambda p:p[0][0],reverse=reverse)
        paths.extend([p[::-1] if reverse else p for p in pairs]); y+=interval; reverse=not reverse
        if len(paths)>LIMIT//2: raise ValueError('Zu viele Fülllinien; Linienintervall erhöhen.')
    return paths

def raster_dimensions(s,interval,max_pixels=None):
    nx=max(1,math.ceil(s.w/interval)); ny=max(1,math.ceil(s.h/interval))
    original=(nx,ny)
    if max_pixels is not None and nx*ny>max_pixels:
        factor=math.sqrt(nx*ny/max_pixels)
        nx=max(1,math.floor(nx/factor)); ny=max(1,math.floor(ny/factor))
        while nx*ny>max_pixels:
            if nx>=ny: nx-=1
            else: ny-=1
    return nx,ny,(nx,ny)!=original

def raster_paths(s,interval,max_pixels=None,dots=False):
    from PIL import Image
    nx,ny,reduced=raster_dimensions(s,interval,max_pixels)
    if nx*ny>LIMIT//2: raise ValueError('Exakter Bildplan zu groß. Vereinfachte Vorschau wählen oder Bearbeitungsauflösung anpassen.')
    if 'image_adjustments' in s.extra:
        from steburn.core.photos import render_photo
        source=render_photo(s.extra['image_original'],s.extra['image_adjustments'],(nx,ny))
    else: source=Image.open(io.BytesIO(base64.b64decode(s.extra['image'])))
    with source as src:
        im=src.convert('L').resize((nx,ny))
        if dots: im=im.convert('1')
        pix=im.load(); result=[]
        for row in range(ny):
            y=s.y+s.h-(row+.5)*s.h/ny
            if dots:
                cols=range(nx) if row%2==0 else range(nx-1,-1,-1)
                for col in cols:
                    if pix[col,row]==0:
                        center=s.x+(col+.5)*s.w/nx; half=min(.04,s.w/nx/8)
                        points=[(center-half,y),(center+half,y)]
                        result.append((points if row%2==0 else points[::-1],1.))
                continue
            # Coalesce equal grey values, including white travel within a raster row.
            columns=list(range(nx) if row%2==0 else range(nx-1,-1,-1))
            begin=0
            while begin<nx:
                value=pix[columns[begin],row]; end=begin+1
                while end<nx and pix[columns[end],row]==value: end+=1
                left=min(columns[begin],columns[end-1]); right=max(columns[begin],columns[end-1])+1
                a=s.x+left*s.w/nx; b=s.x+right*s.w/nx
                result.append(([(a,y),(b,y)] if row%2==0 else [(b,y),(a,y)],(255-value)/255))
                begin=end
        return result

def build_plan(p,ids=None,preview=True):
    p.validate(); segments=[]; warnings=[]; position=(0.,0.); seen=set(); exact=True
    def add(end,speed,power,sid,operation='travel',nominal_power=0.,constant_power=False):
        nonlocal position
        if len(segments)>=LIMIT: raise ValueError('Vorschau überschreitet Segmentlimit. Auflösung reduzieren.')
        if not all(math.isfinite(v) for v in (*end,speed,power)) or speed<=0: raise ValueError('Ungültiger Bearbeitungsweg')
        if math.dist(position,end)>1e-9: segments.append(Segment(position,tuple(end),speed,power,sid,operation,nominal_power,constant_power))
        position=tuple(end)
    raster_weight=sum(resolve(s,next(l for l in p.layers if l.id==s.layer)).passes for s in p.shapes if s.kind=='image' and next(l for l in p.layers if l.id==s.layer).output and (ids is None or s.id in ids))
    pixel_budget=max(1,LIMIT//(4*max(1,raster_weight)))
    for l in p.layers:
        if not l.output: continue
        if not l.visible: warnings.append(f'Ebene {l.name}: unsichtbar, aber Ausgabe aktiviert.')
        for s in p.shapes:
            if s.layer!=l.id or (ids is not None and s.id not in ids): continue
            settings=resolve(s,l)
            x0,y0,x1,y1=bounds([s])
            if x0<0 or y0<0 or x1>p.width or y1>p.height: warnings.append(f'{s.name}: außerhalb der Arbeitsfläche')
            if settings.power==0: warnings.append(f'{s.name}: Leistung 0 %')
            if s.kind=='image':
                if settings.operation in {'cut','mark'}: raise ValueError(f'{s.name}: Bitmap benötigt vor Konturbearbeitung eine Vektorisierung.')
                if settings.fill=='cross' or settings.angle!=0: raise ValueError(f'{s.name}: Kreuzschraffur/Winkel für Bitmaps noch nicht unterstützt.')
                budget=pixel_budget if preview else None
                nx,ny,reduced=raster_dimensions(s,settings.interval,budget)
                if reduced: exact=False
                if reduced: warnings.append(f'{s.name}: vereinfachte Bildvorschau ({nx} × {ny} Rasterpunkte). Bearbeitungsintervall {l.interval:g} mm unverändert; Vorschauzeit nur Näherung.')
                paths=raster_paths(s,settings.interval,budget,dots=settings.fill=='dots')
            else:
                contours=shape_paths(s)
                if any(path[0]!=path[-1] for path in contours): warnings.append(f'{s.name}: offene Kontur')
                paths=[(path,1.) for path in (area_paths(s,settings) if settings.operation=='engrave' else contours)]
            key=tuple(tuple((round(x,5),round(y,5)) for x,y in path) for path,_ in paths)
            if key in seen: warnings.append(f'{s.name}: doppelte Bearbeitungsgeometrie')
            seen.add(key)
            for _ in range(settings.passes):
                for path,intensity in paths:
                    if not path: continue
                    add(path[0],3000,0,s.id)
                    for pt in path[1:]: add(pt,settings.speed,settings.power*intensity,s.id,settings.operation,settings.power,s.extra.get('constant_power',False) is True and settings.operation=='mark')
    if not segments: warnings.append('Kein Bearbeitungsweg vorhanden.')
    return Plan(segments,list(dict.fromkeys(warnings)),exact)

def rectangle_plan(p,shapes):
    x0,y0,x1,y1=bounds(shapes)
    if x0<0 or y0<0 or x1>p.width or y1>p.height: raise ValueError('Rahmen liegt außerhalb der Arbeitsfläche.')
    return [(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)]
