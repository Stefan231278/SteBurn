"""Run manually on a graphical desktop: python tests/gui_smoke.py."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
from copy import deepcopy
from tkinter import messagebox,simpledialog
from steburn.ui.editor import App
from steburn.ui.simulation import Simulation
from steburn.core.planner import build_plan
from steburn.core.model import Project,Shape
from steburn.core.paths import bounds

messagebox.showinfo=lambda *args,**kwargs:None
messagebox.showerror=lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError(str(args)))
messagebox.askyesno=lambda *args,**kwargs:True
messagebox.askokcancel=lambda *args,**kwargs:True
app=App(); errors=[]; app.report_callback_exception=lambda *args: errors.append(args)
app.update(); app.fit(); app.update()

def event(x,y,state=0):
    sx,sy=app.screen(x,y); return SimpleNamespace(x=sx,y=sy,state=state)
assert app.coords(event(0,0))==(0,0)
app.set_tool('rect'); app.press(event(10,20)); app.motion(event(40,60)); app.release(event(40,60)); app.update()
assert all(abs(a-b)<1e-8 for a,b in zip(bounds(app.p.shapes),(10,20,40,60)))
app.duplicate(); app.update(); assert len(app.p.shapes)==2
app.undo(); app.update(); assert len(app.p.shapes)==1
app.redo(); app.update(); assert len(app.p.shapes)==2
app.selection={s.id for s in app.p.shapes}; app.selected=next(iter(app.selection)); app.refresh(); app.group(); app.update()
assert len({s.extra['group'] for s in app.p.shapes})==1
old=bounds(app.p.shapes); app.transform_selection('cw'); app.update(); new=bounds(app.p.shapes)
assert abs((old[2]-old[0])-(new[3]-new[1]))<1e-8
app.quick_layer(app.p.layers[1].id); app.update(); assert all(s.layer==app.p.layers[1].id for s in app.p.shapes)
app.add_layer(); app.update(); assert len(app.p.layers)==4
simpledialog.askstring=lambda *args,**kwargs:'Umbenannt'; app.rename_layer(); app.update(); assert app.p.layers[-1].name=='Umbenannt'
app.set_tool('polygon')
for pt in [(100,100),(130,100),(120,140)]: app.press(event(*pt))
app.finish_polygon(); app.update(); assert app.current().kind=='polygon'
app.set_tool('nodes'); app.update(); s=app.current()
app.notebook.select(app.page_tabs['layers']); app.update()
sim=Simulation(app,build_plan(app.p)); sim.update(); sim.draw(); sim.seek(str(sim.total/2)); sim.update_head(); sim.play(); sim.update(); sim.pause(); sim.reset(); sim.close(); app.update()
# Regression: bitmap resize handles, aspect lock, precision, system fonts and simulation.
from PIL import Image
from steburn.io.importers import image_shape
app.p=Project(); bitmap=image_shape(Image.new('RGB',(330,200),'grey'),app.p.layers[0].id,'Beil',width=100)
bitmap.x=107.28652751423151; bitmap.y=152.06831119544594
app.p.shapes=[bitmap]; app.selection={bitmap.id}; app.selected=bitmap.id; app.set_tool('select'); app.refresh(); app.update()
assert app.vars['x'].get()=='107.3' and app.vars['y'].get()=='152.1'
app.vars['name'].set('Beil neu'); app.apply(); app.update()
assert app.current().x==bitmap.x and app.current().y==bitmap.y
s=app.current(); ratio=s.w/s.h; x0,y0,x1,y1=bounds([s]); app.keep_ratio.set(True)
app.press(event(x1,y1)); assert app.drag[0]=='resize'
app.motion(event(x0+150,y0+110)); app.release(event(x0+150,y0+110)); app.update()
assert abs(app.current().w/app.current().h-ratio)<1e-8
app.undo(); app.update(); s=app.current(); x0,y0,x1,y1=bounds([s]); app.keep_ratio.set(False)
app.press(event(x1,y1)); app.motion(event(x0+150,y0+110)); app.release(event(x0+150,y0+110)); app.update()
assert abs(app.current().w-150)<1e-8 and abs(app.current().h-110)<1e-8
plan=build_plan(app.p); assert plan.segments
sim=Simulation(app,plan); sim.update(); sim.draw(); sim.seek(str(sim.total/2)); sim.update(); sim.close()
text_shape=Shape('text',30,30,80,15,app.p.layers[0].id,'Text','Steburn'); app.p.shapes.append(text_shape); app.selection={text_shape.id}; app.selected=text_shape.id; app.refresh(); app.load_fonts(); app.update()
assert app.fontbox['values']; app.fontbox.set(app.font_faces[0].label); app.system_font_selected(); app.update()
assert app.current().extra['font']==app.font_faces[0].path
app.geometry('1000x650'); app.update(); app.pages['props'].update(); assert app.page_tabs['props'].canvas.bbox('all')[3]>app.page_tabs['props'].canvas.winfo_height()
app.geometry('1320x850'); app.update()
assert not errors,errors
if '--screenshots' in sys.argv:
    from PIL import ImageGrab
    app.set_tool('select'); app.p=Project(title='Steburn – Beispielprojekt'); layer=app.p.layers[0].id
    app.p.shapes=[Shape('rect',70,100,240,140,layer,'Brettrahmen'),Shape('text',110,155,140,20,layer,'Beschriftung','Steburn'),Shape('ellipse',240,130,40,40,app.p.layers[2].id,'Markierung')]
    app.p.layers[0].power=20; app.selection={app.p.shapes[0].id}; app.selected=app.p.shapes[0].id; app.refresh(); app.fit(); app.notebook.select(app.page_tabs['layers']); app.update()
    ImageGrab.grab(bbox=(app.winfo_rootx(),app.winfo_rooty(),app.winfo_rootx()+app.winfo_width(),app.winfo_rooty()+app.winfo_height()),xdisplay=__import__('os').environ.get('DISPLAY')).save('docs/Steburn-Oberflaeche.png')
    sim=Simulation(app,build_plan(app.p)); sim.update(); sim.draw(); sim.seek(str(sim.total/2)); sim.update(); ImageGrab.grab(bbox=(sim.winfo_rootx(),sim.winfo_rooty(),sim.winfo_rootx()+sim.winfo_width(),sim.winfo_rooty()+sim.winfo_height()),xdisplay=__import__('os').environ.get('DISPLAY')).save('docs/Steburn-Simulation.png'); sim.close()
    app.p.save('examples/Steburn-Beispiel.steburn')
for timer in app.tk.call('after','info'): app.after_cancel(timer)
app.destroy(); print('GUI-Smoke: Editor, Simulation, Bitmap-Griffe, Seitenverhältnis, Präzision, Systemfonts und scrollbare Panels bestanden.')
