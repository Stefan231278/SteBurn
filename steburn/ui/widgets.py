import tkinter as tk
from tkinter import ttk
class ScrollPanel(ttk.Frame):
    def __init__(self,parent):
        super().__init__(parent)
        self.canvas=tk.Canvas(self,highlightthickness=0,bg='#eef1f4',width=275)
        self.bar=ttk.Scrollbar(self,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.bar.set); self.canvas.pack(side='left',fill='both',expand=True)
        self.content=ttk.Frame(self.canvas); self.window=self.canvas.create_window(0,0,window=self.content,anchor='nw')
        self.content.bind('<Configure>',self.refresh_scroll)
        self.canvas.bind('<Configure>',self.resize)
        self.winfo_toplevel().bind('<MouseWheel>',self.wheel,add='+')
        self._wheel_remainder=0.
        self.wheel_tag='ScrollPanelWheel'+str(id(self))
        self.bind_class(self.wheel_tag,'<MouseWheel>',self.wheel)
    def resize(self,e):
        self.canvas.itemconfigure(self.window,width=e.width); self.refresh_scroll()
    def refresh_scroll(self,e=None):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        if self.content.winfo_reqheight()>self.canvas.winfo_height()+2:
            if not self.bar.winfo_manager(): self.bar.pack(side='right',fill='y',before=self.canvas)
        else:
            self.bar.pack_forget(); self.canvas.yview_moveto(0)
        def attach(widget):
            tags=widget.bindtags()
            if self.wheel_tag not in tags: widget.bindtags((self.wheel_tag,)+tags)
            for child in widget.winfo_children(): attach(child)
        attach(self.content)
    def wheel(self,e):
        if str(e.widget).startswith(str(self)):
            if not e.delta: return
            self._wheel_remainder-=e.delta/120*24
            pixels=int(self._wheel_remainder); self._wheel_remainder-=pixels
            box=self.canvas.bbox('all')
            if box and box[3]>self.canvas.winfo_height() and pixels:
                self.canvas.yview_moveto(self.canvas.yview()[0]+pixels/box[3])
            return 'break'
