"""Explicit import capabilities; machine files are geometry only and never executed."""
from dataclasses import dataclass
from pathlib import Path
import io,base64,re,math
from steburn.core.model import Shape
from steburn.core.paths import as_paths_shape
from steburn.io.svg import import_svg as basic_svg

BITMAPS={'.bmp','.jpg','.jpeg','.png','.gif','.tif','.tiff','.tga','.webp'}
UNSUPPORTED={'.sc','.rd','.scpro2','.lbrn','.lbrn2','.mage'}
ALL_EXTENSIONS=sorted(BITMAPS|UNSUPPORTED|{'.svg','.dxf','.pdf','.ai','.gc','.gcode','.nc','.hpgl','.plt'})
@dataclass
class ImportResult:
    shapes: list
    warnings: list

def image_shape(im,layer,name,width=100):
    from PIL import Image
    if im.width*im.height>40_000_000: raise ValueError('Bild zu groß (maximal 40 Megapixel).')
    rgba=im.convert('RGBA'); bg=Image.new('RGBA',rgba.size,'white'); bg.alpha_composite(rgba); im=bg.convert('RGB')
    data=io.BytesIO(); im.save(data,format='PNG')
    return Shape('image',20,20,width,width*im.height/im.width,layer,name,extra={'image':base64.b64encode(data.getvalue()).decode(),'pixels':[im.width,im.height]})

def svg_import(path,layer):
    import xml.etree.ElementTree as ET
    from svgpathtools import parse_path
    raw=Path(path).read_bytes()
    if len(raw)>10_000_000 or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper(): raise ValueError('SVG zu groß oder enthält Deklarationen.')
    root=ET.fromstring(raw); vb=[float(x) for x in re.split(r'[ ,]+',root.get('viewBox','').strip()) if x]
    if len(vb)!=4 or vb[:2]!=[0,0] or vb[2]<=0 or vb[3]<=0: raise ValueError('SVG benötigt viewBox mit Ursprung 0,0.')
    def size(v):
        if v is None or not v.endswith('mm'): raise ValueError('SVG benötigt Breite/Höhe in mm für sicheren Maßstab.')
        return float(v[:-2])
    width=size(root.get('width')); height=size(root.get('height')); sx=width/vb[2]; sy=height/vb[3]
    # Basic importer validates unsupported structures too; paths handled separately.
    paths=[]
    for e in list(root.iter()):
        if any(k in e.attrib for k in ('transform','mask','clip-path','filter')): raise ValueError('SVG-Transformation/Maskierung noch nicht unterstützt; vor Import in Pfade umwandeln.')
        if e.tag.split('}')[-1]=='path':
            parsed=parse_path(e.get('d','')); contours=[]
            for sub in parsed.continuous_subpaths():
                pts=[]
                for seg in sub:
                    n=max(1,min(2000,math.ceil(seg.length(error=1e-3)*max(sx,sy)/.4)))
                    if not pts: pts.append((seg.start.real*sx,height-seg.start.imag*sy))
                    pts.extend((seg.point(i/n).real*sx,height-seg.point(i/n).imag*sy) for i in range(1,n+1))
                if len(pts)>1: contours.append(pts)
            if contours: paths.append(as_paths_shape(Shape('polyline',layer=layer,name='SVG-Pfad'),contours))
    if paths:
        # Strip only already processed paths, then use the conservative shape importer.
        for parent in root.iter():
            for child in list(parent):
                if child.tag.split('}')[-1]=='path': parent.remove(child)
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d)/'shape.svg'; ET.ElementTree(root).write(tmp,encoding='utf-8'); basic=basic_svg(tmp,layer)
    else: basic=basic_svg(path,layer)
    for s in basic:
        if s.kind in {'polygon','polyline'}:
            s.y=height-s.y; s.points=[[x,-y] for x,y in s.points]; as_paths_shape(s,[[(s.x+x,s.y+y) for x,y in s.points]])
        else: s.y=height-s.y-s.h
    return ImportResult(basic+paths,['SVG: Farben/Schriften werden nicht vollständig übernommen. Alle Objekte auf aktiver Ebene.'])

