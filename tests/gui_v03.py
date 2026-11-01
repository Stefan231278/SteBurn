"""Graphical integration scenarios; run with DISPLAY set, not unittest discovery."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
from tkinter import messagebox,simpledialog
from steburn.ui.workbench import App
from steburn.core.model import Project,Shape
from steburn.core.planner import build_plan
from PIL import Image,ImageGrab
from steburn.io.importers import image_shape

errors=[]
messagebox.showinfo=lambda *a,**k:None
messagebox.showerror=lambda *a,**k:(_ for _ in ()).throw(AssertionError(str(a)))
messagebox.askyesno=lambda *a,**k:True
messagebox.askokcancel=lambda *a,**k:True
app=App(); app.report_callback_exception=lambda *a:errors.append(a); app.update(); app.fit(); app.update()
def event(x,y,state=0):
    a,b=app.screen(x,y); return SimpleNamespace(x=a,y=b,state=state,x_root=a,y_root=b)
app.set_tool('rect'); app.press(event(20,20)); app.motion(event(60,60)); app.release(event(60,60)); app.update()
assert app.tool=='select'
app.set_tool('ellipse'); app.pinned.set(True); app.press(event(100,100)); app.motion(event(130,130)); app.release(event(130,130)); app.update()
assert app.tool=='ellipse'
app.escape(); assert app.tool=='select'
app.selection.clear(); app.selected=None; app.refresh()
app.press(event(10,10)); app.motion(event(70,70)); app.release(event(70,70)); app.update()
assert len(app.selection)==1 and app.current().kind=='rect'
app.set_operation('engrave'); app.update(); assert app.current().extra['processing']['operation']=='engrave'
app.process_fill.set('Kreuzschraffur'); app.process_power.set('32'); app.apply_processing(); app.update()
assert any(s.power==32 for s in build_plan(app.p).segments)
# Tab click activates only, without changing selected objects.
s=app.current(); old_layer=s.layer
buttons=[w for w in app.palette.winfo_children() if w.winfo_class()=='Button']
buttons[1].invoke(); app.update(); assert app.current().layer==old_layer
menu=app.object_menu(); labels=[menu.entrycget(i,'label') for i in range(menu.index('end')+1) if menu.type(i)!='separator']
assert 'Bearbeitungsart' in labels and not any('Physisch' in v for v in labels)
# Job window and percentage preview preparation work without a device.
app.open_job(); app.update(); assert app.job_window.winfo_exists(); app.job_window.close(); app.update()
# Relief lazy module generates non-output layers while preserving original.
bitmap=image_shape(Image.linear_gradient('L').resize((40,40)),app.p.layers[0].id,'Reliefquelle',width=30)
app.p.shapes.append(bitmap); app.selection={bitmap.id}; app.selected=bitmap.id; app.refresh()
from steburn.ui.relief import ReliefDialog
r=ReliefDialog(app); r.update(); r.generate(); app.update()
relief=app.p.layers[-1]; assert not relief.output
assert len([s for s in app.p.shapes if s.layer==relief.id])==4
assert any(s.id==bitmap.id for s in app.p.shapes)
app.p=Project(title='Steburn 0.3 · Werkstatt'); l=app.p.layers[0]
a=Shape('rect',45,50,180,110,l.id,'Geschenkbrett',extra={'processing':{'operation':'engrave','fill':'cross','interval':1,'power':25}})
b=Shape('text',65,90,100,20,app.p.layers[1].id,'Beschriftung','Steburn',extra={'processing':{'operation':'mark'}})
c=Shape('ellipse',250,200,70,70,app.p.layers[2].id,'Konturschnitt',extra={'processing':{'operation':'cut'}})
app.p.shapes=[a,b,c]; app.selection={a.id}; app.selected=a.id; app.refresh(); app.fit(); app.geometry('1400x940'); app.notebook.select(app.processing_tab); app.update()
app.p.save('examples/Steburn-0.3-Beispiel.steburn')
ImageGrab.grab(bbox=(app.winfo_rootx(),app.winfo_rooty(),app.winfo_rootx()+app.winfo_width(),app.winfo_rooty()+app.winfo_height()),xdisplay=__import__('os').environ['DISPLAY']).save('docs/Steburn-0.3-Oberflaeche.png')
assert not errors,errors
for timer in app.tk.call('after','info'): app.after_cancel(timer)
app.destroy(); print('GUI 0.3: Einmalwerkzeuge, Esc, Rahmenauswahl, Objektgravur, Kontextmenü, Ebenen, Jobfenster und Relief bestanden.')
