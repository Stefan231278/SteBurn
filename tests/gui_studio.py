import sys,time,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace
from unittest.mock import Mock
from steburn.ui.studio import App
from steburn.core.model import Shape
from steburn.core.paths import shape_paths
from steburn.core.materials import MaterialLibrary
from PIL import ImageGrab

a=App(); errors=[]; a.report_callback_exception=lambda *args:errors.append(args)
def settle():
    for _ in range(8): a.update(); time.sleep(.04)
def event(x,y):
    sx,sy=a.screen(x,y); return SimpleNamespace(x=sx,y=sy,state=0)
settle(); a.fit()
s=Shape('rect',45,65,140,85,a.p.layers[1].id,'Schild',extra={'corner_radius':8})
t=Shape('text',65,95,100,15,a.p.layers[0].id,'Beschriftung','SteBurn\nStudio',extra={'text_align':'center'})
a.p.shapes=[s,t]; a.selection={s.id}; a.selected=s.id; a.refresh(); settle()
a.radius.set('12'); a.apply_radius(); assert a.current().extra['corner_radius']==12
a.set_tool('bezier')
for pt in [(220,80),(220,160),(310,160),(310,80)]: a.press(event(*pt))
assert 'bezier' in a.current().extra; assert a.tool=='nodes'
curve=a.current(); old=shape_paths(curve)
a.node_selection=(curve.id,0,1); a.node_x.set('235'); a.node_y.set('170'); a.apply_node(); assert shape_paths(a.current())!=old
a.insert_node(); assert len(a.current().extra['bezier'])==7
a.selection={t.id}; a.selected=t.id; a.refresh(); a.switch_workspace('design'); a.notebook.select(a.text_tab); settle()
a.text_content.delete('1.0','end'); a.text_content.insert('1.0','SteBurn\nStudio'); a.tracking.set('0.4'); a.apply_text(); assert a.current().extra['tracking']==.4
settle(); ImageGrab.grab(window=a.winfo_id()).save('docs/Studio-text.png')
a.text_content.focus_force(); settle(); count=len(a.p.shapes)
a.text_content.event_generate('<Delete>'); a.text_content.event_generate('<Control-d>'); settle()
assert len(a.p.shapes)==count,'Typing shortcuts must not delete or duplicate design objects'
temp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'test-temp')
a.library=MaterialLibrary(Path(temp.name)/'materials.json')
a.new_material(); a.material_vars['name'].set('Testprofil · Materialprobe'); a.material_vars['material'].set('Eigene Probe'); a.material_vars['thickness'].set('3')
a.save_material(); assert a.library.read()['Testprofil · Materialprobe']['power']==0
a.apply_material(); assert a.p.extensions['material_assignments'][a.active_layer]=='Testprofil · Materialprobe'
for workspace in ('design','prepare','materials','machine'):
    a.switch_workspace(workspace); settle()
    assert a.notebook.select()
    ImageGrab.grab(window=a.winfo_id()).save(f'docs/Studio-{workspace}.png')
a.switch_workspace('design'); a.notebook.select(a.vector_tab); a.selection={curve.id}; a.selected=curve.id; a.set_tool('nodes'); a.refresh(); settle()
ImageGrab.grab(window=a.winfo_id()).save('docs/Studio-curves.png')
a.open_job(); settle(); cockpit=a.job_window
assert cockpit.title()=='SteBurn · Job-Cockpit'; assert not a.device.connected
assert len(cockpit.metrics)==4
ImageGrab.grab(window=cockpit.winfo_id()).save('docs/Studio-cockpit.png')
cockpit.runner=SimpleNamespace(state='running',feed=110,power=90,request=Mock())
cockpit.events.put({'state':'running','completed':1,'total':len(cockpit.plan.segments),'status':{'state':'Run','MPos':'12.5,18.2,0','FS':'900,250'}})
settle(); assert cockpit.metrics['feed'].get()=='15.00'; assert cockpit.metrics['position'].get()=='12.5 / 18.2'
cockpit.feed_target.set(125); cockpit.power_target.set(80); cockpit.apply_overrides()
assert cockpit.runner.request.call_args_list[0].args==(('speed',125.0),)
assert cockpit.runner.request.call_args_list[1].args==(('power',80),)
cockpit.runner.state='finished'
cockpit.close(); settle()
assert not errors,errors
for timer in a.tk.call('after','info'): a.after_cancel(timer)
a.destroy(); temp.cleanup(); print('Studio GUI OK: workflow, radii, cubic handles, text, materials, preparation and live cockpit telemetry')
