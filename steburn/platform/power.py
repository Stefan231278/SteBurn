"""Thread-bound Windows idle-sleep prevention; never changes power plan settings."""
import ctypes
import sys
import threading
from dataclasses import dataclass

@dataclass(frozen=True)
class PowerStatus:
    ac: object = None
    percent: object = None

class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [('ACLineStatus',ctypes.c_ubyte),('BatteryFlag',ctypes.c_ubyte),
                ('BatteryLifePercent',ctypes.c_ubyte),('SystemStatusFlag',ctypes.c_ubyte),
                ('BatteryLifeTime',ctypes.c_uint32),('BatteryFullLifeTime',ctypes.c_uint32)]

def battery_status(kernel=None):
    if kernel is None:
        if sys.platform!='win32': return PowerStatus()
        kernel=ctypes.windll.kernel32
    value=SYSTEM_POWER_STATUS()
    if not kernel.GetSystemPowerStatus(ctypes.byref(value)): return PowerStatus()
    return PowerStatus(value.ACLineStatus==1 if value.ACLineStatus in (0,1) else None,
                       value.BatteryLifePercent if value.BatteryLifePercent<=100 and not value.BatteryFlag & 128 else None)

class Awake:
    def __init__(self,kernel=None):
        self.kernel=kernel; self.active=False; self.owner=None
    def acquire(self):
        if self.active: return
        if self.kernel is None:
            if sys.platform!='win32': return
            self.kernel=ctypes.windll.kernel32
        if not self.kernel.SetThreadExecutionState(0x80000001):
            raise OSError('Windows-Wachhalten konnte nicht aktiviert werden. Auftrag nicht gestartet.')
        self.owner=threading.get_ident(); self.active=True
    def release(self):
        if not self.active: return
        if threading.get_ident()!=self.owner: raise RuntimeError('Wachhalten muss im selben Thread beendet werden.')
        if not self.kernel.SetThreadExecutionState(0x80000000): raise OSError('Windows-Wachhalten konnte nicht freigegeben werden.')
        self.active=False
    def __enter__(self): self.acquire(); return self
    def __exit__(self,*args): self.release()
