"""Explicit registration; extensions are trusted local Python code, never auto-downloaded."""
from dataclasses import dataclass
@dataclass(frozen=True)
class Command:
    id: str
    label: str
    run: object
class Registry:
    def __init__(self): self.commands={}
    def register(self,command):
        if command.id in self.commands: raise ValueError('Befehl bereits registriert')
        self.commands[command.id]=command
