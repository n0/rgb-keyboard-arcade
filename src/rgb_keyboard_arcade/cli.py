"""CLI is a full control client; the graphical widget is optional."""
import argparse,json,os,socket,subprocess,sys
from pathlib import Path
from importlib.resources import files
from .config import load_config,default_path,paths,DEFAULT

def main():
 parser=argparse.ArgumentParser(prog='rgb-keyboard-arcade')
 parser.add_argument('--config',type=Path,help='JSON configuration (default: XDG config directory)')
 sub=parser.add_subparsers(dest='command',required=True)
 serve=sub.add_parser('serve',help='run lighting/input daemon');serve.add_argument('--simulate',action='store_true',help='no device access; drive with widget or socket')
 sub.add_parser('init-config',help='write an editable default configuration without overwriting')
 sub.add_parser('widget',help='open the optional standalone Quickshell widget')
 for name in ('status','watch','cycle-game','restart'):sub.add_parser(name)
 mode=sub.add_parser('mode');mode.add_argument('mode',choices=('default','passive','classic'))
 game=sub.add_parser('game');game.add_argument('game',choices=('snake','mines','pong'))
 setting=sub.add_parser('settings');setting.add_argument('--variant');setting.add_argument('--difficulty',type=int,choices=range(4))
 args=parser.parse_args()
 try:
  if args.command=='init-config':
   target=args.config or default_path();target.parent.mkdir(parents=True,exist_ok=True)
   with target.open('x') as f:f.write(json.dumps(DEFAULT,indent=2)+'\n')
   print(target);return
  config=load_config(args.config);sock,_=paths(config)
  if args.command=='serve':
   from .daemon import main as serve_main
   serve_main(args.config,args.simulate);return
  if args.command=='widget':
   env=dict(os.environ,RGB_KEYBOARD_ARCADE_SOCKET=str(sock));widget=files('rgb_keyboard_arcade')/'widgets/quickshell/shell.qml'
   result=subprocess.run(['quickshell','-p',str(widget)],env=env);raise SystemExit(result.returncode)
  msg={'op':args.command.replace('-','_')}
  if args.command=='game':msg={'op':'select_game','game':args.game}
  elif args.command=='mode':msg['mode']=args.mode
  elif args.command=='settings':
   if args.variant is not None:msg['game_mode']=args.variant
   if args.difficulty is not None:msg['difficulty']=args.difficulty
  with socket.socket(socket.AF_UNIX) as s:
   s.settimeout(4);s.connect(str(sock));s.sendall((json.dumps(msg)+'\n').encode());stream=s.makefile()
   if args.command=='watch':
    s.settimeout(None)
    for line in stream:print(line,end='',flush=True)
   else:
    state=json.loads(stream.readline());state.pop('pixels',None);state.pop('layout',None);print(json.dumps(state,indent=2))
    if state.get('error'):raise SystemExit(1)
 except (OSError,ValueError,KeyError,TypeError) as exc:
  parser.exit(1,f'{parser.prog}: {exc}\n')
 except KeyboardInterrupt:pass
