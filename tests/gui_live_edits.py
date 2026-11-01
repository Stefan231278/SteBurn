import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import ImageGrab
from steburn.ui.live_app import App
from steburn.core.model import Shape
from steburn.core.processing import resolve

a=App(); errors=[]; a.report_callback_exception=lambda *args:errors.append(args)
def settle(n=12):
    for _ in range(n): a.update(); time.sleep(.04)
settle()
s=Shape('text',25,25,80,12,a.p.layers[0].id,'Text','SteBurn'); a.p.shapes=[s]; a.selection={s.id}; a.selected=s.id; a.refresh(); settle()
a.text_content.delete('1.0','end'); a.text_content.insert('1.0','Live-Test'); settle()
assert a.current().text=='Live-Test',a.current().text
a.text_size.set('16'); settle(); assert a.current().h==16
a.vars['x'].set('37.25'); settle(); assert a.current().x==37.25,a.current().x
a.quick_layer(a.p.layers[1].id,True); settle()
assert resolve(a.current(),a.p.layers[1]).operation=='cut'
assert resolve(a.current(),a.p.layers[1]).power==60
a.lvars['power'].set('57'); settle(); assert a.p.layers[1].power==57
a.process_power.set('66'); settle(); assert a.current().extra['processing']['power']==66
r=Shape('rect',100,100,30,20,a.p.layers[1].id,'Drehprobe'); a.p.shapes.append(r); a.selection={r.id}; a.selected=r.id; a.refresh()
a.rotation.set('30'); settle(); assert a.current().extra['rotation_angle']==30
a.rotation.set('31'); settle(); assert a.current().extra['rotation_angle']==31
assert not any(e for e in errors),errors
a.switch_workspace('machine'); settle()
ImageGrab.grab(window=a.winfo_id()).save('docs/Steburn-0.8-device.png')
a.switch_workspace('laser'); settle(); cockpit=a.job_window
assert cockpit.wm_state()=='zoomed',cockpit.wm_state()
assert cockpit.power_target.get()==66
assert cockpit.feed_target.get()==a.p.layers[1].speed/60
assert cockpit.pause_button is cockpit.resume_button
ImageGrab.grab(window=cockpit.winfo_id()).save('docs/Steburn-0.8-cockpit.png')
from test_streaming import device
a.device=device(); a.optical_watts=lambda:40; triggered=[False]
def pause_once():
    if not triggered[0]: triggered[0]=True; cockpit.runner.request('pause')
a.device.serial.on_motion=pause_once
cockpit.start()
for _ in range(150):
    settle(1)
    if cockpit.runner.state=='paused' and cockpit.pause_button.cget('text')=='Fortsetzen': break
assert cockpit.runner.state=='paused',cockpit.info.get()
cockpit.pause_button.invoke()
for _ in range(200):
    settle(1)
    if cockpit.runner.state=='finished' and not a.busy: break
assert cockpit.runner.state=='finished',cockpit.info.get()
assert a.device.serial.position==[0,0]
assert 'Wh' in cockpit.timing.get() and 'mm' in cockpit.timing.get()
ImageGrab.grab(window=cockpit.winfo_id()).save('docs/Steburn-0.8-jobstatistik.png')
cockpit.close(); settle()
assert not errors,errors
a.destroy(); print('Live UI OK: text, geometry, layer/object processing apply automatically; quick cut; 04 cockpit; fitted monitor; physical parameter units')
