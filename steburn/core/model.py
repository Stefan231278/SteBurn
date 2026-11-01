"""Versioned, UI-independent document model. All coordinates are millimetres."""
from dataclasses import dataclass, field, asdict
from uuid import uuid4
from copy import deepcopy
import json, math, os, tempfile
from pathlib import Path

KINDS = {'rect', 'ellipse', 'line', 'text', 'polyline', 'polygon', 'image'}
@dataclass
class Layer:
    name: str = 'Gravur'
    color: str = '#279b85'
    mode: str = 'Kontur'
    speed: float = 1200
    power: float = 20
    passes: int = 1
    visible: bool = True
    output: bool = True
    air: bool = False
    interval: float = 0.2
    id: str = field(default_factory=lambda: uuid4().hex)
    operation: str = 'inherit'
@dataclass
class Shape:
    kind: str
    x: float = 0
    y: float = 0
    w: float = 20
    h: float = 20
    layer: str = ''
    name: str = 'Objekt'
    text: str = ''
    points: list = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid4().hex)
    extra: dict = field(default_factory=dict)
@dataclass
class Project:
    title: str = 'Unbenannt'
    width: float = 400
    height: float = 400
    layers: list = field(default_factory=lambda: [Layer('Gravur', '#1878d1', mode='Fläche'), Layer('Schnitt', '#df493b', mode='Kontur', power=60), Layer('Markierung', '#239461', mode='Kontur', power=10)])
    shapes: list = field(default_factory=list)
    extensions: dict = field(default_factory=dict)
    schema: int = 4
    def to_dict(self): return asdict(self)
    @classmethod
    def from_dict(cls, data):
        if data.get('schema') not in (1,2,3,4): raise ValueError('Unbekannte Projektversion. Datei nicht verändert.')
        data=deepcopy(data)
        if data['schema']==1:
            # Version 0.1 used top-left coordinates. Preserve the visual placement.
            for s in data['shapes']:
                if s['kind'] in {'polygon','polyline'}:
                    s['y']=data['height']-s['y']
                    s['points']=[[x,-y] for x,y in s['points']]
                    minx=min(x for x,y in s['points']); miny=min(y for x,y in s['points'])
                    maxx=max(x for x,y in s['points']); maxy=max(y for x,y in s['points'])
                    s['x']+=minx; s['y']+=miny; s['w']=maxx-minx; s['h']=maxy-miny
                    s['points']=[[x-minx,y-miny] for x,y in s['points']]
                elif s['kind']=='line':
                    s['kind']='polyline'; s['points']=[[0,s['h']],[s['w'],0]]
                    s['y']=data['height']-s['y']-s['h']
                else: s['y']=data['height']-s['y']-s['h']
            data['schema']=2
        p = cls(title=data['title'], width=data['width'], height=data['height'],
                layers=[Layer(**l) for l in data['layers']], shapes=[Shape(**s) for s in data['shapes']],
                extensions=data.get('extensions', {}))
        p.validate()
        return p
    def validate(self):
        def finite(n): return isinstance(n, (float,int)) and not isinstance(n,bool) and math.isfinite(n)
        if not all(finite(n) and 0 < n <= 10000 for n in (self.width,self.height)): raise ValueError('Ungültige Arbeitsfläche')
        ids = [l.id for l in self.layers]
        if not ids or len(set(ids)) != len(ids): raise ValueError('Ungültige Ebenen')
        if len({s.id for s in self.shapes}) != len(self.shapes): raise ValueError('Doppelte Objekt-ID')
        for l in self.layers:
            if not finite(l.interval) or not .02<=l.interval<=5: raise ValueError('Linienintervall muss 0.02 bis 5 mm betragen')
            if not (finite(l.speed) and l.speed>0 and finite(l.power) and 0<=l.power<=100 and type(l.passes) is int and 1<=l.passes<=1000): raise ValueError('Ungültige Ebenenparameter')
            if len(l.color)!=7 or l.color[0]!='#' or any(c not in '0123456789abcdefABCDEF' for c in l.color[1:]): raise ValueError('Ungültige Ebenenfarbe')
            if l.mode not in {'Kontur','Fläche'}: raise ValueError('Unbekannter Bearbeitungsmodus')
            if l.operation not in {'inherit','cut','engrave','mark'}: raise ValueError('Unbekannte Ebenenoperation')
        for s in self.shapes:
            from steburn.core.processing import resolve
            if s.layer not in ids: raise ValueError('Ungültige Objektebene')
            if not isinstance(s.extra,dict): raise ValueError('Ungültige Zusatzdaten')
            resolve(s,next(l for l in self.layers if l.id==s.layer))
            if 'corner_radius' in s.extra and (not finite(s.extra['corner_radius']) or s.extra['corner_radius']<0): raise ValueError('Ungültiger Eckenradius')
            if 'bezier' in s.extra:
                nodes=s.extra['bezier']
                if s.kind not in {'polyline','polygon'} or not isinstance(nodes,list) or len(nodes)<4 or (len(nodes)-1)%3 or any(not isinstance(pt,(list,tuple)) or len(pt)!=2 or not all(finite(v) for v in pt) for pt in nodes): raise ValueError('Ungültige Bézierkurve')
            if s.kind=='text':
                if not finite(s.extra.get('tracking',0)) or abs(s.extra.get('tracking',0))>100: raise ValueError('Ungültige Laufweite')
                if not finite(s.extra.get('line_spacing',1.3)) or not .2<=s.extra.get('line_spacing',1.3)<=10: raise ValueError('Ungültiger Zeilenabstand')
                if s.extra.get('text_align','left') not in ('left','center','right'): raise ValueError('Ungültige Textausrichtung')
            contours=s.extra.get('contours')
            if contours is not None:
                if not isinstance(contours,list) or not contours or any(len(path)<2 or any(len(pt)!=2 or not all(finite(v) for v in pt) for pt in path) for path in contours): raise ValueError('Ungültige Konturen')
            if s.kind=='text' and (s.h<=0 or not finite(s.extra.get('text_scale_x',1.)) or s.extra.get('text_scale_x',1.)<=0 or type(s.extra.get('font_index',0)) is not int or s.extra.get('font_index',0)<0): raise ValueError('Ungültige Textgröße/Schrift')
            if s.kind=='image' and (not isinstance(s.extra.get('image'),str) or s.w<=0 or s.h<=0): raise ValueError('Ungültiges Bildobjekt')
            if s.kind=='image' and 'image_adjustments' in s.extra:
                from steburn.core.photos import settings_from
                if not isinstance(s.extra.get('image_original'),str): raise ValueError('Originalbild fehlt.')
                settings_from(s.extra['image_adjustments'])
            if s.kind not in KINDS or s.layer not in ids: raise ValueError('Ungültiges Objekt')
            if not all(finite(n) for n in (s.x,s.y,s.w,s.h)) or s.w<0 or s.h<0: raise ValueError('Ungültige Geometrie')
            if s.kind in {'polygon','polyline'} and (len(s.points)<2 or any(len(pt)!=2 or not all(finite(v) for v in pt) for pt in s.points)): raise ValueError('Ungültiger Linienzug')
        guides=self.extensions.get('guides',[])
        if not isinstance(guides,list) or any(not isinstance(g,(list,tuple)) or len(g)!=2 or g[0] not in ('x','y') or not finite(g[1]) for g in guides): raise ValueError('Ungültige Hilfslinien')
    def save(self, path):
        self.validate()
        path=Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        fd,tmp=tempfile.mkstemp(dir=path.parent, suffix='.tmp')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(self.to_dict(),f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    @classmethod
    def load(cls,path): return cls.from_dict(json.loads(Path(path).read_text(encoding='utf-8')))

class History:
    def __init__(self): self.undo_stack=[]; self.redo_stack=[]
    def checkpoint(self,p):
        self.undo_stack.append(deepcopy(p.to_dict())); self.undo_stack=self.undo_stack[-100:]; self.redo_stack.clear()
    def undo(self,p):
        if not self.undo_stack: return p
        self.redo_stack.append(p.to_dict()); return Project.from_dict(self.undo_stack.pop())
    def redo(self,p):
        if not self.redo_stack: return p
        self.undo_stack.append(p.to_dict()); return Project.from_dict(self.redo_stack.pop())
