"""Translate configured physical keys to existing game actions and control LEDs."""
COMMON={'back':'Esc','mode':'`','difficulty':'Tab'}
ACTIONS={'snake':{'up':'Up','right':'Right','down':'Down','left':'Left'},'pong':{'p1_up':'R Shift','p1_down':'Right','p2_up':'L Shift','p2_down':'L Ctrl'},'mines':{}}
class Bindings:
 def __init__(self,config,layout):
  self.labels={p['label']:(p['row'],p['column']) for p in layout['pixels']};self.maps={};self.hints={}
  for game,actions in ACTIONS.items():
   mapping={};hints={};seen=set()
   for section,entries in (('common',COMMON),(game,actions)):
    for action,logical in entries.items():
     physical=config['bindings'][section][action]
     if physical in ('L Fn','R Fn'):raise ValueError('Fn is firmware-controlled and cannot be used as an input binding')
     if physical not in self.labels:raise ValueError(f'Unknown binding key: {physical}')
     if physical in seen:raise ValueError(f'Conflicting bindings in {game}: {physical}')
     seen.add(physical);mapping[self.labels[physical]]=self.labels[logical];hints[self.labels[logical]]=self.labels[physical]
   self.maps[game]=mapping;self.hints[game]=hints
  if config['shortcut']['key'] not in self.labels:raise ValueError('Shortcut key is absent from layout')
 def resolve(self,game,cell):
  # Remapped original control keys are no longer also bound to the same action.
  mapping=self.maps[game]
  if cell in mapping:return mapping[cell]
  if cell in mapping.values():return None
  return cell
 def frame(self,game,state):
  raw={tuple(p[:2]):tuple(p[2:]) for p in state['pixels']}
  if state['mode']=='default' or state['phase']=='marquee':return raw
  hints=self.hints[game.game_id];active={self.labels['Esc']}
  preview=state['mode']=='passive' and state['phase']=='running'
  if preview:active.update(self.labels[k] for k in ('`','Tab'))
  if state['phase']=='running' and (preview or game.game_id=='pong'):
   if game.game_id=='pong':active.update(game.current.control_keys())
   else:active.update(self.labels[k] for k in ('Up','Right','Down','Left'))
  moves={source:target for source,target in hints.items() if source in active and source!=target}
  values={target:raw.get(source,(0,0,0)) for source,target in moves.items()}
  for source in moves:raw[source]=(0,0,0)
  raw.update(values);return raw
