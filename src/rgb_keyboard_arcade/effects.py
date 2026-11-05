"""Bounded, time-based pixel effects for the keyboard's 20 Hz renderer."""
import math
import random
import colorsys
from .modes import style_color


def orange(index, length):
    return gradient(index,length,((255,88,0),(255,145,18)))


def gradient(index,length,colors):
    t=index/max(1,length-1)
    return tuple(round(a+(b-a)*t) for a,b in zip(*colors))


def timer_gradient(end_fraction,colors):
    # Five countdown rows sample both gradient endpoints, not just its last 80%.
    return gradient((end_fraction-.2)/.8,2,colors)


class RainbowActivation:
    """An orange wave that deposits the persistent countdown border behind it."""
    def __init__(self, origin, positions, timer_cells, previous_border, reduced_motion=False, snake_colors=None):
        self.positions=positions;self.timer_cells=timer_cells
        self.snake_colors=snake_colors or ((255,88,0),(255,145,18))
        self.previous_border=previous_border;self.reduced_motion=reduced_motion
        self.duration=.15 if reduced_motion else 1.
        self.distances={c:math.dist(p,origin) for c,p in positions.items()}
        self.radius=max(self.distances.values()) or 1.
        self.travel=.78

    def overlay(self, frame, age, body):
        for cell,end_fraction in self.timer_cells:
            arrival=self.distances[cell]/self.radius*self.travel
            t=age/.15 if self.reduced_motion else (age-arrival)/.12
            t=max(0,min(1,t));t=t*t*(3-2*t)
            target=tuple(round(v*.8) for v in timer_gradient(end_fraction,self.snake_colors))
            old=self.previous_border.get(cell,(0,0,0))
            frame[cell]=tuple(round(a+(b-a)*t) for a,b in zip(old,target))
        if self.reduced_motion:return frame
        radius=self.radius*max(0,age)/self.travel
        fade=max(0,min(1,(self.duration-age)/.18))
        body=set(body)
        for cell,distance in self.distances.items():
            if cell in body:continue
            strength=max(0,1-abs(distance-radius)/.85)*fade
            if strength:
                color=gradient(distance/self.radius,2,self.snake_colors)
                DeathAnimation.add(frame,cell,tuple(round(v*strength*.8) for v in color))
        return frame


class StageTransition:
    """Hard-edged top/bottom column shutters, with an earlier snake conversion."""
    def __init__(self,body,columns,positions,source,target,initial_frame,passive=False,reduced_motion=False):
        self.body=tuple(body);self.columns=columns;self.positions=positions
        self.source=source;self.target=target;self.initial=initial_frame
        self.passive=passive;self.reduced_motion=reduced_motion
        self.duration=.15 if reduced_motion else 1.8
        self.snake_duration=0. if reduced_motion else .8
        # Alternating column leads produce stepped book-like shutters, rather
        # than a flat horizontal wipe. Every arrival lands on the 20 Hz grid.
        delays=(0.,.25,.10,.35,.20,.40,.15,.30,.05,.25)
        self.arrivals={}
        for x,column in enumerate(columns):
            for y,cell in enumerate(column):
                depth=min(y,4-y)
                self.arrivals[cell]=(0.,.65,1.30)[depth]+delays[x]

    def frame(self,age,apples,rainbow_apples):
        frame={cell:(0,0,0) for cell in self.positions}
        background='passive_background' if self.passive else 'background'
        apple='passive_apple' if self.passive else 'apple'
        for cell,arrival in self.arrivals.items():
            changed=self.reduced_motion or age>=arrival
            frame[cell]=(self.target if changed else self.source)[background]
            if not self.reduced_motion and arrival<=age<arrival+.1:
                # A bright moving lip and a trailing midtone make each shutter
                # readable even though the settled board background stays dim.
                edge=tuple(round(v*.60) for v in self.target['head'])
                frame[cell]=tuple(max(a,b) for a,b in zip(frame[cell],edge))
            elif not self.reduced_motion and arrival+.1<=age<min(arrival+.25,self.duration):
                edge=tuple(round(v*.28) for v in self.target['head'])
                frame[cell]=tuple(max(a,b) for a,b in zip(frame[cell],edge))
            if cell in apples:
                if cell in rainbow_apples:
                    frame[cell]=tuple(round(v*255) for v in colorsys.hsv_to_rgb((age*.65)%1,.95,1))
                else:frame[cell]=(self.target if changed else self.source)[apple]
        for i,cell in reversed(list(enumerate(self.body))):
            arrival=0. if self.reduced_motion else .08+(self.snake_duration-.08)*i/max(1,len(self.body)-1)
            if age>=arrival:
                frame[cell]=gradient(i,len(self.body),(self.target['head'],self.target['tail']))
            elif age>=arrival-.08:frame[cell]=(230,245,255)
            else:frame[cell]=self.initial[cell]
        return frame


