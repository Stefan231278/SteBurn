"""Visual check of tool symbols, theme changes and command routing."""
import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import ImageGrab
from steburn.ui.workspace import App,TOOLS

a=App(); errors=[]; a.report_callback_exception=lambda *args:errors.append(args)
def settle():
    for _ in range(7): a.update(); time.sleep(.04)
settle()
for mode in ('dark','light'):
    a.dark_mode.set(mode=='dark'); a.set_theme(persist=False); settle()
    for tool,_,label in TOOLS:
        button=a.tool_buttons[tool]; button.invoke(); settle()
        assert a.tool==tool
        assert button.cget('image') and button.cget('style')=='RailSelected.TButton'
        assert button.cget('text')==label
    a.set_tool('bezier'); settle()
    assert a.rail_actions['objects'].winfo_y()+a.rail_actions['objects'].winfo_height()<=a.left_dock.winfo_height()
    ImageGrab.grab(window=a.winfo_id()).save('docs/Tool-Icons-'+mode+'.png')
assert not errors,errors
assert not a.device.connected
a.destroy(); print('Tool icons OK: all tool commands, active state, labels, light/dark and complete rail visibility')
