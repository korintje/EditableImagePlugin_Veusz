# EditableSVGPlugin_Veusz
[Veusz](https://veusz.github.io/) plugin to Save/Load re-editable SVG image (Veusz-SVG).
Veusz-SVG images contain self-describing Veusz code in their `metadata` element.

# How to install
1. Clone this repository.
1. Move `load_vszsvg.py` and `savevszsvg.py` to a place where you like.
1. Launch Veusz and import plugins from `Edit` -> `Preferences` -> `Plugins`.
1. Restart Veusz

# How to use
1. You can save your veusz document as Veusz-SVG from `Tools` -> `Save as Veusz-SVG`.
1. You can load an exsisting Veusz-SVG file from `Tools` -> `Load Veusz-SVG`.