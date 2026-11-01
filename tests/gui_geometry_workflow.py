import sys,time
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from tkinter import ttk
from PIL import ImageGrab
from steburn.ui.live_app import App
from steburn.ui.simulation import Simulation
from steburn.ui.widgets import ScrollPanel
from steburn.core.model import Project,Shape
from steburn.core.paths import shape_paths,as_paths_shape
from steburn.core.nodes import paths
from steburn.core.order import layer_for_segment

a=App(); errors=[]; a.report_callback_exception=lambda *args:errors.append(args)
def settle():
    for _ in range(6): a.update(); time.sleep(.03)
def event(x,y):
    sx,sy=a.screen(x,y); return SimpleNamespace(x=sx,y=sy,state=0)
settle(); a.active_layer=a.p.layers[1].id; a.set_tool('line'); a.press(event(20,20)); a.motion(event(60,40)); a.release(event(60,40)); settle()
line=a.current(); assert len(shape_paths(line)[0])==2
assert len([t for item in a.canvas.find_all() for t in a.canvas.gettags(item) if t.startswith('line-end:')])==2
assert not [t for item in a.canvas.find_all() for t in a.canvas.gettags(item) if t.startswith('resize:'+line.id)]
a.press(event(20,20)); a.motion(event(15,25)); a.release(event(15,25)); settle()
assert abs(shape_paths(a.current())[0][0][0]-15)<1e-6
b=as_paths_shape(Shape('polyline',layer=a.active_layer),[[(100,60),(100,100)]])
a.p.shapes.append(b); a.selection={line.id,b.id}; a.selected=line.id; a.refresh(); a.join_contours(True,True); settle()
assert len(a.p.shapes)==1 and len(a.current().extra['bezier'])==10 and a.current().extra['tangent_anchors']==[3,6]
hexagon=as_paths_shape(Shape('polygon',layer=a.active_layer),[[(140,20),(160,20),(180,40),(180,60),(160,80),(140,60),(140,20)]])
a.p.shapes.append(hexagon); a.selection={hexagon.id}; a.selected=hexagon.id; a.set_tool('nodes'); a.refresh(); settle()
a.node_keys={(hexagon.id,0,0),(hexagon.id,0,2)}; a.delete(); settle(); contour=shape_paths(a.current())[0]
assert len(contour)==5 and contour[0]==contour[-1]
a.set_tool('measure'); a.press(event(150,150)); a.mouse_move(event(180,190)); settle()
assert any('50.00 mm'==a.canvas.itemcget(item,'text') for item in a.canvas.find_withtag('measure-live') if a.canvas.type(item)=='text')
a.press(event(180,190)); assert len(a.measurements)==1
a.press(event(200,150)); a.mouse_move(event(230,190)); a.press(event(230,190)); a.render(); assert len(a.measurements)==2 and len(a.canvas.find_withtag('dimension'))==4
ImageGrab.grab(window=a.winfo_id()).save('docs/Steburn-0.11-messen.png'); a.clear_measurements(); assert not a.canvas.find_withtag('dimension')
for x in (200,202): a.p.shapes.append(as_paths_shape(Shape('polyline',layer=a.active_layer),[[(x,200),(x+20,220)]]))
a.refresh(); a.snap_enabled.set(True); snapped=a.coords(event(201.8,200)); assert snapped==(202,200),snapped; a.snap_enabled.set(False)
window=tk.Toplevel(a); window.geometry('320x200'); panel=ScrollPanel(window); panel.pack(fill='both',expand=True); block=ttk.Frame(panel.content,height=20); block.pack(fill='x'); settle()
assert not panel.bar.winfo_manager(); block.configure(height=600); settle(); assert panel.bar.winfo_manager()=='pack'; block.configure(height=20); settle(); assert not panel.bar.winfo_manager(); window.destroy()
a.p=Project(); a.p.shapes=[Shape('rect',20+i*40,20,10,10,l.id) for i,l in enumerate(a.p.layers)]; a.active_layer=a.p.layers[0].id; a.selection=set(); a.selected=None; a.refresh(); settle()
original=[l.id for l in a.p.layers]; simulation=Simulation(a); settle(); simulation.order_widget.combo.current(0); simulation.order_widget.shift(1); settle()
assert [l.id for l in a.p.layers]==[original[1],original[0],original[2]]
assert layer_for_segment(simulation.project,next(s for s in simulation.plan.segments if s.power))==original[1]
ImageGrab.grab(window=simulation.winfo_id()).save('docs/Steburn-0.11-simulation.png'); simulation.close()
a.open_job(); settle(); cockpit=a.job_window; cockpit.order_widget.combo.current(0); cockpit.order_widget.shift(1); settle()
assert [l.id for l in a.p.layers]==original
before=[l.id for l in cockpit.project.layers]; cockpit.runner=SimpleNamespace(state='running'); cockpit.change_order(before[0],1); assert [l.id for l in cockpit.project.layers]==before; cockpit.runner=None
ImageGrab.grab(window=cockpit.winfo_id()).save('docs/Steburn-0.11-cockpit.png'); cockpit.close(); settle()
assert not errors,errors
a.destroy(); print('Geometry workflow GUI OK: line endpoints, tangent joining, multi-node deletion, nearest snap, live measurements, automatic scrollbar and editable/frozen execution order')