class ReadyAnimation:
    """Reveal the actual next body, then keep control hints alive until start."""
    def __init__(self, body, positions, labels, reduced_motion=False, colors=None):
        self.body=tuple(body);self.positions=positions
        self.colors=colors or ((255,88,0),(255,145,18))
        self.arrows=[labels[name] for name in ('Up','Right','Down','Left')]
        self.escape=labels['Esc'];self.reduced_motion=reduced_motion
        self.duration=.15 if reduced_motion else 1.6

    def frame(self, age, cue_strength=1.):
        frame={c:(0,0,0) for c in self.positions}
        for i,cell in enumerate(self.body):
            # Tail first, ending on the deep-orange head: this exact body starts playing.
            delay=0 if self.reduced_motion else (len(self.body)-1-i)*.23
            t=min(1,max(0,(age-delay)/(.15 if self.reduced_motion else .32)))
            t=t*t*(3-2*t)
            frame[cell]=tuple(round(v*t) for v in gradient(i,len(self.body),self.colors))
        frame.update(self.control_frame(age,cue_strength))
        return frame

    def control_frame(self, age, cue_strength=1.):
        frame={}
        fade=min(1,max(0,age/(.15 if self.reduced_motion else .4)))
        frame.update({cell:tuple(round(v*fade*cue_strength) for v in rgb)
                      for cell,rgb in control_orbit(self.arrows,age,self.reduced_motion).items()})
        breath=.45 if self.reduced_motion else .18+.65*(.5-.5*math.cos(age*math.tau/2.4))
        white=round(255*breath*fade*cue_strength)
        frame[self.escape]=(white,white,white)
        return frame


def control_orbit(cells,age,reduced_motion=False):
    """Clockwise rainbow cue shared by every game's actual control groups."""
    frame={};size=len(cells)
    for i,cell in enumerate(cells):
        distance=(age/.4-i+size/2)%size-size/2
        strength=.3 if reduced_motion else .06+.94*math.exp(-distance*distance/.40)
        hue=i/max(1,size) if reduced_motion else (age/4-i*.12)%1
        frame[cell]=tuple(round(v*255*strength) for v in colorsys.hsv_to_rgb(hue,.9,1))
    return frame


