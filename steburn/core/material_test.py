"""Versioned, positionable calibration coupon and operator observations."""
from dataclasses import dataclass,asdict
from uuid import uuid4
import hashlib,json,math,csv,os,tempfile
from pathlib import Path
from steburn.core.model import Project,Layer,Shape
from steburn.core.paths import as_paths_shape,bounds,shape_paths

@dataclass
class TestSpec:
    material: str
    thickness: float
    powers: tuple
    cut_speeds: tuple
    engrave_speeds: tuple
    cut_passes: int=1
    engrave_passes: int=1
    interval: float=.2
    x: float=20.
    y: float=20.
    label_power: float=20.
    label_speed: float=600.
    size: float=50.

def validate(spec,width=400,height=400):
    finite=lambda v:type(v) in (float,int) and math.isfinite(v)
    if not spec.material.strip(): raise ValueError('Materialname fehlt.')
    if len(spec.powers)!=5 or len(set(spec.powers))!=5 or not all(finite(v) and 0<=v<=100 for v in spec.powers) or not any(v>0 for v in spec.powers): raise ValueError('Genau fünf verschiedene Leistungen (0–100 %) angeben.')
    for speeds in (spec.cut_speeds,spec.engrave_speeds):
        if len(speeds)!=3 or len(set(speeds))!=3 or not all(finite(v) and 6<=v<=30000 for v in speeds): raise ValueError('Je drei verschiedene Geschwindigkeiten in mm/min angeben (6–30000).')
    if not finite(spec.thickness) or spec.thickness<0: raise ValueError('Ungültige Materialstärke.')
    if any(type(v) is not int or not 1<=v<=20 for v in (spec.cut_passes,spec.engrave_passes)): raise ValueError('Durchgänge: 1–20.')
    if not finite(spec.interval) or not .05<=spec.interval<=1: raise ValueError('Gravurabstand: 0,05–1 mm.')
    if not finite(spec.size) or not 50<=spec.size<=300: raise ValueError('Testgröße: 50–300 mm. Mindestens 50 mm für lesbare Beschriftungen.')
    if not all(finite(v) for v in (spec.x,spec.y,spec.label_power,spec.label_speed)) or not 5<=spec.x<=width-spec.size-5 or not 5<=spec.y<=height-spec.size-5: raise ValueError(f'{spec.size:g}-mm-Testfläche benötigt mindestens 5 mm Randabstand. Position oder Größe anpassen.')
    if not 0<=spec.label_power<=100 or not 6<=spec.label_speed<=30000: raise ValueError('Ungültige Beschriftungswerte.')
    return spec

# A small built-in stroke alphabet makes labels independent of installed fonts.
SEGMENTS=[((0,1),(.5,1)),((.5,1),(.5,.5)),((.5,.5),(.5,0)),((0,0),(.5,0)),((0,.5),(0,0)),((0,1),(0,.5)),((0,.5),(.5,.5))]
DIGITS={'0':'012345','1':'12','2':'01643','3':'01236','4':'5612','5':'05623','6':'054326','7':'012','8':'0123456','9':'012356'}
LETTERS={
 'S':[[(.5,1),(0,1),(0,.5),(.5,.5),(.5,0),(0,0)]], 'C':[[ (.5,1),(0,1),(0,0),(.5,0)]],
 'H':[[(0,1),(0,0)],[(.5,1),(.5,0)],[(0,.5),(.5,.5)]], 'N':[[(0,0),(0,1),(.5,0),(.5,1)]],
 'I':[[(0,1),(.5,1)],[(.25,1),(.25,0)],[(0,0),(.5,0)]], 'T':[[(0,1),(.5,1)],[(.25,1),(.25,0)]],
 'G':[[ (.5,1),(0,1),(0,0),(.5,0),(.5,.5),(.25,.5)]], 'R':[[(0,0),(0,1),(.5,1),(.5,.5),(0,.5),(.5,0)]],
 'A':[[(0,0),(.25,1),(.5,0)],[(.125,.5),(.375,.5)]], 'V':[[(0,1),(.25,0),(.5,1)]], 'U':[[(0,1),(0,0),(.5,0),(.5,1)]],
 'P':[[(0,0),(0,1),(.5,1),(.5,.5),(0,.5)]], 'F':[[(0,0),(0,1),(.5,1)],[(0,.5),(.4,.5)]],
 'M':[[(0,0),(0,1),(.25,.5),(.5,1),(.5,0)]], '/':[[(0,0),(.5,1)]],
 '%':[[(0,0),(.5,1)],[(0,.9),(.08,1),(.16,.9),(.08,.8),(0,.9)],[(.34,.1),(.42,.2),(.5,.1),(.42,0),(.34,.1)]],
 '.':[[ (.2,0),(.25,0)]], '-':[[(0,.5),(.5,.5)]],
}
def label_paths(text,x,y,height):
    result=[]
    for index,char in enumerate(text.upper()):
        paths=[SEGMENTS[int(i)] for i in DIGITS[char]] if char in DIGITS else LETTERS.get(char,[])
        result.extend([[(x+(index*.7+a)*height,y+b*height) for a,b in path] for path in paths])
    return result

