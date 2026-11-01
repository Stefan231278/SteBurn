"""Interaction regression for button surfaces, contextual help and branding."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tkinter import ttk,messagebox
from steburn.ui.workbench import App
from steburn.ui.presentation import attach_help
from steburn.core.model import Project,Shape
from PIL import ImageGrab

messagebox.showinfo=lambda *a,**k:None
messagebox.showerror=lambda *a,**k:(_ for _ in ()).throw(AssertionError(str(a)))
app=App(); errors=[]; app.report_callback_exception=lambda *a:errors.append(a)
app.geometry('1400x940'); app.update(); app.fit(); app.reflow_header(); app.update()
def all_widgets(root):
    for child in root.winfo_children():
        yield child
        yield from all_widgets(child)
buttons=[w for w in all_widgets(app) if isinstance(w,(ttk.Button,ttk.Checkbutton))]
missing=[w.cget('text') for w in buttons if not hasattr(w,'usage_help')]
assert not missing,missing
assert app.appearance.logo is not None and len(app.appearance.icon_images)==5
assert not app.appearance.icon_error,app.appearance.icon_error
brand=next(w for w in all_widgets(app) if isinstance(w,ttk.Label) and w.cget('text')=='Steburn')
assert brand.cget('image')
style=ttk.Style(app)
assert 'Steburn.TButton.surface' in str(style.layout('TButton'))
select=next(w for w in buttons if w.cget('text')=='Auswählen / bewegen')
assert select.cget('style')=='Selected.TButton'
lasern=next(w for w in buttons if w.cget('text')=='Lasern')
assert lasern.cget('style')=='Toolbar.Accent.TButton'
assert lasern.winfo_width()>=lasern.winfo_reqwidth(),(lasern.winfo_width(),lasern.winfo_reqwidth())
assert 'öffnet' in lasern.usage_help.text.lower()
lasern.invoke(); app.update()
window=app.job_window
assert window.title()=='Steburn · Lasern'
assert window.start_button.cget('text')=='Auftrag starten · Lasern'
assert hasattr(window.start_button,'usage_help')
assert app.device.serial is None # Opening Lasern never opens a port or starts a job.
window.close(); app.update()
# Tooltip creation, positioning, hiding and destroy-before-delay.
lasern.usage_help.show(); app.update()
assert lasern.usage_help.window.winfo_ismapped()
lasern.usage_help.hide(); app.update(); assert lasern.usage_help.window is None
frame=ttk.Frame(app); button=ttk.Button(frame,text='Neu'); attach_help(frame)
button.usage_help.schedule(); button.destroy(); frame.destroy(); app.update()
# Screenshot of a real editor scene with visible buttons and logo.
p=Project(title='Steburn · Entwurf'); lid=p.layers[0].id
p.shapes=[Shape('rect',50,60,160,100,lid,'Holzbrett',extra={'processing':{'operation':'engrave','fill':'lines','interval':1}}),Shape('text',75,95,90,20,p.layers[1].id,'Schrift','Steburn')]
app.p=p; app.selection={p.shapes[0].id}; app.selected=p.shapes[0].id; app.refresh(); app.fit(); app.update()
ImageGrab.grab(bbox=(app.winfo_rootx(),app.winfo_rooty(),app.winfo_rootx()+app.winfo_width(),app.winfo_rooty()+app.winfo_height()),xdisplay=__import__('os').environ['DISPLAY']).save('docs/Steburn-0.3.1-Oberflaeche.png')
lasern.usage_help.show(); app.update()
ImageGrab.grab(xdisplay=__import__('os').environ['DISPLAY']).save('docs/Steburn-0.3.1-Mouseover.png')
lasern.usage_help.hide()
assert not errors,errors
for timer in app.tk.call('after','info'): app.after_cancel(timer)
app.destroy(); print('GUI Präsentation: Buttonflächen, Auswahlzustand, alle Buttonhilfen, Tooltip-Lebenszyklus, Logo und Lasern-Einstieg bestanden.')
