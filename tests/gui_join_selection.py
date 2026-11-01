import sys,time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from steburn.ui.live_app import App
from steburn.core.model import Shape
from steburn.core.paths import as_paths_shape,shape_paths
from PIL import ImageGrab

a=App(); errors=[]; a.report_callback_exception=lambda *args:errors.append(args)
def settle():
    for _ in range(6): a.update(); time.sleep(.03)
def event(x,y,state=0):
    px,py=a.screen(x,y); return SimpleNamespace(x=px,y=py,state=state)
def box(start,end,state=0):
    a.press(event(*start,state)); a.motion(event(*end,state)); a.release(event(*end,state)); settle()
settle()
first=as_paths_shape(Shape('polyline',layer=a.p.layers[0].id,name='Ziel'),[[(20,20),(100,80)]])
first.extra.update(group='target-group',processing={'operation':'mark','power':20})
base=as_paths_shape(Shape('polyline',layer=a.p.layers[1].id,name='Meine Basis'),[[(115,80),(180,120)]])
base.extra.update(group='base-group',processing={'operation':'cut','power':71,'speed':650})
partner=Shape('rect',250,200,20,20,first.layer,extra={'group':'target-group'})
a.p.shapes=[first,base,partner]; a.selection=set(); a.selected=None; a.refresh(); a.set_tool('select'); settle()
a.press(event(150,101.54)); a.release(event(150,101.54)); settle(); assert a.selection_order==[base.id]
a.set_tool('nodes'); box((95,70),(120,90))
assert a.node_keys=={(first.id,0,1),(base.id,0,0)},(a.node_keys,a.drag,a.selection,[(s.name,shape_paths(s)) for s in a.p.shapes])
assert a.ordered_node_keys()[0]==(base.id,0,0)
assert a.canvas.find_withtag('join-basis')
ImageGrab.grab(window=a.winfo_id()).save('docs/Steburn-0.11.1-basis.png')
before=a.p.to_dict(); a.join_contours(); settle()
assert len(a.p.shapes)==2; joined=next(s for s in a.p.shapes if s.id==base.id)
assert joined.name==base.name and joined.layer==base.layer and joined.extra['processing']==base.extra['processing']
assert joined.extra['group']=='base-group' and next(s for s in a.p.shapes if s.id==partner.id).extra['group']=='base-group'
assert a.selection=={base.id,partner.id}
a.undo(); settle(); assert a.p.to_dict()==before
# No previous object selection: one frame catches both previously unselected ends.
a.selection=set(); a.selected=None; a.selection_order=[]; a.node_keys=set(); a.node_order=[]; a.refresh(); box((95,70),(120,90))
assert a.node_keys=={(first.id,0,1),(base.id,0,0)} and a.ordered_node_keys() and a.ordered_node_keys()[0]==(first.id,0,1),(a.node_keys,a.selection,a.node_order,a.drag)
# Additive point selection retains chronology even if project order is opposite.
a.selection={first.id,base.id}; a.node_keys=set(); a.node_order=[]; a.refresh(); settle()
a.press(event(115,80)); a.release(event(115,80)); settle()
a.press(event(100,80,1)); a.release(event(100,80,1)); settle()
assert a.ordered_node_keys()==[(base.id,0,0),(first.id,0,1)],a.ordered_node_keys()
a.join_contours(True,True); settle(); assert next(s for s in a.p.shapes if s.id==base.id).extra.get('bezier')
assert not errors,errors
a.destroy(); print('Join selection GUI OK: unselected endpoints caught by frame, chronological base, inherited parameters, group union and undo')
