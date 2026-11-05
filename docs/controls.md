# Game controls

**Snake:** arrows steer. Rainbow and Timer variants retain their own previews and effects. During Rainbow Passive or an Active rainbow frenzy, tapping an empty board cell creates a lethal red/white flashing bomb. Ordinary Active taps add apples. Every fifth apple is rainbow; five taps on an ordinary apple also upgrade it. Food pauses during a frenzy and its stage transition. Timer food fades white → yellow → orange → red; eat it before expiry. Timer wraps at edges; Rainbow has walls after the initial spawn shield.

**Minesweeper:** 58 playable keys. Tap and release to reveal; hold 450 ms to flag/unflag. First opening and its neighbors are safe. LEDs indicate clue values by color; the optional widget displays exact numbers. Easy through Expert use 6 / 9 / 12 / 15 mines. Random boards can require guesses. [Clue color guide](configuration.md#minesweeper-colors).

**Pong:** solo against an AI, or two players. P1 uses Right Shift / Right Arrow for up/down; P2 uses Left Shift / Left Ctrl. Difficulty sets ball speed, and solo AI movement also scales. First to **three** wins. P2/AI scores fill Left Fn → Super → Left Alt; P1 scores fill Right Alt → Right Fn → Right Ctrl. Unscored LEDs stay off. Holding moves continuously; release stops movement.

During previews, ordinary typing still reaches the desktop. Active games capture only the configured keyboard. Capture is released on lock, suspend, or exit. Normal play does not log keys; explicit calibration can save movement captures locally.
