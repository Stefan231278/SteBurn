"""Editable cubic paths and rounded rectangles, in millimetres."""
import math

def cubic_points(nodes,tolerance=.04):
    if len(nodes)<4 or (len(nodes)-1)%3:
        raise ValueError('Eine Bézierkette benötigt 1 + 3n Kontrollpunkte.')
    if any(len(p)!=2 or not all(math.isfinite(v) for v in p) for p in nodes):
        raise ValueError('Ungültige Bézierpunkte.')
    result=[tuple(nodes[0])]
    def split(a,b,c,d,depth=0):
        # Distance of control polygon from the chord bounds flatness.
        length=math.dist(a,d)
        def distance(p):
            if length<1e-12: return math.dist(a,p)
            return abs((d[0]-a[0])*(a[1]-p[1])-(a[0]-p[0])*(d[1]-a[1]))/length
        if depth>=16 or max(distance(b),distance(c),math.dist(a,b)+math.dist(b,c)+math.dist(c,d)-length)<=tolerance:
            result.append(tuple(d)); return
        mid=lambda p,q:tuple((x+y)/2 for x,y in zip(p,q))
        ab,bc,cd=mid(a,b),mid(b,c),mid(c,d)
        abc,bcd=mid(ab,bc),mid(bc,cd); center=mid(abc,bcd)
        split(a,ab,abc,center,depth+1); split(center,bcd,cd,d,depth+1)
    for i in range(0,len(nodes)-1,3): split(*nodes[i:i+4])
    return result

def rounded_rectangle(width,height,radius):
    if not all(math.isfinite(v) for v in (width,height,radius)) or radius<0:
        raise ValueError('Ungültiger Eckenradius.')
    r=min(radius,width/2,height/2)
    if r<=0: return [(0,0),(width,0),(width,height),(0,height),(0,0)]
    points=[]
    for cx,cy,start in [(width-r,r,-90),(width-r,height-r,0),(r,height-r,90),(r,r,180)]:
        count=max(4,math.ceil((math.pi/2)/max(.01,2*math.acos(max(-1,1-.02/r)))))
        for i in range(count+1):
            a=math.radians(start+90*i/count); points.append((cx+r*math.cos(a),cy+r*math.sin(a)))
    points.append(points[0]); return points

def set_bezier(shape,absolute_nodes):
    """Keep control points and a sampled compatibility contour together."""
    from steburn.core.paths import as_paths_shape
    path=cubic_points(absolute_nodes)
    as_paths_shape(shape,[path])
    shape.extra['bezier']=[[x-shape.x,y-shape.y] for x,y in absolute_nodes]
    return shape

def split_cubic(nodes,segment):
    nodes=[list(p) for p in nodes]; i=segment*3
    if i<0 or i+3>=len(nodes): raise ValueError('Kein Kurvensegment gewählt.')
    a,b,c,d=nodes[i:i+4]
    mid=lambda p,q:[(x+y)/2 for x,y in zip(p,q)]
    ab,bc,cd=mid(a,b),mid(b,c),mid(c,d)
    abc,bcd=mid(ab,bc),mid(bc,cd); m=mid(abc,bcd)
    return nodes[:i]+[a,ab,abc,m,bcd,cd,d]+nodes[i+4:]

def rotate_shape(shape,angle,center=None):
    """Rotate editable cubic controls; other vector shapes become paths."""
    from copy import deepcopy
    from steburn.core.paths import bounds,shape_paths,as_paths_shape
    if not math.isfinite(angle): raise ValueError('Ungültiger Drehwinkel.')
    if shape.kind in ('image','text'): raise ValueError('Bild-/Textbearbeitung über den jeweiligen Bereich verwenden.')
    s=deepcopy(shape); a,b,c,d=bounds([s]); cx,cy=center or ((a+c)/2,(b+d)/2)
    rad=math.radians(angle); co,si=math.cos(rad),math.sin(rad)
    point=lambda x,y:(cx+(x-cx)*co-(y-cy)*si,cy+(x-cx)*si+(y-cy)*co)
    if 'bezier' in s.extra: return set_bezier(s,[point(s.x+x,s.y+y) for x,y in s.extra['bezier']])
    return as_paths_shape(s,[[point(x,y) for x,y in path] for path in shape_paths(s)])