def dxf_import(path,layer):
    import ezdxf
    from ezdxf import units
    from ezdxf.path import make_path
    doc=ezdxf.readfile(path); unit=doc.header.get('$INSUNITS',0); warnings=[]
    factor=units.conversion_factor(unit,units.MM) if unit else 1
    if not unit: warnings.append('DXF ohne Einheit: Millimeter angenommen. Maße vor Verwendung prüfen.')
    shapes=[]
    for e in doc.modelspace():
        typ=e.dxftype()
        if typ not in {'LINE','LWPOLYLINE','POLYLINE','CIRCLE','ARC','ELLIPSE','SPLINE'}: raise ValueError(f'DXF-Element {typ} noch nicht unterstützt. Datei vollständig abgebrochen.')
        if getattr(e.dxf,'elevation',0) not in (0,None):
            value=e.dxf.elevation
            if isinstance(value,(int,float)) and value!=0: raise ValueError('Nur ebene DXF-Geometrie unterstützt.')
        pts=[(v.x*factor,v.y*factor) for v in make_path(e).flattening(.2/factor)]
        if len(pts)>1: shapes.append(as_paths_shape(Shape('polyline',layer=layer,name='DXF '+typ),[pts]))
    return ImportResult(shapes,warnings)

def hpgl_import(path,layer):
    raw=Path(path).read_text(encoding='ascii'); commands=re.findall(r'([A-Za-z]{2})([^;]*)(?:;|$)',raw)
    allowed={'IN','SP','PA','PR','PU','PD','VS','FS'}
    if any(cmd.upper() not in allowed for cmd,args in commands): raise ValueError('HPGL enthält nicht unterstützte Befehle (z. B. Kurven, Skalierung oder Beschriftung).')
    position=(0.,0.); absolute=True; down=False; contours=[]; current=[]
    for cmd,args in commands:
        cmd=cmd.upper()
        if cmd in {'IN','SP','VS','FS'}: continue
        if cmd=='PA': absolute=True
        if cmd=='PR': absolute=False
        if cmd=='PU':
            if len(current)>1: contours.append(current)
            current=[]; down=False
        if cmd=='PD': down=True
        nums=[float(n) for n in re.split(r'[,\s]+',args.strip()) if n]
        if len(nums)%2: raise ValueError('HPGL: unvollständiges Koordinatenpaar')
        for i in range(0,len(nums),2):
            pt=(nums[i]/40,nums[i+1]/40)
            if not absolute: pt=(position[0]+pt[0],position[1]+pt[1])
            if down:
                if not current: current=[position]
                current.append(pt)
            position=pt
    if len(current)>1: contours.append(current)
    shapes=[as_paths_shape(Shape('polyline',layer=layer,name='HPGL'),[c]) for c in contours]
    return ImportResult(shapes,['HPGL: 40 Einheiten/mm; Stift-, Geschwindigkeits- und Kraftwerte nicht übernommen.'])

def gcode_import(path,layer):
    # Deliberately restricted geometry import. Reject macros, arcs and machine-specific code.
    position=[0.,0.]; absolute=True; factor=1.; motion=0; laser=False; power=0.; paths=[]
    for raw in Path(path).read_text(encoding='utf-8-sig').splitlines():
        line=re.sub(r'\([^)]*\)','',raw).split(';')[0].strip().upper()
        if not line or line=='%': continue
        if any(c in line for c in '#[]$'): raise ValueError('GCode-Makros/Controllerbefehle werden nicht importiert.')
        tokens=re.findall(r'([A-Z])\s*([-+]?\d*\.?\d+)',line)
        leftover=re.sub(r'([A-Z])\s*([-+]?\d*\.?\d+)','',line).strip()
        if leftover: raise ValueError('Nicht unterstützte GCode-Syntax.')
        values={}
        for key,n in tokens:
            val=float(n)
            if key=='G':
                if val not in {0,1,4,17,20,21,90,91,94}: raise ValueError(f'G{val:g} noch nicht unterstützt; kein partieller Import.')
                if val in {0,1}: motion=int(val)
                if val==20: factor=25.4
                if val==21: factor=1.
                if val==90: absolute=True
                if val==91: absolute=False
            elif key=='M':
                if val not in {2,3,4,5,8,9,30}: raise ValueError(f'M{val:g} noch nicht unterstützt.')
                if val in {3,4}: laser=True
                if val==5: laser=False
            elif key=='S': power=val
            elif key in {'X','Y'}: values[key]=val*factor
            elif key=='Z':
                if val!=0: raise ValueError('GCode mit Z-Bewegung noch nicht unterstützt.')
            elif key not in {'F','N','P'}: raise ValueError(f'GCode-Wort {key} noch nicht unterstützt.')
        if not values: continue
        end=[values.get(k,position[i]) if absolute else position[i]+values.get(k,0) for i,k in enumerate(('X','Y'))]
        if motion==1 and laser and power>0: paths.append([tuple(position),tuple(end)])
        position=end
    shapes=[as_paths_shape(Shape('polyline',layer=layer,name='GCode-Geometrie'),[p]) for p in paths]
    return ImportResult(shapes,['GCode nur als Geometrie importiert. Maschinenbefehle nie ausgeführt; Leistung/Geschwindigkeit nicht übernommen. Nur G0/G1, keine Kreisbögen.'])

