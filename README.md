# Import Gmsh .msh (Physical surfaces) — Blender Add-on

A small single-file Blender add-on that imports Gmsh `.msh` surface meshes and creates one Blender object per *physical surface* found in the file. The add-on tries to use `meshio` (if available) for maximum compatibility; otherwise it falls back to a lightweight built-in ASCII MSH v2.x parser so the add-on works out-of-the-box for the most common cases.

---

## Features

- Imports `.msh` files exported by Gmsh.
- Creates one Blender mesh/object per *physical surface* (physical group) present in the file.
- Uses the `physical` tag name (if present) to name the created objects; otherwise uses `basename_phys<tag>`.
- No external dependencies required for ASCII MSH v2.x files (fallback parser built in).
- If `meshio` is installed in Blender's bundled Python, the add-on will use it automatically for broader support (MSH v4, binary, more element types).

---

## Quick install (for GitHub release or manual)

1. Download the `import_gmsh_msh_addon.py` file from this repository (or clone the repo).
2. In Blender: **Edit > Preferences > Add-ons > Install...** and select the `import_gmsh_msh_addon.py` file.
3. Enable the add-on in the Add-ons list.
4. Use the importer: **File > Import > Gmsh (.msh) - Physical surfaces** and select your `.msh` file.

> Alternatively you can place the file into your addons folder:
>
> ```text
> ~/Library/Application Support/Blender/<VERSION>/scripts/addons/    # macOS
> %APPDATA%\Blender Foundation\Blender\<VERSION>\scripts\addons\     # Windows
> ~/.config/blender/<VERSION>/scripts/addons/                       # Linux
> ```
>
> and then enable it in Blender preferences.

---

## Optional: Install `meshio` for better compatibility

`meshio` enables support for MSH v4 (binary) and more flexible parsing. If you want full compatibility, install `meshio` into the Python bundled with your Blender installation.

## Notes:

You do not need to install meshio to use the add-on for the typical ASCII MSH v2.x files — the included parser will work. Installing meshio only improves compatibility.

If you get permission errors, try adding --user or run the command with sudo where appropriate.

---

## Usage

1. File > Import > Gmsh (.msh) - Physical surfaces.
2. Choose a .msh file and confirm.

The importer creates one object per physical group. Objects are created in the active collection.

---

## Behavior / limitations

The built-in parser supports ASCII MSH v2.x and reads PhysicalNames, Nodes and Elements (triangle / quad surface elements). It ignores volumetric elements (tetra, hexa, ...).

When meshio is present, the add-on will use it and will typically support more MSH versions and element types.

For large meshes the add-on duplicates vertex coordinates per object (simple and robust approach). This may increase memory usage; if you need a memory-efficient alternative the add-on can be extended to create a single mesh and separate by material/attribute.

---

## Troubleshooting

- Import failed: check Blender System Console (Window > Toggle System Console on Windows, or run Blender from terminal on macOS/Linux) for traceback.

- meshio not found: this is not an error — the fallback parser will be used for ASCII MSH v2.x. Install meshio into Blender's Python if you need full support.

- Unexpected physical tags or missing faces: verify the .msh file in Gmsh (View > Visibility filters) to ensure physical surfaces are assigned and elements are exported as surfaces.
