#!/usr/bin/env python3
"""Render the real game frames without a keyboard, compositor, or personal assets."""
import argparse,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from rgb_keyboard_arcade.arcade import Arcade
from rgb_keyboard_arcade.config import DEFAULT,load_profile
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path('docs/demo.gif'));args=parser.parse_args()
layout,movement=load_profile(DEFAULT);game=Arcade(layout,movement_map=movement)
for instance in game.instances.values():instance.rng.seed(42)
font=ImageFont.load_default(size=16);small=ImageFont.load_default(size=11);frames=[];clock=0.;fps=8

def render(now):
 state=game.state(now);colors={tuple(p[:2]):tuple(p[2:]) for p in state['pixels']};clues={tuple(p[:2]):str(p[2]).replace('⚑','F') for p in state.get('cell_labels',[])}
 im=Image.new('RGB',(840,340),(15,13,17));d=ImageDraw.Draw(im)
 d.text((20,14),'rgb-keyboard-arcade',(245,224,205),font=font)
 d.text((20,39),state['game_name']+' / '+state.get('game_mode_name',''),(180,160,150),font=small)
 for p in layout['pixels']:
  b=p['physical'];x=20+b['x']*53;y=75+b['y']*33;w=b['width']*53-4;h=b['height']*33-4;c=(p['row'],p['column'])
  rgb=colors.get(c,(0,0,0));fill=tuple(max(8,v) for v in rgb)
  d.rounded_rectangle((x,y,x+w,y+h),4,fill=fill,outline=(46,38,43))
  if not state.get('marquee'):
   text=clues.get(c,'') if state['game_id']=='mines' and c in game.current.cellset else p['label'].replace('L ','').replace('R ','')
   if len(text)>5:text=text[:4]
   color=(20,15,20) if sum(rgb)>440 else (225,215,210)
   d.text((x+w/2,y+h/2),text,font=small,fill=color,anchor='mm')
 status=state.get('status_text') or ('Rainbow preview · '+str(state['length'])+' segments')
 d.text((20,285),status[:100],font=small,fill=(225,205,190))
 helptext={'snake':'Arrows play · tap to place bombs during rainbow','mines':'Release to reveal · hold 0.45s to flag · 58 keys','pong':'Solo / two players · first to 3 · per-side LED scores'}[state['game_id']]
 d.text((20,308),helptext,font=small,fill=(175,150,140));frames.append(im)

def advance(seconds):
 global clock
 for _ in range(math.ceil(seconds*fps)):
  game.tick(clock);render(clock);clock+=1/fps

game.cycle_game(clock);advance(game.marquee.duration+.15);advance(3)
for key,duration in (('mines',5),('pong',6)):
 game.select_game(key,clock);advance(game.marquee.duration+.15);advance(duration)
args.output.parent.mkdir(parents=True,exist_ok=True)
frames[0].save(args.output,save_all=True,append_images=frames[1:],duration=round(1000/fps),loop=0,optimize=True)
print(f'{args.output}: {len(frames)} frames, {len(frames)/fps:.1f}s')
