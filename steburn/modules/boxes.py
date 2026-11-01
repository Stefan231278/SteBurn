"""Independent parametric laser-box geometry. No MakerCase implementation code.

Rectangular finger joints partition the shared edge volume between face pairs.
Curved/polygonal containers use laminated rings: no implied bevel or bend test.
"""
from dataclasses import dataclass,asdict,field
import math,json
from uuid import uuid4
from shapely.geometry import box,Polygon,Point
from shapely.ops import unary_union
from shapely import affinity

@dataclass(frozen=True)
class BoxSpec:
    style: str='rect'
    width: float=120.
    depth: float=80.
    height: float=60.
    thickness: float=3.
    dimensions: str='outer'
    joint: str='finger'
    closure: str='open'
    finger: float=9.
    kerf: float=0.
    clearance: float=.15
    radius: float=12.
    sides: int=6
    columns: int=1
    rows: int=1
    gap: float=4.
    material: str='Sperrholz'
    def validate(self):
        numeric=(self.width,self.depth,self.height,self.thickness,self.finger,self.kerf,self.clearance,self.radius,self.gap)
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in numeric): raise ValueError('Alle Maße müssen endliche Zahlen sein.')
        if self.style not in {'rect','polygon','round','rounded'} or self.dimensions not in {'inner','outer'} or self.joint not in {'finger','butt'} or self.closure not in {'open','closed','loose'}: raise ValueError('Unbekannte Boxoption')
        if not all(1<=v<=2000 for v in (self.width,self.depth,self.height)) or not .5<=self.thickness<=20: raise ValueError('Maße 1–2000 mm; Materialstärke 0,5–20 mm.')
        if not 0<self.finger<=200 or not 0<=self.kerf<=1 or not 0<=self.clearance<=2 or not 1<=self.gap<=50 or not 0<self.radius<=1000: raise ValueError('Fingerbreite mindestens Materialstärke; Schnittspalt 0–1 mm, Spiel 0–2 mm, Abstand 1–50 mm.')
        if any(type(v) is not int for v in (self.sides,self.columns,self.rows)) or not 3<=self.sides<=24 or not 1<=self.columns<=12 or not 1<=self.rows<=12: raise ValueError('Seiten 3–24, Gefache je Richtung 1–12.')
        if self.style=='rect' and self.joint=='finger' and self.finger<self.thickness: raise ValueError('Fingerbreite muss mindestens der Materialstärke entsprechen.')
        if self.style=='rect' and (self.joint=='finger' or self.columns>1 or self.rows>1) and self.kerf>=self.thickness: raise ValueError('Schnittspalt muss bei Steckverbindungen kleiner als die Materialstärke sein.')
        if self.style!='rect' and (self.columns!=1 or self.rows!=1): raise ValueError('Gefache sind aktuell für Rechteckboxen verfügbar.')
        if self.style=='rounded' and self.radius>min(self.width,self.depth)/2: raise ValueError('Eckenradius ist größer als die halbe kurze Seite.')

@dataclass
class Part:
    name: str
    nominal: object
    plane: str='xy'
    origin: tuple=(0.,0.,0.)
    thickness: float=3.
    role: str='wall'
    geometry: object=None
    def point3(self,u,v,offset=0.):
        x,y,z=self.origin
        if self.plane=='xy': return (x+u,y+v,z+offset)
        if self.plane=='xz': return (x+u,y+offset,z+v)
        return (x+offset,y+u,z+v)
    def contains3(self,x,y,z):
        a,b,c=self.origin
        if self.plane=='xy': u,v,n=x-a,y-b,z-c
        elif self.plane=='xz': u,v,n=x-a,z-c,y-b
        else: u,v,n=y-b,z-c,x-a
        return 0<n<self.thickness and self.nominal.contains(Point(u,v))

@dataclass
class BoxResult:
    spec: BoxSpec
    parts: list
    outer: tuple
    inner: tuple
    warnings: list=field(default_factory=list)

@dataclass(frozen=True)
class Placement:
    part: int
    page: int
    x: float
    y: float
    rotation: int


def odd_count(length,t,target):
    available=length-2*t
    if available<3*t: raise ValueError('Für Fingerzinken muss jede Kante mindestens fünf Materialstärken lang sein.')
    maximum=min(101,int(available/t))
    if maximum%2==0: maximum-=1
    n=max(3,min(maximum,int(round(available/target))))
    if n%2==0: n+=1 if n<maximum else -1
    return n


