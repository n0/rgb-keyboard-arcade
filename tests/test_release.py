"""User workflows through the installed package and a real isolated socket daemon."""
import unittest,os,tempfile,subprocess,sys,time,json,socket
from pathlib import Path
from rgb_keyboard_arcade.config import DEFAULT,load_profile
from rgb_keyboard_arcade.arcade import Arcade
from rgb_keyboard_arcade.arcade_games import Pong
from rgb_keyboard_arcade.bindings import Bindings

class ReleaseWorkflows(unittest.TestCase):
 def test_pong_three_points_and_control_score_separation(self):
  layout,movement=load_profile(DEFAULT);g=Pong(layout,movement_map=movement,game_mode='duo');g.set_mode('classic',0)
  for point in range(1,4):
   g.serve_at=None;g.ball=[9.25,0];g.velocity=[g.SPEED[0],0];g.last_time=point-.1;g.tick(point)
   self.assertEqual(g.points,[point,0])
   f=g.frame(point)
   self.assertEqual(sum(max(f[g.labels[k]])>0 for k in ('L Fn','Super','L Alt')),point)
   self.assertTrue(all(f[g.labels[k]]==(0,0,0) for k in ('R Alt','R Fn','R Ctrl')))
  self.assertEqual(g.phase,'dying')
 def test_rebound_key_drives_action_and_moves_hint(self):
  config=json.loads(json.dumps(DEFAULT));config['bindings']['snake']['up']='R Ctrl'
  layout,movement=load_profile(config);g=Arcade(layout,movement_map=movement);g.cycle_game(0);g.cycle_game(.1)
  binds=Bindings(config,layout);cell=binds.resolve('snake',g.labels['R Ctrl'])
  g.request_active({g.labels['Up']:'up'}[cell],.2);g.tick(3);g.begin_active(3)
  self.assertEqual(g.direction,'up');self.assertIsNone(binds.resolve('snake',g.labels['Up']))
  g.back(4);state=g.state(4.8);f=binds.frame(g,state)
  self.assertEqual(f[g.labels['Up']],(0,0,0));self.assertGreater(max(f[g.labels['R Ctrl']]),0)
 def test_headless_daemon_without_watch_and_invalid_request(self):
  with tempfile.TemporaryDirectory() as tmp:
   env=dict(os.environ,XDG_RUNTIME_DIR=tmp,XDG_STATE_HOME=tmp,XDG_CONFIG_HOME=tmp)
   config=Path(tmp)/'config.json';config.write_text(json.dumps({'bindings':{'common':{'back':'F12'}}}))
   command=[sys.executable,'-m','rgb_keyboard_arcade','--config',str(config)]
   process=subprocess.Popen(command+['serve','--simulate'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   sock=Path(tmp)/'rgb-keyboard-arcade.sock'
   def req(**message):
    with socket.socket(socket.AF_UNIX) as s:
     s.settimeout(2);s.connect(str(sock));s.sendall((json.dumps(message)+'\n').encode());return json.loads(s.makefile().readline())
   try:
    for _ in range(100):
     if sock.exists():break
     if process.poll() is not None:self.fail(process.communicate()[1])
     time.sleep(.03)
    self.assertEqual(sock.stat().st_mode&0o777,0o600)
    req(op='cycle_game');state=req(op='cycle_game');self.assertEqual(state['phase'],'running')
    req(op='select_game',game='mines');req(op='cycle_game')
    state=req(op='status');labels={p['label']:(p['row'],p['column']) for p in state['layout']};q=labels['Q']
    req(op='key_down',row=q[0],column=q[1]);state=req(op='key_up',row=q[0],column=q[1]);self.assertEqual(state['phase'],'entering')
    time.sleep(1.6);state=req(op='status');self.assertEqual(state['mode'],'classic');self.assertGreater(state['score'],0)
    # No watch connection or GUI exists: the original five-second UI guard must not end play.
    time.sleep(5.3);state=req(op='status');self.assertEqual(state['mode'],'classic')
    bad=req(op='select_game',game='does-not-exist');self.assertIn('Unknown game',bad['error']);self.assertEqual(bad['mode'],'classic')
    row,col=labels['F12'];state=req(op='press',row=row,column=col);self.assertEqual(state['mode'],'passive')
    result=subprocess.run(command+['mode','default'],env=env,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
   finally:
    process.terminate();out,err=process.communicate(timeout=5)
    self.assertEqual(process.returncode,0,err);self.assertFalse(sock.exists())

if __name__=='__main__':unittest.main()