def import_file(path,layer):
    ext=Path(path).suffix.lower()
    if ext=='.svg': return svg_import(path,layer)
    if ext=='.dxf': return dxf_import(path,layer)
    if ext in {'.hpgl','.plt'}: return hpgl_import(path,layer)
    if ext in {'.gc','.gcode','.nc'}: return gcode_import(path,layer)
    if ext in BITMAPS:
        from PIL import Image,ImageOps
        with Image.open(path) as im:
            warnings=['Bildgröße zunächst 100 mm breit; gewünschte Maße rechts einstellen.']
            if getattr(im,'n_frames',1)>1: warnings.append('Mehrbilddatei: nur erstes Bild importiert.')
            shape=image_shape(ImageOps.exif_transpose(im),layer,Path(path).stem)
        return ImportResult([shape],warnings)
    if ext in {'.pdf','.ai'}:
        import fitz
        if ext=='.ai' and b'%PDF-' not in Path(path).read_bytes()[:1024]: raise ValueError('AI nur mit PDF-Kompatibilität unterstützt. Bitte als SVG oder PDF exportieren.')
        with fitz.open(path) as doc:
            if doc.is_encrypted: raise ValueError('Passwortgeschütztes PDF nicht unterstützt.')
            if len(doc)!=1: raise ValueError('Mehrseitiges PDF: gewünschte Seite zuerst als eigene PDF speichern.')
            page=doc[0]; pix=page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
            from PIL import Image
            with Image.open(io.BytesIO(pix.tobytes('png'))) as im: s=image_shape(im,layer,Path(path).stem,width=page.rect.width*25.4/72)
        return ImportResult([s],['PDF/AI als Rasterbild importiert (144 dpi), keine editierbaren Vektoren.'])
    if ext in UNSUPPORTED: raise ValueError(f'{ext}: proprietäres Projekt-/Maschinenformat noch nicht unterstützt. Aus LightBurn als SVG exportieren.')
    raise ValueError(f'Format {ext} nicht unterstützt.')

def export_svg(p,path):
    import xml.etree.ElementTree as ET
    from steburn.core.paths import shape_paths
    root=ET.Element('svg',xmlns='http://www.w3.org/2000/svg',width=f'{p.width}mm',height=f'{p.height}mm',viewBox=f'0 0 {p.width} {p.height}')
    for s in p.shapes:
        layer=next(l for l in p.layers if l.id==s.layer)
        if not layer.visible: continue
        if s.kind=='image':
            ET.SubElement(root,'image',{'x':str(s.x),'y':str(p.height-s.y-s.h),'width':str(s.w),'height':str(s.h),'href':'data:image/png;base64,'+s.extra['image']}); continue
        for pts in shape_paths(s):
            d='M '+' L '.join(f'{x:.6f},{p.height-y:.6f}' for x,y in pts)
            ET.SubElement(root,'path',{'d':d,'stroke':layer.color,'fill':'none','stroke-width':'0.2'})
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)
