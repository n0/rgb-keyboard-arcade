"""Keyboard-display Snake. No hardware or input side effects in this module."""
import math
import colorsys
import random
from collections import deque
from .autopilot import random_cycle, choose_next, choose_avoiding
from .effects import DeathAnimation, RainbowDeathAnimation, RainbowActivation, ReadyAnimation, EntryAnimation, StageTransition, orange, gradient, timer_gradient
from .stages import palette as stage_palette, name as stage_name, normal_step
from .modes import MODES as GAME_MODES, DIFFICULTIES, TIMER_PALETTE, style_color, temperature, static_routes, tail_route


class Game:
    MODES = ('default', 'passive', 'classic')
    CLASSIC_START_SECONDS = .34
    RAINBOW_STEP_SECONDS = .17
    BOOST_SECONDS = 10.0
    SHIELD_SECONDS = 3.0

    def __init__(self, layout, seed=None, movement_map=None, reduced_motion=False, game_mode='rainbow', difficulty=0):
        self.layout = layout
        if game_mode not in dict(GAME_MODES) or type(difficulty) is not int or not 0<=difficulty<len(DIFFICULTIES):raise ValueError('Invalid game settings')
        self.game_mode=game_mode;self.difficulty=difficulty
        self.timer_food={};self.preview_route=[];self.death_reason=None;self.bombs=set()
        self.observed_step=math.ceil(DIFFICULTIES[difficulty][2]/.025)*.025+.005
        self.reduced_motion = reduced_motion
        self.death = None
        self.ready_animation = None
        self.ready_start = 0.
        self.activation=None;self.finish_after_powerup=False
        self.pending_active=None
        self.touch_death_pending=False
        self.shield_start=None
        self.rng = random.Random(seed)
        self.rainbow_apples=set();self.spawn_count=0;self.boost_start=None
        self.apple_presses={}
        self.stage=0;self.stage_source=stage_palette(0);self.stage_speed_from=normal_step(0)
        self.stage_pending=False;self.stage_animation=None
        self.held_food={}
        self.palette_from=0.;self.palette_to=0.;self.palette_start=0.;self.palette_duration=.45
        self.labels={(p['label']):(p['row'],p['column']) for p in layout['pixels']}
        fallback=list(zip([f'F{i}' for i in range(1,11)],'1234567890',
                          'QWERTYUIOP','ASDFGHJKL;','ZXCVBNM,./'))
        recorded=movement_map['columns'] if movement_map else fallback
        full_columns=[column for column in recorded if len(column)==5][:10]
        if len(full_columns)!=10:raise ValueError('Snake needs ten complete calibrated columns')
        self.columns=[[self.labels[label] for label in column] for column in full_columns]
        self.cells=[cell for column in self.columns for cell in column]
        self.cellset=set(self.cells)
        if len(self.cellset)!=50:raise ValueError('Playable columns must contain 50 distinct keys')
        for column in self.columns:
            if [c[0] for c in column]!=list(range(5)):
                raise ValueError('Playable columns must span each game row once')
        self.positions = {}
        self.all_positions = {}
        self.labels = {}
        for p in layout['pixels']:
            box = p['physical']; cell = (p['row'], p['column'])
            self.all_positions[cell] = (box['x'] + box['width']/2, box['y'] + box['height']/2)
            if cell in self.cellset: self.positions[cell] = self.all_positions[cell]
            self.labels[p['label']] = cell
        self.right_border=[self.labels[label] for label in ('F11','-','[','Enter','R Shift')]
        self.border = [c for c in self.all_positions
                       if (c[0]==0 and c[1]<=self.labels['F11'][1])
                       or c[0]==5 or c[1]==1 or c in self.right_border]
        # Side-only timer leaves the bottom clear for controls and portal play.
        self.timer_cells=[]
        for edge in (['L Shift','Caps','Tab','`','Esc'],
                     ['R Shift','Enter','\\','Backspace','Power']):
            for i,label in enumerate(edge):self.timer_cells.append((self.labels[label],(i+1)/5))
        assert not ({c for c,_ in self.timer_cells} & self.cellset)
        self.control_hints=ReadyAnimation((),self.all_positions,self.labels,reduced_motion)

        # A closed route on the 10×5 board. Reserve the top row for the return
        # trip, then weave down/up the columns. Every edge is a calibrated move.
        self.cycle=[self.columns[0][0]]
        for index,column in enumerate(self.columns):
            self.cycle.extend(column[1:] if index%2==0 else reversed(column[1:]))
        self.cycle.extend(column[0] for column in reversed(self.columns[1:]))
        assert len(self.cycle)==len(self.cellset)==len(set(self.cycle))
        assert set(self.cycle)==self.cellset
        self.cycle_index={c:i for i,c in enumerate(self.cycle)}
        self.moves={}
        for x,column in enumerate(self.columns):
            for y,cell in enumerate(column):
                self.moves[cell]={
                    'up':column[y-1] if y else None,
                    'down':column[y+1] if y<4 else None,
                    'left':self.columns[x-1][y] if x else None,
                    'right':self.columns[x+1][y] if x<9 else None,
                }
        self.base_cycle=list(self.cycle)
        self.grid_coords={cell:(x,y) for x,col in enumerate(self.columns) for y,cell in enumerate(col)}
        self.wrapped_moves={cell:{d:other if other is not None else self.portal_neighbor(cell,d)
                                  for d,other in directions.items()} for cell,directions in self.moves.items()}
        self.movement_source=movement_map.get('source_session') if movement_map else 'layout_default'
        self.mode = 'default'; self.phase = 'idle'; self.body = deque()
        self.apples = set(); self.score = 0; self.rounds = 0
        self.direction = 'right'; self.turns = deque(maxlen=2)
        self.last_step = 0.; self.phase_start = 0.; self.time = 0.
        self.previous_mode = 'default'; self.transition_start = -100.
        self.transition_frame = {}

    def set_mode(self, mode, now):
        if mode not in self.MODES: raise ValueError('Unknown keyboard mode')
        if mode == self.mode: return
        self.transition_frame = self.frame(now)
        self.previous_mode = self.mode; self.transition_start = now
        self.mode = mode; self.score = 0; self.rounds = 0
        self.reset(now)

    def reset(self, now):
        self.death = None
        self.ready_animation = None
        self.activation=None;self.finish_after_powerup=False
        self.pending_active=None
        self.touch_death_pending=False
        self.shield_start=None
        self.rainbow_apples.clear();self.spawn_count=0;self.boost_start=None
        self.apple_presses.clear()
        self.stage=0;self.stage_source=stage_palette(0);self.stage_speed_from=normal_step(0)
        self.stage_pending=False;self.stage_animation=None
        self.held_food.clear()
        self.timer_food.clear();self.preview_route=[];self.death_reason=None
        self.bombs.clear()
        self.stage_source=self.palette_for_stage(0);self.stage_speed_from=self.normal_stage_seconds(0)
        self.observed_step=math.ceil(DIFFICULTIES[self.difficulty][2]/.025)*.025+.005
        self.palette_from=0.;self.palette_to=0.;self.palette_start=now
        self.apples.clear(); self.turns.clear(); self.score = 0
        self.phase = 'idle' if self.mode == 'default' else ('revealing' if self.mode == 'classic' else 'running')
        if self.mode == 'passive':
            self.cycle=random_cycle(self.base_cycle,self.moves,self.rng)
            self.cycle_index={c:i for i,c in enumerate(self.cycle)}
            center=[c for c,(x,y) in self.grid_coords.items() if x in (4,5) and y in (2,3)]
            start=self.cycle_index[self.rng.choice(center)]
            self.body = deque(self.cycle[(start-i) % len(self.cycle)] for i in range(12))
            self.direction=next(d for d,c in self.moves[self.body[1]].items() if c==self.body[0])
        elif self.mode == 'classic':
            self.body = deque([self.labels['U'], self.labels['Y'], self.labels['T']])
            self.direction = 'right'
            self.ready_start=now
            p=self.palette_for_stage(0)
            self.ready_animation=ReadyAnimation(self.body,self.all_positions,self.labels,self.reduced_motion,colors=(p['head'],p['tail']))
            self.ready_animation.duration=.15 if self.reduced_motion else .85
        else: self.body.clear()
        self.phase_start = now; self.last_step = now
        if self.mode=='passive' and self.game_mode=='timer':self.spawn(now=now)

    def is_rainbow_preview(self):return self.mode=='passive' and self.game_mode=='rainbow'

    def palette_for_stage(self,stage):return TIMER_PALETTE if self.game_mode=='timer' else stage_palette(stage)

    def normal_stage_seconds(self,stage):
        preset=DIFFICULTIES[self.difficulty]
        return preset[2] if self.game_mode=='timer' else max(preset[4],preset[2]-.025*stage)

    def configure(self,now,game_mode=None,difficulty=None):
        if self.mode!='passive' or self.phase!='running':return False
        game_mode=self.game_mode if game_mode is None else game_mode
        difficulty=self.difficulty if difficulty is None else difficulty
        if game_mode not in dict(GAME_MODES) or type(difficulty) is not int or not 0<=difficulty<len(DIFFICULTIES):raise ValueError('Invalid game settings')
        if game_mode==self.game_mode and difficulty==self.difficulty:return False
        changed=game_mode!=self.game_mode;self.game_mode=game_mode;self.difficulty=difficulty
        if changed:self.reset(now)
        else:
            self.last_step=now;self.observed_step=math.ceil(DIFFICULTIES[difficulty][2]/.025)*.025+.005
            if self.game_mode=='timer':
                self.apples.clear();self.timer_food.clear();self.preview_route=[];self.spawn(now=now)
        return True

    def selector_press(self,cell,now):
        if cell not in (self.labels['`'],self.labels['Tab']):return False
        if self.mode=='passive' and self.phase=='running':
            if cell==self.labels['`']:
                ids=[m[0] for m in GAME_MODES];self.configure(now,game_mode=ids[(ids.index(self.game_mode)+1)%len(ids)])
            else:self.configure(now,difficulty=(self.difficulty+1)%len(DIFFICULTIES))
        return True

    def restart(self, now):
        if self.mode=='classic' and self.phase=='dying' and not isinstance(self.death,EntryAnimation):
            self.request_active(self.direction,now);return
        # Both arrows and toolbar requests must respect the full sequence.
        if self.mode!='default' and self.phase not in ('dying','revealing','starting','powering','handoff','staging'):
            self.reset(now)

    def request_active(self, direction, now):
        if direction not in ('left','right','up','down'):return
        if self.mode in ('passive','classic') and self.phase=='dying':
            # Queue intent without replacing or shortening the current effect.
            if not self.pending_active:self.pending_active=direction
            return
        if self.mode!='passive' or self.phase!='running':return
        target=[self.labels[k] for k in ('U','Y','T')]
        if direction=='left':target.reverse()
        p=self.palette_for_stage(0)
        self.death=EntryAnimation(self.body,target,self.all_positions,self.positions,
                                  self.rng.getrandbits(64),self.reduced_motion,style=self.game_mode,
                                  colors=(p['head'],p['tail']),background=p['background'],clock=now)
        self.pending_active=direction;self.phase='dying';self.phase_start=now;self.turns.clear()

    def begin_active(self, now):
        if self.phase!='handoff' or not self.pending_active:return
        direction=self.pending_active
        body=self.ready_animation.body if self.ready_animation else self.death.target_body
        if self.mode=='classic':
            self.reset(now);self.transition_frame={};self.transition_start=-100.
        else:self.set_mode('classic',now)
        self.body=deque(body);self.direction=direction;self.ready_animation=None
        self.phase='running';self.phase_start=now;self.last_step=now;self.shield_start=now
        self.spawn(now=now);self.spawn_bomb(now)

    def back(self, now):
        if self.mode=='classic':self.set_mode('passive',now)
        elif self.mode=='passive' and self.pending_active:self.reset(now)
        else:self.set_mode('default',now)

    def spawn(self, preferred=None,now=None):
        if self.stage_pending or self.is_rainbow_preview():return False
        now=self.time if now is None else now
        available = self.cellset - set(self.body) - self.apples - self.bombs
        if not available: return False
        routes={}
        if self.game_mode=='timer':
            if self.mode=='passive':
                # Preview follows the same cyclic safety invariant as roaming;
                # a locally short food route can otherwise trap the next move.
                target=self.rng.choice(sorted(available));trail=deque(self.body);route=[]
                neighbors=lambda cell:list(self.wrapped_moves[cell].values())
                for _ in range(len(self.cells)*2):
                    nxt=choose_next(trail,{target},self.cycle,self.cycle_index,neighbors,self.rng)
                    route.append(nxt);trail.appendleft(nxt);trail.pop()
                    if nxt==target:
                        routes={target:tuple(route)};break
            else:
                routes=static_routes(tuple(self.body),self.direction,self.wrapped_moves,available,self.apples)
                if not routes:routes=tail_route(tuple(self.body),self.direction,self.wrapped_moves,available,self.apples)
            available=set(routes)
            if not available:return False
        if preferred in available: cell = preferred
        elif preferred in self.all_positions:
            x,y = self.all_positions[preferred]
            cell = min(available, key=lambda c: ((self.positions[c][0]-x)**2 + (self.positions[c][1]-y)**2, c))
        else: cell = self.rng.choice(sorted(available))
        self.apples.add(cell)
        self.apple_presses[cell]=0
        self.spawn_count+=1
        if self.game_mode=='timer':
            route=routes[cell];step=max(DIFFICULTIES[self.difficulty][2],self.observed_step)
            first=max(0.,step-(now-self.last_step));travel=first+max(0,len(route)-1)*step
            slack=max(0.,1-self.score/(len(self.cells)-5))**1.7
            duration=travel*(1+.9*slack)+step*1.8*slack+max(.055,step*.20)
            self.timer_food[cell]={'start':now,'deadline':now+duration,'duration':duration,'steps':len(route)}
            if self.mode=='passive':self.preview_route=list(route)
        return True

    def spawn_bomb(self,now):
        if self.mode!='classic' or self.game_mode!='rainbow' or self.phase!='running' or not self.boost_seconds(now):return
        target=min(3,1+self.score//5)
        if len(self.bombs)>=target:return
        free=self.cellset-set(self.body)-self.apples-self.bombs
        # Preserve room for food; never place a new bomb on an immediate neighbor.
        available=free-{self.neighbor(self.body[0],d,now) for d in ('up','right','down','left')}
        if len(free)<=1 or not available:return
        self.bombs.add(self.rng.choice(sorted(available)))

    def food_rainbows(self):
        if self.game_mode=='timer':return set()
        # Mark whichever food is eaten fifth, regardless of manually added food.
        return self.apples if self.mode=='classic' and (self.score+1)%5==0 else self.rainbow_apples

    def press(self, cell=None, now=None):
        if self.mode not in ('passive','classic') or self.phase not in ('running','powering','staging'): return
        now=self.time if now is None else now
        if self.selector_press(cell,now):return
        if cell in self.body:
            if self.phase in ('powering','staging'):self.touch_death_pending=True
            else:self.start_death(now)
            return
        if self.phase=='running' and self.game_mode=='rainbow' and (self.is_rainbow_preview() or self.boost_seconds(now)>0):
            if cell in self.cellset and cell not in self.apples:self.bombs.add(cell)
            return
        if self.stage_pending or self.mode=='passive':return
        if cell in self.bombs:return
        if cell in self.apples:
            # Five fresh presses on this existing apple upgrade it in place.
            # Further presses on a rainbow apple never spill into nearby cells.
            if self.game_mode=='rainbow' and cell not in self.food_rainbows():
                self.apple_presses[cell]=min(5,self.apple_presses.get(cell,0)+1)
                if self.apple_presses[cell]==5:self.rainbow_apples.add(cell)
            return
        self.spawn(cell,now=now)

    def steer(self, direction, now):
        if self.mode != 'classic' or direction not in ('left','right','up','down'): return
        if self.phase=='dying':self.request_active(direction,now);return
        if self.phase not in ('ready','running','powering','staging'): return
        if self.phase == 'ready': self.phase = 'starting'; self.phase_start = now
        previous = self.turns[-1] if self.turns else self.direction
        opposite = {'left':'right','right':'left','up':'down','down':'up'}
        if direction != opposite[previous] and direction != previous and len(self.turns)<2:
            self.turns.append(direction)

    def boost_seconds(self, now):
        if self.phase=='powering':return self.BOOST_SECONDS
        if self.boost_start is None or self.phase!='running':return 0.
        return max(0.,self.BOOST_SECONDS-(now-self.boost_start))

    def palette_mix(self, now):
        if self.phase=='staging':return 0.
        if self.boost_start is not None and self.phase!='powering':
            return 1. if self.stage_pending else 0.
        t=max(0,min(1,(now-self.palette_start)/self.palette_duration))
        eased=t*t*(3-2*t)
        return self.palette_from+(self.palette_to-self.palette_from)*eased

    def activate_rainbow(self, now):
        if self.stage_pending or self.game_mode!='rainbow' or self.is_rainbow_preview():return
        previous_border=self.timer_frame(now)
        previous_mix=self.palette_mix(now)
        # Food is suspended until the complete shutter transition commits the
        # next palette, so every earned stage gets a visible handoff.
        self.stage_source=self.current_palette(now)
        self.stage_speed_from=self.normal_seconds(now)
        self.stage+=1
        self.stage_pending=True
        self.held_food={cell:(cell in self.rainbow_apples,self.apple_presses.get(cell,0)) for cell in self.apples}
        self.apples.clear();self.rainbow_apples.clear();self.apple_presses.clear()
        upcoming=stage_palette(self.stage)
        self.activation=RainbowActivation(self.all_positions[self.body[0]],self.all_positions,
                                           self.timer_cells,previous_border,self.reduced_motion,
                                           (upcoming['head'],upcoming['tail']))
        self.palette_from=previous_mix;self.palette_to=1.
        self.palette_start=now;self.palette_duration=self.activation.duration*.8
        self.boost_start=now+self.activation.duration
        self.phase='powering';self.phase_start=now

    def timer_frame(self, now):
        frame={c:(0,0,0) for c,_ in self.timer_cells}
        if not self.boost_seconds(now):return frame
        age=max(0.,now-self.boost_start)
        for cell,end_fraction in self.timer_cells:
            until_black=end_fraction*self.BOOST_SECONDS-age
            strength=max(0.,min(1.,until_black/.15))
            upcoming=stage_palette(self.stage)
            color=timer_gradient(end_fraction,(upcoming['head'],upcoming['tail']))
            frame[cell]=tuple(round(v*.8*strength) for v in color)
        return frame

    def current_palette(self,now):
        return self.stage_source if self.stage_pending else self.palette_for_stage(self.stage)

    def normal_seconds(self,now):
        return self.stage_speed_from if self.stage_pending else self.normal_stage_seconds(self.stage)

    def step_seconds(self, now):
        if self.is_rainbow_preview():return DIFFICULTIES[self.difficulty][3]
        if self.game_mode=='timer':return DIFFICULTIES[self.difficulty][2]
        normal=self.normal_seconds(now)
        # Both control modes share the same pace. Keep rainbow a modest boost
        # even when score-based movement is already faster than its base target.
        boosted=min(DIFFICULTIES[self.difficulty][3],normal*.9)
        return normal+(boosted-normal)*self.palette_mix(now)

    def shield_seconds(self,now):
        if self.mode!='classic' or self.shield_start is None:return 0.
        return max(0.,self.SHIELD_SECONDS-(now-self.shield_start))

    def rainbow_head_hue(self,now,background):
        # Bounce smoothly through the opposite half of the hue wheel. A full
        # cycle through all hues would inevitably blend into the background.
        hue=colorsys.rgb_to_hsv(*background)[0]
        travel=.5-.5*math.cos(now*.08*math.tau)
        return (hue+.28+travel*.44)%1

    def restore_food(self):
        free=self.cellset-set(self.body)-self.bombs
        for cell,(rainbow,presses) in self.held_food.items():
            if not free:break
            if cell not in free:
                cell=min(free,key=lambda c:math.dist(self.positions[c],self.positions[cell]))
            free.remove(cell);self.apples.add(cell);self.apple_presses[cell]=presses
            if rainbow:self.rainbow_apples.add(cell)
        self.held_food.clear()
        if self.mode=='classic':self.spawn()

    def portal_neighbor(self,cell,direction):
        x,y=self.grid_coords[cell]
        # Shift one lane at each crossing. Opposite portals are exact inverses;
        # a straight run visits all 50 cells before returning to its own trail.
        x,y={'up':((x+1)%10,4),'down':((x-1)%10,0),
             'left':(9,(y+1)%5),'right':(0,(y-1)%5)}[direction]
        return self.columns[x][y]

    def neighbor(self,cell,direction,now):
        if self.game_mode=='timer' or self.shield_seconds(now):return self.wrapped_moves[cell][direction]
        return self.moves[cell][direction]

    def tick(self, now):
        self.time = now
        if self.mode == 'default': return
        if self.phase=='staging':
            if now-self.phase_start>=self.stage_animation.duration:
                self.stage_source=self.palette_for_stage(self.stage);self.stage_speed_from=self.normal_stage_seconds(self.stage)
                self.stage_pending=False;self.stage_animation=None;self.boost_start=None
                self.palette_from=self.palette_to=0.
                self.restore_food()
                self.phase='running';self.phase_start=now;self.last_step=now
                if self.touch_death_pending:self.start_death(now)
            return
        if self.phase == 'dying':
            if now-self.phase_start >= self.death.duration:
                if self.pending_active:
                    if isinstance(self.death,EntryAnimation):self.phase='handoff'
                    else:
                        target=[self.labels[k] for k in ('U','Y','T')]
                        if self.pending_active=='left':target.reverse()
                        p=self.palette_for_stage(0)
                        self.ready_animation=ReadyAnimation(target,self.all_positions,self.labels,self.reduced_motion,colors=(p['head'],p['tail']))
                        self.ready_animation.duration=.15 if self.reduced_motion else .85
                        self.ready_start=now;self.phase='revealing';self.phase_start=now
                elif self.mode=='passive':
                    rounds=self.rounds+1;self.reset(now);self.rounds=rounds
                    self.transition_frame={};self.transition_start=now
                else:self.set_mode('passive',now)
            return
        if self.phase=='revealing':
            if now-self.ready_start>=self.ready_animation.duration:
                if self.pending_active:self.phase='handoff'
                else:self.phase='running';self.last_step=now;self.shield_start=now;self.spawn();self.spawn_bomb(now)
            return
        if self.phase=='starting':
            if now-self.phase_start>=.25:
                self.phase='running';self.last_step=now;self.shield_start=now;self.spawn();self.spawn_bomb(now)
            return
        if self.phase=='powering':
            if now-self.phase_start>=self.activation.duration:
                self.phase='running';self.last_step=now;self.boost_start=now
                self.activation=None
                for _ in range(3):self.spawn_bomb(now)
                if self.touch_death_pending or (self.finish_after_powerup and (self.mode=='classic' or not self.apples)):
                    self.start_death(now)
            return
        if self.phase != 'running': return
        if self.game_mode=='timer' and any(now>f['deadline'] for f in self.timer_food.values()):
            self.start_death(now,reason='timeout');return
        if self.stage_pending and self.boost_start is not None and now>=self.boost_start+self.BOOST_SECONDS:
            self.bombs.clear()
            initial=self.frame(now)
            self.stage_animation=StageTransition(self.body,self.columns,self.all_positions,
                self.stage_source,stage_palette(self.stage),initial,self.mode=='passive',self.reduced_motion)
            self.phase='staging';self.phase_start=now
            return
        if now-self.last_step+1e-9 < self.step_seconds(now): return
        interval=now-self.last_step
        if self.game_mode=='timer' and interval<self.step_seconds(now)*2:
            self.observed_step=self.observed_step*.8+interval*.2
        self.last_step = now
        if self.mode == 'passive':
            if self.game_mode=='timer' and self.preview_route:
                head=self.preview_route.pop(0)
                self.direction=next(d for d,c in self.wrapped_moves[self.body[0]].items() if c==head)
            else:
                neighbors=lambda cell:[self.neighbor(cell,d,now) for d in ('up','right','down','left')]
                head=(choose_avoiding(self.body,self.bombs,neighbors,self.rng) if self.bombs else
                      choose_next(self.body,self.apples,self.cycle,self.cycle_index,neighbors,self.rng))
        else:
            if self.turns:self.direction=self.turns.popleft()
            head=self.neighbor(self.body[0],self.direction,now)
        eating = head in self.apples
        rainbow_eaten=eating and head in self.food_rainbows()
        growing = eating and self.mode=='classic' and len(self.body)<len(self.cells)
        occupied = set(list(self.body) if growing else list(self.body)[:-1])
        if head is None:
            self.start_death(now,wall_direction=self.direction if self.mode=='classic' else None);return
        if head in self.bombs:
            self.body.appendleft(head);self.body.pop()
            self.start_death(now,reason='bomb');return
        if head in occupied and not self.shield_seconds(now):
            self.start_death(now); return
        self.body.appendleft(head)
        if not growing: self.body.pop()
        if eating:
            self.apples.remove(head); self.score += 1
            self.apple_presses.pop(head,None)
            self.timer_food.pop(head,None)
            self.rainbow_apples.discard(head)
            if rainbow_eaten:self.activate_rainbow(now)
            if self.mode=='classic':
                if len(self.body)+len(self.bombs)==len(self.cells):
                    if self.phase=='powering':self.finish_after_powerup=True
                    else:self.start_death(now)
                elif not self.stage_pending:
                    if not self.spawn(now=now) and not self.apples:self.start_death(now,reason='blocked')
            elif self.game_mode=='timer':
                if not self.spawn(now=now):self.start_death(now,reason='blocked')
            if self.mode=='classic' and self.phase in ('running','powering'):self.spawn_bomb(now)

    def start_death(self, now, wall_direction=None, reason='collision'):
        start_colors=self.frame(now)
        animation=RainbowDeathAnimation if self.boost_seconds(now)>0 or self.is_rainbow_preview() else DeathAnimation
        self.death_reason=reason
        self.phase='dying';self.phase_start=now;self.turns.clear()
        self.ready_animation=None
        self.death=animation(tuple(dict.fromkeys(self.body)),self.all_positions,self.border,
                                  self.rng.getrandbits(64),self.reduced_motion,start_colors,
                                  wall_direction=wall_direction)

    def frame(self,now):
        frame=self._frame(now)
        if self.mode in ('passive','classic'):
            preview=self.mode=='passive' and self.phase=='running'
            frame[self.labels['Tab']]=DIFFICULTIES[self.difficulty][1] if preview else (0,0,0)
            if preview:frame[self.labels['`']]=style_color(self.game_mode,0. if self.reduced_motion else now)
            if self.phase=='running' and (self.is_rainbow_preview() or self.boost_seconds(now)>0):
                flash=(255,0,0) if self.reduced_motion or int(now*10)%2==0 else (255,255,255)
                frame.update({cell:flash for cell in self.bombs})
        return frame

    def _frame(self, now):
        if self.mode=='default': return {}
        if self.phase=='staging':
            frame=self.stage_animation.frame(now-self.phase_start,self.apples,self.rainbow_apples)
            frame.update({self.labels['Esc']:self.control_hints.control_frame(now-self.phase_start)[self.labels['Esc']]})
            return frame
        if self.phase=='dying':return self.death.frame(now-self.phase_start)
        if self.phase=='handoff':
            if self.ready_animation:return self.ready_animation.frame(self.ready_animation.duration,0.)
            return self.death.frame(self.death.duration)
        if self.phase in ('revealing','ready','starting'):
            strength=0. if self.mode=='classic' else 1.
            if self.phase=='starting':
                t=max(0,min(1,(now-self.phase_start)/.25));strength=1-t*t*(3-2*t)
            return self.ready_animation.frame(now-self.ready_start,strength)
        palette=self.current_palette(now)
        background=palette['passive_background' if self.mode=='passive' else 'background']
        apple=palette['passive_apple' if self.mode=='passive' else 'apple']
        frame = {c:background for c in self.cells}
        pulse = .8 + .2*math.sin(now*4)
        rainbow_food=self.food_rainbows()
        for cell in self.apples:
            if self.game_mode=='timer':
                food=self.timer_food.get(cell)
                progress=max(0,min(1,(now-food['start'])/food['duration'])) if food else 0.
                frame[cell]=tuple(round(v*(1-progress)**.6) for v in temperature(progress))
            elif cell in rainbow_food:
                frame[cell]=tuple(round(c*255) for c in colorsys.hsv_to_rgb(self.rainbow_head_hue(now*8,background),.95,1))
            else:frame[cell]=tuple(round(v*pulse) for v in apple)
        rainbow_mix=1. if self.is_rainbow_preview() else self.palette_mix(now)
        shield=self.shield_seconds(now)
        opacity=.04+.96*(.5+.5*math.cos((now-self.shield_start)*math.tau)) if shield and not self.reduced_motion else 1.
        # Head wins when protected segments overlap during spawn invulnerability.
        for i,cell in reversed(list(enumerate(self.body))):
            color = gradient(i,len(self.body),(palette['head'],palette['tail']))
            if rainbow_mix:
                hue=(self.rainbow_head_hue(now,background)+i/max(1,len(self.body)-1)*.85)%1
                rainbow=tuple(round(c*255) for c in colorsys.hsv_to_rgb(hue,.92,1))
                color=tuple(round(a+(b-a)*rainbow_mix) for a,b in zip(color,rainbow))
            strength=max(.7,opacity) if i==0 and rainbow_mix else opacity
            frame[cell]=tuple(round(a+(b-a)*strength) for a,b in zip(background,color))
        if self.phase=='powering':
            self.activation.overlay(frame,now-self.phase_start,self.body)
        else:frame.update(self.timer_frame(now))
        if self.phase=='running':
            hints=self.control_hints.control_frame(now-self.phase_start)
            if self.mode=='passive':
                for cell,color in hints.items():
                    if cell in (self.labels[k] for k in ('Up','Right','Down','Left')):
                        strength=max(color)/255;color=tuple(round(v*strength) for v in style_color(self.game_mode,now,phase=cell[1]*.11))
                    if cell!=self.labels['Esc'] or not self.boost_seconds(now):frame[cell]=color
            elif self.mode=='classic' and not self.boost_seconds(now):
                frame[self.labels['Esc']]=hints[self.labels['Esc']]
        if now-self.transition_start < .35:
            t=max(0,(now-self.transition_start)/.35)
            frame={c:tuple(int(self.transition_frame.get(c,(0,0,0))[i]*(1-t)+rgb[i]*t) for i in range(3)) for c,rgb in frame.items()}
        return frame

    def state(self, now):
        remaining=min((max(0.,f['deadline']-now) for f in self.timer_food.values()),default=0.)
        return {
            'mode':self.mode,'phase':self.phase,'game_mode':self.game_mode,'game_mode_name':dict(GAME_MODES)[self.game_mode],
            'difficulty':self.difficulty,'difficulty_name':DIFFICULTIES[self.difficulty][0],
            'game_modes':[{'id':key,'label':label} for key,label in GAME_MODES],
            'difficulties':[{'id':i,'label':d[0],'color':'#'+''.join(f'{v:02x}' for v in d[1])} for i,d in enumerate(DIFFICULTIES)],
            'selectors_enabled':self.mode=='passive' and self.phase=='running',
            'stage':self.stage+1,'stage_name':'Timer' if self.game_mode=='timer' else stage_name(self.stage),
            'rainbows_eaten':self.stage,'food_paused':self.stage_pending or self.is_rainbow_preview(),
            'stage_seconds':math.ceil(max(0,self.stage_animation.duration-(now-self.phase_start))*10)/10 if self.phase=='staging' else 0.,
            'apple_seconds':math.ceil(remaining*10)/10,'pending_active':self.pending_active,
            'portals':self.phase=='running' and bool(self.game_mode=='timer' or self.shield_seconds(now)),
            'shield_seconds':math.ceil(self.shield_seconds(now)*10)/10,
            'death_stage':self.death.stage(now-self.phase_start) if self.phase=='dying' else None,'death_reason':self.death_reason,
            'score':self.score,'length':len(self.body),'apples':len(self.apples),'bombs':len(self.bombs),'rounds':self.rounds,
            'boost_seconds':math.ceil(self.boost_seconds(now)*10)/10,'step_seconds':round(self.step_seconds(now),4),
            'playfield':self.cells,'movement_source':self.movement_source,'pixels':[[*c,*rgb] for c,rgb in self.frame(now).items()],
        }
