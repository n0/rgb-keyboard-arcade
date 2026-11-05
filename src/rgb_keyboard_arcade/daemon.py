#!/usr/bin/env python3
"""Keyboard games. Key sequences are saved only during explicit calibration."""
import argparse,json,os,selectors,signal,socket,sys,time
from pathlib import Path
from .arcade import Arcade as Game
from .config import load_config, load_profile, paths
from .bindings import Bindings


class Hardware:
    def __init__(self,config,layout):
        from openrazer.client import DeviceManager
        self.manager=DeviceManager()
        ds=[d for d in self.manager.devices if d.name==config['device_name']]
        if len(ds)!=1:raise RuntimeError('Expected exactly one configured OpenRazer device; check device_name')
        self.device=ds[0]
        self.rows=layout['matrix']['rows'];self.columns=layout['matrix']['columns']
        if (self.device.fx.advanced.rows,self.device.fx.advanced.cols)!=(self.rows,self.columns):raise RuntimeError('Unexpected RGB grid')
        self.last=None
    def draw(self,frame):
        if frame==self.last:return
        for y in range(self.rows):
            for x in range(self.columns):self.device.fx.advanced.matrix[y,x]=frame.get((y,x),(0,0,0))
        self.device.fx.advanced.draw();self.last=dict(frame)
    def restore(self):
        # Default is deliberately the existing hardware spectrum effect. Future
        # default-mode renderers plug in here without changing either Snake game.
        self.device.fx.spectrum();self.last=None

class Inputs:
    def __init__(self,layout,config):
        self.vendor,self.product=(int(v,16) for v in layout["usb_id"].split(":"))
        import evdev
        self.evdev=evdev;self.devices=[];self.grabbed=[];self.down=set()
        E=evdev.ecodes;labels={p['label']:(p['row'],p['column']) for p in layout['pixels']}
        aliases={'Esc':'ESC','Delete':'DELETE','Power':'POWER','Backspace':'BACKSPACE','Tab':'TAB','Caps':'CAPSLOCK','Enter':'ENTER','L Shift':'LEFTSHIFT','R Shift':'RIGHTSHIFT','L Ctrl':'LEFTCTRL','R Ctrl':'RIGHTCTRL','Super':'LEFTMETA','L Alt':'LEFTALT','R Alt':'RIGHTALT','Left':'LEFT','Right':'RIGHT','Up':'UP','Down':'DOWN','`':'GRAVE','-':'MINUS','=':'EQUAL','[':'LEFTBRACE',']':'RIGHTBRACE','\\':'BACKSLASH',';':'SEMICOLON',"'":'APOSTROPHE',',':'COMMA','.':'DOT','/':'SLASH'}
        self.mapping={}
        for label,cell in labels.items():
            code=getattr(E,'KEY_'+aliases.get(label,label),None)
            if code is not None:self.mapping[code]=cell
    def open(self,classic=False):
        self.close()
        try:
            for path in self.evdev.list_devices():
                d=self.evdev.InputDevice(path)
                if d.info.vendor==self.vendor and d.info.product==self.product and self.evdev.ecodes.KEY_A in d.capabilities().get(self.evdev.ecodes.EV_KEY,[]):self.devices.append(d)
                else:d.close()
            if not self.devices:raise RuntimeError('Keyboard input access unavailable')
            if classic:
                if any(d.active_keys() for d in self.devices):raise RuntimeError('Release keyboard keys, then choose Classic again')
                for d in self.devices:d.grab();self.grabbed.append(d)
        except BaseException:self.close();raise
    def close(self):
        for d in self.grabbed:
            try:d.ungrab()
            except OSError:pass
        for d in self.devices:d.close()
        self.devices=[];self.grabbed=[];self.down.clear()
    def poll(self):
        events=[];batch=[]
        for d in self.devices:
            try:batch.extend(d.read())
            except BlockingIOError:continue
        # Preserve real event order across the keyboard's HID interfaces.
        for e in sorted(batch,key=lambda event:event.timestamp()):
            if e.type!=self.evdev.ecodes.EV_KEY:continue
            if e.value==0:
                self.down.discard(e.code);events.append((e.code,False))
            elif e.value==1 and e.code not in self.down:
                self.down.add(e.code);events.append((e.code,True))
        return events

