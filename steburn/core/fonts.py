"""Read installed font metadata, including Windows user fonts and TTC faces."""
from dataclasses import dataclass
from pathlib import Path
import os
from functools import lru_cache

@dataclass(frozen=True)
class FontFace:
    label: str
    path: str
    index: int=0

@lru_cache(maxsize=1)
def installed_fonts():
    files=set()
    folders=[Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts']
    local=os.environ.get('LOCALAPPDATA')
    if local: folders.append(Path(local)/'Microsoft/Windows/Fonts')
    if os.name=='nt':
        import winreg
        for hive in (winreg.HKEY_LOCAL_MACHINE,winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(hive,r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts') as key:
                    for i in range(winreg.QueryInfoKey(key)[1]):
                        _,value,_=winreg.EnumValue(key,i)
                        if not isinstance(value,str): continue
                        path=Path(value)
                        if path.is_absolute() and path.is_file(): files.add(path)
                        else:
                            for folder in folders:
                                if (folder/path).is_file(): files.add(folder/path)
            except OSError: pass
    else: folders.extend([Path('/usr/share/fonts'),Path('/usr/local/share/fonts'),Path.home()/'.fonts',Path.home()/'.local/share/fonts',Path('/System/Library/Fonts'),Path('/Library/Fonts')])
    for folder in folders:
        if folder.exists():
            files.update(p for p in folder.rglob('*') if p.suffix.lower() in {'.ttf','.otf','.ttc','.otc'} and p.is_file())
    from fontTools.ttLib import TTFont,TTCollection
    faces=[]; labels=set()
    for path in sorted(files):
        try:
            if path.suffix.lower() in {'.ttc','.otc'}:
                collection=TTCollection(path,lazy=True); indices=range(len(collection.fonts)); collection.close()
            else: indices=range(1)
            for index in indices:
                with TTFont(path,fontNumber=index,lazy=True) as font:
                    names=font['name']
                    family=names.getDebugName(16) or names.getDebugName(1) or path.stem
                    style=names.getDebugName(17) or names.getDebugName(2) or 'Regular'
                    label=family+' · '+style
                    if label in labels: continue
                    labels.add(label); faces.append(FontFace(label,str(path),index))
        except Exception: continue
    return tuple(sorted(faces,key=lambda f:f.label.casefold()))
