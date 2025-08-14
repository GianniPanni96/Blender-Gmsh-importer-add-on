# Blender-Gmsh-importer-add-on
A small single‑file Blender add‑on that imports Gmsh .msh surface meshes and creates one Blender object per physical surface found in the file. The add‑on tries to use meshio (if available) for maximum compatibility; otherwise it falls back to a lightweight built‑in ASCII MSH v2.x parser so the add‑on works out‑of‑the‑box for the most common cases.