class Service:
    def __init__(self,config_path=None,simulate=False):
        self.config=load_config(config_path);self.simulate=simulate
        self.socket_path,self.settings_path=paths(self.config)
        self.layout,movement_map=load_profile(self.config)
        self.bindings=Bindings(self.config,self.layout)
        try:settings=json.loads(self.settings_path.read_text())
        except (OSError,ValueError):settings={}
        self.game=Game(self.layout,movement_map=movement_map,reduced_motion=self.config['reduced_motion'],settings=settings)
        self.hardware=NullHardware() if simulate else Hardware(self.config,self.layout)
        self.inputs=NullInputs() if simulate else Inputs(self.layout,self.config)
        self.modifiers=set()
        self.selector=selectors.DefaultSelector();self.clients={};self.error='';self.running=True
        self.last_broadcast=0;self.last_draw=0;self.last_lock_check=0;self.last_tick=time.monotonic();self.no_ui_since=None
        self.server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.socket_path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        if self.socket_path.exists():
            probe=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            try:probe.connect(str(self.socket_path))
            except OSError:self.socket_path.unlink()
            else:raise RuntimeError('A keyboard service is already running')
            finally:probe.close()
        self.server.bind(str(self.socket_path));os.chmod(self.socket_path,0o600);self.server.listen(8);self.server.setblocking(False)
        self.selector.register(self.server,selectors.EVENT_READ)
        self.hardware.restore()
    def notify(self,message):
        addr=os.environ.get('NOTIFY_SOCKET')
        if not addr:return
        if addr.startswith('@'):addr='\0'+addr[1:]
        with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as s:
            try:s.sendto(message.encode(),addr)
            except OSError:pass
    def state(self):
        s=self.game.state(time.monotonic());s["pixels"]=[[*c,*rgb] for c,rgb in self.bindings.frame(self.game,s).items()];s["layout"]=self.layout["pixels"];s["control_cells"]=list(self.bindings.maps[self.game.game_id]);s.update(error=self.error,available=True,inputCaptured=bool(self.inputs.grabbed));return s
    def switch(self,mode):
        if mode not in Game.MODES:raise ValueError('Unknown mode')
        if mode=='classic':
            if self.game.mode=='classic':return
            if self.game.mode!='passive':self.switch('passive')
            self.game.request_active('right',time.monotonic());return
        if mode==self.game.mode:self.error='';return
        self.inputs.close()
        try:
            if mode!='default':self.inputs.open(classic=mode in ('classic','calibration'))
            self.game.set_mode(mode,time.monotonic());self.error=''
            if mode=='default':self.hardware.restore()
        except Exception as exc:
            self.inputs.close();self.game.set_mode('default',time.monotonic());self.hardware.restore();self.error=str(exc)

    def sync_inputs(self,now):
        if self.game.phase=='handoff':
            # Wait until the initiating key and any other typing have been released.
            # A grab while a key is held could hide its release from the desktop.
            if any(d.active_keys() for d in self.inputs.devices):return
            try:
                self.inputs.open(classic=True)
                self.game.begin_active(now);self.error=''
            except Exception as exc:
                self.game.back(now);self.inputs.open(classic=False);self.error=str(exc)
        elif self.game.mode=='passive' and self.inputs.grabbed:
            self.inputs.open(classic=False)

    def go_back(self,now):
        self.game.back(now);self.inputs.close()
        if self.game.mode!='default':self.inputs.open(classic=False)
        else:self.hardware.restore()

    def touch_cell(self,cell,now):
        if cell==self.game.labels['Esc']:
            self.go_back(now);return
        before=self.game.settings()
        if self.game.game_id!='snake':
            self.game.press(cell,now)
            if before!=self.game.settings():self.save_settings()
            return
        if self.game.selector_press(cell,now):
            if before!=self.game.settings():self.save_settings()
            return
        for label,direction in [('Up','up'),('Right','right'),('Down','down'),('Left','left')]:
            if cell==self.game.labels[label]:
                if self.game.mode=='passive':self.game.request_active(direction,now)
                elif self.game.mode=='classic':self.game.steer(direction,now)
                return
        self.game.press(cell,now)
    def cycle_game(self,now,key=None):
        if key is not None and key not in self.game.instances:raise ValueError("Unknown game")
        self.inputs.close();self.modifiers.clear()
        if key is None:self.game.cycle_game(now)
        else:self.game.select_game(key,now)
        self.inputs.open(classic=False);self.error='';self.save_settings()
    def key_event(self,code,pressed,now):
        E=self.inputs.evdev.ecodes
        modifier_codes={'Super':(E.KEY_LEFTMETA,E.KEY_RIGHTMETA),'Ctrl':(E.KEY_LEFTCTRL,E.KEY_RIGHTCTRL),'Alt':(E.KEY_LEFTALT,E.KEY_RIGHTALT),'Shift':(E.KEY_LEFTSHIFT,E.KEY_RIGHTSHIFT)}
        for name,codes in modifier_codes.items():
            if code in codes:
                if pressed:self.modifiers.add(code)
                else:self.modifiers.discard(code)
        physical=self.inputs.mapping.get(code)
        shortcut=self.config['shortcut']
        mods_match=all(any(c in self.modifiers for c in modifier_codes[name]) for name in shortcut['modifiers'])
        if pressed and physical==self.bindings.labels[shortcut['key']] and mods_match:
            if self.inputs.grabbed:self.cycle_game(now)
            return
        cell=self.bindings.resolve(self.game.game_id,physical)
        self.handle_cell(cell,pressed,now)
    def handle_cell(self,cell,pressed,now):
        if cell is None:return
        if cell==self.game.labels['Esc']:
            if pressed:self.go_back(now)
            return
        if self.game.mode=='calibration':
            if pressed:self.game.press(cell)
        elif self.game.game_id=='snake':
            if pressed:self.touch_cell(cell,now)
        else:
            before=self.game.settings()
            if pressed:self.game.key_down(cell,now)
            else:self.game.key_up(cell,now)
            if before!=self.game.settings():self.save_settings()

    def save_settings(self):
        self.settings_path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        temp=self.settings_path.with_suffix('.tmp')
        temp.write_text(json.dumps(self.game.settings())+'\n')
        temp.chmod(0o600);temp.replace(self.settings_path)
    def locked(self):
        if self.simulate:return False
        # Session activity is checked only while input-sensitive modes run.
        import dbus
        bus=dbus.SystemBus();manager=dbus.Interface(bus.get_object('org.freedesktop.login1','/org/freedesktop/login1'),'org.freedesktop.login1.Manager')
        sessions=manager.ListSessions(timeout=1)
        for sid,uid,user,seat,path in sessions:
            if int(uid)!=os.getuid() or not seat:continue
            props=dbus.Interface(bus.get_object('org.freedesktop.login1',path),'org.freedesktop.DBus.Properties').GetAll('org.freedesktop.login1.Session',timeout=1)
            if str(props.get('Type')) in ('wayland','x11') and props.get('Active'):
                return bool(props.get('LockedHint',False))
        return True
    def send(self,conn):
        try:conn.sendall((json.dumps(self.state(),separators=(',',':'))+'\n').encode())
        except OSError:self.drop(conn)
    def drop(self,conn):
        try:self.selector.unregister(conn)
        except Exception:pass
        self.clients.pop(conn,None);conn.close()
    def request(self,conn,line):
        msg=json.loads(line)
        if not isinstance(msg,dict):raise ValueError('Expected an object')
        op=msg.get('op','status')
        if op=='watch':self.clients[conn]['watch']=True
        elif op=='mode':self.switch(msg.get('mode'))
        elif op=='cycle_game':self.cycle_game(time.monotonic())
        elif op=='select_game':self.cycle_game(time.monotonic(),msg.get('game'))
        elif op=='restart':
            self.game.restart(time.monotonic())
        elif op=='settings':
            if self.game.configure(time.monotonic(),game_mode=msg.get('game_mode'),difficulty=msg.get('difficulty')):self.save_settings()
        elif op in ('press','key_down','key_up'):
            row,column=msg.get('row'),msg.get('column')
            if type(row) is not int or type(column) is not int or (row,column) not in self.game.all_positions:
                raise ValueError('Expected a visible keyboard cell')
            if self.game.mode in ('passive','classic'):
                now=time.monotonic();cell=(row,column)
                cell=self.bindings.resolve(self.game.game_id,cell)
                if op=='press' and self.game.game_id!='snake' and cell!=self.game.labels['Esc']:
                    before=self.game.settings();self.game.press(cell,now)
                    if before!=self.game.settings():self.save_settings()
                else:self.handle_cell(cell,op!='key_up',now)
        elif op!='status':raise ValueError('Unknown operation')
        self.send(conn)
    def run(self):
        self.notify('READY=1')
        try:
            while self.running:
                for key,_ in self.selector.select(timeout=.2 if self.game.mode=='default' else .025):
                    conn=key.fileobj
                    if conn is self.server:
                        new,_=self.server.accept();new.setblocking(False)
                        if len(self.clients)>=8:new.close();continue
                        self.clients[new]={'buf':b'','watch':False};self.selector.register(new,selectors.EVENT_READ)
                    else:
                        try:
                            chunk=conn.recv(4096)
                            if not chunk:self.drop(conn);continue
                            entry=self.clients[conn];entry['buf']+=chunk
                            if len(entry['buf'])>8192:self.drop(conn);continue
                            while b'\n' in entry['buf']:
                                line,entry['buf']=entry['buf'].split(b'\n',1)
                                try:self.request(conn,line)
                                except (ValueError,TypeError,KeyError) as exc:
                                    self.error=str(exc);self.send(conn)
                        except OSError:self.drop(conn)
                now=time.monotonic()
                if self.game.mode!='default':
                    if now-self.last_tick>2:
                        self.switch('default');self.error='Returned to Default after suspend or a delayed update'
                    if now-self.last_lock_check>2:
                        self.last_lock_check=now
                        try:locked=self.locked()
                        except Exception:locked=True
                        if locked:self.switch('default')
                    try:
                        for code,pressed in self.inputs.poll():self.key_event(code,pressed,now)
                    except OSError:self.switch('default');self.error='Keyboard disconnected; input released'
                self.last_tick=now
                watching=any(c['watch'] for c in self.clients.values())
                if self.game.mode=='classic' and self.config['require_watch_client'] and not watching:
                    if self.no_ui_since is None:self.no_ui_since=now
                    elif now-self.no_ui_since>5:self.switch('default');self.error='Controls disconnected; keyboard released'
                else:self.no_ui_since=None
                self.game.tick(now)
                try:self.sync_inputs(now)
                except OSError:self.switch('default');self.error='Keyboard disconnected; input released'
                if self.game.mode=='calibration':
                    if self.game.phase=='expired':self.switch('default')
                    elif self.game.phase=='complete':self.inputs.close()
                if self.game.mode!='default' and now-self.last_draw>=.05:
                    self.hardware.draw(self.bindings.frame(self.game,self.game.state(now)));self.last_draw=now
                if now-self.last_broadcast>(1.0 if self.game.mode=='default' else .12 if self.game.mode=='calibration' else .05):
                    self.last_broadcast=now
                    for conn,entry in list(self.clients.items()):
                        if entry['watch']:self.send(conn)
                self.notify('WATCHDOG=1')
        finally:
            self.inputs.close()
            try:self.hardware.restore()
            finally:
                for conn in list(self.clients):self.drop(conn)
                self.server.close();self.socket_path.unlink(missing_ok=True)

class NullHardware:
    def draw(self,frame):pass
    def restore(self):pass

class NullInputs:
    def __init__(self):self.devices=[];self.grabbed=[]
    def open(self,classic=False):pass
    def close(self):pass
    def poll(self):return []

def main(config_path=None,simulate=False):
    service=Service(config_path,simulate)
    def stop(*_):service.running=False
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    service.run()
