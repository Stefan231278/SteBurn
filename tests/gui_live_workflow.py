import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
from steburn.ui.workbench import App
from PIL import ImageGrab

a=App(); errors=[]; a.report_callback_exception=lambda *args:errors.append(args)
def settle():
    for _ in range(8): a.update(); time.sleep(.04)
settle()
print('screen',a.winfo_screenwidth(),a.winfo_screenheight(),'window',a.winfo_width(),a.winfo_height())
for key,panel in [*a.page_tabs.items(),('processing',a.processing_tab)]:
    a.notebook.select(panel); settle()
    print(key,panel.canvas.winfo_height(),panel.canvas.bbox('all'))
    assert panel.canvas.bbox('all')[3]<=panel.canvas.winfo_height(),key
old=a.oy; a.wheel(SimpleNamespace(state=0,delta=30,x=100,y=100)); assert a.oy!=old
a.device.link_ok=True; a.device.serial=SimpleNamespace(is_open=True)
a.poll(); assert a.connection_dot.cget('fg')=='#46cf83'
a.device.link_ok=False; a.poll(); assert a.connection_dot.cget('fg')=='#d64545'
a.device.serial=None
a.notebook.select(a.page_tabs['machine']); settle()
ImageGrab.grab(window=a.winfo_id()).save('docs/Steburn-0.5-Livetest.png')
a.open_job(); settle(); assert 'Lasern' in a.job_window.start_button.cget('text'); a.job_window.close()
a.state('normal'); a.geometry('1000x650'); a.notebook.select(a.page_tabs['props']); settle()
panel=a.page_tabs['props']; panel.canvas.yview_moveto(0)
entry=next(w for w in panel.content.winfo_children() if w.winfo_class()=='TEntry')
before=entry.get(); entry.event_generate('<MouseWheel>',delta=-30); settle()
assert panel.canvas.yview()[0]>0,'Small touchpad delta over an input must scroll'
assert entry.get()==before
assert not errors,errors
for timer in a.tk.call('after','info'): a.after_cancel(timer)
a.destroy()
print('GUI OK')
