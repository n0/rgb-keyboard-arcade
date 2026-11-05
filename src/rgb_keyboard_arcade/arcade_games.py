"""Keyboard-native Minesweeper and Pong; pure simulation, no input/device I/O."""
import math,random
from collections import deque
from .game import Game
from .modes import DIFFICULTIES
from .effects import control_orbit

THEMES={'mines':(35,160,255),'pong':(235,45,190)}
def mix(a,b,t):return tuple(round(x+(y-x)*max(0,min(1,t))) for x,y in zip(a,b))
class DisplayGame(Game):
 id='';variant_modes=()
 def __init__(self,layout,seed=None,movement_map=None,reduced_motion=False,game_mode=None,difficulty=0):
  super().__init__(layout,seed,movement_map,reduced_motion,'rainbow',difficulty)
  self.game_mode=game_mode if game_mode in dict(self.variant_modes) else self.variant_modes[0][0]
  self.held={};self.queued=False;self.pending_action=None;self.last_time=0.;self.effect_start=0.;self.result=None
 def reset(self,now):
  self.held.clear();self.queued=False;self.result=None;self.pending_active=None
  self.phase='idle' if self.mode=='default' else 'running';self.phase_start=now;self.last_time=now
  self._new_round(now)
 def configure(self,now,game_mode=None,difficulty=None):
  if self.mode!='passive' or self.phase!='running':return False
  variant=self.game_mode if game_mode is None else game_mode;level=self.difficulty if difficulty is None else difficulty
  if variant not in dict(self.variant_modes) or type(level) is not int or not 0<=level<4:raise ValueError('Invalid game settings')
  if (variant,level)==(self.game_mode,self.difficulty):return False
  self.game_mode=variant;self.difficulty=level;self.reset(now);return True
 def selector_press(self,cell,now):
  if cell not in (self.labels['`'],self.labels['Tab']):return False
  if self.mode=='passive' and self.phase=='running':
   if cell==self.labels['Tab']:self.configure(now,difficulty=(self.difficulty+1)%4)
   else:
    ids=[k for k,_ in self.variant_modes];self.configure(now,game_mode=ids[(ids.index(self.game_mode)+1)%len(ids)])
  return True
 def request_active(self,direction,now):
  if self.phase=='dying':self.queued=True;return
  if self.mode!='passive' or self.phase!='running':return
  self.held.clear();self.phase='entering';self.phase_start=now;self.pending_active='play'
 def begin_active(self,now):
  if self.phase!='handoff':return
  action=self.pending_action;self.mode='classic';self.reset(now);self.pending_action=None
  self.action_after_start(action,now)
 def action_after_start(self,action,now):pass
 def restart(self,now):
  if self.mode=='default':return
  if self.phase=='dying':self.queued=True;return
  if self.phase!='running':return
  if self.mode=='classic':
   self.mode='passive';self.request_active('play',now)
  else:self.reset(now)
 def back(self,now):
  self.pending_action=None
  self.set_mode('passive' if self.mode=='classic' or self.phase in ('entering','handoff') else 'default',now)
  # set_mode can be idempotent while entry still owns Passive.
  if self.mode=='passive' and self.phase in ('entering','handoff'):self.reset(now)
 def steer(self,direction,now):
  if self.mode=='passive' or self.phase=='dying':self.request_active(direction,now)
 def finish(self,now,result):
  self.phase='dying';self.phase_start=now;self.result=result;self.held.clear();self.queued=False
 def base_tick(self,now):
  self.time=now
  if self.phase=='entering':
   if now-self.phase_start>=(.2 if self.reduced_motion else 1.4):self.phase='handoff'
   return False
  if self.phase=='dying':
   if now-self.phase_start>=(.5 if self.reduced_motion else 3.):
    if self.queued:
     self.mode='passive';self.phase='running';self.request_active('play',now)
    elif self.mode=='passive':self.reset(now)
    else:self.set_mode('passive',now)
   return False
  return self.mode!='default' and self.phase=='running'
 def controls(self,frame,now):
  if self.mode=='default':return {}
  preview=self.mode=='passive' and self.phase=='running'
  frame[self.labels['Tab']]=DIFFICULTIES[self.difficulty][1] if preview else (0,0,0)
  if preview:
   frame[self.labels['`']]=self.mode_color(now)
  if self.phase=='running' and (preview or self.id=='pong'):
   frame.update(control_orbit(self.control_keys(),now-self.phase_start,self.reduced_motion))
  return frame
 def control_keys(self):return [self.labels[k] for k in ('Up','Right','Down','Left')]
 def mode_color(self,now):return THEMES[self.id]
 def state(self,now):
  return {'mode':self.mode,'phase':self.phase,'game_mode':self.game_mode,'game_mode_name':dict(self.variant_modes)[self.game_mode],
   'game_modes':[{'id':k,'label':v} for k,v in self.variant_modes],
   'difficulty':self.difficulty,'difficulty_name':DIFFICULTIES[self.difficulty][0],
   'difficulties':[{'id':i,'label':d[0],'color':'#'+''.join(f'{v:02x}' for v in d[1])} for i,d in enumerate(DIFFICULTIES)],
   'selectors_enabled':self.mode=='passive' and self.phase=='running','playfield':self.cells,
   'score':self.score,'length':0,'apples':0,'bombs':0,'rounds':0,'boost_seconds':0,'shield_seconds':0,
   'stage':1,'stage_name':self.id,'stage_seconds':0,'food_paused':False,'portals':False,
   'pending_active':self.pending_active,'death_stage':self.result,'death_reason':self.result,
   'status_text':self.status_text(now),'cell_labels':self.cell_labels(),
   'pixels':[[*c,*rgb] for c,rgb in self.frame(now).items()]}
 def cell_labels(self):return []
 def entry_frame(self,now):
  age=now-self.phase_start;t=min(1,age/1.4);frame={}
  for c,(x,y) in self.grid_coords.items():
   if self.id=='mines':
    distance=abs(x-5.5)+abs(y-2);edge=t*10
    strength=max(0,1-abs(distance-edge)/1.6)
    frame[c]=mix((1,3,8),THEMES[self.id],strength)
   else:
    # Opposed paddle streaks converge to serve, then resolve into the arena.
    edge=t*4.5;strength=max(0,1-min(abs(x-edge),abs(9-x-edge))/1.4)
    frame[c]=mix((3,1,5),THEMES[self.id],strength*(.4+.6*(y==2)))
  return frame

