"""Conservative SVG subset. Unsupported geometry aborts import: never silently drop paths."""
import xml.etree.ElementTree as ET
import re
from pathlib import Path
from steburn.core.model import Shape

def export_svg(p,path):
    root=ET.Element('svg',xmlns='http://www.w3.org/2000/svg',width=f'{p.width}mm',height=f'{p.height}mm',viewBox=f'0 0 {p.width} {p.height}')
    for l in p.layers:
        if not l.visible: continue
        g=ET.SubElement(root,'g',{'stroke':l.color,'fill':'none','stroke-width':'0.25'})
        for s in p.shapes:
            if s.layer!=l.id: continue
            a={'x':str(s.x),'y':str(s.y)}
            if s.kind=='rect': ET.SubElement(g,'rect',a|{'width':str(s.w),'height':str(s.h)})
            elif s.kind=='ellipse': ET.SubElement(g,'ellipse',{'cx':str(s.x+s.w/2),'cy':str(s.y+s.h/2),'rx':str(s.w/2),'ry':str(s.h/2)})
            elif s.kind=='line': ET.SubElement(g,'line',{'x1':str(s.x),'y1':str(s.y),'x2':str(s.x+s.w),'y2':str(s.y+s.h)})
            elif s.kind=='text':
                n=ET.SubElement(g,'text',a|{'y':str(s.y+s.h),'font-size':str(s.h),'font-family':'sans-serif','fill':l.color,'stroke':'none'}); n.text=s.text
            else: ET.SubElement(g,s.kind,{'points':' '.join(f'{s.x+x},{s.y+y}' for x,y in s.points)})
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)

def import_svg(path,layer):
    raw=Path(path).read_bytes()
    if len(raw)>5_000_000 or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper(): raise ValueError('SVG zu groß oder enthält nicht unterstützte Deklarationen.')
    root=ET.fromstring(raw); shapes=[]
    vb=root.get('viewBox')
    if vb:
        v=[float(n) for n in re.split(r'[ ,]+',vb.strip())]
        if len(v)!=4 or v[:2]!=[0,0]: raise ValueError('Nur SVG mit viewBox-Ursprung 0,0 unterstützt.')
        def mm(value):
            if value is None or not value.endswith('mm'): raise ValueError('SVG mit viewBox benötigt explizite Breite/Höhe in mm.')
            return float(value[:-2])
        sx=mm(root.get('width'))/v[2]; sy=mm(root.get('height'))/v[3]
    else:
        raise ValueError('SVG benötigt viewBox und physische Größe in mm; Maßstab sonst unklar.')
    for e in root.iter():
        tag=e.tag.split('}')[-1]
        if any(k in e.attrib for k in ('transform','clip-path','mask','filter')): raise ValueError('Transformationen/Masken sind noch nicht unterstützt.')
        if tag in {'svg','g','title','desc','metadata'}: continue
        def f(key,default=0): return float(e.get(key,str(default)))
        if tag=='rect': s=Shape('rect',f('x')*sx,f('y')*sy,f('width')*sx,f('height')*sy,layer)
        elif tag in {'ellipse','circle'}:
            rx=f('r') if tag=='circle' else f('rx'); ry=f('r') if tag=='circle' else f('ry')
            s=Shape('ellipse',(f('cx')-rx)*sx,(f('cy')-ry)*sy,2*rx*sx,2*ry*sy,layer)
        elif tag=='line':
            pts=[[f('x1')*sx,f('y1')*sy],[f('x2')*sx,f('y2')*sy]]
            s=Shape('polyline',layer=layer,points=pts)
        elif tag in {'polygon','polyline'}:
            nums=[float(n) for n in re.split(r'[ ,\s]+',e.get('points','').strip())]
            if len(nums)%2: raise ValueError('Ungültige SVG-Punkte')
            s=Shape(tag,layer=layer,points=[[nums[i]*sx,nums[i+1]*sy] for i in range(0,len(nums),2)])
        elif tag=='text':
            if list(e): raise ValueError('Mehrteiliger SVG-Text noch nicht unterstützt.')
            h=f('font-size',10)*sy; s=Shape('text',f('x')*sx,f('y')*sy-h,40,h,layer,text=e.text or '')
        else: raise ValueError(f'SVG-Element „{tag}“ noch nicht unterstützt. Import vollständig abgebrochen.')
        if s.kind in {'polygon','polyline'}:
            xs=[pt[0] for pt in s.points]; ys=[pt[1] for pt in s.points]
            s.x=min(xs); s.y=min(ys); s.w=max(xs)-s.x; s.h=max(ys)-s.y
            s.points=[[x-s.x,y-s.y] for x,y in s.points]
        s.name=tag; shapes.append(s)
    return shapes