def finger_panel(w,h,t,edges,corners,target):
    """edges: bottom/right/top/left = owning parity True, complementary False,
    or None for an unjoined free edge. corners: bottom-left/right, top-right/left.
    Shared patterns use increasing global coordinates, independent of outline order.
    """
    pieces=[box(t,t,w-t,h-t)]
    for edge,owner in enumerate(edges):
        length=w if edge in (0,2) else h
        n=odd_count(length,t,target) if owner is not None else 1
        step=(length-2*t)/n
        for i in range(n):
            if owner is not None and ((i%2==0)!=owner): continue
            a=t+i*step; b=length-t if i==n-1 else t+(i+1)*step
            if edge==0: pieces.append(box(a,0,b,t))
            elif edge==2: pieces.append(box(a,h-t,b,h))
            elif edge==1: pieces.append(box(w-t,a,w,b))
            else: pieces.append(box(0,a,t,b))
    for include,(x,y) in zip(corners,[(0,0),(w-t,0),(w-t,h-t),(0,h-t)]):
        if include: pieces.append(box(x,y,x+t,y+t))
    geo=unary_union(pieces)
    if geo.geom_type!='Polygon' or not geo.is_valid: raise ValueError('Fingerzinken ergeben keine zusammenhängende Platte. Maße prüfen.')
    return geo


def rectangular(spec):
    t=spec.thickness; top=spec.closure!='open'
    if spec.dimensions=='inner': W,D,H=spec.width+2*t,spec.depth+2*t,spec.height+t+(t if top else 0)
    else: W,D,H=spec.width,spec.depth,spec.height
    bodyH=H-t if spec.closure=='loose' else H
    inner=(W-2*t,D-2*t,H-t-(t if top else 0))
    if min(inner)<=t: raise ValueError('Materialstärke lässt zu wenig Innenraum.')
    parts=[]
    def add(name,geo,plane,origin,role='wall'): parts.append(Part(name,geo,plane,origin,t,role))
    if spec.joint=='finger':
        for length in (W,D,bodyH): odd_count(length,t,spec.finger)
        cap=finger_panel(W,D,t,(True,True,True,True),(True,True,True,True),spec.finger)
        add('Boden',cap,'xy',(0,0,0),'base')
        fixedTop=spec.closure=='closed'
        front=finger_panel(W,bodyH,t,(False,True,False if fixedTop else None,True),(False,False,not fixedTop,not fixedTop),spec.finger)
        side=finger_panel(D,bodyH,t,(False,False,False if fixedTop else None,False),(False,False,False,False),spec.finger)
        add('Vorderwand',front,'xz',(0,0,0)); add('Rückwand',front,'xz',(0,D-t,0))
        add('Linke Wand',side,'yz',(0,0,0)); add('Rechte Wand',side,'yz',(W-t,0,0))
        if fixedTop: add('Deckel (verzinkt)',cap,'xy',(0,0,H-t),'lid')
        elif spec.closure=='loose': add('Deckel (lose aufliegend)',box(0,0,W,D),'xy',(0,0,bodyH),'lid')
    else:
        wh=H-t-(t if top else 0)
        add('Boden',box(0,0,W,D),'xy',(0,0,0),'base')
        add('Vorderwand',box(0,0,W,wh),'xz',(0,0,t)); add('Rückwand',box(0,0,W,wh),'xz',(0,D-t,t))
        add('Linke Wand',box(0,0,D-2*t,wh),'yz',(0,t,t)); add('Rechte Wand',box(0,0,D-2*t,wh),'yz',(W-t,t,t))
        if top: add('Deckel',box(0,0,W,D),'xy',(0,0,H-t),'lid')
    warnings=['Zusammenbau und Passung noch nicht am Material getestet. Erst eine kleine Passprobe schneiden.']
    if spec.closure=='loose': warnings.append('Loser Deckel liegt ohne Führung auf; keine Rastung oder Schiebeführung.')
    if spec.joint=='butt': warnings.append('Stumpfe Kanten benötigen eine geeignete Klebeverbindung.')
    if spec.columns>1 or spec.rows>1:
        wi,di,hi=inner; dh=hi-.2
        cw=(wi-(spec.columns-1)*t)/spec.columns; cd=(di-(spec.rows-1)*t)/spec.rows
        if min(cw,cd)<2*t or dh<=2*t: raise ValueError('Gefache zu klein oder zu niedrig für diese Materialstärke.')
        xs=[i*cw+(i-1)*t for i in range(1,spec.columns)]
        ys=[i*cd+(i-1)*t for i in range(1,spec.rows)]
        # Cross-lap: long X strips have bottom notches; Y strips top notches.
        for i,y in enumerate(ys):
            geo=box(0,0,wi,dh)
            for x in xs: geo=geo.difference(box(x-spec.clearance/2,-1,x+t+spec.clearance/2,dh/2+spec.clearance/2))
            add(f'Gefach quer {i+1}',geo,'xz',(t,t+y,t),'divider')
        for i,x in enumerate(xs):
            geo=box(0,0,di,dh)
            for y in ys: geo=geo.difference(box(y-spec.clearance/2,dh/2-spec.clearance/2,y+t+spec.clearance/2,dh+1))
            add(f'Gefach längs {i+1}',geo,'yz',(t+x,t,t),'divider')
        warnings.append('Gefache werden lose eingesetzt; Schlitze mit Materialstärke plus Spiel, ohne Wandverzahnung.')
    return BoxResult(spec,parts,(W,D,H),inner,warnings)


