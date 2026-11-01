from copy import deepcopy

def move_layer(project,lid,direction):
    result=deepcopy(project); i=next(i for i,l in enumerate(result.layers) if l.id==lid); j=i+direction
    if 0<=j<len(result.layers): result.layers[i],result.layers[j]=result.layers[j],result.layers[i]
    return result

def layer_for_segment(project,segment):
    return next((s.layer for s in project.shapes if s.id==segment.shape_id),None)