class DeathAnimation:
    def __init__(self, body, positions, border, seed, reduced_motion=False, start_colors=None, wall_direction=None):
        self.start_colors=start_colors or {}
        self.body=tuple(body);self.positions=positions;self.border=tuple(border)
        self.reduced_motion=reduced_motion
        self.wave=max(.55,min(1.35,.045*max(1,len(body)-1)))
        self.charge=.18;self.burst=1.35;self.blackout=.55
        self.duration=.9 if reduced_motion else self.wave+self.charge+self.burst+self.blackout
        self.head=positions[body[0]];self.bodyset=set(body)
        self.wall_distances={};self.wall_span=0.
        if wall_direction:
            # Follow the actual stepped wall, including the spacebar gap,
            # rather than pretending the narrower right wall is rectangular.
            center=(sum(positions[c][0] for c in self.border)/len(self.border),
                    sum(positions[c][1] for c in self.border)/len(self.border))
            ring=sorted(self.border,key=lambda c:math.atan2(positions[c][1]-center[1],positions[c][0]-center[0]))
            arcs={};segments=[];perimeter=0.
            for a,b in zip(ring,ring[1:]+ring[:1]):
                p=positions[a];q=positions[b];length=math.dist(p,q)
                arcs[a]=perimeter;segments.append((p,q,length,perimeter));perimeter+=length
            ray={'up':(0,-1),'right':(1,0),'down':(0,1),'left':(-1,0)}[wall_direction]
            cross=lambda a,b:a[0]*b[1]-a[1]*b[0]
            hits=[]
            for p,q,length,offset in segments:
                edge=(q[0]-p[0],q[1]-p[1]);delta=(p[0]-self.head[0],p[1]-self.head[1])
                divisor=cross(ray,edge)
                if abs(divisor)<1e-9:continue
                distance=cross(delta,edge)/divisor;along=cross(delta,ray)/divisor
                if distance>=-1e-9 and -1e-9<=along<=1+1e-9:
                    hits.append((max(0,distance),offset+max(0,min(1,along))*length))
            if hits:
                impact=min(hits)[1];self.wall_span=perimeter/6
                for cell,s in arcs.items():
                    delta=abs(s-impact)%perimeter;distance=min(delta,perimeter-delta)
                    if distance<=self.wall_span:self.wall_distances[cell]=distance
        rng=random.Random(seed)
        center=(sum(positions[c][0] for c in body)/len(body),sum(positions[c][1] for c in body)/len(body))
        self.particles=[]
        for index,cell in enumerate(body):
            x,y=positions[cell]
            for _ in range(4):
                angle=math.atan2(y-center[1],x-center[0])+rng.uniform(-1.1,1.1)
                speed=rng.uniform(9.,16.)
                self.particles.append((x,y,math.cos(angle)*speed,math.sin(angle)*speed,
                                       rng.uniform(1.,1.4),rng.random()))
        for i in range(16):
            angle=i*math.tau/16;speed=rng.uniform(14.,22.)
            self.particles.append((*self.head,math.cos(angle)*speed,math.sin(angle)*speed,1.2,rng.random()))

    def stage(self, age):
        if self.reduced_motion:return 'wave' if age<.35 else 'blackout'
        if age<self.wave:return 'wave'
        if age<self.wave+self.charge:return 'charge'
        if age<self.wave+self.charge+self.burst:return 'burst'
        return 'blackout'

    def wall_overlay(self,frame,age):
        if not self.wall_distances:return frame
        if self.reduced_motion:
            radius=self.wall_span;fade=max(0,1-age/.35)
        else:
            t=max(0,min(1,age/.28));radius=self.wall_span*(1-(1-t)**3)
            fade=max(0,min(1,1-(age-self.wave-self.charge)/.45))
        for cell,distance in self.wall_distances.items():
            front=max(0,min(1,(radius-distance+.35)/.35))
            strength=front*fade*(1-.6*(distance/self.wall_span)**1.4)
            if strength:self.add(frame,cell,(round(255*strength),round(8*strength),0))
        return frame

    def frame(self, age):
        frame={c:(0,0,0) for c in self.positions}
        if self.reduced_motion:
            strength=max(0,1-age/.35)
            for c in self.bodyset:frame[c]=(round(170*strength),0,0)
            return self.wall_overlay(frame,age)
        stage=self.stage(age)
        if stage=='blackout':return frame
        if stage in ('wave','charge'):
            for i,cell in enumerate(self.body):
                delay=(self.wave-.12)*i/max(1,len(self.body)-1)
                t=1 if i==0 else max(0,min(1,(age-delay)/.12))
                frame[cell]=tuple(round(a+(b-a)*t) for a,b in zip(self.start_colors.get(cell,orange(i,len(self.body))),(255,0,0)))
            return self.wall_overlay(frame,age)
        t=age-self.wave-self.charge
        # A thin shockwave travels away from the head, then vanishes.
        for c,(x,y) in self.positions.items():
            d=math.dist((x,y),self.head)
            wave=max(0,1-abs(d-t*10)/.7)*max(0,1-t/.75)
            if wave:self.add(frame,c,(round(130*wave),round(16*wave),0))
        for x,y,vx,vy,life,flicker in self.particles:
            if t>=life:continue
            px=x+vx*t;py=y+vy*t+1.5*t*t
            strength=(1-t/life)**1.5
            # Two discrete ember levels add a retro sparkle, never a full-board strobe.
            strength*=1 if (int(t*12+flicker*8)%4) else .45
            hot=max(0,1-t/.35)
            color=(round(255*strength),round((25+150*hot)*strength),round(45*hot*strength))
            self.splat(frame,px,py,color)
            self.splat(frame,px-vx*.055,py-vy*.055,tuple(round(v*.24) for v in color))
        return self.wall_overlay(frame,age)

    @staticmethod
    def add(frame,cell,color):
        frame[cell]=tuple(min(255,a+b) for a,b in zip(frame.get(cell,(0,0,0)),color))

    def splat(self,frame,x,y,color):
        if not (-.5<=x<=15.5 and -.5<=y<=6.5):return
        cell=min(self.positions,key=lambda c:(self.positions[c][0]-x)**2+(self.positions[c][1]-y)**2)
        if (self.positions[cell][0]-x)**2+(self.positions[cell][1]-y)**2<.7:
            self.add(frame,cell,color)


