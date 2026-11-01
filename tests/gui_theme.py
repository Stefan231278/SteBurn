"""Verify appearance switching, persistence and unchanged document colours."""
import sys,time,tempfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageGrab
from steburn.ui.workspace import App
from steburn.ui.image_studio import ImageStudio
from steburn.ui.theme import ThemeManager
from steburn.core.model import Shape
from steburn.io.importers import image_shape

a=App(); errors=[]; a.report_callback_exception=lambda *args:errors.append(args)
def settle():
    for _ in range(8): a.update(); time.sleep(.04)
settle()
p=a.p; s=Shape('rect',40,50,120,90,p.layers[1].id,extra={'corner_radius':8}); p.shapes.append(s)
photo=image_shape(Image.new('RGB',(60,40),(210,180,130)),a.active_layer,'Farbprobe',width=80); photo.x=190; p.shapes.append(photo)
a.selection={s.id}; a.selected=s.id; a.refresh(); settle(); before=a.p.to_dict()
with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'test-temp') as tmp:
    a.theme.path=Path(tmp)/'settings.json'; a.theme.path.write_text('{"other":"keep"}',encoding='utf-8')
    for mode in ('dark','light','dark'):
        a.dark_mode.set(mode=='dark'); a.set_theme(); a.render(); settle()
        assert ThemeManager(a,a.theme.path).mode==mode
        assert json.loads(a.theme.path.read_text())['other']=='keep'
        assert a.p.to_dict()==before
        assert a.canvas.itemcget(a.canvas.find_withtag('workarea')[0],'fill')==('#1c293a' if mode=='dark' else 'white')
        assert a.tree.cget('style')=='' # Shared style, no per-document recolouring.
    ImageGrab.grab(window=a.winfo_id()).save('docs/Steburn-Darkmode.png')
    window=ImageStudio(a,photo); settle()
    assert window.file_list.cget('background')==a.theme.colors['field']
    assert window.original_image.getpixel((0,0))==(210,180,130)
    a.dark_mode.set(False); a.set_theme(); settle(); assert window.file_list.cget('background')=='#ffffff'
    a.dark_mode.set(True); a.set_theme(); settle(); assert window.images['original'].cget('background')=='#111926'
    window.close()
    a.open_job(); settle(); cockpit=a.job_window
    assert cockpit.log.cget('background')==a.theme.colors['field']
    cockpit.draw(); paper=next(i for i in cockpit.canvas.find_all() if cockpit.canvas.type(i)=='rectangle')
    assert cockpit.canvas.itemcget(paper,'fill')=='#1c293a'
    cockpit.close()
assert a.p.to_dict()==before
assert not errors,errors
for timer in a.tk.call('after','info'): a.after_cancel(timer)
a.destroy(); print('Darkmode GUI OK: canvas, fields, existing/new dialogs, persistence and unchanged artwork')
