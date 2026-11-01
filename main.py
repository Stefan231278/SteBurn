"""Windows identity must be set before Tk creates any native windows."""
import sys

def prepare_windows_identity():
    if sys.platform!='win32': return
    import ctypes
    try:
        call=ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
        call.argtypes=[ctypes.c_wchar_p]; call.restype=ctypes.c_long
        result=call('Steburn.Desktop')
        if result!=0: print(f'Windows-App-Kennung nicht gesetzt: {result}',file=sys.stderr)
    except (AttributeError,OSError) as ex:
        print(f'Windows-App-Kennung: {ex}',file=sys.stderr)

if __name__ == '__main__':
    prepare_windows_identity()
    from steburn.ui.live_app import App
    App().mainloop()
