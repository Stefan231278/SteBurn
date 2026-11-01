"""Direct node selection, closed-path editing and live construction previews."""
from copy import deepcopy
from steburn.core.nodes import paths,transform_nodes
from steburn.core.design import cubic_points,set_bezier
from steburn.core.nodes import delete_nodes
from steburn.core.paths import shape_paths
import math
import tkinter as tk
from tkinter import ttk

class Drawing:
    def remember_objects(self):
        order=[sid for sid in getattr(self,'selection_order',[]) if sid in self.selection]
        order.extend(shape.id for shape in self.p.shapes if shape.id in self.selection and shape.id not in order)
        self.selection_order=order; return order
    def ordered_node_keys(self):
        keys={k for k in getattr(self,'node_keys',set()) if k[0] in self.selection}
        order=[key for key in getattr(self,'node_order',[]) if key in keys]
        objects=self.remember_objects(); rank={sid:i for i,sid in enumerate(objects)}
        order.extend(sorted(keys-set(order),key=lambda k:(rank.get(k[0],len(rank)),k[1],k[2])))
        self.node_order=order; return order
    def set_node_keys(self,keys,sequence=None):
        self.node_keys=set(keys)
        self.node_order=[key for key in getattr(self,'node_order',[]) if key in self.node_keys]
        for key in sequence or []:
            if key in self.node_keys and key not in self.node_order: self.node_order.append(key)
        self.ordered_node_keys()
    @property
    def measurements(self):
        values=self.p.extensions.get('measurements',[])
        if not isinstance(values,list): return []
        result=[]
        for pair in values:
            if isinstance(pair,(list,tuple)) and len(pair)==2 and all(isinstance(point,(list,tuple)) and len(point)==2 and all(type(v) in (int,float) and math.isfinite(v) for v in point) for point in pair): result.append(pair)
        return result
    def build_vector_panel(self):
        super().build_vector_panel()
        card=self.card(self.vector_tab.content,'Offene Konturen verbinden')
        for label,curve,tangent in [('Mit Gerade verbinden',False,False),('Mit Kurve verbinden',True,False),('Mit tangentialer Kurve verbinden',True,True)]:
            ttk.Button(card,text=label,style='Compact.TButton',command=lambda c=curve,t=tangent:self.join_contours(c,t)).pack(fill='x',pady=2)
        ttk.Button(card,text='Tangentialbedingung lösen',style='Compact.TButton',command=self.release_tangency).pack(fill='x',pady=2)
        ttk.Label(card,text='Zwei Endpunkte einrahmen oder nacheinander auswählen. Der erste bildet die Basis (Ebene und Bearbeitungswerte). Verbundene Teile werden gruppiert.',wraplength=290).pack(fill='x',pady=4)
    def object_menu(self):
        menu=super().object_menu(); joins=tk.Menu(menu,tearoff=False)
        for label,c,t in [('Gerade',False,False),('Kurve',True,False),('Tangentiale Kurve',True,True)]: joins.add_command(label=label,command=lambda c=c,t=t:self.join_contours(c,t))
        joins.add_separator(); joins.add_command(label='Tangentialbedingung lösen',command=self.release_tangency)
        menu.add_cascade(label='Offene Konturen verbinden',menu=joins); return menu
    def release_tangency(self):
        project=deepcopy(self.p); changed=False
        for shape in project.shapes:
            if shape.id not in self.selection or shape.extra.get('locked'): continue
            constrained=shape.extra.get('tangent_anchors',[]); selected={i for sid,ci,i in getattr(self,'node_keys',set()) if sid==shape.id and ci==0 and i%3==0}
            remaining=[i for i in constrained if i not in selected] if selected else []
            if remaining!=constrained: shape.extra['tangent_anchors']=remaining; changed=True
        if changed: self.commit(project); self.status.set('Lokale Tangentialbedingungen gelöst. „Tangenten spiegeln“ ist eine separate Einstellung.')
    def coords(self,e):
        fallback=super().coords(e); self.snap_target=None
        if not getattr(self,'workspace_ready',False) or not self.snap_enabled.get() or getattr(e,'state',0)&8: return fallback
        raw=((e.x-self.ox)/self.scale,self.p.height-(e.y-self.oy)/self.scale); candidates=[]
        excluded=set()
        if self.drag and self.drag[0]=='move_many': excluded={s.id for s in self.drag[3]}
        if self.drag and self.drag[0]=='resize': excluded={self.drag[1].id}
        for shape in self.p.shapes:
            if shape.id in excluded or shape.kind in ('image','text') or not next(l for l in self.p.layers if l.id==shape.layer).visible: continue
            for ci,path in enumerate(paths(shape)):
                for i,point in enumerate(path):
                    if 'bezier' in shape.extra and i%3: continue
                    canonical=0 if i==len(path)-1 and path[0]==path[-1] else i
                    if self.drag and self.drag[0]=='node-group' and (shape.id,ci,canonical) in getattr(self,'node_keys',set()): continue
                    distance=math.dist(raw,point)
                    if distance*self.scale<=10: candidates.append((distance,point))
        for point in self.poly_points if self.tool=='polygon' else []:
            distance=math.dist(raw,point)
            if distance*self.scale<=10: candidates.append((distance,point))
        if candidates: self.snap_target=min(candidates,key=lambda item:item[0])[1]; return self.snap_target
        return fallback
    def delete(self):
        if self.tool=='nodes' and getattr(self,'node_keys',set()): return self.delete_node()
        return super().delete()
    def delete_node(self):
        keys={k for k in getattr(self,'node_keys',set()) if k[0] in self.selection}
        if not keys: return super().delete_node()
        project=deepcopy(self.p); output=[]
        for shape in project.shapes:
            selected={(ci,i) for sid,ci,i in keys if sid==shape.id}
            replacement=delete_nodes(shape,selected) if selected and not shape.extra.get('locked') else shape
            if replacement is not None: output.append(replacement)
        project.shapes=output; self.node_keys=set(); self.node_selection=None; self.commit(project)
    def clear_measurements(self):
        self.measuring=None; project=deepcopy(self.p); project.extensions.pop('measurements',None); self.commit(project); self.status.set('Alle Maße entfernt.')
    def join_contours(self,curve=False,tangent=False):
        from steburn.core.connect import join,endpoints
        try:
            keys=self.ordered_node_keys() if self.tool=='nodes' else []
            if keys and len(keys)!=2: raise ValueError('Zum Verbinden genau zwei offene Endpunkte einrahmen oder markieren.')
            if len(keys)==2:
                chosen=[]
                for sid,ci,index in keys:
                    shape=next(s for s in self.p.shapes if s.id==sid); ends=endpoints(shape)
                    if ci or index not in (0,len(paths(shape)[0])-1): raise ValueError('Zum Verbinden genau zwei offene Endknoten auswählen.')
                    chosen.append((shape,0 if index==0 else 1))
                (first,a),(second,b)=chosen
            else:
                table={s.id:s for s in self.p.shapes}; selected=[table[sid] for sid in self.remember_objects()]
                if len(selected)==1:
                    first=second=selected[0]; a,b=1,0; endpoints(first)
                elif len(selected)==2:
                    first,second=selected; ea,eb=endpoints(first),endpoints(second)
                    a,b=min(((i,j) for i in (0,1) for j in (0,1)),key=lambda pair:math.dist(ea[pair[0]],eb[pair[1]]))
                else: raise ValueError('Zwei offene Konturen oder zwei offene Endknoten auswählen.')
            if first.extra.get('locked') or second.extra.get('locked'): raise ValueError('Gesperrte Konturen zuerst entsperren.')
            result=join(first,second,a,b,curve,tangent); project=deepcopy(self.p)
            project.shapes=[result if s.id==first.id else s for s in project.shapes if s.id!=second.id or s.id==first.id]
            groups={s.extra.get('group') for s in (first,second)}-{None}; group=result.extra['group']
            for shape in project.shapes:
                if shape.extra.get('group') in groups: shape.extra['group']=group
            self.selection={s.id for s in project.shapes if s.extra.get('group')==group}; self.selected=result.id
            self.selection_order=[result.id]+[sid for sid in self.remember_objects() if sid!=result.id]
            self.node_keys=set(); self.node_order=[]; self.node_selection=None; self.commit(project)
            layer=next(l for l in project.layers if l.id==result.layer)
            self.status.set(f'Verbunden und gruppiert · Basis: {first.name} · Ebene und Bearbeitungswerte aus „{layer.name}“'+(' · tangential' if tangent else '')+' · Strg+Z macht rückgängig.')
        except (ValueError,StopIteration) as ex: self.status.set(str(ex))
    def set_tool(self,tool):
        super().set_tool(tool)
        if tool=='nodes':
            self.node_keys={k for k in getattr(self,'node_keys',set()) if k[0] in self.selection}
            if self.node_selection and self.node_selection[0] not in self.selection: self.node_selection=None
            self.status.set('Knoten klicken oder einrahmen · Shift/Strg: ergänzen · Ziehen: gemeinsam verschieben · Entf: ausgewählte Knoten löschen.')
    def move_curve_node(self,shape,nodes,index,target):
        original=deepcopy(shape); set_bezier(original,nodes)
        dx,dy=target[0]-nodes[index][0],target[1]-nodes[index][1]
        result=transform_nodes(original,{(0,index)},lambda x,y:(x+dx,y+dy)); shape.__dict__.update(result.__dict__)
    def node_points(self,all_visible=False):
        for shape in self.p.shapes if all_visible else self.chosen():
            if shape.kind in ('text','image') or shape.extra.get('locked'): continue
            if not next(l for l in self.p.layers if l.id==shape.layer).visible: continue
            for ci,path in enumerate(paths(shape)):
                count=len(path)-1 if len(path)>1 and path[0]==path[-1] else len(path)
                for i,point in enumerate(path[:count]): yield (shape.id,ci,i),point
    def render(self):
        super().render()
        for a,b in getattr(self,'measurements',[]): self.draw_measure(a,b)
        if self.tool!='nodes': return
        c=self.canvas
        for item in c.find_all():
            if any(t.startswith(('node:','curve:')) for t in c.gettags(item)): c.delete(item)
        selected=getattr(self,'node_keys',set()); points=[]
        for key,point in self.node_points():
            x,y=self.screen(*point); active=key in selected; r=5 if active else 4
            curve=next(s for s in self.p.shapes if s.id==key[0]).extra.get('bezier')
            draw=c.create_oval if curve and key[2]%3 else c.create_rectangle
            draw(x-r,y-r,x+r,y+r,fill='#f59e0b' if active else '#ffffff',outline='#7c3aed',width=2,tags='edit-node:'+':'.join(map(str,key)))
            if key[2] in next(s for s in self.p.shapes if s.id==key[0]).extra.get('tangent_anchors',[]):
                c.create_text(x+9,y+10,text='T',fill='#0d9488',font=('Segoe UI',8,'bold'),tags='tangent-condition')
            if active: points.append(point)
        ordered=self.ordered_node_keys()
        if len(ordered)==2:
            positions=dict(self.node_points())
            for i,key in enumerate(ordered):
                if key in positions:
                    x,y=self.screen(*positions[key]); c.create_text(x+10,y-12,text='1 · Basis' if i==0 else '2',anchor='w',fill='#0d9488',font=('Segoe UI',9,'bold'),tags='join-basis')
        chosen=self.chosen(); simple_line=len(chosen)==1 and 'bezier' not in chosen[0].extra and len(paths(chosen[0]))==1 and len(paths(chosen[0])[0])==2
        if len(points)>1 and not simple_line:
            x0,y0=min(p[0] for p in points),min(p[1] for p in points); x1,y1=max(p[0] for p in points),max(p[1] for p in points)
            c.create_rectangle(*self.screen(x0,y0),*self.screen(x1,y1),outline='#f59e0b',dash=(3,3))
            if x1-x0>1e-6 and y1-y0>1e-6:
                for name,point in [('sw',(x0,y0)),('se',(x1,y0)),('nw',(x0,y1)),('ne',(x1,y1)),('e',(x1,(y0+y1)/2)),('w',(x0,(y0+y1)/2)),('n',((x0+x1)/2,y1)),('s',((x0+x1)/2,y0))]:
                    x,y=self.screen(*point); x+=10 if 'e' in name else -10 if 'w' in name else 0; y+=-10 if 'n' in name else 10 if 's' in name else 0
                    c.create_oval(x-4,y-4,x+4,y+4,fill='#f59e0b',outline='#9a6209',tags='node-scale:'+name)
    def mouse_move(self,e):
        super().mouse_move(e); point=self.coords(e); self.construction_preview(point)
        self.canvas.delete('measure-live')
        if self.tool=='measure' and self.measuring is not None: self.draw_measure(self.measuring,point,True)
        self.show_snap_target()
    def show_snap_target(self):
        self.canvas.delete('snap-target')
        if getattr(self,'snap_target',None) is not None:
            x,y=self.screen(*self.snap_target); self.canvas.create_oval(x-7,y-7,x+7,y+7,outline='#0d9488',width=2,tags='snap-target')
    def draw_measure(self,a,b,live=False):
        c=self.canvas; tag='measure-live' if live else 'dimension'; ax,ay=self.screen(*a); bx,by=self.screen(*b)
        c.create_line(ax,ay,bx,by,fill='#bc73ed',width=2,dash=(4,3) if live else (),arrow='both',tags=tag)
        c.create_text((ax+bx)/2,(ay+by)/2-12,text=f'{math.dist(a,b):.2f} mm',fill='#bc73ed',font=('Segoe UI',10,'bold'),tags=tag)
    def construction_preview(self,point):
        c=self.canvas; c.delete('construction-preview')
        committed=self.poly_points if self.tool=='polygon' else self.curve_clicks if self.tool=='bezier' else []
        if not committed: return
        points=committed+[point]
        c.create_line(*[v for p in points for v in self.screen(*p)],fill='#7c3aed',dash=(4,3),tags='construction-preview')
        if self.tool=='bezier' and len(points)==4:
            c.create_line(*[v for p in cubic_points(points) for v in self.screen(*p)],fill='#a855f7',width=2,tags='construction-preview')
        if self.tool=='polygon' and len(committed)>1:
            c.create_line(*self.screen(*point),*self.screen(*committed[0]),fill='#a78bfa',dash=(2,4),tags='construction-preview')
    def press(self,e):
        if self.tool=='measure':
            point=self.coords(e)
            if self.measuring is None: self.measuring=point; self.mouse_move(e)
            else:
                project=deepcopy(self.p); project.extensions['measurements']=self.measurements+[(self.measuring,point)]; self.measuring=None; self.commit(project)
            return
        if self.tool=='select':
            for item in reversed(self.canvas.find_overlapping(e.x-6,e.y-6,e.x+6,e.y+6)):
                for tag in self.canvas.gettags(item):
                    if tag.startswith('line-end:'):
                        _,sid,index=tag.split(':'); shape=next(s for s in self.p.shapes if s.id==sid)
                        if shape.extra.get('locked'): return
                        self.selected=sid; self.selection={sid}
                        self.set_node_keys({(sid,0,int(index))},[(sid,0,int(index))]); self.checkpoint(); self.drag=('node-group',self.coords(e),[deepcopy(shape)],None,(0,0,1,1)); return
        if self.tool!='nodes' or self.space_pan or e.x<28 or e.y<24:
            result=super().press(e); self.remember_objects(); return result
        self.canvas.focus_set(); point=self.coords(e); keys=getattr(self,'node_keys',set())
        hits=[tag for item in reversed(self.canvas.find_overlapping(e.x-6,e.y-6,e.x+6,e.y+6)) for tag in self.canvas.gettags(item)]
        scale=next((tag.split(':')[1] for tag in hits if tag.startswith('node-scale:')),None)
        candidates={tuple(tag.split(':')[1:]) for tag in hits if tag.startswith('edit-node:')}
        locations={tuple(map(str,key)):p for key,p in self.node_points()}
        key=min(candidates,key=lambda key:(locations[key][0]-point[0])**2+(locations[key][1]-point[1])**2) if candidates else None
        if key:
            key=(key[0],int(key[1]),int(key[2]))
            if e.state&5:
                keys=set(keys); keys.symmetric_difference_update({key})
            elif key not in keys: keys={key}
            self.set_node_keys(keys,[key]); self.selected=key[0]; self.node_selection=key
            if key not in keys: self.render(); return
        elif not scale:
            sid=next((tag[2:] for tag in hits if tag.startswith('s:')),None)
            self.drag=('node-box',point,bool(e.state&5),set(keys),sid); return
        originals=[deepcopy(s) for s in self.chosen() if any(key[0]==s.id for key in keys) and not s.extra.get('locked')]
        points=[p for k,p in self.node_points() if k in keys]
        if not points: return
        box=(min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points))
        self.checkpoint(); self.drag=('node-group',point,originals,scale,box); self.refresh_nodes(); self.render()
    def motion(self,e):
        if self.tool=='measure' and self.measuring is not None: self.mouse_move(e); return
        if not self.drag or self.drag[0] not in ('node-box','node-group'):
            result=super().motion(e); self.show_snap_target(); return result
        point=self.coords(e)
        if self.drag[0]=='node-box':
            a=self.drag[1]; self.canvas.delete('node-box'); self.canvas.create_rectangle(*self.screen(*a),*self.screen(*point),outline='#7c3aed',dash=(4,3),tags='node-box'); return
        _,start,originals,handle,box=self.drag; dx,dy=point[0]-start[0],point[1]-start[1]
        fn=lambda x,y:(x+dx,y+dy)
        if handle:
            x0,y0,x1,y1=box; ax=x1 if 'w' in handle else x0; ay=y1 if 's' in handle else y0
            sx=max(.001,1+(dx if 'e' in handle else -dx)/(x1-x0)) if 'w' in handle or 'e' in handle else 1
            sy=max(.001,1+(dy if 'n' in handle else -dy)/(y1-y0)) if 's' in handle or 'n' in handle else 1
            fn=lambda x,y:(ax+(x-ax)*sx,ay+(y-ay)*sy)
        replacements={old.id:transform_nodes(old,{(c,i) for sid,c,i in self.node_keys if sid==old.id},fn) for old in originals}
        self.p.shapes=[replacements.get(s.id,s) for s in self.p.shapes]; self.render(); self.show_snap_target()
    def release(self,e):
        if self.drag and self.drag[0]=='node-box':
            _,a,add,keys,sid=self.drag; b=self.coords(e); self.drag=None
            if sid and math.dist(a,b)*self.scale<3:
                if not add: self.selection=set(); self.node_keys=set(); self.node_order=[]; self.node_selection=None
                self.selection.add(sid); self.selected=sid; self.remember_objects(); self.refresh(); return
            objects=self.remember_objects(); rank={sid:i for i,sid in enumerate(objects)}
            caught=[(k,p) for k,p in self.node_points(True) if min(a[0],b[0])<=p[0]<=max(a[0],b[0]) and min(a[1],b[1])<=p[1]<=max(a[1],b[1])]
            caught.sort(key=lambda item:(rank.get(item[0][0],len(rank)),math.dist(a,item[1]),item[0]))
            self.selection.update(k[0] for k,p in caught)
            if not add: self.node_order=[]
            self.set_node_keys((keys if add else set())|{k for k,p in caught},[k for k,p in caught])
            if self.node_order: self.selected=self.node_order[0][0]; self.node_selection=self.node_order[0]
            self.remember_objects(); self.refresh(); return
        if self.drag and self.drag[0]=='node-group':
            self.motion(e); self.drag=None; self.changed(); self.refresh(); return
        super().release(e)
    def select_node_row(self,e=None):
        items=self.node_tree.selection(); shape=self.current()
        if not items or not shape: return
        keys={(shape.id,*map(int,item.split(':'))) for item in items}
        self.set_node_keys({k for k in getattr(self,'node_keys',set()) if k[0]!=shape.id}|keys,[(shape.id,*map(int,item.split(':'))) for item in items])
        key=next((key for key in self.node_order if key in keys),next(iter(keys))); self.node_selection=key
        contours=paths(shape)
        if key[1]>=len(contours) or key[2]>=len(contours[key[1]]): return
        x,y=contours[key[1]][key[2]]; self.auto_suspended+=1
        try: self.node_x.set(f'{x:.6f}'); self.node_y.set(f'{y:.6f}')
        finally: self.auto_suspended-=1
        self.render()
    def refresh_nodes(self):
        if not hasattr(self,'node_tree'): return
        self.auto_suspended+=1
        try:
            self.node_tree.configure(selectmode='extended'); self.node_tree.delete(*self.node_tree.get_children()); shape=self.current()
            if not shape or shape.kind in ('text','image'): return
            selected=[]
            for ci,path in enumerate(paths(shape)):
                count=len(path)-1 if len(path)>1 and path[0]==path[-1] else len(path)
                for i,(x,y) in enumerate(path[:min(count,1000)]):
                    role=('Anker' if i%3==0 else 'Griff') if 'bezier' in shape.extra else 'Knoten'
                    if i in shape.extra.get('tangent_anchors',[]): role+=' · T'
                    iid=f'{ci}:{i}'; self.node_tree.insert('','end',iid=iid,values=(f'{role} {ci+1}.{i+1}',f'{x:.3f}',f'{y:.3f}'))
                    if (shape.id,ci,i) in getattr(self,'node_keys',set()): selected.append(iid)
                    if self.node_selection==(shape.id,ci,i): self.node_x.set(f'{x:.6f}'); self.node_y.set(f'{y:.6f}')
            if selected: self.node_tree.selection_set(selected)
        finally: self.auto_suspended-=1
