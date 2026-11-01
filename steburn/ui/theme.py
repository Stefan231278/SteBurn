"""Application-wide appearance without changing document or bitmap colours."""
import json,os,tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk

PALETTES={
    'dark':dict(bg='#151e2b',surface='#202c3d',field='#253348',text='#e1e8f2',muted='#a6b5c9',border='#40516a',canvas='#111926',paper='#1c293a',grid='#293a50',selected='#294c71',accent='#93c5fd',header='#101827'),
    'light':dict(bg='#f3f5f9',surface='#ffffff',field='#ffffff',text='#25334a',muted='#64748b',border='#cbd5e1',canvas='#e6ebf3',paper='#ffffff',grid='#edf1f6',selected='#dbeafe',accent='#1d4ed8',header='#172338'),
}

class ThemeManager:
    def __init__(self,root,path=None):
        self.root=root; self.path=Path(path) if path else Path(__file__).resolve().parents[2]/'user-data'/'settings.json'
        self.mode=self.read(); self.original_layouts={name:ttk.Style(root).layout(name) for name in ('TButton','Accent.TButton','Danger.TButton','Selected.TButton','Toolbar.TButton','Toolbar.Accent.TButton')}
    @property
    def dark(self): return self.mode=='dark'
    @property
    def colors(self): return PALETTES[self.mode]
    def read(self):
        try:
            mode=json.loads(self.path.read_text(encoding='utf-8')).get('theme','dark')
            return mode if mode in PALETTES else 'dark'
        except (OSError,ValueError,AttributeError): return 'dark'
    def save(self):
        try: data=json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError,ValueError): data={}
        if not isinstance(data,dict): data={}
        data['theme']=self.mode; self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(dir=self.path.parent,suffix='.tmp')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as file: json.dump(data,file,ensure_ascii=False,indent=2)
            os.replace(tmp,self.path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    def apply(self,mode=None,persist=False):
        if mode is not None:
            if mode not in PALETTES: raise ValueError('Unbekannte Darstellung')
            self.mode=mode
        p=self.colors; style=ttk.Style(self.root)
        style.configure('.',background=p['bg'],foreground=p['text'])
        for name in ('TFrame','TLabel','TCheckbutton','TRadiobutton','TLabelframe','TLabelframe.Label','TPanedwindow'):
            style.configure(name,background=p['bg'],foreground=p['text'],bordercolor=p['border'])
        for name in ('TCheckbutton','TRadiobutton'):
            style.configure(name,indicatorbackground=p['field'],indicatorforeground=p['accent'],indicatormargin=3)
            style.map(name,background=[('active',p['bg'])],foreground=[('disabled',p['muted']),('active',p['text'])],indicatorbackground=[('selected',p['selected']),('active',p['surface'])])
        style.configure('Studio.Dark.TFrame',background=p['header']); style.configure('Studio.Dark.TLabel',background=p['header'],foreground='#edf3fc')
        style.configure('Dark.TFrame',background=p['header']); style.configure('Dark.TLabel',background=p['header'],foreground='#edf3fc')
        style.configure('Studio.Card.TFrame',background=p['surface']); style.configure('Studio.Card.TLabel',background=p['surface'],foreground=p['text'])
        style.configure('Studio.Muted.TLabel',background=p['bg'],foreground=p['muted'])
        for name in ('TEntry','TCombobox','TSpinbox'):
            style.configure(name,fieldbackground=p['field'],background=p['surface'],foreground=p['text'],insertcolor=p['text'],bordercolor=p['border'],lightcolor=p['border'],darkcolor=p['border'],arrowcolor=p['text'],selectbackground=p['selected'],selectforeground=p['text'])
            style.map(name,fieldbackground=[('disabled',p['bg']),('readonly',p['field'])],foreground=[('disabled',p['muted']),('readonly',p['text'])],background=[('active',p['selected'])])
        style.configure('TNotebook',background=p['bg'],bordercolor=p['border'],lightcolor=p['border'],darkcolor=p['border'])
        style.configure('TNotebook.Tab',background=p['surface'],foreground=p['muted'],bordercolor=p['border'],lightcolor=p['border'],darkcolor=p['border'])
        style.map('TNotebook.Tab',background=[('selected',p['selected']),('active',p['field'])],foreground=[('selected',p['text']),('active',p['text'])])
        style.configure('Treeview',background=p['field'],fieldbackground=p['field'],foreground=p['text'],bordercolor=p['border'],lightcolor=p['border'],darkcolor=p['border'])
        style.configure('Treeview.Heading',background=p['surface'],foreground=p['text'],bordercolor=p['border'])
        style.map('Treeview',background=[('selected',p['selected'])],foreground=[('selected',p['text'])]); style.map('Treeview.Heading',background=[('active',p['selected'])])
        button_layout=[('Button.border',{'sticky':'nswe','children':[('Button.padding',{'sticky':'nswe','children':[('Button.label',{'sticky':'nswe'})]})]})]
        for name in ('TButton','Compact.TButton','Selected.TButton','Accent.TButton','Danger.TButton','Toolbar.TButton','Toolbar.Accent.TButton','Nav.TButton','NavSelected.TButton'):
            if self.dark: style.layout(name,button_layout)
            elif name in self.original_layouts: style.layout(name,self.original_layouts[name])
            accent='Accent' in name; danger='Danger' in name; selected=name in ('Selected.TButton','NavSelected.TButton')
            background='#d47726' if accent else '#a83842' if danger else p['selected'] if selected else p['surface']
            foreground='#101827' if accent else '#ffffff' if danger else p['text']
            style.configure(name,background=background,foreground=foreground,bordercolor=p['border'],lightcolor=p['border'],darkcolor=p['border'])
            style.map(name,background=[('disabled',p['bg']),('pressed',p['selected']),('active','#e58a36' if accent else '#be4550' if danger else p['selected'])],foreground=[('disabled',p['muted']),('active',foreground)])
        for name in ('Vertical.TScrollbar','Horizontal.TScrollbar'):
            style.configure(name,background=p['surface'],troughcolor=p['bg'],arrowcolor=p['muted'],bordercolor=p['border'],lightcolor=p['border'],darkcolor=p['border']); style.map(name,background=[('active',p['selected'])])
        style.configure('Horizontal.TScale',background=p['bg'],troughcolor=p['field'],bordercolor=p['border'])
        style.configure('Horizontal.TProgressbar',background='#38b9a5',troughcolor=p['field'],bordercolor=p['border'])
        style.configure('TSeparator',background=p['border']); style.configure('Sash',background=p['border'])
        for option,key in [('background','field'),('foreground','text'),('selectBackground','selected'),('selectForeground','text')]: self.root.option_add('*TCombobox*Listbox.'+option,p[key])
        self.style_widgets(self.root)
        if hasattr(self.root,'refresh_tool_icons'): self.root.refresh_tool_icons()
        if persist: self.save()
    def style_widgets(self,widget):
        p=self.colors
        try:
            if isinstance(widget,(tk.Tk,tk.Toplevel,tk.Frame)): widget.configure(background=p['bg'])
            elif isinstance(widget,tk.Canvas):
                widget.configure(background=p['canvas']); self.style_canvas(widget)
            elif isinstance(widget,(tk.Text,tk.Entry,tk.Listbox)):
                widget.configure(background=p['field'],foreground=p['text'],selectbackground=p['selected'],selectforeground=p['text'],highlightbackground=p['border'],highlightcolor=p['accent'])
                if isinstance(widget,(tk.Text,tk.Entry)): widget.configure(insertbackground=p['text'])
            elif isinstance(widget,tk.Label):
                # The connection dot retains its semantic red/green foreground.
                widget.configure(background=p['header'] if widget==getattr(self.root,'connection_dot',None) else p['bg'])
                if widget!=getattr(self.root,'connection_dot',None): widget.configure(foreground=p['text'])
            elif isinstance(widget,tk.Menu): widget.configure(background=p['surface'],foreground=p['text'],activebackground=p['selected'],activeforeground=p['text'],disabledforeground=p['muted'],selectcolor=p['accent'])
            elif isinstance(widget,tk.Button):
                if widget.master==getattr(self.root,'palette',None):
                    buttons=[w for w in widget.master.winfo_children() if isinstance(w,tk.Button)]
                    index=buttons.index(widget)
                    active=index<len(self.root.p.layers) and self.root.p.layers[index].id==self.root.active_layer
                    widget.configure(highlightbackground=p['accent'] if active else p['bg'],activebackground=widget.cget('background'))
            elif isinstance(widget,ttk.Combobox):
                popup=str(self.root.tk.call('ttk::combobox::PopdownWindow',str(widget)))+'.f.l'
                self.root.tk.call(popup,'configure','-background',p['field'],'-foreground',p['text'],'-selectbackground',p['selected'],'-selectforeground',p['text'])
            if isinstance(widget,(tk.Tk,tk.Toplevel)): self.titlebar(widget)
        except tk.TclError: pass
        for child in widget.winfo_children(): self.style_widgets(child)
    def titlebar(self,window):
        if os.name!='nt': return
        try:
            import ctypes
            from ctypes import wintypes
            window.update_idletasks()
            ancestor=ctypes.windll.user32.GetAncestor; ancestor.argtypes=[wintypes.HWND,wintypes.UINT]; ancestor.restype=wintypes.HWND
            handle=ancestor(window.winfo_id(),2); value=ctypes.c_int(self.dark)
            call=ctypes.windll.dwmapi.DwmSetWindowAttribute; call.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
            call(handle,20,ctypes.byref(value),ctypes.sizeof(value))
        except (OSError,AttributeError): pass
    def style_canvas(self,canvas):
        p=self.colors
        roles={'white':'paper','#ffffff':'paper','#edf0f3':'grid','#edf1f6':'grid','#f4f6fa':'surface','#ced7e3':'border','#cbd5e1':'border','#8795a3':'border','#8997a5':'border','#8895a4':'border','#657588':'muted','#64748b':'muted','#666':'muted','#182b40':'text','#354d67':'accent','#94a3b8':'muted'}
        cache=getattr(canvas,'_theme_originals',{}); live=set(canvas.find_all()); cache={item:values for item,values in cache.items() if item in live}
        for item in live:
            # Document colours and photo pixels are never recoloured.
            tags=canvas.gettags(item)
            if any(tag.startswith('s:') for tag in tags) or 'fill-preview' in tags: continue
            options=canvas.itemconfigure(item)
            for option in ('fill','outline'):
                if option not in options: continue
                value=cache.get(item,{}).get(option,canvas.itemcget(item,option))
                if value.lower() in roles:
                    cache.setdefault(item,{})[option]=value
                    target=p[roles[value.lower()]] if self.dark else value
                    canvas.itemconfigure(item,**{option:target})
        canvas._theme_originals=cache