# Continuous, conventional numerals avoid the tiny seven-segment appearance.
READABLE_DIGITS={
 '0': [[(.12,0),(0,.15),(0,.85),(.12,1),(.42,1),(.56,.85),(.56,.15),(.42,0),(.12,0)]],
 '1': [[(.06,.78),(.3,1),(.3,0)],[(.06,0),(.54,0)]],
 '2': [[(0,.8),(.1,1),(.43,1),(.56,.83),(.52,.65),(0,0),(.56,0)]],
 '3': [[(0,1),(.56,1),(.26,.56),(.44,.56),(.56,.4),(.56,.16),(.42,0),(.1,0),(0,.12)]],
 '4': [[(.44,0),(.44,1),(0,.32),(.58,.32)]],
 '5': [[(.56,1),(0,1),(0,.56),(.42,.56),(.56,.42),(.56,.16),(.42,0),(.1,0),(0,.12)]],
 '6': [[(.52,.92),(.38,1),(.17,.92),(0,.6),(0,.16),(.14,0),(.42,0),(.56,.16),(.56,.4),(.42,.56),(0,.56)]],
 '7': [[(0,1),(.56,1),(.13,0)]],
 '8': [[(.14,.52),(0,.68),(0,.85),(.14,1),(.42,1),(.56,.85),(.56,.68),(.42,.52),(.14,.52),(0,.34),(0,.16),(.14,0),(.42,0),(.56,.16),(.56,.34),(.42,.52)]],
 '9': [[(.56,.44),(.14,.44),(0,.6),(0,.85),(.14,1),(.42,1),(.56,.85),(.56,.4),(.4,.08),(.18,0),(.04,.08)]],
}

def readable_label(text,x,y,height,max_width=None):
    paths=[]
    for i,char in enumerate(text.upper()):
        glyph=READABLE_DIGITS.get(char,LETTERS.get(char,[]))
        paths.extend([[(i*.78+a,b) for a,b in path] for path in glyph])
    if not paths: return []
    width=max(a for path in paths for a,b in path)
    sx=min(height,max_width/width) if max_width and width else height
    return [[(x+a*sx,y+b*height) for a,b in path] for path in paths]

def generate(spec,width=400,height=400,pattern_version=3):
    validate(spec,width,height); identifier=uuid4().hex
    if pattern_version not in (1,2,3): raise ValueError('Unbekannte Prüfmuster-Version.')
    if pattern_version==1 and spec.size!=50: raise ValueError('Historische Prüfmuster haben eine feste Größe von 50 mm.')
    values=asdict(spec)
    if pattern_version==1: values.pop('size')
    signature=hashlib.sha256(json.dumps(dict(pattern=pattern_version,**values),sort_keys=True).encode()).hexdigest()
    engrave=Layer('Test · Gravur',mode='Fläche',operation='engrave',color='#1878d1')
    labels=Layer('Test · Kennzeichnung',operation='mark',color='#239461')
    cut=Layer('Test · Schnitt',operation='cut',color='#df493b')
    p=Project(title=f'Materialtest · {spec.material} · {spec.size:g} × {spec.size:g} mm',width=width,height=height,layers=[engrave,labels,cut])
    cells=[]
    def marked(name,paths):
        s=as_paths_shape(Shape('polyline',layer=labels.id,name=name),paths)
        s.extra.update(group=identifier,processing=dict(operation='mark',power=spec.label_power,speed=spec.label_speed,passes=1)); p.shapes.append(s)
        if pattern_version>=3 and 'Umriss' not in name: s.extra['constant_power']=True
    marked('50 × 50 mm Umriss (Markierung)',[[(spec.x,spec.y),(spec.x+50,spec.y),(spec.x+50,spec.y+50),(spec.x,spec.y+50),(spec.x,spec.y)]])
    def text(text,x,y,old_height,new_height,max_width=None):
        return label_paths(text,x,y,old_height) if pattern_version==1 else readable_label(text,x,y,new_height,max_width)
    for title,y in [('SCHNITT',47.5),('GRAVUR',25.2)]: marked(title,text(title,spec.x+1,spec.y+y,1.45,1.9))
    for powers_y in (45.0,22.5):
        marked('P %',text('P %',spec.x+.7,spec.y+powers_y,1.3,1.8))
        for col,power in enumerate(spec.powers): marked(f'Leistung {power:g} %',text(f'{power:g}',spec.x+8.2+col*8,spec.y+powers_y,1.4,1.9,6.6))
    for operation,speeds,base_y,layer,passes in [('engrave',spec.engrave_speeds,17.5,engrave,spec.engrave_passes),('cut',spec.cut_speeds,39.,cut,spec.cut_passes)]:
        for row,speed in enumerate(speeds):
            y=spec.y+base_y-row*5.5
            marked(f'{operation} Vorschub {speed:g}',text(f'{speed:g}',spec.x+.6,y+1,1.25,1.8,6.7))
            for col,power in enumerate(spec.powers):
                x=spec.x+8+col*8; cell_id=('C' if operation=='cut' else 'G')+f'{row*5+col+1:02}'
                h=4.1 if operation=='cut' else 3.7
                s=Shape('rect',x,y,5.8,h,layer.id,f'{cell_id} · {power:g}% · {speed:g} mm/min')
                s.extra.update(group=identifier,material_cell=cell_id,processing=dict(operation=operation,power=power,speed=speed,passes=passes,interval=spec.interval,fill='lines'))
                p.shapes.append(s)
                cells.append(dict(id=cell_id,operation=operation,power=power,speed=speed,passes=passes,x=x,y=y,w=5.8,h=h))
    marked('Legende',text('F MM/MIN   P %',spec.x+1.2,spec.y+1.4,1.3,1.7))
    factor=spec.size/50
    if factor!=1:
        point=lambda x,y:(spec.x+(x-spec.x)*factor,spec.y+(y-spec.y)*factor)
        for shape in p.shapes:
            if shape.kind=='rect': shape.x,shape.y=point(shape.x,shape.y); shape.w*=factor; shape.h*=factor
            else: as_paths_shape(shape,[[point(x,y) for x,y in path] for path in shape_paths(shape)])
        for cell in cells:
            cell['x'],cell['y']=point(cell['x'],cell['y']); cell['w']*=factor; cell['h']*=factor
    p.extensions['material_test']=dict(id=identifier,pattern_version=pattern_version,pattern_hash=signature,size_mm=[spec.size,spec.size],spec=values,cells=cells)
    p.validate()
    x0,y0,x1,y1=bounds(p.shapes)
    if min(x0-spec.x,y0-spec.y)<-1e-6 or max(x1-spec.x,y1-spec.y)>spec.size+.000001: raise ValueError('Beschriftung überschreitet die Testfläche. Werte kürzer wählen.')
    return p

