import sys,time,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
from PIL import Image,ImageDraw,ImageGrab
from steburn.ui.workspace import App
from steburn.ui.image_studio import ImageStudio
from steburn.core.model import Shape
from steburn.io.importers import image_shape
from steburn.core.photos import decode_image

a=App(); errors=[]; a.report_callback_exception=lambda *args:errors.append(args)
def settle(n=10):
    for _ in range(n): a.update(); time.sleep(.04)
def event(x,y):
    sx,sy=a.screen(x,y); return SimpleNamespace(x=sx,y=sy,state=0)
settle(); a.fit(); a.update()
assert a.main_pane.sashpos(0)<80
width=a.canvas.winfo_width(); a.toggle_dock(); settle(); assert a.canvas.winfo_width()>width; a.toggle_dock(); settle(); assert abs(a.canvas.winfo_width()-width)<10
a.set_tool('rect'); a.draw_radius.set('6'); a.snap_enabled.set(True)
a.press(event(42,52)); a.motion(event(128,117)); a.release(event(128,117)); settle()
assert a.current().extra['corner_radius']==6
assert a.current().x==40 and a.current().y==50
a.undo(); assert not a.p.shapes; a.redo(); settle()
a.selection={a.p.shapes[0].id}; a.selected=a.p.shapes[0].id; a.refresh()
a.rotation.set('30'); a.rotate_selection(); assert a.current().kind=='polygon'; a.undo(); settle()
a.set_tool('pencil'); a.press(event(220,220))
for pt in [(225,230),(240,235),(250,225)]: a.motion(event(*pt))
a.release(event(250,225)); assert a.current().name=='Freihand'
a.snap_enabled.set(False)
a.press(SimpleNamespace(x=150,y=10,state=0)); a.motion(event(100,180)); a.release(event(100,180)); settle()
assert a.p.extensions['guides'][0][0]=='y'
sample=Image.new('RGB',(480,320)); pixels=sample.load()
for y in range(320):
    for x in range(480): pixels[x,y]=(round(220-100*y/320),round(230-90*y/320),round(240-60*y/320))
d=ImageDraw.Draw(sample); d.ellipse((330,30,420,120),fill='#f1cb85'); d.polygon([(0,260),(100,110),(220,270),(310,160),(480,280),(480,320),(0,320)],fill='#597b86'); d.polygon([(20,320),(150,190),(290,320)],fill='#223b4a'); d.text((20,20),'LASER / PHOTO',fill='#243247')
shape=image_shape(sample,a.active_layer,'Bildprobe',width=90); shape.x=170; shape.y=90
a.p.shapes.append(shape); a.selection={shape.id}; a.selected=shape.id; a.refresh(); settle()
a.open_inspector(a.image_tab); settle(); ImageGrab.grab(window=a.winfo_id()).save('docs/Workspace-0.7-design.png')
window=ImageStudio(a,shape); settle(); window.vars['contrast'].set('1.5'); window.vars['sharpness'].set('1.7'); window.interval.set('.5')
for _ in range(80):
    settle(1)
    if getattr(window,'processed_image',None) is not None and 'aktuell' in window.info.get(): break
assert window.processed_image is not None,window.info.get()
assert set(window.processed_image.tobytes())<={0,255}
window.tabs.select(window.pages['Laser']); settle()
ImageGrab.grab(window=window.winfo_id()).save('docs/Workspace-0.7-photo.png')
window.vars['mode'].set('Atkinson · Rasterpunkte'); settle(20)
window.apply()
for _ in range(150):
    settle(1)
    if window.closed: break
assert window.closed,window.info.get()
result=next(s for s in a.p.shapes if s.id==shape.id)
assert result.extra['image_original']==shape.extra['image']; assert result.extra['image_adjustments']['mode']=='atkinson'
assert decode_image(result.extra['image']).size==(180,120)
a.adjust_image(); settle(); assert a.photo_window.vars['contrast'].get()=='1.5'; a.photo_window.close()
with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'test-temp') as tmp:
    file=Path(tmp)/'Importprobe.png'; sample.save(file); count=len(a.p.shapes)
    a.import_paths([str(file)]); settle(); assert len(a.photo_window.records)==1
    a.photo_window.close(); assert len(a.p.shapes)==count,'Cancelling import must leave the project untouched'
for stage in ('prepare','materials','machine','design'): a.switch_workspace(stage); settle(3)
assert not errors,errors
assert not a.device.connected
for timer in a.tk.call('after','info'): a.after_cancel(timer)
a.destroy(); print('Workspace GUI OK: compact rail, dock, contextual controls, snap, guides, photo preview/apply/reopen and unchanged laser navigation')
