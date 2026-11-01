import sys,time,tempfile,json
from types import SimpleNamespace
from unittest.mock import patch
from dataclasses import replace
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import ImageGrab
from tkinter import ttk
from steburn.ui.live_app import App
from steburn.core.model import Shape
from steburn.core.materials import MaterialLibrary
from steburn.core.material_test import generate,save_session
from test_streaming import device

a=App(); errors=[]; a.report_callback_exception=lambda *args:errors.append(args)
def settle(n=8):
    for _ in range(n): a.update(); time.sleep(.04)
def wait_for(test,count=250):
    for _ in range(count):
        settle(1)
        if test(): return
    raise AssertionError('Timed out')
with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'test-temp') as tmp:
    a.library=MaterialLibrary(Path(tmp)/'materials.json'); a.report_directory=Path(tmp)/'job-reports'
    a.device_trace_directory=Path(tmp)/'device-traces'
    a.p.shapes=[Shape('rect',30,30,20,20,a.p.layers[1].id)]; a.refresh(); settle(); original=a.p.to_dict()
    a.open_job(); settle(); cockpit=a.job_window
    cockpit.start(); settle()
    assert cockpit.runner is None and 'Ports suchen' in cockpit.failure_hint.get()
    assert 'Kein Gerät verbunden' in cockpit.log.get('1.0','end')
    def widgets(parent):
        for w in parent.winfo_children(): yield w; yield from widgets(w)
    assert not any(isinstance(w,ttk.Scale) for w in widgets(cockpit))
    assert cockpit.power_target.get()==60
    cockpit.step_parameter('speed',1); cockpit.step_parameter('power',1)
    assert abs(cockpit.feed_target.get()*60-1450)<1e-8; assert cockpit.power_target.get()==65
    a.device=device(); a.device.settings[31]=0; a.optical_watts=lambda:40; paused=[False]
    def pause():
        if not paused[0]: paused[0]=True; cockpit.runner.request('pause')
    a.device.serial.on_motion=pause; cockpit.start()
    wait_for(lambda:cockpit.runner.state=='paused' and cockpit.pause_button.cget('text')=='Fortsetzen')
    cockpit.step_parameter('speed',1); cockpit.step_parameter('power',1); cockpit.pause_button.invoke()
    wait_for(lambda:cockpit.runner.state=='finished' and not a.busy)
    records=cockpit.last_stats['adjustments']; assert any(r['key']=='power' and r['value']==70 and r['state']=='active' for r in records)
    assert cockpit.report_path.exists(); report=json.loads(cockpit.report_path.read_text(encoding='utf-8')); assert report['statistics']['adjustments']
    ImageGrab.grab(window=cockpit.winfo_id()).save('docs/Steburn-0.9-controls.png')
    with patch.object(a.device,'status',side_effect=TimeoutError('Kein frischer Controllerstatus')):
        cockpit.start(); wait_for(lambda:cockpit.runner.state=='failed' and not a.busy)
    assert cockpit.report_data['error']['reason']=='Kein frischer Controllerstatus'
    assert 'USB und Stromversorgung' in cockpit.failure_hint.get()
    assert 'Fehler: Kein frischer Controllerstatus' in cockpit.log.get('1.0','end')
    ImageGrab.grab(window=cockpit.winfo_id()).save('docs/Steburn-0.9.1-startfehler.png'); cockpit.close(); settle()
    a.open_material_test(); settle(); window=a.material_test_window
    assert window.project and len(window.session['test']['cells'])==30
    assert a.p.to_dict()==original
    window.tabs.select(2); settle(); window.vars['size'].set('100'); settle()
    ox,oy,scale,height=window.bed_transform
    event=SimpleNamespace(x=ox+180*scale,y=oy+(height-220)*scale)
    window.position_press(event); window.position_release(event); settle()
    assert window.session['test']['spec']['x']==130 and window.session['test']['spec']['y']==170
    assert window.session['test']['size_mm']==[100,100]
    ImageGrab.grab(window=window.winfo_id()).save('docs/Steburn-0.9.1-positionierung.png')
    a.device=device(); jogs=[0]
    def stop_test_frame():
        jogs[0]+=1
        if jogs[0]==3: a.device.stop_frame()
    a.device.serial.on_jog=stop_test_frame; window.frame_test(); wait_for(lambda:not a.busy)
    assert a.device.last_position==(230,270) and a.device.homed
    window.vars['x'].set('140'); window.generate(); jogs[0]=0; window.frame_test(); wait_for(lambda:not a.busy)
    assert a.device.last_position==(240,270) and a.device.homed and a.device.origin_confirmed
    a.device.settings[31]=0; a.pointer_light_var.set(True); window.position_mode.set('pointer')
    original_spec=dict(window.session['test']['spec']); window.pointer_to((155,210)); wait_for(lambda:not a.busy); settle()
    assert window.pointer_position==(155,210) and window.session['test']['spec']==original_spec
    assert any(b'G4 P0.15' in data for data in a.device.serial.writes)
    ImageGrab.grab(window=window.winfo_id()).save('docs/Steburn-0.9.2-pointer.png')
    window.position_mode.set('place'); a.pointer_light_var.set(False)
    window.tabs.select(0); settle()
    ImageGrab.grab(window=window.winfo_id()).save('docs/Steburn-0.9-materialtest.png')
    window.tabs.select(1); window.tree.selection_set('C01'); settle()
    window.depth.set('1.25'); window.through.set('Nein'); window.quality.set('Zu schwach'); settle(10)
    assert window.session['observations']['C01']['depth_mm']==1.25
    window.depth.set('.75'); window.tree.selection_set('G01'); settle(); assert window.session['observations']['C01']['depth_mm']==.75
    window.depth.set('.2'); window.quality.set('Gut'); settle(10); window.store_profile(); assert a.library.read()
    ImageGrab.grab(window=window.winfo_id()).save('docs/Steburn-0.9-testresults.png')
    window.test_labels(); settle(); labeljob=a.job_window
    assert labeljob.project.extensions['material_test']['phase']=='labels_only'
    assert not any(s.extra.get('material_cell') for s in labeljob.project.shapes)
    labeljob.start(); wait_for(lambda:labeljob.runner.state=='finished' and not a.busy)
    labeljob.close(); settle()
    window.open_cockpit(); settle(); testjob=a.job_window
    assert testjob.fixed_parameters
    power=testjob.power_target.get(); testjob.step_parameter('power',1); assert testjob.power_target.get()==power
    testjob.start(); wait_for(lambda:testjob.runner.state=='finished' and not a.busy)
    assert a.p.to_dict()==original
    assert testjob.report_data['material_test']['id']==window.session['test']['id']
    window.save(); assert window.session.get('job_report')
    testjob.close(); legacy=generate(replace(window.form(),size=50),pattern_version=1)
    path=Path(tmp)/'legacy-test.json'; save_session(path,dict(version=1,test=legacy.extensions['material_test'],observations={}))
    with patch('steburn.ui.material_test.filedialog.askopenfilename',return_value=str(path)): window.load_session()
    assert window.session['test']['pattern_version']==1 and window.vars['size'].get()=='50.0'
    assert window.ensure_project() and window.session['test']['pattern_version']==1
    window.close(); settle()
    assert not errors,errors
a.destroy(); print('Calibration GUI OK: live steps, actionable start errors, saved reports, positioned/scaled coupon and frame, measurements, profiles and historical test loading')
