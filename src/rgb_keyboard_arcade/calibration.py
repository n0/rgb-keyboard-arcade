"""Explicit, temporary movement calibration. Only game-area presses are saved."""
import json,os,time
from datetime import datetime,timezone
from pathlib import Path
from .game import Game as SnakeGame

class CalibrationGame(SnakeGame):
    MODES = SnakeGame.MODES + ('calibration',)

    def set_mode(self, mode, now):
        if self.mode=='calibration' and mode!=self.mode:
            self.save_capture('complete' if not self.remaining else 'stopped')
        super().set_mode(mode,now)

    def reset(self, now):
        if self.mode!='calibration':return super().reset(now)
        self.death=None;self.rainbow_apples.clear();self.spawn_count=0;self.boost_start=None
        self.activation=None;self.finish_after_powerup=False
        self.pending_active=None
        self.touch_death_pending=False
        self.shield_start=None
        self.apple_presses.clear()
        self.palette_from=0.;self.palette_to=0.;self.palette_start=now
        self.body.clear();self.apples.clear();self.score=0;self.rounds=0;self.turns.clear()
        self.remaining=set(self.cells);self.events=[];self.phase='recording'
        self.phase_start=now;self.last_step=now;self.capture_start=now
        self.capture_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        self.capture_dir=Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'rgb-keyboard-arcade/calibration'
        self.capture_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.capture_path=self.capture_dir/(self.capture_id+'.json')
        self.save_capture('recording')

    def save_capture(self,status):
        data={'schema_version':1,'session':self.capture_id,'status':status,
              'intended_direction':'top_to_bottom_columns','gap_hint_seconds':2,
              'playfield':self.cells,'events':self.events,'remaining':sorted(self.remaining)}
        raw=json.dumps(data,indent=2)+'\n'
        for target in (self.capture_path,self.capture_dir/'latest.json'):
            tmp=target.with_suffix('.tmp')
            fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(fd,'w') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            tmp.replace(target)

    def press(self,cell=None,now=None):
        if self.mode!='calibration':return super().press(cell,now)
        if self.phase!='recording' or cell not in self.cellset:return
        now=time.monotonic();previous=self.events[-1] if self.events else None
        elapsed=round(now-self.capture_start,4)
        label=next(label for label,c in self.labels.items() if c==cell)
        self.events.append({'index':len(self.events)+1,'label':label,'cell':cell,'seconds':elapsed,
                            'gap':None if previous is None else round(elapsed-previous['seconds'],4),
                            'first_press':cell in self.remaining})
        self.remaining.discard(cell)
        self.score=len(self.cells)-len(self.remaining)
        if not self.remaining:self.phase='complete'
        self.save_capture(self.phase)

    def tick(self,now):
        if self.mode!='calibration':return super().tick(now)
        if self.phase=='recording' and now-self.capture_start>600:
            self.phase='expired';self.save_capture('expired')

    def frame(self,now):
        if self.mode!='calibration':return super().frame(now)
        return {cell:((180,180,180) if cell in self.remaining else (0,0,0)) for cell in self.cells}
