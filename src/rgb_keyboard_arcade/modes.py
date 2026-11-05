"""Mode styles, fixed difficulty presets, and bounded reachable-food planning."""
import colorsys,math
from collections import deque
MODES=(('rainbow','Rainbow'),('timer','Timer'))
DIFFICULTIES=(
    ('Easy',(0,255,0),.34,.17,.16),
    ('Medium',(255,100,0),.26,.145,.125),
    ('Hard',(255,0,0),.20,.12,.10),
    ('Expert',(110,0,255),.15,.095,.08),
)
TEMPERATURE=((255,255,255),(255,222,35),(255,125,15),(235,28,24))
TIMER_PALETTE=dict(head=(100,35,185),tail=(245,100,225),background=(1,1,1),
                   passive_background=(2,2,2),apple=TEMPERATURE[0],passive_apple=TEMPERATURE[0])
DIRECTIONS=('up','right','down','left')
OPPOSITE={'up':'down','down':'up','left':'right','right':'left'}

def temperature(progress):
    p=max(0.,min(1.,progress))*(len(TEMPERATURE)-1);index=min(len(TEMPERATURE)-2,int(p));t=p-index
    return tuple(round(a+(b-a)*t) for a,b in zip(TEMPERATURE[index],TEMPERATURE[index+1]))

def style_color(mode,now,phase=0.):
    if mode=='rainbow':return tuple(round(v*255) for v in colorsys.hsv_to_rgb((now*.22+phase)%1,.92,1))
    # Reversing at white/red keeps the cycle continuous without crossing pink or violet.
    return temperature(.5-.5*math.cos(now*.85+phase*math.tau))

def static_routes(body,direction,moves,available,other_food=()):
    """Shortest simple routes without cutting through the current body or food."""
    blocked=set(body);blocked.discard(body[0]);blocked.discard(body[-1]);blocked.update(other_food)
    blocked.discard(body[0]);queue=deque([(body[0],direction,())]);seen={(body[0],direction)};found={}
    while queue:
        cell,heading,path=queue.popleft()
        for turn in DIRECTIONS:
            if turn==OPPOSITE[heading]:continue
            nxt=moves[cell][turn]
            if nxt is None or nxt in blocked or nxt==body[0] or nxt in path:continue
            route=path+(nxt,)
            if nxt in available and nxt not in found:found[nxt]=route
            state=(nxt,turn)
            if state not in seen:seen.add(state);queue.append((nxt,turn,route))
    return found

def tail_route(body,direction,moves,available,other_food=(),limit=1800):
    """Find a legal moving-tail route when the static body closes every exit."""
    queue=deque([(tuple(body),direction,())]);seen={(tuple(body),direction)};blocked=set(other_food)
    while queue and len(seen)<limit:
        trail,heading,path=queue.popleft()
        for turn in DIRECTIONS:
            if turn==OPPOSITE[heading]:continue
            nxt=moves[trail[0]][turn]
            if nxt is None or nxt in trail[:-1] or nxt in blocked:continue
            route=path+(nxt,)
            if nxt in available:return {nxt:route}
            new=(nxt,)+trail[:-1];state=(new,turn)
            if state not in seen:seen.add(state);queue.append((new,turn,route))
    return {}