class Minesweeper(DisplayGame):
 id='mines';variant_modes=(('sweep','Survey'),)
 NUMBER_COLORS=((5,12,15),(0,80,255),(0,225,30),(255,0,0),(128,0,255),(255,200,0),(0,225,220),(255,40,150),(235,235,235))
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  cols=kwargs.get('movement_map')['columns'] if kwargs.get('movement_map') else None
  if cols:
   self.cells=[self.labels[k] for col in cols for k in col];self.cellset=set(self.cells)
   self.grid_coords={self.labels[k]:(x,y) for x,col in enumerate(cols) for y,k in enumerate(col)}
  self.adj={c:{d for d in self.cells if d!=c and max(abs(self.grid_coords[c][0]-self.grid_coords[d][0]),abs(self.grid_coords[c][1]-self.grid_coords[d][1]))==1} for c in self.cells}
  self.mine_count=(6,9,12,15)[self.difficulty]
  self.mines=set();self.revealed=set();self.flags=set();self.reveal_at={};self.preview_next=0;self.detonation=None;self.sweep_origin=None
 def mode_color(self,now):return mix((0,75,255),(70,225,255),.5+.5*math.sin(now*2.4))
 def _new_round(self,now):
  self.mine_count=(6,9,12,15)[self.difficulty];self.mines=set();self.revealed=set();self.flags=set();self.reveal_at={}
  self.score=0;self.preview_next=now+1.;self.detonation=None;self.sweep_origin=None;self.board_ready=False
 def arm(self,cell):
  allowed=sorted(self.cellset-{cell}-self.adj[cell]);self.mines=set(self.rng.sample(allowed,self.mine_count));self.board_ready=True
 def count(self,cell):return len(self.adj[cell]&self.mines)
 def reveal(self,cell,now):
  if cell not in self.cellset or cell in self.flags or cell in self.revealed:return
  if not self.board_ready:self.arm(cell)
  if cell in self.mines:
   self.detonation=cell;self.finish(now,'mine');return
  queue=deque([cell]);seen={cell};origin=self.grid_coords[cell];self.sweep_origin=origin
  while queue:
   c=queue.popleft();self.revealed.add(c)
   distance=math.dist(origin,self.grid_coords[c]);self.reveal_at[c]=now+(0 if self.reduced_motion else distance*.055)
   if self.count(c)==0:
    for d in self.adj[c]-self.mines-self.flags-seen:seen.add(d);queue.append(d)
  self.score=len(self.revealed)
  if self.mode=='classic' and self.score==len(self.cells)-self.mine_count:self.finish(now,'win')
 def flag(self,cell):
  if cell not in self.cellset or cell in self.revealed:return
  if cell in self.flags:self.flags.remove(cell)
  elif len(self.flags)<self.mine_count:self.flags.add(cell)
 def key_down(self,cell,now):
  if self.selector_press(cell,now):return
  if cell in [self.labels[k] for k in ('Up','Right','Down','Left')] and (self.mode=='passive' or self.phase=='dying'):
   self.request_active('play',now);return
  if cell in self.cellset and self.phase=='running':self.held[cell]=(now,False)
  elif self.phase=='dying' and cell in self.cellset:self.pending_action=(cell,False);self.queued=True
 def key_up(self,cell,now):
  held=self.held.pop(cell,None)
  if not held:return
  start,committed=held
  if committed:return
  is_flag=now-start>=.45
  if self.mode=='passive':
   self.pending_action=(cell,is_flag);self.request_active('play',now)
  elif self.mode=='classic' and self.phase=='running':
   if is_flag:self.flag(cell)
   else:self.reveal(cell,now)
 def press(self,cell=None,now=None):
  now=self.time if now is None else now;self.key_down(cell,now);self.key_up(cell,now+.01)
 def action_after_start(self,action,now):
  if action:
   cell,is_flag=action
   if is_flag:self.flag(cell)
   else:self.reveal(cell,now)
 def tick(self,now):
  if not self.base_tick(now):return
  for cell,(start,committed) in list(self.held.items()):
   if not committed and now-start>=.45:
    if self.mode=='classic':self.flag(cell);self.held[cell]=(start,True)
    else:
     self.pending_action=(cell,True);self.request_active('play',now);break
  if self.mode=='passive' and now>=self.preview_next:
   self.preview_next=now+.65
   if not self.board_ready:self.arm(self.rng.choice(self.cells))
   covered=self.cellset-self.revealed-self.mines
   if not covered or len(self.revealed)>len(self.cells)*.72:self._new_round(now);return
   # Demonstration marks real mines and reveals safe cells with expanding waves.
   if self.rng.random()<.27 and self.mines-self.flags:self.flags.add(self.rng.choice(sorted(self.mines-self.flags)))
   else:self.reveal(self.rng.choice(sorted(covered)),now)
 def cell_labels(self):
  return [[*c,('⚑' if c in self.flags else str(self.count(c)) if c in self.revealed and self.count(c) else '')] for c in self.cells if c in self.flags or c in self.revealed and self.time>=self.reveal_at.get(c,0)]
 def status_text(self,now):
  if self.phase=='entering':return 'Survey sweep · release held keys to begin'
  if self.phase=='handoff':return 'Release keys to begin survey'
  if self.phase=='dying':return 'Board cleared!' if self.result=='win' else 'Mine struck · chain detonation'
  if self.mode=='passive':return 'Survey demo · tap a board key to begin'
  return f'{self.score}/{len(self.cells)-self.mine_count} safe · {len(self.flags)}/{self.mine_count} flags'
 def frame(self,now):
  if self.mode=='default':return {}
  if self.phase in ('entering','handoff'):return self.controls(self.entry_frame(now),now)
  f={c:(8,18,30) for c in self.cells}
  for c in self.revealed:
   age=now-self.reveal_at.get(c,now)
   if age>=0:f[c]=mix((100,235,255),self.NUMBER_COLORS[self.count(c)],min(1,age/.35))
  for c in self.flags:f[c]=(255,125,0)
  for c,(start,committed) in self.held.items():
   if not committed:f[c]=mix(f.get(c,(0,0,0)),(255,170,25),min(1,(now-start)/.45))
  if self.phase=='dying':
   age=now-self.phase_start;origin=self.grid_coords.get(self.detonation,(6,2));theme=(45,255,150) if self.result=='win' else (255,15,0)
   for c,(x,y) in self.grid_coords.items():
    distance=math.dist(origin,(x,y));delay=distance*.065
    if age>=delay:
     strength=max(0,1-(age-delay)/2.0)
     if self.result=='mine' and c in self.mines:strength*=.6+.4*math.cos(age*22)**2
     f[c]=mix((0,0,0),theme,strength)
  return self.controls(f,now)

