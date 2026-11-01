"""Box-module integration and one-row toolbar scenarios, no device access."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tkinter import messagebox,ttk
from PIL import ImageGrab
from steburn.ui.workbench import App
from steburn.ui.boxes import BoxDialog
from steburn.core.model import Project

messagebox.showinfo=lambda *a,**k:None
messagebox.showerror=lambda *a,**k:(_ for _ in ()).throw(AssertionError(str(a)))
messagebox.askokcancel=lambda *a,**k:True
app=App(); errors=[]; app.report_callback_exception=lambda *a:errors.append(a)
app.geometry('1400x940'); app.update(); app.reflow_header(); app.update()
assert all(w.master==app.header for w in app.workflow_buttons)
assert all(w.winfo_ismapped() for w in app.workflow_buttons)
ys={w.winfo_rooty() for w in app.header_actions if w.winfo_ismapped()}
assert len(ys)==1,ys
assert app.canvas.winfo_rooty()<app.header.winfo_rooty()+app.header.winfo_height()+30
# Narrow window retains primary actions; overflow keeps secondary commands available.
app.geometry('1000x700'); app.update(); app.reflow_header(); app.update()
assert app.lasern_button.winfo_ismapped()
assert app.lasern_button.winfo_width()>=app.lasern_button.winfo_reqwidth()
assert app.overflow.winfo_ismapped()
app.geometry('1400x940'); app.update(); app.reflow_header(); app.update()
r=BoxDialog(app); r.update(); assert r.result and r.placements
assert r.result.spec.style=='rect'
r.values['columns'].set('3'); r.values['rows'].set('2'); r.refresh_preview(); r.update()
assert len([p for p in r.result.parts if p.role=='divider'])==3
r.tabs.select(r.three); r.draw_3d(); r.update(); assert r.three.find_all()
r.explode.set(True); r.draw_3d(); r.update(); assert r.three.find_all()
# Unit change preserves physical dimensions.
w=r.result.spec.width; r.units.set('Zoll'); r.change_units(); r.refresh_preview()
assert r.result is not None,r.summary.get()
assert abs(r.result.spec.width-w)<1e-5
r.units.set('mm'); r.change_units(); r.refresh_preview()
# Invalid edits disable apply/export instead of retaining stale valid geometry.
r.values['thickness'].set('0'); r.refresh_preview(); assert r.apply_button.instate(['disabled'])
r.values['thickness'].set('3'); r.refresh_preview(); assert r.apply_button.instate(['!disabled'])
r.apply(); app.update()
assert app.p.extensions['box_models'] and app.p.shapes
mid=app.current().extra['box_model']; old=len(app.p.shapes)
r=BoxDialog(app); r.update(); assert r.model_id==mid
r.values['width'].set('130'); r.refresh_preview(); r.apply(); app.update()
assert len(app.p.shapes)==old
assert app.p.extensions['box_models'][mid]['parameters']['width']==130
menu=app.object_menu(); assert any(menu.type(i)!='separator' and menu.entrycget(i,'label')=='Boxparameter bearbeiten …' for i in range(menu.index('end')+1))
# New laminated polygon model and page selection.
app.selection.clear(); app.selected=None; app.refresh()
r=BoxDialog(app); r.values['columns'].set('3'); r.values['height'].set('30')
for label in ['Runde Dose · Schichtbau','Abgerundet · Schichtbau','Vieleck · Schichtbau']:
    r.style.set(label); r.refresh_preview(); r.update(); assert r.result is not None,r.summary.get()
assert r.result.spec.style=='polygon'; assert len(r.pagebox['values'])>=2
r.tabs.select(r.three); r.draw_3d(); r.update()
ImageGrab.grab(bbox=(r.winfo_rootx(),r.winfo_rooty(),r.winfo_rootx()+r.winfo_width(),r.winfo_rooty()+r.winfo_height()),xdisplay=__import__('os').environ['DISPLAY']).save('docs/Steburn-0.4-Boxmodul.png')
r.close(); app.update()
app.fit(); app.update(); app.p.save('examples/Steburn-Box-Gefache.steburn')
ImageGrab.grab(bbox=(app.winfo_rootx(),app.winfo_rooty(),app.winfo_rootx()+app.winfo_width(),app.winfo_rooty()+app.winfo_height()),xdisplay=__import__('os').environ['DISPLAY']).save('docs/Steburn-0.4-Oberflaeche.png')
assert not errors,errors
assert app.device.serial is None
for timer in app.tk.call('after','info'): app.after_cancel(timer)
app.destroy(); print('GUI Boxen: einzeilige Leiste, Overflow, vier Formen, Gefache, 3D-Schema, Einheiten, Eingabesperre und Regeneration bestanden.')