def label_project(project):
    """Independent label-only probe at exactly the coupon's final location."""
    from copy import deepcopy
    result=deepcopy(project); result.title='Beschriftungsprobe · '+project.title
    result.shapes=[s for s in result.shapes if not s.extra.get('material_cell')]
    result.extensions['material_test']['phase']='labels_only'
    return result

def export_assignment(path,session):
    """Readable reference map also works for already burned, unlabelled tests."""
    from PIL import Image,ImageDraw,ImageFont
    from steburn.core.paths import font_path
    test=session['test']; spec=test['spec']; size=test['size_mm'][0]
    image=Image.new('RGB',(1400,1550),'white'); draw=ImageDraw.Draw(image)
    font=ImageFont.truetype(str(font_path()),25); small=ImageFont.truetype(str(font_path()),21); title=ImageFont.truetype(str(font_path()),35)
    draw.text((45,25),f'Materialtest: {spec["material"]}',font=title,fill='#17263a')
    draw.text((45,78),f'{size:g} × {size:g} mm · X {spec["x"]:g} / Y {spec["y"]:g} · oben Schnitt, unten Gravur',font=font,fill='#334155')
    draw.text((45,120),'Ansicht wie im Prüfmuster; alle Werte stehen direkt im jeweiligen Feld.',font=small,fill='#475569')
    for section,operation in enumerate(('cut','engrave')):
        top=200+section*600; draw.text((45,top),'SCHNITT' if operation=='cut' else 'GRAVUR',font=title,fill='#17263a')
        for i,cell in enumerate(c for c in test['cells'] if c['operation']==operation):
            row,col=divmod(i,5); x=45+col*265; y=top+60+row*155
            draw.rectangle((x,y,x+250,y+140),outline='#df493b' if operation=='cut' else '#1878d1',width=3)
            draw.text((x+12,y+9),cell['id'],font=title,fill='#17263a')
            draw.text((x+12,y+57),f'{cell["power"]:g} %',font=font,fill='#17263a')
            draw.text((x+12,y+96),f'{cell["speed"]:g} mm/min · {cell["passes"]}×',font=small,fill='#17263a')
    draw.text((45,1435),f'Versuch: {test["id"]}',font=small,fill='#475569')
    image.save(path)

def save_session(path,data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as file: json.dump(data,file,ensure_ascii=False,indent=2)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def export_results(path,session):
    fields=['id','operation','power','speed','passes','depth_mm','cut_through','quality','notes']
    with Path(path).open('w',encoding='utf-8-sig',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=fields,delimiter=';'); writer.writeheader()
        for cell in session['test']['cells']:
            observation=session.get('observations',{}).get(cell['id'],{})
            writer.writerow({key:cell.get(key,observation.get(key,'')) for key in fields})