class Pong(DisplayGame):
 id='pong';GOAL=3;variant_modes=(('solo','One player'),('duo','Two players'))
 SPEED=(4.2,5.7,7.2,9.)
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self._new_round(0)
 def _new_round(self,now):
  self.score=0;self.points=[0,0];self.paddles=[2.,2.];self.ball=[4.5,2.];self.velocity=[0.,0.]
  self.trail=deque(maxlen=7);self.serve_at=now+1.2;self.last_time=now;self.point_side=None;self.hit_at=-100.;self.hit_pos=(4.5,2.);self.miss_at=-100.;self.ai_error=self.rng.uniform(-.6,.6);self.ai_next=now
 def serve(self,now):
  speed=self.SPEED[self.difficulty];angle=self.rng.uniform(-.55,.55)
  self.velocity=[self.rng.choice((-1,1))*speed*math.cos(angle),speed*math.sin(angle)]
  self.serve_at=None;self.trail.clear()
 def control_keys(self):
  keys=('R Shift','Right') if self.game_mode=='solo' else ('L Shift','R Shift','Right','L Ctrl')
  return [self.labels[k] for k in keys]
 def mode_color(self,now):
  if self.game_mode=='solo':return (30,190,255)
  return mix((30,190,255),(255,35,165),.5+.5*math.sin(now*3))
 def key_down(self,cell,now):
  if self.selector_press(cell,now):return
  if cell not in [self.labels[k] for k in ('R Shift','Right','L Shift','L Ctrl','Up','Down','Left')]:return
  if self.mode=='passive' or self.phase=='dying':self.request_active('play',now)
  elif self.phase=='running':self.held[cell]=(now,False)
 def key_up(self,cell,now):self.held.pop(cell,None)
 def press(self,cell=None,now=None):
  now=self.time if now is None else now;self.key_down(cell,now)
  if self.mode=='classic' and self.phase=='running':
   # Preview clicks are discrete paddle nudges; hardware holds remain continuous.
   for side,up,down in ((1,'R Shift','Right'),(0,'L Shift','L Ctrl')):
    if cell==self.labels[up]:self.paddles[side]=max(.5,self.paddles[side]-.65)
    elif cell==self.labels[down]:self.paddles[side]=min(3.5,self.paddles[side]+.65)
  self.key_up(cell,now)
 def tick(self,now):
  if not self.base_tick(now):self.last_time=now;return
  elapsed=min(.12,max(0,now-self.last_time));self.last_time=now
  # Small physics substeps prevent tunneling through paddles at Expert speed.
  steps=max(1,math.ceil(elapsed/.012));dt=elapsed/steps
  for _ in range(steps):
   if self.phase!='running':break
   self.advance(dt,now)
 def advance(self,dt,now):
  preview=self.mode=='passive'
  for side,up,down in ((1,'R Shift','Right'),(0,'L Shift','L Ctrl')):
   ai=preview or side==0 and self.game_mode=='solo'
   if ai:
    target=max(.5,min(3.5,self.ball[1]+self.ai_error))
    if now>=self.ai_next:self.ai_error=self.rng.uniform(-.55,.55);self.ai_next=now+.22
    speed=5.2 if preview else (2.6,3.3,4.0,4.8)[self.difficulty]
    move=max(-speed*dt,min(speed*dt,target-self.paddles[side]))
   else:move=((self.labels[down] in self.held)-(self.labels[up] in self.held))*5.5*dt
   self.paddles[side]=max(.5,min(3.5,self.paddles[side]+move))
  if self.serve_at is not None:
   if now>=self.serve_at:self.serve(now)
   return
  old=list(self.ball);self.ball[0]+=self.velocity[0]*dt;self.ball[1]+=self.velocity[1]*dt
  if self.ball[1]<0:self.ball[1]=-self.ball[1];self.velocity[1]=abs(self.velocity[1]);self.hit_at=now;self.hit_pos=tuple(self.ball)
  elif self.ball[1]>4:self.ball[1]=8-self.ball[1];self.velocity[1]=-abs(self.velocity[1]);self.hit_at=now;self.hit_pos=tuple(self.ball)
  side=0 if self.velocity[0]<0 else 1;plane=.55 if side==0 else 8.45
  crossed=(old[0]>=plane>=self.ball[0]) if side==0 else (old[0]<=plane<=self.ball[0])
  if crossed:
   # Interpolate the exact impact rather than checking the next LED cell.
   fraction=(plane-old[0])/(self.ball[0]-old[0]);impact=old[1]+(self.ball[1]-old[1])*fraction
   if abs(impact-self.paddles[side])<=1.03:
    offset=max(-1,min(1,(impact-self.paddles[side])/1.03));angle=offset*1.02
    speed=self.SPEED[self.difficulty];self.velocity=[(1 if side==0 else -1)*speed*math.cos(angle),speed*math.sin(angle)]
    self.ball[0]=plane;self.hit_at=now;self.hit_pos=tuple(self.ball)
  if self.ball[0]<-.3 or self.ball[0]>9.3:
   winner=1-side;self.points[winner]+=1;self.score=self.points[1];self.point_side=winner;self.miss_at=now
   if max(self.points)>=self.GOAL:
    self.finish(now,'p1_win' if winner==1 else 'p2_win')
   else:self.ball=[4.5,2.];self.velocity=[0,0];self.trail.clear();self.serve_at=now+1.3
   return
  if not self.trail or math.dist(self.trail[-1],self.ball)>.3:self.trail.append(tuple(self.ball))
 def status_text(self,now):
  if self.phase=='entering':return 'Paddles charging · serve assembling'
  if self.phase=='handoff':return 'Release keys to serve'
  if self.phase=='dying':return 'Player 1 wins!' if self.result=='p1_win' else ('AI wins' if self.game_mode=='solo' else 'Player 2 wins!')
  if self.mode=='passive':return f'{dict(self.variant_modes)[self.game_mode]} demo · arrows or Shift to play'
  return f'P1 {self.points[1]} : {self.points[0]} '+('AI' if self.game_mode=='solo' else 'P2')+(' · serve…' if self.serve_at else ' · first to 3')
 def state(self,now):
  state=super().state(now);state.update(scores={'p1':self.points[1],'p2':self.points[0]},target_score=self.GOAL);return state
 def frame(self,now):
  if self.mode=='default':return {}
  if self.phase in ('entering','handoff'):return self.controls(self.entry_frame(now),now)
  f={c:((1,3,9) if self.game_mode=='solo' else (7,1,8)) for c in self.cells}
  for y in range(5):f[self.columns[4][y]]=f[self.columns[5][y]]=(7,4,13) if y%2==0 else (2,2,8)
  for side,color in ((0,(255,35,150)),(1,(20,210,255))):
   x=0 if side==0 else 9
   for y in range(5):
    coverage=max(0,min(1,1.5-abs(y-self.paddles[side])))
    if coverage:f[self.columns[x][y]]=tuple(round(v*coverage) for v in color)
  for i,(x,y) in enumerate(self.trail):
   c=self.columns[max(0,min(9,round(x)))][max(0,min(4,round(y)))];f[c]=mix(f[c],(255,120,30),(i+1)/len(self.trail)*.45)
  hit_age=now-self.hit_at
  if 0<=hit_age<.28 and not self.reduced_motion:
   radius=hit_age*9
   for c,(cx,cy) in self.grid_coords.items():
    strength=max(0,1-abs(math.dist((cx,cy),self.hit_pos)-radius))*(1-hit_age/.28)*.55
    if strength:f[c]=mix(f[c],(255,175,60),strength)
  x,y=self.ball
  for ix in (math.floor(x),math.ceil(x)):
   for iy in (math.floor(y),math.ceil(y)):
    if 0<=ix<10 and 0<=iy<5:
     weight=(1-abs(ix-x))*(1-abs(iy-y));c=self.columns[ix][iy]
     strength=weight*(.35+.65*(.5+.5*math.sin(now*9))) if self.serve_at else weight
     f[c]=mix(f[c],(255,245,200),strength)
  age=now-self.miss_at
  if 0<=age<.8:
   color=(20,210,255) if self.point_side==1 else (255,35,150)
   for c,(cx,cy) in self.grid_coords.items():
    distance=abs(cx-(9 if self.point_side==1 else 0));strength=max(0,1-abs(distance-age*17)/1.6)
    if strength:f[c]=mix(f[c],color,strength)
  if self.phase=='dying':
   color=(20,210,255) if self.result=='p1_win' else (255,35,150);age=now-self.phase_start
   for c,(cx,cy) in self.grid_coords.items():f[c]=mix((0,0,0),color,max(0,1-age/3)*(.3+.7*math.cos(cx*.7-age*5)**2))
  # Three score LEDs per side, entirely separate from the paddle controls.
  for side,keys,color in ((1,('R Alt','R Fn','R Ctrl'),(20,210,255)),(0,('L Fn','Super','L Alt'),(255,35,150))):
   for i,k in enumerate(keys):f[self.labels[k]]=color if i<self.points[side] else (0,0,0)
  return self.controls(f,now)
