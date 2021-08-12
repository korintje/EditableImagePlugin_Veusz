# EditableImagePlugin_Veusz
[Veusz](https://veusz.github.io/) plugin to Save/Load re-editable images (Veusz-SVG or Veusz-PNG).
Veusz-SVG images contain self-describing Veusz code in their `metadata` element.
Veusz-PNG images contain self-describing Veusz code in their `tEXt` chunk.

# How to install
1. Clone this repository.
2. Move `load_vszimg.py` and `savevszimg.py` to a place where you like.
3. Launch Veusz and import plugins from `Edit` -> `Preferences` -> `Plugins`.
4. Restart Veusz
    - If you build Veusz by yourself in your Python environment (not independent executable), you cannnot import `load_vszimg.py` and `savevszimg.py` in the current version (Veusz 3.3.1). In this case, you can alternatively use `load_vszpng.py`, `load_vszimg.py`, `save_vszpng.py`, and `save_vszpng.py` in the directory `for_self-building_env`.

# How to use
1. You can save your veusz document as Veusz-SVG from `Tools` -> `Save Veusz-image`.
1. You can load an exsisting Veusz-SVG file from `Tools` -> `Load Veusz-image`.
