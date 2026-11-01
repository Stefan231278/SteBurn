"""Resize math without rounding stored geometry to display precision."""
from copy import deepcopy
from steburn.core.paths import bounds,shape_paths,as_paths_shape

def resize_shape(original,handle,pointer,keep_ratio):
    x0,y0,x1,y1=bounds([original]); width=x1-x0; height=y1-y0
    if width<=0 or height<=0: raise ValueError('Nullbreite/-höhe kann nicht am Rahmen skaliert werden.')
    anchor_x=x1 if 'w' in handle else x0
    anchor_y=y1 if 's' in handle else y0
    new_w=max(.1,abs(pointer[0]-anchor_x)) if 'w' in handle or 'e' in handle else width
    new_h=max(.1,abs(pointer[1]-anchor_y)) if 's' in handle or 'n' in handle else height
    if keep_ratio and len(handle)==2:
        if handle in {'e','w'}: factor=new_w/width
        elif handle in {'n','s'}: factor=new_h/height
        else: factor=max(new_w/width,new_h/height)
        new_w=width*factor; new_h=height*factor
    nx=anchor_x-new_w if 'w' in handle else anchor_x
    ny=anchor_y-new_h if 's' in handle else anchor_y
    # Side handles keep the opposite side and orthogonal centre fixed.
    if handle in {'e','w'}: ny=(y0+y1-new_h)/2
    if handle in {'n','s'}: nx=(x0+x1-new_w)/2
    result=deepcopy(original)
    if result.kind=='image': result.x=nx; result.y=ny; result.w=new_w; result.h=new_h
    elif result.kind in ('rect','ellipse') and 'contours' not in result.extra:
        result.x=nx; result.y=ny; result.w=new_w; result.h=new_h
        if 'corner_radius' in result.extra: result.extra['corner_radius']=min(result.extra['corner_radius']*min(new_w/width,new_h/height),new_w/2,new_h/2)
    elif 'bezier' in result.extra:
        from steburn.core.design import set_bezier
        nodes=[(nx+(original.x+x-x0)*new_w/width,ny+(original.y+y-y0)*new_h/height) for x,y in original.extra['bezier']]
        set_bezier(result,nodes)
    elif result.kind=='text':
        result.x=nx; result.y=ny; result.h=original.h*new_h/height
        oldscale=original.extra.get('text_scale_x',1.)
        result.extra['text_scale_x']=oldscale*(new_w/width)/(new_h/height)
        result.w=new_w
    else:
        paths=[[(nx+(x-x0)*new_w/width,ny+(y-y0)*new_h/height) for x,y in path] for path in shape_paths(original)]
        as_paths_shape(result,paths)
    return result
