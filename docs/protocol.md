# Local JSON protocol

UTF-8 JSON objects, one per line, over the user's `rgb-keyboard-arcade.sock` Unix socket (0600). The process runs as that user. Do not expose the socket as a network service.

Each command returns a complete state object. `watch` subscribes to subsequent states, roughly 20 Hz during games and 1 Hz in Default. State includes game/variant/difficulty, phase, physical `layout`, `playfield`, `pixels` (`[row,column,r,g,b]`), selector availability and game-specific clues/scores. The client can be any language; Qt is not required.

```json
{"op":"status"}
{"op":"watch"}
{"op":"cycle_game"}
{"op":"select_game","game":"pong"}
{"op":"mode","mode":"default"}
{"op":"settings","game_mode":"duo","difficulty":1}
{"op":"key_down","row":2,"column":2}
{"op":"key_up","row":2,"column":2}
{"op":"restart"}
```

`cycle_game` enters from Default, skips a currently scrolling title without changing the game, or cycles when no title is showing. `select_game` accepts `snake`, `mines`, `pong`. `mode` accepts `default`, `passive`, `classic` (the internal identifier for Active). Variant IDs: Snake `rainbow`/`timer`; Minesweeper `sweep`; Pong `solo`/`duo`. Difficulty 0–3. Variant/difficulty changes are accepted only in a running Passive preview.

Coordinates are **physical profile addresses**, just like real keys, and follow configured input bindings. Send down and up separately for Minesweeper holds and continuous Pong controls. The legacy `press` operation is an instantaneous tap/nudge; it cannot represent a hold. Invalid commands return an error state; invalid game selection does not release an ongoing capture. Clients should display `error` and `available`, handle socket loss, and reconnect. Layout/color data is a rendering description, not firmware readback.