class RainbowDeathAnimation(DeathAnimation):
    """White ignition, expanding spectrum shockwaves, then scattered color sparks."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.wave=max(.7,min(1.15,len(self.body)*.035))
        self.charge=.25;self.burst=1.8;self.blackout=.6
        self.duration=.9 if self.reduced_motion else self.wave+self.charge+self.burst+self.blackout

    def stage(self,age):
        stage=super().stage(age)
        return 'blackout' if stage=='blackout' else 'prism_'+stage

    @staticmethod
    def spectrum(hue,strength,saturation=.9):
        return tuple(round(v*255*max(0,min(1,strength)))
                     for v in colorsys.hsv_to_rgb(hue%1,saturation,1))

    def frame(self,age):
        frame={c:(0,0,0) for c in self.positions}
        if self.reduced_motion:
            for i,c in enumerate(self.body):
                frame[c]=self.spectrum(i/max(1,len(self.body)),.65*max(0,1-age/.35))
            return self.wall_overlay(frame,age)
        stage=super().stage(age)
        if stage=='blackout':return self.wall_overlay(frame,age)
        if stage in ('wave','charge'):
            for i,c in enumerate(self.body):
                delay=(self.wave-.15)*i/max(1,len(self.body)-1)
                t=1 if i==0 else max(0,min(1,(age-delay)/.15))
                color=self.start_colors.get(c,self.spectrum(i/max(1,len(self.body)),1))
                frame[c]=tuple(round(a+(235-a)*t) for a in color)
            return self.wall_overlay(frame,age)
        t=age-self.wave-self.charge
        # Two expanding rainbow rings add depth without flashing the whole board.
        for c,(x,y) in self.positions.items():
            distance=math.dist((x,y),self.head)
            angle=math.atan2(y-self.head[1],x-self.head[0])/math.tau
            for delay in (0,.22):
                age_ring=t-delay
                if age_ring<0:continue
                strength=max(0,1-abs(distance-age_ring*9)/.8)*max(0,1-age_ring/1.1)*.7
                if strength:self.add(frame,c,self.spectrum(angle+age_ring*.7,strength))
        for i,(x,y,vx,vy,life,phase) in enumerate(self.particles):
            lifetime=life*1.6
            if t>=lifetime:continue
            # Curved flight and short multicolor trails separate this from red embers.
            bend=math.sin(t*3+phase*math.tau)*t*.7
            px=x+vx*t*.75+bend;py=y+vy*t*.75+t*t*.5
            strength=(1-t/lifetime)**1.2*(.65+.35*math.sin(t*6+phase*math.tau)**2)
            hue=i/max(1,len(self.particles))+t*.18
            self.splat(frame,px,py,self.spectrum(hue,strength))
            self.splat(frame,px-vx*.07,py-vy*.07,self.spectrum(hue+.12,strength*.3))
        return self.wall_overlay(frame,age)


class EntryAnimation:
    """A position-relative red burst with a legible orange spring into the new body."""
    def __init__(self, body, target_body, positions, play_positions, seed, reduced_motion=False,
                 style='rainbow',colors=None,background=(1,3,9),clock=0.):
        self.body=tuple(dict.fromkeys(body));self.target_body=tuple(target_body)
        self.style=style;self.clock=clock;self.colors=colors or ((255,88,0),(255,145,18));self.background=background
        self.positions=positions;self.play_positions=play_positions;self.reduced_motion=reduced_motion
        self.ignite=.16;self.burst=.5;self.pull=1.3;self.settle=.2
        self.duration=.35 if reduced_motion else self.ignite+self.burst+self.pull+self.settle
        rng=random.Random(seed);self.particles=[]
        self.bounds=(min(p[0] for p in positions.values()),max(p[0] for p in positions.values()),
                     min(p[1] for p in positions.values()),max(p[1] for p in positions.values()))
        center=(sum(positions[c][0] for c in self.body)/len(self.body),sum(positions[c][1] for c in self.body)/len(self.body))
        per_segment=max(1,min(3,72//len(self.body)))
        for cell in self.body:
            x,y=positions[cell]
            for _ in range(per_segment):
                angle=math.atan2(y-center[1],x-center[0])+rng.uniform(-1.3,1.3)
                self.make_particle((x,y),angle,rng)
        # Keep a readable outward fan without blanketing the keyboard in red.
        for i in range(12):self.make_particle(positions[self.body[0]],i*math.tau/12+rng.uniform(-.06,.06),rng)

    def make_particle(self,origin,angle,rng):
        x,y=origin;vx,vy=math.cos(angle),math.sin(angle)
        xmin,xmax,ymin,ymax=self.bounds
        hits=[]
        if vx>.0001:hits.append((xmax-x)/vx)
        elif vx<-.0001:hits.append((xmin-x)/vx)
        if vy>.0001:hits.append((ymax-y)/vy)
        elif vy<-.0001:hits.append((ymin-y)/vy)
        distance=max(0,min(min(hits),rng.uniform(2.8,4.8)))
        edge=(x+vx*distance,y+vy*distance)
        outward=max(.16,min(.4,distance/rng.uniform(12.,18.)))
        target=rng.randrange(len(self.target_body));destination=self.positions[self.target_body[target]]
        self.particles.append((origin,edge,destination,target,rng.uniform(-.35,.35),outward,rng.uniform(1.1,1.35)))

    def stage(self, age):
        if self.reduced_motion:return 'entry_settle'
        if age<self.ignite:return 'entry_ignite'
        if age<self.ignite+self.burst:return 'entry_burst'
        if age<self.ignite+self.burst+self.pull:return 'entry_pull'
        return 'entry_settle'

    def flight(self,particle,elapsed):
        origin,edge,target,index,bend,outward,return_time=particle
        source=style_color(self.style,self.clock+elapsed,phase=(bend+.35)/.7)
        if elapsed<=outward:
            t=max(0,elapsed/outward)
            return (origin[0]+(edge[0]-origin[0])*t,origin[1]+(edge[1]-origin[1])*t,source)
        q=max(0,min(1,(elapsed-outward)/return_time))
        # A critically damped return keeps the inward flight readable instead of
        # snapping almost the entire distance during its first few frames.
        spring=(1-(1+3*q)*math.exp(-3*q))/(1-4*math.exp(-3))
        curve=math.sin(math.pi*q)*bend
        x=edge[0]+(target[0]-edge[0])*spring+curve
        y=edge[1]+(target[1]-edge[1])*spring+curve*.65
        color_t=q*q*(3-2*q);shade=gradient(index,len(self.target_body),self.colors)
        color=tuple(round(a+(b-a)*color_t) for a,b in zip(source,shade))
        return x,y,color

    def frame(self, age):
        frame={c:(0,0,0) for c in self.positions}
        if self.reduced_motion:
            t=max(0,min(1,age/self.duration))
            for i,c in enumerate(self.body):frame[c]=tuple(round(v*(1-t)) for v in style_color(self.style,self.clock+age,phase=i/max(1,len(self.body))))
            for i,c in enumerate(self.target_body):frame[c]=tuple(round(v*t) for v in gradient(i,len(self.target_body),self.colors))
            for c in self.play_positions:
                if c not in self.target_body and c not in self.body:frame[c]=tuple(round(v*t) for v in self.background)
            return frame
        stage=self.stage(age)
        if stage=='entry_ignite':
            for i,c in enumerate(self.body):frame[c]=style_color(self.style,self.clock+age,phase=i/max(1,len(self.body)))
            return frame
        elapsed=age-self.ignite
        formed=max(0,min(1,((elapsed-self.burst)/self.pull-.65)/.35))
        if stage!='entry_settle':
            for particle in self.particles:
                x,y,color=self.flight(particle,elapsed);self.splat(frame,x,y,color)
                px,py,trail=self.flight(particle,max(0,elapsed-.035))
                self.splat(frame,px,py,tuple(round(v*.32) for v in trail))
        for i,c in enumerate(self.target_body):
            shade=gradient(i,len(self.target_body),self.colors)
            frame[c]=tuple(max(a,round(b*formed)) for a,b in zip(frame[c],shade))
        for c in self.play_positions:
            if c not in self.target_body:frame[c]=tuple(max(a,round(b*formed)) for a,b in zip(frame[c],self.background))
        return frame

    def splat(self,frame,x,y,color):
        cell=min(self.positions,key=lambda c:(self.positions[c][0]-x)**2+(self.positions[c][1]-y)**2)
        if (self.positions[cell][0]-x)**2+(self.positions[cell][1]-y)**2<.8:
            frame[cell]=tuple(max(a,b) for a,b in zip(frame[cell],color))
