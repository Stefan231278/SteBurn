import sys,time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from steburn.ui.live_app import App
from steburn.core.model import Shape
from steburn.core.nodes import paths
from steburn.core.paths import shape_paths,bounds
from steburn.core.processing import resolve
from PIL import ImageGrab

a=App(); errors=[]; a.report_callback_exception=lambda *args:errors.append(args)
def settle():
    for _ in range(5): a.update(); time.sleep(.03)
def event(x,y,state=0):
    px,py=a.screen(x,y); return SimpleNamespace(x=px,y=py,state=state)
def drag(start,end):
    a.press(event(*start)); a.motion(event(*end)); a.release(event(*end)); settle()
settle(); rect=Shape('rect',20,20,40,30,a.active_layer); a.p.shapes=[rect]; a.selection={rect.id}; a.selected=rect.id; a.refresh(); settle()
a.set_tool('nodes'); settle(); assert len(list(a.node_points()))==4
drag((20,20),(15,23)); r=a.current(); assert shape_paths(r)[0][0]==shape_paths(r)[0][-1]
assert all(abs(x-y)<1e-6 for x,y in zip(shape_paths(r)[0][0],(15,23))),shape_paths(r)
a.press(event(10,10)); a.motion(event(70,70)); a.release(event(70,70)); settle(); assert len(a.node_keys)==4
drag((15,23),(20,28)); assert len(a.node_keys)==4
r=a.current(); assert all(abs(x-y)<1e-6 for x,y in zip(shape_paths(r)[0][0],(20,28)))
item=a.canvas.find_withtag('node-scale:e')[0]; x0,y0,x1,y1=a.canvas.coords(item); start=SimpleNamespace(x=(x0+x1)/2,y=(y0+y1)/2,state=0)
before=bounds([r]); a.press(start); end=SimpleNamespace(x=start.x+20*a.scale,y=start.y,state=0); a.motion(end); a.release(end); settle()
after=bounds([a.current()]); assert abs((after[2]-after[0])-(before[2]-before[0])-20)<1e-6; assert after[3]-after[1]==before[3]-before[1]
a.set_tool('polygon'); a.press(event(100,100)); a.mouse_move(event(130,100)); assert a.canvas.find_withtag('construction-preview')
a.escape(); a.set_tool('line'); a.press(event(100,100)); a.motion(event(150,140)); assert a.canvas.type(a.canvas.find_withtag('ghost')[0])=='line'; a.release(event(150,140)); settle()
a.set_tool('bezier'); a.press(event(100,40)); a.mouse_move(event(120,90)); assert a.canvas.find_withtag('construction-preview')
a.press(event(120,90)); a.press(event(150,90)); a.mouse_move(event(170,40)); assert len(a.canvas.find_withtag('construction-preview'))==2
a.press(event(170,40)); settle(); curve=a.current(); assert 'bezier' in curve.extra
old=paths(curve)[0]; drag(old[0],(105,45)); new=paths(a.current())[0]; assert all(abs(x-y)<1e-6 for point,target in zip(new[:2],[(105,45),(125,95)]) for x,y in zip(point,target)),new
ImageGrab.grab(window=a.winfo_id()).save('docs/Steburn-0.10-knoten.png')
ellipse=Shape('ellipse',200,200,40,40,a.active_layer); a.p.shapes.append(ellipse); a.selection={ellipse.id}; a.selected=ellipse.id; a.refresh(); settle()
key,point=next(iter(a.node_points())); drag(point,(point[0]+2,point[1]+3)); contour=shape_paths(a.current())[0]
assert contour[0]==contour[-1] and a.current().kind=='polygon'
count=len(a.p.layers); a.add_layer(); target=a.active_layer; extra=Shape('ellipse',200,100,40,40,target); a.p.shapes.append(extra); a.refresh(); settings=resolve(extra,next(l for l in a.p.layers if l.id==target))
a.remove_layer(); settle(); assert len(a.p.layers)==count and len(a.p.shapes)==5
moved=next(s for s in a.p.shapes if s.id==extra.id); assert resolve(moved,next(l for l in a.p.layers if l.id==moved.layer))==settings
a.undo(); settle(); assert any(l.id==target for l in a.p.layers)
assert not errors,errors
a.destroy(); print('Drawing GUI OK: primitive and multi-node editing, closure, stretch, live line/polygon/cubic previews, tangent movement and layer removal/undo')
