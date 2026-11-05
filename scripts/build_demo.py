#!/usr/bin/env python3
"""Reproducible, captioned demos from the real engine. No keyboard or desktop I/O.

Inputs are scripted; game rules, timing, LED effects, and physical geometry are
unchanged. Snake's scripted player plans legal routes; Minesweeper's scripted
player knows the seeded board. This is a showcase, not a claim of human play.
"""
import argparse
import copy
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from rgb_keyboard_arcade.arcade import Arcade
from rgb_keyboard_arcade.autopilot import choose_avoiding
from rgb_keyboard_arcade.config import DEFAULT, load_profile
from rgb_keyboard_arcade.modes import static_routes, tail_route

WIDTH, HEIGHT = 960, 490
STEP = .025  # Same simulation cadence as the device daemon.
BG = (12, 13, 17)
INK = (244, 231, 215)
MUTED = (144, 143, 153)
ACCENTS = {'arcade': (255, 153, 71), 'snake': (255, 125, 43),
           'mines': (70, 202, 255), 'pong': (247, 108, 199)}
layout, movement = load_profile(DEFAULT)
FONTS = {size: ImageFont.load_default(size=size) for size in (10, 12, 14, 17, 24, 30)}


def fresh(key='snake', seed=42, variant=None):
    a = Arcade(layout, movement_map=movement)
    for g in a.instances.values():
        g.rng.seed(seed)
    a.game_id = key
    if variant:
        a.current.game_mode = variant
    return a


