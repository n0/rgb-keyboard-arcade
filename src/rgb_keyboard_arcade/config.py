"""Explicit configuration; no machine-specific paths or installation side effects."""
import json,os
from pathlib import Path
from importlib.resources import files
DEFAULT={
 'profile':'blade-15-2022-us','device_name':'Razer Blade 15 Advanced (Early 2022)',
 'reduced_motion':False,'require_watch_client':False,'socket':None,
 'shortcut':{'key':'Esc','modifiers':['Super']},
 'bindings':{
  'common':{'back':'Esc','mode':'`','difficulty':'Tab'},
  'snake':{'up':'Up','right':'Right','down':'Down','left':'Left'},
  'pong':{'p1_up':'R Shift','p1_down':'Right','p2_up':'L Shift','p2_down':'L Ctrl'}
 }
}

def default_path():return Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'rgb-keyboard-arcade/config.json'
def merge(base,update):
 result=json.loads(json.dumps(base))
 for key,value in update.items():
  if key not in base:raise ValueError(f'Unknown configuration key: {key}')
  result[key]=merge(base[key],value) if isinstance(base[key],dict) and isinstance(value,dict) else value
 return result

def load_config(path=None):
 target=Path(path).expanduser() if path else default_path()
 if target.exists():
  data=json.loads(target.read_text())
  if not isinstance(data,dict):raise ValueError('Configuration must be an object')
  config=merge(DEFAULT,data)
 elif path:raise ValueError(f'Configuration not found: {target}')
 else:config=merge(DEFAULT,{})
 if not isinstance(config['profile'],str):raise ValueError('profile must be a string')
 if not isinstance(config['bindings'],dict) or any(not isinstance(v,dict) for v in config['bindings'].values()):raise ValueError('bindings sections must be objects')
 for key in ('reduced_motion','require_watch_client'):
  if type(config[key]) is not bool:raise ValueError(f'{key} must be true or false')
 if not isinstance(config['device_name'],str) or not config['device_name']:raise ValueError('device_name must be a nonempty string')
 if not isinstance(config['shortcut'],dict) or not isinstance(config['shortcut'].get('modifiers'),list) or not config['shortcut']['modifiers']:raise ValueError('shortcut requires modifier keys')
 if any(m not in ('Super','Ctrl','Alt','Shift') for m in config['shortcut']['modifiers']):raise ValueError('Unknown shortcut modifier')
 if config['socket'] is not None and (not isinstance(config['socket'],str) or not Path(config['socket']).expanduser().is_absolute()):raise ValueError('socket must be an absolute path')
 return config

def load_profile(config):
 profile=config['profile']
 if profile=='blade-15-2022-us':
  root=files('rgb_keyboard_arcade')/'profiles'
  return json.loads((root/(profile+'.layout.json')).read_text()),json.loads((root/(profile+'.movement.json')).read_text())
 # Custom profiles retain this version's required grid/labels. This is not a universal layout mapper.
 root=Path(profile).expanduser()
 return json.loads((root/'layout.json').read_text()),json.loads((root/'movement.json').read_text())

def paths(config):
 runtime=Path(os.environ.get('XDG_RUNTIME_DIR',str(Path.home()/'.cache/rgb-keyboard-arcade')))
 sock=Path(config['socket']).expanduser() if config['socket'] else runtime/'rgb-keyboard-arcade.sock'
 state=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'rgb-keyboard-arcade/settings.json'
 return sock,state
