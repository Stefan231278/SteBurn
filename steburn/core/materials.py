"""User-calibrated material presets; used presets travel with the project."""
import json,math,os,tempfile
from pathlib import Path

FIELDS=('speed','power','passes','interval','air','mode')

def validate_preset(preset):
    from steburn.core.model import Project
    p=Project(); layer=p.layers[0]
    for key in FIELDS:
        if key in preset: setattr(layer,key,preset[key])
    p.validate()
    if not preset.get('name','').strip(): raise ValueError('Bitte einen Profilnamen angeben.')
    thickness=preset.get('thickness',0)
    if not isinstance(thickness,(int,float)) or not math.isfinite(thickness) or thickness<0:
        raise ValueError('Ungültige Materialstärke.')
    if preset.get('operation','cut') not in ('cut','engrave','mark'): raise ValueError('Unbekannte Bearbeitungsart.')
    return dict(preset)

class MaterialLibrary:
    def __init__(self,path): self.path=Path(path)
    def read(self):
        if not self.path.exists(): return {}
        data=json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(data,dict): raise ValueError('Ungültige Materialbibliothek.')
        return {name:validate_preset(p) for name,p in data.items()}
    def write(self,presets):
        data={name:validate_preset(p) for name,p in presets.items()}
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(dir=self.path.parent,suffix='.tmp')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                json.dump(data,f,ensure_ascii=False,indent=2); f.flush(); os.fsync(f.fileno())
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)

def apply_preset(project,preset,layer_id,selection=None):
    from copy import deepcopy
    validate_preset(preset); p=deepcopy(project)
    if selection:
        for shape in p.shapes:
            if shape.id in selection and not shape.extra.get('locked'):
                shape.extra['processing']={key:preset[key] for key in ('operation','speed','power','passes','interval')}
                shape.extra['material']=preset['name']
    else:
        layer=next(l for l in p.layers if l.id==layer_id)
        for key in FIELDS:
            if key in preset: setattr(layer,key,preset[key])
        layer.operation=preset['operation']
        p.extensions.setdefault('material_assignments',{})[layer_id]=preset['name']
    p.extensions.setdefault('materials',{})[preset['name']]=dict(preset)
    p.validate(); return p
