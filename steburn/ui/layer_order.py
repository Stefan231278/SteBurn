from tkinter import ttk,StringVar

class LayerOrder(ttk.Frame):
    def __init__(self,parent,project,change):
        super().__init__(parent,padding=(8,3)); self.project=project; self.change=change; self.enabled=True
        row=ttk.Frame(self); row.pack(fill='x'); ttk.Label(row,text='Ebene verschieben:').pack(side='left',padx=(0,6))
        self.combo=ttk.Combobox(row,state='readonly',width=32); self.combo.pack(side='left')
        self.buttons=[]
        for label,step in [('↑',-1),('↓',1)]:
            button=ttk.Button(row,text=label,width=3,style='Compact.TButton',command=lambda s=step:self.shift(s)); button.pack(side='left',padx=2); self.buttons.append(button)
        self.current=StringVar(value='Noch nicht gestartet'); ttk.Label(row,textvariable=self.current).pack(side='left',padx=10)
        self.chain=StringVar(); ttk.Label(row,textvariable=self.chain,style='Studio.Muted.TLabel').pack(side='left',padx=8)
        self.refresh()
    def refresh(self,selected=None):
        before=self.combo.current(); layers=self.project().layers; self.ids=[l.id for l in layers]
        values=[f'{i+1:02} · {l.name}'+(' [aus]' if not l.output else '') for i,l in enumerate(layers)]
        self.combo['values']=values
        if self.ids: self.combo.current(self.ids.index(selected) if selected in self.ids else max(0,min(before,len(self.ids)-1)))
        self.chain.set('Reihenfolge: '+' → '.join(values))
    def shift(self,step):
        index=self.combo.current()
        if self.enabled and 0<=index<len(self.ids):
            lid=self.ids[index]; self.change(lid,step); self.refresh(lid)
    def set_enabled(self,enabled):
        self.enabled=enabled; self.combo.configure(state='readonly' if enabled else 'disabled')
        for button in self.buttons: button.configure(state='normal' if enabled else 'disabled')
    def set_current(self,lid=None,finished=False):
        layers=self.project().layers
        self.current.set('Abgeschlossen' if finished else next((f'Aktuell: {i+1:02} · {l.name}' for i,l in enumerate(layers) if l.id==lid),'Noch nicht gestartet'))
