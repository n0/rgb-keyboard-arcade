# Attribution

The games, effects, input daemon, CLI, bindings, and widget were developed for this arcade and extracted from its working desktop installation. Distributed here under GNU GPL version 3.

The bundled `blade-15-2022-us.layout.json` derives its LED addresses and approximate key geometry from **Polychromatic**, with physical LED checks and movement calibration refining the result:

- Upstream project: https://github.com/polychromatic/polychromatic
- Source map: https://github.com/polychromatic/polychromatic/blob/cd024b28f583dea330e015d203bf0af58eaf78f4/data/devicemaps/blade_advanced_2021_en_US.svg
- Polychromatic contributors retain copyright in their original work. The repository's GPL-3.0 license text is included as `LICENSE`.
- Changes: JSON conversion, visible/masked cell enumeration, US key labels and approximate rectangles, physical LED verification, and a separately calibrated game movement map. No upstream SVG artwork is embedded in the demo.

OpenRazer, python-evdev, D-Bus Python, Quickshell, Qt, Python and Pillow are external dependencies and retain their own licenses. Their implementations are not vendored. The demo GIF is generated from this project's renderer and attributed layout geometry; it includes no character art or desktop photography.
