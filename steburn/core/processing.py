"""Resolve object overrides once for both editor rendering and path planning."""
from dataclasses import dataclass
import math

OPERATIONS={'inherit','cut','engrave','mark'}
FILLS={'lines','cross','dots','solid'}
@dataclass(frozen=True)
class Processing:
    operation: str
    fill: str
    power: float
    speed: float
    passes: int
    interval: float
    angle: float

def resolve(shape,layer):
    values=shape.extra.get('processing',{})
    if not isinstance(values,dict) or set(values)-{'operation','fill','power','speed','passes','interval','angle'}:
        raise ValueError('Unbekannte Objekt-Bearbeitungsparameter')
    op=values.get('operation','inherit')
    if op not in OPERATIONS: raise ValueError('Unbekannte Bearbeitungsart')
    if op=='inherit':
        op='engrave' if shape.kind=='image' else layer.operation if layer.operation!='inherit' else 'engrave' if layer.mode=='Fläche' else 'cut' if layer.name.casefold() in ('schnitt','schneiden','cut') else 'mark'
    fill=values.get('fill','lines')
    if fill not in FILLS: raise ValueError('Unbekannte Füllung')
    data={k:values.get(k,getattr(layer,k)) for k in ('power','speed','passes','interval')}
    angle=values.get('angle',0.)
    def finite(v): return type(v) in (float,int) and math.isfinite(v)
    if not all(finite(v) for v in (*data.values(),angle)): raise ValueError('Ungültige Bearbeitungswerte')
    if not 0<=data['power']<=100 or not 0<data['speed']<=30000 or not .02<=data['interval']<=5 or type(data['passes']) is not int or not 1<=data['passes']<=1000 or not -360<=angle<=360:
        raise ValueError('Bearbeitungswert außerhalb gültiger Grenzen')
    return Processing(op,fill,**data,angle=angle)

def area_paths(shape,settings,display=False):
    """Millimetre paths. Dot engraving is short strokes, never stationary burns."""
    from shapely import affinity
    from shapely.geometry import LineString
    from steburn.core.paths import polygon_geometry
    interval=max(settings.interval,2.) if display else settings.interval
    geo=polygon_geometry(shape)
    if geo.is_empty: return []
    origin=geo.centroid.coords[0]
    angles=[settings.angle,settings.angle+90] if settings.fill=='cross' else [settings.angle]
    result=[]
    for angle in angles:
        rotated=affinity.rotate(geo,-angle,origin=origin)
        x0,y0,x1,y1=rotated.bounds
        if (y1-y0)/interval>125000: raise ValueError('Zu viele Fülllinien')
        y=y0+interval/2; reverse=False
        while y<y1:
            cut=rotated.intersection(LineString([(x0-1,y),(x1+1,y)]))
            parts=list(cut.geoms) if hasattr(cut,'geoms') else [cut]
            lines=[p for p in parts if p.geom_type=='LineString' and p.length>0]
            lines.sort(key=lambda p:p.bounds[0],reverse=reverse)
            for line in lines:
                strokes=[line]
                if settings.fill=='dots':
                    a,b=line.bounds[0],line.bounds[2]; strokes=[]; x=a+interval/2
                    while x<b:
                        strokes.append(LineString([(x,y),(min(b,x+min(.08,interval/4)),y)])); x+=interval
                        if len(strokes)+len(result)>125000: raise ValueError('Zu viele Punkte')
                for stroke in strokes:
                    coords=list(affinity.rotate(stroke,angle,origin=origin).coords)
                    result.append(coords[::-1] if reverse else coords)
                    if len(result)>125000: raise ValueError('Zu viele Füllwege')
            y+=interval; reverse=not reverse
    return result
