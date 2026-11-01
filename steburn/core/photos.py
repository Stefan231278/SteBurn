"""Reversible photo processing shared by preview and laser bitmap generation."""
from dataclasses import dataclass,asdict
from copy import deepcopy
import base64,io,math
from PIL import Image,ImageOps,ImageEnhance,ImageFilter

MODES={'gray','floyd','atkinson','threshold'}

@dataclass
class PhotoSettings:
    brightness: float=1.
    contrast: float=1.
    gamma: float=1.
    sharpness: float=1.
    black: int=0
    white: int=255
    threshold: int=128
    invert: bool=False
    autocontrast: bool=False
    mode: str='floyd'
    crop: tuple=(0.,0.,1.,1.)
    rotate: int=0
    mirror: bool=False

def settings_from(values=None):
    p=PhotoSettings(**(values or {}))
    def finite(v): return type(v) in (float,int) and math.isfinite(v)
    for key,lo,hi in [('brightness',.1,3),('contrast',.1,4),('gamma',.2,3),('sharpness',0,4)]:
        if not finite(getattr(p,key)) or not lo<=getattr(p,key)<=hi: raise ValueError('Bildwert außerhalb des Bereichs: '+key)
    if not all(type(v) is int for v in (p.black,p.white,p.threshold)) or not 0<=p.black<p.white<=255 or not 0<=p.threshold<=255: raise ValueError('Schwarzpunkt muss kleiner als Weißpunkt sein (0–255).')
    if p.mode not in MODES or p.rotate not in (0,90,180,270): raise ValueError('Unbekannter Bildmodus / Drehwinkel.')
    if not isinstance(p.crop,(list,tuple)) or len(p.crop)!=4 or not all(finite(v) for v in p.crop) or not 0<=p.crop[0]<p.crop[2]<=1 or not 0<=p.crop[1]<p.crop[3]<=1: raise ValueError('Ungültiger Zuschnitt.')
    if any(type(v) is not bool for v in (p.invert,p.autocontrast,p.mirror)): raise ValueError('Ungültiger Bildschalter.')
    return p

def decode_image(data):
    with Image.open(io.BytesIO(base64.b64decode(data,validate=True))) as source:
        if source.width*source.height>40_000_000: raise ValueError('Bild zu groß (max. 40 Megapixel).')
        rgba=source.convert('RGBA'); white=Image.new('RGBA',rgba.size,'white'); white.alpha_composite(rgba)
        return white.convert('RGB')

def encode_image(image):
    data=io.BytesIO(); image.save(data,format='PNG'); return base64.b64encode(data.getvalue()).decode('ascii')

def cropped_size(source_size,settings):
    p=settings_from(settings) if isinstance(settings,dict) else settings
    w,h=source_size
    width=max(1,round(w*(p.crop[2]-p.crop[0]))); height=max(1,round(h*(p.crop[3]-p.crop[1])))
    return (height,width) if p.rotate in (90,270) else (width,height)

def raster_size(width,height,interval,passes=1):
    if not all(type(v) in (int,float) and math.isfinite(v) and v>0 for v in (width,height,interval)) or not .02<=interval<=5: raise ValueError('Ungültige Bildmaße oder Rasterabstand (0,02–5 mm).')
    if type(passes) is not int or not 1<=passes<=1000: raise ValueError('Ungültige Durchgänge.')
    size=(max(1,math.ceil(width/interval)),max(1,math.ceil(height/interval)))
    if size[0]*size[1]*passes>120000:
        suggested=max(.02,math.ceil(math.sqrt(width*height*passes/110000)*100)/100)
        raise ValueError(f'Raster zu groß für den vorhandenen Auftragsplan. Abstand mindestens ca. {suggested:g} mm wählen oder Bild verkleinern.')
    return size

def recommended_interval(width,height,passes=1):
    return max(.2,math.ceil(math.sqrt(width*height*passes/100000)*100)/100)

def render_photo(source,settings=None,target_size=None):
    p=settings_from(settings)
    image=decode_image(source) if isinstance(source,str) else source.convert('RGB')
    w,h=image.size; a,b,c,d=p.crop
    image=image.crop((int(a*w),int(b*h),max(int(a*w)+1,round(c*w)),max(int(b*h)+1,round(d*h))))
    if p.rotate: image=image.rotate(-p.rotate,expand=True)
    if p.mirror: image=ImageOps.mirror(image)
    if target_size:
        if len(target_size)!=2 or any(type(v) is not int or not 1<=v<=20000 for v in target_size) or target_size[0]*target_size[1]>125000: raise ValueError('Rasterauflösung überschreitet das vorhandene Planlimit.')
        image=image.resize(target_size,Image.Resampling.LANCZOS)
    image=ImageOps.grayscale(image)
    if p.autocontrast: image=ImageOps.autocontrast(image,cutoff=.5)
    image=ImageEnhance.Brightness(image).enhance(p.brightness)
    image=ImageEnhance.Contrast(image).enhance(p.contrast)
    if p.sharpness!=1: image=ImageEnhance.Sharpness(image).enhance(p.sharpness)
    lut=[round(255*(min(1,max(0,(v-p.black)/(p.white-p.black)))**(1/p.gamma))) for v in range(256)]
    image=image.point(lut)
    if p.invert: image=ImageOps.invert(image)
    if p.mode=='floyd': image=image.convert('1',dither=Image.Dither.FLOYDSTEINBERG).convert('L')
    elif p.mode=='threshold': image=image.point([0 if v<p.threshold else 255 for v in range(256)])
    elif p.mode=='atkinson':
        w,h=image.size; values=[float(v) for v in image.tobytes()]; output=bytearray(w*h)
        for y in range(h):
            for x in range(w):
                i=y*w+x; old=values[i]; new=255 if old>=p.threshold else 0; output[i]=new; error=(old-new)/8
                for dx,dy in ((1,0),(2,0),(-1,1),(0,1),(1,1),(0,2)):
                    nx,ny=x+dx,y+dy
                    if 0<=nx<w and ny<h: values[ny*w+nx]+=error
        image=Image.frombytes('L',(w,h),bytes(output))
    return image

def processed_shape(shape,values,width,height,interval,power,speed,passes):
    from steburn.core.model import Project
    settings=settings_from(values); size=raster_size(width,height,interval,passes)
    result=deepcopy(shape); source=shape.extra.get('image_original',shape.extra['image'])
    result.extra['image_original']=source
    result.extra['image_adjustments']=asdict(settings)
    result.extra['image']=encode_image(render_photo(source,asdict(settings),size))
    result.extra['pixels']=list(size); result.w=width; result.h=height
    result.extra['processing']={'operation':'engrave','fill':'lines','power':power,'speed':speed,'passes':passes,'interval':interval,'angle':0}
    # Validate all processing values before the UI can mutate a project.
    from steburn.core.processing import resolve
    from steburn.core.model import Layer
    resolve(result,Layer())
    return result