def laminated(spec):
    t=spec.thickness; top=spec.closure!='open'; countTop=int(top)
    if spec.style in {'round','polygon'}:
        n=spec.sides if spec.style=='polygon' else 0
        R=spec.width/2
        if spec.dimensions=='inner': R+=t/math.cos(math.pi/n) if n else t
        if n:
            base=Polygon([(R+R*math.cos(2*math.pi*i/n),R+R*math.sin(2*math.pi*i/n)) for i in range(n)])
        else: base=Point(R,R).buffer(R,quad_segs=64)
    else:
        W=spec.width+(2*t if spec.dimensions=='inner' else 0); D=spec.depth+(2*t if spec.dimensions=='inner' else 0)
        R=spec.radius+(t if spec.dimensions=='inner' else 0)
        if R>min(W,D)/2: raise ValueError('Eckenradius passt nicht zur Grundfläche.')
        base=box(R,R,W-R,D-R).buffer(R,quad_segs=20)
    cavity=base.buffer(-t,join_style=2 if spec.style=='polygon' else 1)
    if cavity.is_empty or cavity.geom_type!='Polygon': raise ValueError('Materialstärke lässt keine nutzbare Öffnung.')
    targetH=spec.height+(t+countTop*t if spec.dimensions=='inner' else 0)
    rings=max(1,math.ceil((targetH-t-countTop*t)/t-1e-10))
    if rings>120: raise ValueError('Mehr als 120 Wandschichten. Höhe reduzieren oder Materialstärke erhöhen.')
    if targetH<t*(2+countTop): raise ValueError('Höhe benötigt mindestens Boden, eine Wandschicht und gegebenenfalls Deckel.')
    actualH=(rings+1+countTop)*t
    ring=base.difference(cavity)
    parts=[Part('Boden',base,'xy',(0,0,0),t,'base')]
    parts.extend(Part(f'Wandring {i+1}/{rings}',ring,'xy',(0,0,(i+1)*t),t,'ring') for i in range(rings))
    if top: parts.append(Part('Deckel'+(' (lose)' if spec.closure=='loose' else ''),base,'xy',(0,0,(rings+1)*t),t,'lid'))
    x0,y0,x1,y1=base.bounds; a,b,c,d=cavity.bounds
    warnings=['Schichtbauweise: Ringe aufeinander kleben. Keine Biegeschlitze, keine schrägen Gehrungen. Materialpassprobe erforderlich.']
    if abs(actualH-targetH)>1e-7: warnings.append(f'Höhe auf ganze Materiallagen aufgerundet: außen {actualH:g} mm statt {targetH:g} mm.')
    if spec.style=='polygon': warnings.append('Breite bezeichnet den Durchmesser des Eckkreises, nicht das Maß über parallele Flächen.')
    return BoxResult(spec,parts,(x1-x0,y1-y0,actualH),(c-a,d-b,rings*t),warnings)


def generate(spec):
    spec.validate()
    result=rectangular(spec) if spec.style=='rect' else laminated(spec)
    for part in result.parts:
        if part.nominal.is_empty or not part.nominal.is_valid or part.nominal.geom_type!='Polygon': raise ValueError('Ungültiges Schnittteil: '+part.name)
        part.geometry=part.nominal.buffer(spec.kerf/2,join_style=2) if spec.kerf else part.nominal
        if part.geometry.geom_type!='Polygon' or not part.geometry.is_valid or len(part.geometry.interiors)!=len(part.nominal.interiors): raise ValueError('Schnittspaltkorrektur zerstört Konturen: '+part.name)
    if spec.kerf: result.warnings.append(f'Konturen bereits um halben Schnittspalt ({spec.kerf/2:g} mm) versetzt. Keine zweite Kerf-Korrektur anwenden.')
    return result


def placed_geometry(part,placement):
    geo=affinity.rotate(part.geometry,placement.rotation,origin=(0,0)) if placement.rotation else part.geometry
    a,b,_,_=geo.bounds
    return affinity.translate(geo,placement.x-a,placement.y-b)


