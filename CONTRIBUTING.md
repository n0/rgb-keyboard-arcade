# Contributing

Start with `serve --simulate`, the optional widget, or the demo renderer. Engine tests do not require OpenRazer, input permissions or a supported keyboard.

Useful contributions: clearer setup, verified profiles, bug fixes, accessible clue presentation, and well-scoped hardware adapters. This release is the current working implementation, not a universal driver framework. A new keyboard needs verified LED addresses, physical geometry, game regions, key labels and input access; changing the device name alone is insufficient. Document tested hardware and evidence instead of claiming compatibility from the USB family.

Keep games independent of device I/O. Keep the widget optional and communicate through the JSON protocol. Never add desktop-wide key logging. Preserve lock/suspend release and explicit capture boundaries. Hardware testing must be opt-in and target the configured device only.

Tests should exercise player-visible behavior or integration boundaries. Avoid tests that restate implementation expressions, snapshots that merely detect changes, and regression tests without a demonstrated behavioral gap. Describe what you tried with or without hardware in a contribution.

All contributions must be distributable under GPL-3.0 with appropriate attribution. Do not add private desktop assets or upstream code without compatible licensing and notices.
