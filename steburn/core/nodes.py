"""Node transformations preserving closed seams and editable cubic controls."""
from copy import deepcopy
from steburn.core.paths import shape_paths,as_paths_shape
from steburn.core.design import set_bezier
import math

def paths(shape):
    if 'bezier' in shape.extra: return [[(shape.x+x,shape.y+y) for x,y in shape.extra['bezier']]]
    return shape_paths(shape)

def transform_nodes(original,selected,point):
    result=deepcopy(original); contours=paths(original)
    for ci,path in enumerate(contours):
        closed=len(path)>1 and path[0]==path[-1]; count=len(path)-1 if closed else len(path)
        indices={i%count for c,i in selected if c==ci}
        changed={i:point(*path[i]) for i in indices}
        if 'bezier' in original.extra:
            for i in indices:
                if i%3==0:
                    adjacent=(i-1 if i>0 else count-1 if closed else -1,i+1)
                    for j in adjacent:
                        if 0<=j<len(path) and j not in changed:
                            # Affine node-group transforms also transform adjacent tangents.
                            changed[j]=point(*path[j])
        for i,value in changed.items(): path[i]=value
        if 'bezier' in original.extra:
            constrained=set(original.extra.get('tangent_anchors',[]))
            if original.extra.get('curve_smooth'): constrained.update(range(0,count,3))
            for anchor in constrained:
                if anchor<0 or anchor>=count: continue
                left=anchor-1 if anchor else count-1 if closed else -1; right=anchor+1
                if not 0<=left<len(path) or right>=len(path): continue
                source=right if right in indices else left if left in indices else None
                if source is None: continue
                opposite=left if source==right else right
                vector=(path[anchor][0]-path[source][0],path[anchor][1]-path[source][1]); norm=math.hypot(*vector)
                if norm<1e-12: path[opposite]=path[anchor]; continue
                factor=1. if original.extra.get('curve_smooth') else math.dist(path[anchor],path[opposite])/norm
                path[opposite]=(path[anchor][0]+vector[0]*factor,path[anchor][1]+vector[1]*factor)
        if closed: path[-1]=path[0]
    if 'bezier' in original.extra: return set_bezier(result,contours[0])
    return as_paths_shape(result,contours)

def delete_nodes(original,selected):
    result=deepcopy(original); contours=paths(original); output=[]
    if 'bezier' in original.extra:
        nodes=contours[0]; closed=nodes[0]==nodes[-1]; count=(len(nodes)-1)//3
        anchors=count if closed else count+1
        removed={i//3 for ci,i in selected if ci==0 and i%3==0}
        keep=[i for i in range(anchors) if i not in removed]
        if len(keep)<2: return None
        for ci,i in selected:
            if ci==0 and i%3:
                anchor=i-1 if i%3==1 else i+1; nodes[i]=nodes[anchor]
        chain=[nodes[keep[0]*3]]; sequence=keep+[keep[0]] if closed else keep
        for a,b in zip(sequence,sequence[1:]): chain.extend([nodes[a*3+1],nodes[b*3-1 if b else -2],nodes[b*3]])
        result.extra['tangent_anchors']=[j*3 for j,i in enumerate(keep) if i*3 in original.extra.get('tangent_anchors',[])]
        return set_bezier(result,chain)
    for ci,path in enumerate(contours):
        closed=path[0]==path[-1]; unique=path[:-1] if closed else path
        removed={i%len(unique) for c,i in selected if c==ci}
        kept=[p for i,p in enumerate(unique) if i not in removed]
        if len(kept)>=(3 if closed else 2): output.append(kept+[kept[0]] if closed else kept)
    return as_paths_shape(result,output) if output else None
