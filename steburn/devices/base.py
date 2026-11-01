from typing import Protocol
class DeviceAdapter(Protocol):
    """Future controller interface. UI must never write directly to transport."""
    def identify(self) -> dict: ...
    def status(self) -> dict: ...
    def disconnect(self) -> None: ...
class OfflineAdapter:
    def identify(self): return {'model':'Atomstack A40 Pro','verified':False}
    def status(self): return {'connected':False,'machine_output_enabled':False}
    def disconnect(self): pass
