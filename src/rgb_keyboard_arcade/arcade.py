"""Shared game selection, marquee, Escape identity, and saved preferences."""
import math
from .calibration import CalibrationGame
from .arcade_games import Minesweeper,Pong
from .marquee import Marquee
GAMES=(('snake','Snake',(255,105,10)),('mines','Minesweeper',(35,160,255)),('pong','Pong',(235,45,190)))
class Arcade:
 MODES=CalibrationGame.MODES
 def __init__(self,layout,movement_map=None,reduced_motion=False,settings=None):
  settings=settings if isinstance(settings,dict) else {};saved=settings.get('games',{})
  saved=saved if isinstance(saved,dict) else {};self.instances={};self.reduced_motion=reduced_motion
  for key,cls,default in (('snake',CalibrationGame,'rainbow'),('mines',Minesweeper,'sweep'),('pong',Pong,'solo')):
   prefs=saved.get(key,{}) if isinstance(saved.get(key,{}),dict) else {}
   if key=='snake' and not prefs:prefs=settings
   variant=prefs.get('game_mode',default);level=prefs.get('difficulty',0)
   if type(level) is not int or not 0<=level<4:level=0
   allowed={'snake':('rainbow','timer'),'mines':('sweep',),'pong':('solo','duo')}[key]
   if variant not in allowed:variant=default
   self.instances[key]=cls(layout,movement_map=movement_map,reduced_motion=reduced_motion,game_mode=variant,difficulty=level)
  self.game_id=settings.get('game_id','snake')
  if self.game_id not in self.instances:self.game_id='snake'
  self.marquee=None;self.marquee_start=0.;self.now=0.
 def __getattr__(self,key):return getattr(self.instances[self.game_id],key)
 @property
 def current(self):return self.instances[self.game_id]
 def settings(self):return {'game_id':self.game_id,'games':{k:{'game_mode':v.game_mode,'difficulty':v.difficulty} for k,v in self.instances.items()}}
 def showing_title(self):return self.marquee is not None
 def title(self,text,style,now):
  self.marquee=Marquee(self.current,text,style);self.marquee_start=now
  if self.reduced_motion:self.marquee.lead=0.;self.marquee.duration=(14+self.marquee.width)/self.marquee.speed+.25
 def select_game(self,key,now):
  if key not in self.instances:raise ValueError('Unknown game')
  self.current.set_mode('default',now);self.game_id=key;self.current.set_mode('passive',now)
  self.title(dict((k,v.upper()) for k,v,_ in GAMES)[key],key,now)
 def cycle_game(self,now):
  if self.marquee:
   self.marquee=None;self.current.reset(now)
  elif self.mode=='default':
   self.current.set_mode('passive',now);self.title('GAME MODE','startup',now)
  else:
   ids=[k for k,_,_ in GAMES];self.select_game(ids[(ids.index(self.game_id)+1)%len(ids)],now)
 def set_mode(self,mode,now):
  old=self.mode;self.current.set_mode(mode,now)
  if mode=='default':self.marquee=None
  elif old=='default' and mode=='passive':self.title('GAME MODE','startup',now)
 def back(self,now):
  if self.marquee:
   self.marquee=None;self.current.set_mode('default',now)
  else:self.current.back(now)
 def configure(self,now,**kwargs):return False if self.marquee else self.current.configure(now,**kwargs)
 def selector_press(self,cell,now):return True if self.marquee else self.current.selector_press(cell,now)
 def request_active(self,direction,now):
  if not self.marquee:self.current.request_active(direction,now)
 def press(self,cell=None,now=None):
  if not self.marquee:self.current.press(cell,now)
 def key_down(self,cell,now):
  if not self.marquee:self.current.key_down(cell,now)
 def key_up(self,cell,now):
  if not self.marquee:self.current.key_up(cell,now)
 def restart(self,now):
  if not self.marquee:self.current.restart(now)
 def tick(self,now):
  self.now=now
  if self.marquee:
   duration=self.marquee.duration
   if now-self.marquee_start>=duration:
    self.marquee=None;self.current.reset(now)
   return
  self.current.tick(now)
 def frame(self,now):
  if self.marquee:
   return self.marquee.frame(now-self.marquee_start)
  frame=self.current.frame(now)
  if self.mode in ('passive','classic'):
   color=dict((k,c) for k,_,c in GAMES)[self.game_id]
   strength=.3+.7*(.5+.5*math.sin(now*2.5))
   if self.reduced_motion:strength=.7
   frame[self.labels['Esc']]=tuple(round(v*strength) for v in color)
  return frame
 def state(self,now):
  state=self.current.state(now)
  state.update(game_id=self.game_id,game_name=dict((k,n) for k,n,_ in GAMES)[self.game_id],
   games=[{'id':k,'label':n,'color':'#'+''.join(f'{v:02x}' for v in c)} for k,n,c in GAMES],
   marquee=self.marquee.text if self.marquee else '',
   pixels=[[*c,*rgb] for c,rgb in self.frame(now).items()])
  if self.marquee:state.update(phase='marquee',selectors_enabled=False,status_text=self.marquee.text+' · scrolling title')
  return state