def arrange(result,width=400.,height=400.,margin=5.):
    if any(not math.isfinite(v) for v in (width,height,margin)) or min(width,height)<=2*margin or margin<0: raise ValueError('Ungültige Plattengröße')
    gap=result.spec.gap; page=0; x=y=margin; rowH=0.; placements=[]
    for index in sorted(range(len(result.parts)),key=lambda i:(result.parts[i].geometry.bounds[3]-result.parts[i].geometry.bounds[1]),reverse=True):
        a,b,c,d=result.parts[index].geometry.bounds; w,h=c-a,d-b; rotation=0
        options=[(w,h,0),(h,w,90)]
        fits=[o for o in options if o[0]<=width-2*margin+1e-8 and o[1]<=height-2*margin+1e-8]
        if not fits: raise ValueError(f'Teil „{result.parts[index].name}“ ({w:.1f} × {h:.1f} mm) passt nicht auf {width:g} × {height:g} mm. Es wird nicht automatisch skaliert.')
        inrow=[o for o in fits if x+o[0]<=width-margin+1e-8 and y+max(rowH,o[1])<=height-margin+1e-8]
        if inrow: w,h,rotation=min(inrow,key=lambda o:max(rowH,o[1]))
        else:
            x=margin; y+=rowH+gap; rowH=0.
            feasible=[o for o in fits if y+o[1]<=height-margin+1e-8]
            if not feasible: page+=1; y=margin; feasible=fits
            w,h,rotation=min(feasible,key=lambda o:o[1])
        placements.append(Placement(index,page,x,y,rotation)); x+=w+gap; rowH=max(rowH,h)
    return placements


def into_project(project,result,placements,model_id=None):
    """Atomic replacement of one generated model; unrelated objects are retained."""
    from copy import deepcopy
    from steburn.core.model import Layer,Shape
    from steburn.core.paths import as_paths_shape,geometry_paths
    p=deepcopy(project); mid=model_id or uuid4().hex
    models=p.extensions.setdefault('box_models',{})
    old=models.get(mid,{})
    p.shapes=[s for s in p.shapes if s.extra.get('box_model')!=mid]
    used={s.layer for s in p.shapes}; oldLayers=set(old.get('layers',[]))
    p.layers=[l for l in p.layers if l.id not in oldLayers or l.id in used]
    layers={}
    for page in sorted({v.page for v in placements}):
        layer=Layer(f'Box · Platte {page+1}',color='#df493b',mode='Kontur',power=0,output=False,visible=(page==0))
        layers[page]=layer; p.layers.append(layer)
    for place in placements:
        part=result.parts[place.part]
        s=Shape('polygon',layer=layers[place.page].id,name=part.name,
                extra={'processing':{'operation':'cut'},'box_model':mid,'box_part':place.part,'box_page':place.page,'kerf_applied_mm':result.spec.kerf,'group':mid+'-'+str(place.page)})
        as_paths_shape(s,geometry_paths(placed_geometry(part,place))); p.shapes.append(s)
    models[mid]={'version':1,'parameters':asdict(result.spec),'layers':[l.id for l in layers.values()],
                 'outer_mm':result.outer,'inner_mm':result.inner,'warnings':result.warnings,'pages':len(layers)}
    p.validate(); return p,mid,layers[0].id


def export_page(path,result,placements,width,height,page=0,kind='svg'):
    selected=[v for v in placements if v.page==page]
    if not selected: raise ValueError('Platte enthält keine Teile.')
    if kind=='svg':
        import xml.etree.ElementTree as ET
        root=ET.Element('svg',xmlns='http://www.w3.org/2000/svg',width=f'{width}mm',height=f'{height}mm',viewBox=f'0 0 {width} {height}')
        ET.SubElement(root,'metadata').text=json.dumps({'steburn_box_version':1,'parameters':asdict(result.spec)},ensure_ascii=False)
        for v in selected:
            part=result.parts[v.part]; geo=placed_geometry(part,v)
            d=' '.join('M '+' L '.join(f'{x:.5f},{height-y:.5f}' for x,y in ring.coords)+' Z' for ring in [geo.exterior,*geo.interiors])
            ET.SubElement(root,'path',d=d,fill='none',stroke='#df493b',attrib={'stroke-width':'0.1','data-part':part.name})
        ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
    elif kind=='dxf':
        import ezdxf
        doc=ezdxf.new(); doc.units=4; doc.header['$INSUNITS']=4; doc.layers.new('Schnitt',dxfattribs={'color':1})
        for v in selected:
            geo=placed_geometry(result.parts[v.part],v)
            for ring in [geo.exterior,*geo.interiors]: doc.modelspace().add_lwpolyline(list(ring.coords)[:-1],close=True,dxfattribs={'layer':'Schnitt'})
        doc.saveas(path)
    else: raise ValueError('Exportformat nicht unterstützt')
