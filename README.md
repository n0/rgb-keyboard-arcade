# rgb-keyboard-arcade

**The dumbest way to play video games with a computer.**

Snake, Minesweeper, and Pong. Your RGB keyboard is the screen and controller.

![ARCADE scrolling across the keyboard](docs/demos/arcade.gif)

Linux + OpenRazer. Tested on the **Razer Blade 15 Advanced (Early 2022), US ANSI, `1532:028a`**. Other keyboards and operating systems need porting work. The Quickshell UI is optional.

## Games

Demos use actual engine frames and scripted input at 20 fps.

### Snake

Rainbow frenzies, bombs, stage palettes, and elaborate ways to die. Timer mode adds food deadlines and edge portals.

![Snake gameplay and effects](docs/demos/snake.gif)

<details>
<summary>Rainbow death and Timer mode</summary>

![Rainbow death](docs/demos/snake-frenzy.gif)

![Timer mode](docs/demos/snake-timer.gif)

</details>

### Minesweeper

Tap to reveal. Hold to flag. 58 keys; 6–15 mines. LEDs show clue colors; the optional widget adds numbers, shown below.

![Minesweeper gameplay](docs/demos/minesweeper.gif)

### Pong

Solo against AI or two players. First to three wins; bottom-row LEDs keep score.

![Pong gameplay](docs/demos/pong.gif)

[Still images](docs/demos/) · [Demo timings](docs/demos/scenes.json)

## Try without hardware

Python 3.10+, from this checkout:

```sh
python -m venv .venv
.venv/bin/pip install --no-deps .
.venv/bin/rgb-keyboard-arcade serve --simulate
```

In another terminal:

```sh
.venv/bin/rgb-keyboard-arcade cycle-game
.venv/bin/rgb-keyboard-arcade widget      # optional; Quickshell on Wayland
```

Simulation uses no device LEDs or keyboard input. Interact through the widget or [JSON protocol](docs/protocol.md). Ctrl+C stops the daemon.

## Run on a keyboard

1. Set up [OpenRazer](https://openrazer.github.io/). Per-key lighting must work as your normal user.
2. Install your distribution's Python OpenRazer client, `evdev`, and D-Bus bindings. Install this package using that Python, or a venv with `--system-site-packages`.
3. Give your user access to the keyboard's input interfaces ([example rule](examples/70-rgb-keyboard-arcade.rules)). Run Arcade as your normal user.
4. Stop other RGB effect writers, then run:

```sh
rgb-keyboard-arcade init-config
rgb-keyboard-arcade serve
```

5. Bind **Super+Esc** to `rgb-keyboard-arcade cycle-game` ([Hyprland example](examples/hyprland.lua)). Use an absolute executable path if needed.

Autostart is optional: [user service](examples/rgb-keyboard-arcade.service). Active games release input on lock, suspend, or exit. Exit restores the hardware spectrum effect, rather than your previous RGB scene.

## Controls

| Key | Action |
| --- | --- |
| Super+Esc | Open Arcade / cycle games |
| Super+Esc during a title | Skip to that game's preview |
| Esc | Game → preview → default lighting |
| Backtick | Change variant in preview |
| Tab | Change difficulty in preview |
| Arrows | Steer Snake |
| Tap / hold 450 ms | Reveal / flag in Minesweeper |
| Right Shift / Right Arrow | Pong P1: up / down |
| Left Shift / Left Ctrl | Pong P2: up / down |

Previews leave ordinary typing alone. Active games capture the configured keyboard. [Full game rules and controls](docs/controls.md).

## Configuration and UI

Edit `~/.config/rgb-keyboard-arcade/config.json`, then restart. To use another file, put `--config PATH` before the subcommand. [Example](examples/config.json) · [Settings and clue colors](docs/configuration.md).

For the optional preview/settings panel, install Quickshell with Qt Quick Controls and run:

```sh
rgb-keyboard-arcade widget
```

Closing it leaves the game running. The [QML panel](src/rgb_keyboard_arcade/widgets/quickshell/KeyboardPanel.qml) can also be embedded in your own shell. No UI is required to play.

## Development

```sh
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python scripts/build_demo.py
python -m build
```

Demo builds need no hardware. Use `--only arcade`, `snake`, `minesweeper`, or `pong` to rebuild a subset. Snake includes both extra clips.

## Contributing

More keyboards and Windows/macOS ports welcome. Useful starting points:

- **Device profiles:** verified LED addresses, key geometry, and input mappings.
- **Flexible layouts:** remove the current 10×5 board, key-label, and 6×16 device assumptions.
- **Platform backends:** LED output, input capture, shortcuts, and lock/suspend handling. The current integration uses Linux/OpenRazer.

The games are pure Python; hardware integration lives in `daemon.py`. Open an issue with your device and proposed approach. [Contribution guide](CONTRIBUTING.md).

## License

[GPL-3.0](LICENSE). The layout derives from Polychromatic; see [NOTICE](NOTICE.md). OpenRazer and Quickshell are external dependencies.
