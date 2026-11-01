"""Join open contours without changing existing geometry or process values."""
from copy import deepcopy
import math
from steburn.core.nodes import paths
from steburn.core.paths import as_paths_shape
from steburn.core.design import set_bezier
from uuid import uuid4

def endpoints(shape):
    contours=paths(shape)
    if len(contours)!=1 or len(contours[0])<2 or contours[0][0]==contours[0][-1]: raise ValueError('Bitte offene, einzelne Konturen auswählen.')
    return contours[0][0],contours[0][-1]

def cubic(shape,reverse=False):
    contour=paths(shape)[0]
    if reverse: contour=contour[::-1]
    if 'bezier' in shape.extra: return list(contour)
    result=[contour[0]]
    for a,b in zip(contour,contour[1:]): result.extend([tuple(x+(y-x)/3 for x,y in zip(a,b)),tuple(x+2*(y-x)/3 for x,y in zip(a,b)),b])
    return result

def join(first,second,end_first,end_second,curve=False,tangent=False):
    endpoints(first); endpoints(second)
    same=first.id==second.id
    if same and end_first==end_second: raise ValueError('Zwei unterschiedliche offene Endpunkte wählen.')
    if tangent and not curve: raise ValueError('Tangentiale Verbindung benötigt „Kurve“; eine Gerade kann beliebige Tangenten nicht glatt verbinden.')
    # The source ends at the joint; the target begins at it.
    a=cubic(first,reverse=end_first==0); b=cubic(second,reverse=end_second==1)
    if same: b=[a[0]]
    start,end=a[-1],b[0]; length=math.dist(start,end)
    if length<1e-7 and curve: raise ValueError('Endpunkte liegen bereits zusammen. Mit Gerade zu einer Kontur vereinigen.')
    constraints=[]
    if curve:
        if tangent:
            incoming=a[-2]; outgoing=a[1] if same else b[1]
            def unit(v):
                norm=math.hypot(*v)
                if norm<1e-9: raise ValueError('Tangente nicht bestimmbar: benachbarte Punkte oder Griffe liegen zusammen.')
                return tuple(x/norm for x in v)
            u=unit(tuple(x-y for x,y in zip(start,incoming))); v=unit(tuple(x-y for x,y in zip(outgoing,end)))
            c1=tuple(x+y*length/3 for x,y in zip(start,u)); c2=tuple(x-y*length/3 for x,y in zip(end,v))
            constraints=[len(a)-1,len(a)+2]
        else:
            dx,dy=end[0]-start[0],end[1]-start[1]
            c1=(start[0]+dx/3-dy/4,start[1]+dy/3+dx/4); c2=(start[0]+2*dx/3-dy/4,start[1]+2*dy/3+dx/4)
    else: c1=tuple(x+(y-x)/3 for x,y in zip(start,end)); c2=tuple(x+2*(y-x)/3 for x,y in zip(start,end))
    result=deepcopy(first)
    result.extra['group']=first.extra.get('group') or second.extra.get('group') or uuid4().hex
    if not curve and 'bezier' not in first.extra and 'bezier' not in second.extra:
        left=paths(first)[0]; right=paths(second)[0]
        if end_first==0: left=left[::-1]
        if end_second==1: right=right[::-1]
        result=as_paths_shape(result,[list(left)+([left[0]] if same else list(right)[1:] if length<1e-7 else list(right))])
    else:
        chain=a+([c1,c2,end] if length>=1e-7 or same else [])+([] if same else b[1:])
        result=set_bezier(result,chain)
        # Existing constraints survive orientation changes as well.
        old1=first.extra.get('tangent_anchors',[]); old2=second.extra.get('tangent_anchors',[])
        anchors=[len(a)-1-i if end_first==0 else i for i in old1]
        offset=len(a)+2 if length>=1e-7 else len(a)-1
        if not same: anchors.extend(offset+(len(b)-1-i if end_second==1 else i) for i in old2)
        anchors.extend(0 if same and i==len(chain)-1 else i for i in constraints)
        result.extra['tangent_anchors']=sorted(set(anchors))
    return result
