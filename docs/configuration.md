# Configuration

`rgb-keyboard-arcade init-config` creates the default JSON and refuses to overwrite an existing file. `--config PATH` selects another file. Configuration is read at daemon startup; use the same config for the CLI/widget. By default XDG config/state/runtime paths are used. Preferences migrate independently of bindings.

- `profile`: `blade-15-2022-us`, or a directory containing `layout.json` and `movement.json` compatible with the current engine's required labels and dimensions.
- `device_name`: exact OpenRazer device name. USB input matching comes from the profile's `usb_id`. The driver checks matrix dimensions before drawing.
- `bindings.common`: back, mode, difficulty. `bindings.snake`: up/right/down/left. `bindings.pong`: p1_up/down and p2_up/down. Values are physical labels from the profile, such as `F12`, `R Ctrl`, or `Right`. Duplicate binds within a game are rejected. Fn is firmware-controlled and cannot be bound as an input.
- `shortcut`: key and nonempty modifier list (`Super`, `Ctrl`, `Alt`, `Shift`). This matches the chord while Active owns the keyboard. **Configure the same shortcut in your desktop to execute `rgb-keyboard-arcade cycle-game`**; the daemon deliberately does not read input in Default or silently rewrite desktop bindings.
- `reduced_motion`: limits decorative motion/flashing; necessary game movement and readable title scrolling remain.
- `require_watch_client`: `false` by default, so the UI is optional. Set `true` to release Active after five seconds without a widget or `watch` connection.
- `socket`: optional absolute Unix socket path. Defaults to `$XDG_RUNTIME_DIR/rgb-keyboard-arcade.sock` (a private cache directory if unset). The CLI exports the selected path when launching the widget.

Control LED hints follow rebindings. Prefer unused keys outside the game board and Pong score keys: binding a gameplay key as a control reserves that input and its hint can obscure that cell. This release does not redesign the game regions around arbitrary controls. Mode and difficulty only change in Passive; Minesweeper retains board tap/hold and arrow-start behavior.

## Minesweeper colors

| Value | Color |
| --- | --- |
| Covered | Dim blue |
| Revealed empty | Dim near-black |
| 1 | Blue |
| 2 | Green |
| 3 | Red |
| 4 | Violet |
| 5 | Gold |
| 6 | Cyan |
| 7 | Pink |
| 8 | White |
| Flag | Orange |

The widget overlays numeric clues and a flag glyph. A key's LED alone cannot display a literal number; color is the keyboard-only clue encoding.