class Clip:
    def __init__(self, name, title, game, fps, output):
        self.name, self.title, self.game = name, title, game
        self.fps, self.output = fps, output
        self.now = 0.
        self.frames, self.chapters, self.proofs = [], [], []
        self.caption = ('', '')
        self.next_frame = 0.
        self.shots = []
        self.last_phase = None

    def chapter(self, title, detail):
        for text, size in ((title, 24), (detail, 14)):
            assert FONTS[size].getlength(text) <= WIDTH - 68, f'Caption overflows: {text}'
        self.caption = (title, detail)
        self.chapters.append({'at': round(self.now, 3), 'title': title, 'detail': detail})
        self.shots.append((len(self.frames) + round(self.fps * .7), title))

    def advance(self, seconds, player=None):
        target = self.now + seconds
        while self.now < target - STEP / 2:
            if player:
                player(self)
            self.game.tick(self.now)
            if self.game.current.phase == 'handoff':
                # The real daemon waits for held inputs to release; none remain
                # held by these scripted players at an entry boundary.
                self.game.current.begin_active(self.now)
            phase = self.game.state(self.now)['phase']
            if phase != self.last_phase:
                self.proofs.append({'at': round(self.now, 3), 'phase': phase})
                self.last_phase = phase
            if self.now + 1e-8 >= self.next_frame:
                self.frames.append(self.render())
                self.next_frame += 1 / self.fps
            self.now = round(self.now + STEP, 6)

    def until(self, predicate, limit, player=None):
        deadline = self.now + limit
        while not predicate() and self.now < deadline:
            self.advance(STEP, player)
        if not predicate():
            raise RuntimeError(f'{self.name}: expected event did not occur within {limit}s')

    def render(self):
        state = self.game.state(self.now)
        colors = {tuple(p[:2]): tuple(p[2:]) for p in state['pixels']}
        clues = {tuple(p[:2]): str(p[2]).replace('⚑', 'F') for p in state.get('cell_labels', [])}
        im = Image.new('RGB', (WIDTH, HEIGHT), BG)
        d = ImageDraw.Draw(im)
        accent = ACCENTS.get(self.game.game_id, ACCENTS['arcade'])
        if self.name == 'arcade':
            accent = ACCENTS['arcade']
        d.text((34, 19), self.title, font=FONTS[30], fill=INK)
        d.text((WIDTH - 34, 26), 'RGB KEYBOARD ARCADE', anchor='ra', font=FONTS[12], fill=MUTED)
        if state.get('marquee'):
            mode = 'SCROLLING TITLE'
        elif state['phase'] in ('entering', 'handoff') or state['pending_active']:
            mode = 'ROUND ENTRY'
        elif state['phase'] == 'dying':
            mode = 'ROUND OVER'
        else:
            mode = 'LIVE PREVIEW' if state['mode'] == 'passive' else 'SCRIPTED PLAY'
        d.ellipse((35, 65, 40, 70), fill=accent)
        d.text((48, 60), mode, font=FONTS[10], fill=MUTED)
        if self.game.game_id == 'pong' and not state.get('marquee'):
            scores = state['scores']
            d.text((WIDTH - 34, 57), f"P2  {scores['p2']}     :     {scores['p1']}  P1",
                   anchor='ra', font=FONTS[17], fill=INK)
        # Keycaps retain actual size, staggering, split arrows and unlit spacebar.
        d.rounded_rectangle((24, 94, 936, 373), 14, fill=(19, 20, 26), outline=(38, 39, 47))
        glow = Image.new('RGB', im.size, (0, 0, 0))
        gd = ImageDraw.Draw(glow)
        boxes = []
        for p in layout['pixels']:
            b = p['physical']
            x, y = 39 + b['x'] * 59, 108 + b['y'] * 42
            w, h = b['width'] * 59 - 5, b['height'] * 42 - 5
            cell = (p['row'], p['column'])
            rgb = colors.get(cell, (0, 0, 0))
            box = (x, y, x + w, y + h)
            if max(rgb) > 12:
                gd.rounded_rectangle(box, 4, fill=tuple(round(v * .35) for v in rgb))
            boxes.append((p, cell, rgb, box))
        # A modest optical halo helps small particles read; it adds no LED cells.
        im = ImageChops.add(im, glow.filter(ImageFilter.GaussianBlur(5)))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((39 + 4 * 59, 318, 39 + 9 * 59 - 5, 355), 4,
                           fill=(15, 16, 21), outline=(30, 31, 38))
        for p, cell, rgb, box in boxes:
            fill = tuple(round(11 + v * .78) for v in rgb)
            outline = tuple(round(33 + v * .35) for v in rgb)
            d.rounded_rectangle(box, 4, fill=fill, outline=outline)
            if state.get('marquee'):
                continue  # Uninterrupted five-row letter silhouettes.
            text = p['label'].replace('L ', '').replace('R ', '')
            text = {'Left': '<', 'Right': '>', 'Up': '^', 'Down': 'v',
                    'Backspace': 'BACK', 'Power': 'PWR', 'Super': 'WIN'}.get(text, text)
            if self.game.game_id == 'mines' and cell in self.game.current.cellset:
                text = clues.get(cell, '')
            lit = max(rgb) > 45
            foreground = (23, 20, 25) if sum(rgb) > 430 else ((242, 235, 222) if lit else (83, 84, 94))
            d.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), text,
                   anchor='mm', font=FONTS[10 if len(text) > 3 else 12], fill=foreground)
        d.line((34, 392, WIDTH - 34, 392), fill=(41, 40, 47))
        d.rectangle((34, 391, 69, 393), fill=accent)
        d.text((34, 407), self.caption[0], font=FONTS[24], fill=INK)
        d.text((34, 446), self.caption[1], font=FONTS[14], fill=MUTED)
        return im

    def save(self):
        self.output.mkdir(parents=True, exist_ok=True)
        # One palette per clip prevents unrelated per-frame color quantization
        # from making static keys/captions shimmer. Reserve resolution for LEDs.
        swatches = Image.new('RGB', (160 * 24, 82))
        for i in range(24):
            index = round(i * (len(self.frames) - 1) / 23)
            swatches.paste(self.frames[index].resize((160, 82)), (i * 160, 0))
        sampled = swatches.quantize(colors=224, method=Image.Quantize.MEDIANCUT)
        # Downsampled swatches can lose the exact text ink and tint captions
        # toward a nearby LED hue. Reserve the static UI colors explicitly.
        reserved = [BG, INK, MUTED, (19, 20, 26), (38, 39, 47), (15, 16, 21),
                    (30, 31, 38), (41, 40, 47), (23, 20, 25), (242, 235, 222),
                    (83, 84, 94), (11, 11, 11), (33, 33, 33), (235, 235, 235),
                    (255, 255, 255), ACCENTS.get(self.game.game_id, ACCENTS['arcade'])]
        reserved += [tuple(round(a + (b-a)*i/15) for a, b in zip(BG, INK))
                     for i in range(16)]
        palette = Image.new('P', (1, 1))
        palette.putpalette(sampled.getpalette()[:224*3] + [v for color in reserved for v in color])
        indexed = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in self.frames]
        path = self.output / f'{self.name}.gif'
        # GIF timings use centiseconds. At 20fps, every frame is exactly 50ms.
        indexed[0].save(path, save_all=True, append_images=indexed[1:],
                        duration=round(1000 / self.fps), loop=0, optimize=True, disposal=1)
        poster_titles = {'snake': 'Rainbow frenzy. A wave becomes the timer.',
                         'minesweeper': 'Clues ripple through the board.',
                         'pong': 'Every point lights up the score.',
                         'snake-timer': 'Edges become portals.'}
        poster_time = next((c['at'] + 1.1 for c in self.chapters
                            if c['title'] == poster_titles.get(self.name)), 2.2 if self.name == 'arcade' else .7)
        poster_index = min(len(self.frames) - 1, round(self.fps * poster_time))
        if self.name == 'arcade':
            assert self.frames[0].tobytes() == self.frames[-1].tobytes(), 'Startup loop must close on the same dark matrix'
        self.frames[poster_index].save(self.output / f'{self.name}.png')
        print(f'{path}: {len(self.frames)/self.fps:.2f}s, {len(self.frames)} frames, {path.stat().st_size/1024/1024:.2f} MiB', flush=True)
        return {'file': path.name, 'seconds': round(len(self.frames)/self.fps, 2),
                'fps': self.fps, 'chapters': self.chapters, 'engine_phases': self.proofs}

    def contact_sheet(self, path):
        thumbs = []
        for index, title in self.shots:
            index = min(index, len(self.frames) - 1)
            thumb = self.frames[index].resize((480, 245))
            thumbs.append(thumb)
        sheet = Image.new('RGB', (960, 245 * math.ceil(len(thumbs) / 2)), BG)
        for i, thumb in enumerate(thumbs):
            sheet.paste(thumb, ((i % 2) * 480, (i // 2) * 245))
        sheet.save(path)


def title(clip, key):
    clip.game.select_game(key, clip.now)
    clip.chapter('Every game gets an entrance.', 'Actual five-row LED lettering, on the calibrated keyboard layout.')
    clip.advance(clip.game.marquee.duration + .1)


def snake_player(clip):
    g, now = clip.game.current, clip.now
    if g.phase != 'running' or g.mode != 'classic' or g.turns:
        return
    if now - g.last_step + STEP < g.step_seconds(now):
        return
    moves = {c: {d: g.neighbor(c, d, now) for d in ('up', 'right', 'down', 'left')} for c in g.cells}
    if g.apples:
        routes = static_routes(tuple(g.body), g.direction, moves, set(g.apples), ())
        if not routes:
            routes = tail_route(tuple(g.body), g.direction, moves, set(g.apples), ())
        route = min(routes.values(), key=len) if routes else ()
        nxt = route[0] if route else None
    else:
        nxt = choose_avoiding(g.body, g.bombs, lambda c: list(moves[c].values()), g.rng)
    if nxt is not None:
        direction = next(d for d, c in moves[g.body[0]].items() if c == nxt)
        g.steer(direction, now)


def arcade_demo(fps, output):
    clip = Clip('arcade', 'ARCADE', fresh(), fps, output)
    clip.game.cycle_game(0)
    clip.chapter('Your keyboard is the display.', 'Super + Esc opens Arcade. Press again to skip a title or switch games.')
    # Start and finish on an unlit matrix; the title's natural lead/break loops.
    clip.advance(clip.game.marquee.duration - .025)
    # Reuse the real final dark frame as a one-frame editorial bookend. No
    # lettering is redrawn or retimed; the complete startup sweep stays intact.
    clip.frames.insert(0, clip.frames[-1].copy())
    return clip


def snake_demo(fps, output):
    clip = Clip('snake', 'SNAKE', fresh(seed=17), fps, output)
    title(clip, 'snake')
    clip.chapter('The menu is already playing.', 'A roaming rainbow snake previews the mode. Arrow keys start a fresh round.')
    clip.advance(2)
    clip.game.request_active('right', clip.now)
    clip.chapter('Scatter. Spring back. Start.', 'The preview bursts outward, then every particle gathers into your new snake.')
    clip.until(lambda: clip.game.phase == 'running' and clip.game.mode == 'classic', 4)
    clip.chapter('Eat. Grow. Keep moving.', 'Orange head to amber tail. The opening shield breathes for three seconds.')
    clip.until(lambda: clip.game.phase == 'powering', 30, snake_player)
    assert clip.game.score == 5, 'Show five real apple pickups before the frenzy'
    clip.chapter('Rainbow frenzy. A wave becomes the timer.', 'The fifth apple sends a shockwave to the edges. Dodge bombs until the side LEDs run out.')
    clip.until(lambda: clip.game.phase == 'running', 2)
    frenzy = fresh()
    frenzy.__dict__ = copy.deepcopy(clip.game.__dict__)
    frenzy_now = clip.now
    clip.until(lambda: clip.game.phase == 'staging', 11, snake_player)
    clip.chapter('Next stage, one shutter at a time.', 'The snake recolors first. Opposed column shutters count you back into play.')
    clip.until(lambda: clip.game.phase == 'running', 3)
    clip.advance(1.2, snake_player)
    clip.chapter('Even losing gets choreography.', 'Red travels from head to tail, then the body scatters into embers and goes dark.')
    clip.game.press(clip.game.body[0], clip.now)
    clip.advance(clip.game.death.duration - .025)
    return clip, frenzy, frenzy_now


def frenzy_demo(fps, output, saved, saved_now):
    clip = Clip('snake-frenzy', 'SNAKE / RAINBOW', saved, fps, output)
    clip.now = saved_now
    clip.next_frame = saved_now
    # Chapter times in manifests are relative to the clip, not engine time.
    clip.chapter('A bomb in your path.', 'Tapping an empty cell during a frenzy places a flashing red / white hazard.')
    clip.advance(1.5, snake_player)
    g = clip.game.current
    # Script a real board tap, then drive into that hazard. Do not synthesize a
    # death frame or call the animation directly.
    moves = g.moves[g.body[0]]
    options = [(d, c) for d, c in moves.items() if c is not None and c not in g.body and c not in g.bombs]
    assert options, 'Seed must leave a legal bomb placement beside the head'
    direction, cell = options[0]
    g.press(cell, clip.now)
    g.steer(direction, clip.now)
    clip.chapter('Rainbow deaths go out differently.', 'White ignition, expanding spectrum rings, curved sparks, then blackout.')
    clip.until(lambda: g.phase == 'dying', 1)
    assert g.death_reason == 'bomb'
    clip.advance(g.death.duration - .025)
    for chapter in clip.chapters:
        chapter['at'] = round(chapter['at'] - saved_now, 3)
    for proof in clip.proofs:
        proof['at'] = round(proof['at'] - saved_now, 3)
    return clip


def timer_demo(fps, output):
    clip = Clip('snake-timer', 'SNAKE / TIMER', fresh(seed=12, variant='timer'), fps, output)
    clip.game.set_mode('passive', 0)
    # Skip only the startup title; this clip is about the alternate rule set.
    clip.game.cycle_game(0)
    clip.chapter('A different kind of pressure.', 'Timer mode: purple snake, fixed pace, and an apple with a deadline.')
    clip.advance(3)
    clip.game.request_active('right', clip.now)
    clip.until(lambda: clip.game.phase == 'running' and clip.game.mode == 'classic', 4)
    clip.chapter('Edges become portals.', 'Cross an edge, reappear one lane over. Eat before white turns yellow, orange, red.')
    clip.until(lambda: clip.game.score >= 2, 15, snake_player)
    clip.advance(1, snake_player)
    clip.chapter('Miss the deadline. Feel the consequence.', 'The apple fades away; a procedural death sequence follows the body.')
    # Keep moving through portals without eating this apple, so its complete
    # temperature/depletion sequence remains visible before a real timeout.
    def miss_deadline(c):
        g = c.game.current
        if g.phase != 'running' or g.turns or c.now - g.last_step + STEP < g.step_seconds(c.now):
            return
        nxt = choose_avoiding(g.body, g.apples, lambda cell: list(g.wrapped_moves[cell].values()), g.rng)
        if nxt is not None:
            direction = next(d for d, cell in g.wrapped_moves[g.body[0]].items() if cell == nxt)
            g.steer(direction, c.now)
    clip.until(lambda: clip.game.phase == 'dying', 15, miss_deadline)
    assert clip.game.death_reason == 'timeout'
    clip.advance(clip.game.death.duration - .025)
    return clip


def mines_demo(fps, output):
    clip = Clip('minesweeper', 'MINESWEEPER', fresh('mines', seed=28), fps, output)
    title(clip, 'mines')
    clip.chapter('Fifty-eight keys. One minefield.', 'A live survey preview. The optional widget adds exact clue numbers, shown here.')
    clip.advance(2)
    g = clip.game.current
    origin = g.labels['G']
    g.key_down(origin, clip.now)
    g.key_up(origin, clip.now + .1)
    clip.chapter('Tap, release, reveal.', 'A safe first opening expands outward as a wave of clues.')
    clip.until(lambda: g.mode == 'classic' and g.phase == 'running', 3)
    clip.advance(1.5)
    frontier = sorted(g.mines, key=lambda c: min(math.dist(g.grid_coords[c], g.grid_coords[r]) for r in g.revealed))
    mine = frontier[0]
    clip.chapter('Hold to flag.', 'A 450 ms hold warms the key to orange. Release keeps the flag in place.')
    g.key_down(mine, clip.now)
    clip.advance(.65)
    g.key_up(mine, clip.now)
    assert mine in g.flags
    clip.advance(2.5)
    clip.chapter('Clues ripple through the board.', 'Real seeded layout. Scripted safe reveals; every number comes from neighboring mines.')
    for _ in range(5):
        safe = g.cellset - g.mines - g.revealed
        if not safe:
            break
        cell = min(safe, key=lambda c: (g.count(c) == 0, g.grid_coords[c]))
        g.key_down(cell, clip.now)
        clip.advance(.1)
        g.key_up(cell, clip.now)
        clip.advance(.65)
    clip.chapter('One wrong tap. Chain detonation.', 'The impact spreads across the physical key layout, then the board falls dark.')
    other = next(c for c in sorted(g.mines) if c not in g.flags)
    g.key_down(other, clip.now)
    g.key_up(other, clip.now + .1)
    assert g.result == 'mine'
    clip.advance(2.95)
    return clip


def pong_player(clip):
    g, now = clip.game.current, clip.now
    if g.mode != 'classic' or g.phase != 'running':
        return
    # A deterministic two-player rally, using the same held-key controls as the
    # hardware. P2 intentionally lets the fourth inbound ball past for a score.
    for side, up, down in ((0, 'L Shift', 'L Ctrl'), (1, 'R Shift', 'Right')):
        target = g.ball[1]
        if side == 0 and now - clip.active_start > 5:
            target = .5 if g.ball[1] > 2 else 3.5
        delta = target - g.paddles[side]
        desired = g.labels[down] if delta > .18 else g.labels[up] if delta < -.18 else None
        for label in (up, down):
            cell = g.labels[label]
            if cell == desired and cell not in g.held:
                g.key_down(cell, now)
            elif cell != desired:
                g.key_up(cell, now)


def pong_demo(fps, output):
    clip = Clip('pong', 'PONG', fresh('pong', seed=9, variant='duo'), fps, output)
    title(clip, 'pong')
    clip.chapter('Two paddles. One very small arena.', 'Solo AI or two players. The preview plays while the controls orbit in rainbow.')
    clip.advance(2)
    clip.game.current.key_down(clip.game.labels['R Shift'], clip.now)
    clip.chapter('Charge the paddles. Assemble the serve.', 'P1: right Shift / right arrow. P2: left Shift / left Ctrl.')
    clip.until(lambda: clip.game.mode == 'classic' and clip.game.phase == 'running', 3)
    clip.active_start = clip.now
    clip.advance(1.2, pong_player)
    clip.chapter('A rally across the keys.', 'Continuous paddle control, ball trails, wall impacts, and collision ripples.')
    clip.advance(4.8, pong_player)
    clip.chapter('Every point lights up the score.', 'Bottom-right Alt / Fn / Ctrl tally P1. Bottom-left Fn / Super / Alt tally P2.')
    clip.until(lambda: clip.game.current.phase == 'dying', 35, pong_player)
    assert max(clip.game.points) == 3
    clip.chapter('First to three. Victory wave.', 'The winning side washes across the arena. Score LEDs stay lit through the celebration.')
    clip.advance(2.95)
    return clip


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('docs/demos'))
    parser.add_argument('--only', choices=('arcade', 'snake', 'minesweeper', 'pong'))
    args = parser.parse_args()
    fps = 20
    clips = []
    if args.only in (None, 'arcade'):
        clips.append(arcade_demo(fps, args.output_dir))
    if args.only in (None, 'snake'):
        snake, saved, saved_now = snake_demo(fps, args.output_dir)
        clips.extend((snake, frenzy_demo(fps, args.output_dir, saved, saved_now), timer_demo(fps, args.output_dir)))
    if args.only in (None, 'minesweeper'):
        clips.append(mines_demo(fps, args.output_dir))
    if args.only in (None, 'pong'):
        clips.append(pong_demo(fps, args.output_dir))
    metadata = []
    for clip in clips:
        metadata.append(clip.save())
        clip.contact_sheet(Path('/tmp') / f'rgb-arcade-{clip.name}-contact.png')
    manifest_path = args.output_dir / 'scenes.json'
    if args.only and manifest_path.exists():
        previous = json.loads(manifest_path.read_text())['clips']
        metadata = [c for c in previous if c['file'] not in {m['file'] for m in metadata}] + metadata
    manifest_path.write_text(json.dumps({'simulation_step': STEP, 'scripted_inputs': True,
                                        'clips': metadata}, indent=2) + '\n')


if __name__ == '__main__':
    main()
