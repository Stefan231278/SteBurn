"""Preview geometry only. No machine output or physical result prediction."""
import math

def outline(s):
    if s.kind=='text': return []
    if s.kind=='ellipse':
        return [(s.x+s.w/2+math.cos(i*math.tau/96)*s.w/2,s.y+s.h/2+math.sin(i*math.tau/96)*s.h/2) for i in range(97)]
    if s.kind=='line': return [(s.x,s.y),(s.x+s.w,s.y+s.h)]
    if s.kind=='rect': return [(s.x,s.y),(s.x+s.w,s.y),(s.x+s.w,s.y+s.h),(s.x,s.y+s.h),(s.x,s.y)]
    pts=[(s.x+x,s.y+y) for x,y in s.points]
    return pts+[pts[0]] if s.kind=='polygon' else pts

def checks(p):
    warnings=[]; seen=set()
    for s in p.shapes:
        if not next(l for l in p.layers if l.id==s.layer).visible: continue
        pts=outline(s)
        if not pts:
            warnings.append(f'{s.name}: Text ist noch nicht in Laserpfade umgewandelt.'); continue
        if any(x<0 or y<0 or x>p.width or y>p.height for x,y in pts): warnings.append(f'{s.name}: außerhalb der Arbeitsfläche.')
        if s.kind in {'line','polyline'}: warnings.append(f'{s.name}: offene Kontur (bei Schnitt prüfen).')
        key=tuple((round(x,5),round(y,5)) for x,y in pts)
        if key in seen: warnings.append(f'{s.name}: identische Kontur mehrfach vorhanden.')
        seen.add(key)
    if any(l.visible and l.mode=='Fläche' and any(s.layer==l.id for s in p.shapes) for l in p.layers): warnings.append('Flächenfüllung wird in dieser Version noch nicht berechnet.')
    return warnings
