"""Original, antialiased tool symbols drawn from a shared 28-unit geometry."""
import math
from PIL import Image,ImageDraw

def draw_icon(name,dark=False,active=False,size=28):
    scale=size/28*4
    image=Image.new('RGBA',(size*4,size*4)); draw=ImageDraw.Draw(image)
    ink='#f3fbff' if active else '#d9e5f3' if dark else '#33465e'
    accent='#99f6e4' if active else '#5eead4' if dark else '#08978c'
    muted='#a0bdce' if active else '#748ca6' if dark else '#91a2b5'
    def points(values): return [(x*scale,y*scale) for x,y in values]
    def line(values,color=ink,width=2,round_caps=True):
        xy=points(values); w=max(1,round(width*scale)); draw.line(xy,fill=color,width=w,joint='curve')
        if round_caps:
            r=w/2
            for x,y in (xy[0],xy[-1]): draw.ellipse((x-r,y-r,x+r,y+r),fill=color)
    def circle(x,y,r,color=ink,fill=None,width=2):
        draw.ellipse(((x-r)*scale,(y-r)*scale,(x+r)*scale,(y+r)*scale),outline=color,fill=fill,width=max(1,round(width*scale)))
    def box(rect,color=ink,fill=None,radius=0,width=2):
        draw.rounded_rectangle(tuple(v*scale for v in rect),radius=radius*scale,outline=color,fill=fill,width=max(1,round(width*scale)))
    def polygon(values,color=ink,fill=None,width=2):
        draw.polygon(points(values),fill=fill)
        line(values+[values[0]],color,width,False)
    if name=='select':
        polygon([(5,3),(5,23),(10.4,17.5),(14.2,25),(18.1,23),(14.2,15.7),(22,15)],fill=ink,width=1)
        line([(6.5,5),(6.5,16)],accent,1.5)
    elif name=='rect':
        box((3.5,5,24.5,23),radius=3,width=2.2); box((20.5,19,25,23.5),color=accent,fill=accent,radius=1,width=1)
    elif name=='ellipse':
        draw.ellipse((3.5*scale,5*scale,24.5*scale,23*scale),outline=ink,width=round(2.2*scale))
        circle(22.3,9,2,accent,accent,width=1)
    elif name=='line':
        line([(5,23),(23,5)],ink,2.2)
        for x,y in ((5,23),(23,5)): circle(x,y,2.6,accent,accent,width=1)
    elif name=='bezier':
        line([(4,22),(7,5)],muted,1.2); line([(24,21),(20,4)],muted,1.2)
        curve=[]
        for i in range(41):
            t=i/40; u=1-t
            curve.append((u**3*4+3*u*u*t*7+3*u*t*t*20+t**3*24,u**3*22+3*u*u*t*5+3*u*t*t*4+t**3*21))
        line(curve,ink,2.2)
        for x,y in ((4,22),(24,21)): box((x-2.2,y-2.2,x+2.2,y+2.2),accent,accent,radius=.6,width=1)
        for x,y in ((7,5),(20,4)): circle(x,y,1.7,muted,muted,width=1)
    elif name=='pencil':
        polygon([(5,18),(18.8,4.2),(24,9.5),(10.2,23.3)],fill=ink,width=1)
        polygon([(5,18),(3,25),(10.2,23.3)],accent,accent,width=1)
        line([(17,6.1),(22,11.1)],accent,1.5)
        line([(8.5,18),(18.5,8)],'#243d51' if active or dark else '#ffffff',1.4)
    elif name=='polygon':
        vertices=[(14+10.5*math.cos(-math.pi/2+i*math.tau/6),14+10.5*math.sin(-math.pi/2+i*math.tau/6)) for i in range(6)]
        polygon(vertices,width=2.1)
        for x,y in (vertices[0],vertices[2],vertices[4]): circle(x,y,1.9,accent,accent,width=1)
    elif name=='nodes':
        line([(4,22),(13.5,6),(24,19)],ink,2)
        for x,y in ((4,22),(24,19)): box((x-2.3,y-2.3,x+2.3,y+2.3),ink,ink,radius=.6,width=1)
        box((10,2.5,17,9.5),accent,accent,radius=1.3,width=1)
        line([(18.5,3.5),(24.5,3.5)],muted,1.3)
    elif name=='text':
        line([(4,7),(4,4.5),(24,4.5),(24,7)],ink,2.1)
        line([(14,5),(14,24)],ink,2.4); line([(9.5,24),(18.5,24)],accent,2.1)
    elif name=='measure':
        polygon([(3,20),(20,3),(25,8),(8,25)],width=1.9)
        for t in (.22,.43,.64,.83):
            x,y=3+17*t,20-17*t; delta=2.6 if t==.43 else 1.8
            line([(x,y),(x+delta,y+delta)],accent,1.4)
    elif name=='position':
        circle(14,14,7.5,width=1.9)
        for a,b in [((14,2),(14,8)),((14,20),(14,26)),((2,14),(8,14)),((20,14),(26,14))]: line([a,b],ink,1.8)
        circle(14,14,2.5,'#fb7185','#fb7185',width=1)
    elif name=='import':
        box((3,4,24,22),radius=2.5,width=1.9)
        circle(18.5,9,2,accent,accent,width=1)
        line([(5,19),(10,13),(15,18),(18,15),(23,20)],ink,1.7)
        circle(22,22,5,accent,accent,width=1)
        line([(19.5,22),(24.5,22)],'#102c35',1.5); line([(22,19.5),(22,24.5)],'#102c35',1.5)
    elif name=='objects':
        polygon([(3,9),(14,3),(25,9),(14,15)],width=1.9)
        line([(3,14),(14,20),(25,14)],muted,1.9)
        line([(3,19),(14,25),(25,19)],accent,2)
    else: raise ValueError('Unbekanntes Werkzeugsymbol: '+name)
    return image.resize((size,size),Image.Resampling.LANCZOS)
