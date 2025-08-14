bl_info = {
    "name": "Import Gmsh .msh (Physical surfaces)",
    "author": "GianniPanni",
    "version": (1, 0, 0),
    "blender": (4, 3, 0),
    "location": "File > Import > Gmsh (.msh)",
    "description": "Import .msh (Gmsh) and create one Blender object per physical surface (supports ASCII MSH v2.2).\nIf 'meshio' is installed it will be used for broader format support.",
    "category": "Import-Export",
}

import bpy
import os
from collections import defaultdict
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator

# -----------------------------
# Lightweight MSH v2.2 parser
# -----------------------------

def parse_msh_v2(filepath):
    """
    Very small parser for ASCII Gmsh MSH format v2.x (text). Supports:
      - $PhysicalNames  (optional)
      - $Nodes
      - $Elements  (reads element type 2=triangle, 3=quad)
    Returns: verts, groups, phys_names
      - verts: list of (x,y,z)
      - groups: dict phys_tag -> list of faces (each face is list of zero-based vertex indices)
      - phys_names: dict phys_tag -> name (if present)

    This is intentionally minimal to avoid external dependencies. If your file is MSH v4 or
    binary, consider installing 'meshio' and let the addon use it instead.
    """
    verts = []
    node_id_to_index = {}
    groups = defaultdict(list)
    phys_names = {}

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f
        state = None
        for raw in lines:
            line = raw.strip()
            if not line:
                continue
            if line.startswith('$'):
                # section start or end
                if line == '$PhysicalNames':
                    state = 'PhysicalNames'
                    continue
                elif line == '$Nodes':
                    state = 'Nodes'
                    continue
                elif line == '$Elements':
                    state = 'Elements'
                    continue
                elif line.startswith('$End'):
                    state = None
                    continue
                else:
                    state = None
                    continue

            if state == 'PhysicalNames':
                # first line is number of names
                try:
                    count = int(line)
                except ValueError:
                    # possibly we are already on the first name line
                    count = None
                if count is not None:
                    # read next 'count' lines
                    for _ in range(count):
                        l = next(lines).strip()
                        # format: dim tag "name"
                        parts = l.split()
                        if len(parts) >= 3:
                            dim = parts[0]
                            tag = int(parts[1])
                            # name may contain spaces and be quoted
                            name = l.split(' ', 2)[2].strip()
                            if name.startswith('"') and name.endswith('"'):
                                name = name[1:-1]
                            phys_names[tag] = name
                    state = None
                    continue

            if state == 'Nodes':
                # first non-empty line is number of nodes
                try:
                    n_nodes = int(line)
                except ValueError:
                    continue
                for _ in range(n_nodes):
                    l = next(lines).strip()
                    if not l:
                        continue
                    parts = l.split()
                    # id x y z
                    nid = int(parts[0])
                    coords = tuple(float(x) for x in parts[1:4])
                    node_id_to_index[nid] = len(verts)
                    verts.append(coords)
                state = None
                continue

            if state == 'Elements':
                try:
                    n_el = int(line)
                except ValueError:
                    continue
                for _ in range(n_el):
                    l = next(lines).strip()
                    if not l:
                        continue
                    parts = l.split()
                    # elem_id, elem_type, num_tags, tags..., node_ids...
                    eid = int(parts[0])
                    etype = int(parts[1])
                    n_tags = int(parts[2])
                    tags = [int(t) for t in parts[3:3+n_tags]] if n_tags>0 else []
                    node_ids = [int(t) for t in parts[3+n_tags:]]

                    # physical group tag is typically the first tag when present
                    phys_tag = tags[0] if len(tags) > 0 else 0

                    # only handle surface elements (triangle=2, quad=3) here
                    if etype == 2 or etype == 3:
                        # map node ids to zero-based contiguous indices
                        try:
                            face = [node_id_to_index[nid] for nid in node_ids]
                        except KeyError:
                            # node referenced not found; skip
                            continue
                        groups[int(phys_tag)].append(face)
                    else:
                        # ignore other element types (lines, tets, hex, ...)
                        continue
                state = None
                continue

    return verts, groups, phys_names


# -----------------------------
# meshio fallback loader
# -----------------------------

def load_with_meshio(filepath):
    import meshio
    mesh = meshio.read(filepath)
    # vertices
    verts = [tuple(p) for p in mesh.points]
    # collect groups by gmsh:physical if available
    groups = defaultdict(list)
    phys_names = {}
    cell_blocks = mesh.cells
    phys_data = mesh.cell_data.get('gmsh:physical', [])

    # If mesh has PhysicalNames in field data, try to extract (meshio usually stores names differently)
    # Fallback: just leave phys_names empty; names will be generated from tags
    for blk_idx, block in enumerate(cell_blocks):
        if block.type not in ('triangle', 'quad'):
            continue
        tags = phys_data[blk_idx] if blk_idx < len(phys_data) else [0]*len(block.data)
        for local_idx, tag in enumerate(tags):
            face = block.data[local_idx].tolist()
            groups[int(tag)].append(face)

    return verts, groups, phys_names


# -----------------------------
# Blender import logic
# -----------------------------

def import_msh_to_blender(filepath):
    # Try meshio first (if installed) for maximum compatibility
    try:
        import meshio  # type: ignore
    except Exception:
        meshio = None

    if meshio is not None:
        try:
            verts, groups, phys_names = load_with_meshio(filepath)
        except Exception as e:
            # fallback to simple parser
            print('meshio failed, falling back to simple parser:', e)
            verts, groups, phys_names = parse_msh_v2(filepath)
    else:
        verts, groups, phys_names = parse_msh_v2(filepath)

    base_name = os.path.splitext(os.path.basename(filepath))[0]

    created = []
    for phys_tag, faces in groups.items():
        if not faces:
            continue
        name = phys_names.get(phys_tag, f'{base_name}_phys{phys_tag}')
        obj_name = name if name else f'{base_name}_phys{phys_tag}'
        mesh_name = obj_name + '_Mesh'

        bl_mesh = bpy.data.meshes.new(mesh_name)
        bl_obj = bpy.data.objects.new(obj_name, bl_mesh)
        bpy.context.scene.collection.objects.link(bl_obj)

        # from_pydata expects list of verts and faces referencing zero-based indices
        bl_mesh.from_pydata(verts, [], faces)
        bl_mesh.update()

        # set origin to center and place at 0,0,0
        try:
            bpy.context.view_layer.objects.active = bl_obj
            bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='MEDIAN')
        except Exception:
            pass
        bl_obj.location = (0, 0, 0)
        created.append(bl_obj)

    return created


# -----------------------------
# Blender Operator + UI
# -----------------------------
class IMPORT_OT_gmsh_msh(Operator, ImportHelper):
    bl_idname = "import_scene.gmsh_msh"
    bl_label = "Import Gmsh .msh (Physical surfaces)"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".msh"
    filter_glob: StringProperty(
        default='*.msh',
        options={'HIDDEN'},
    )

    def execute(self, context):
        filepath = self.filepath
        if not os.path.isfile(filepath):
            self.report({'ERROR'}, f"File not found: {filepath}")
            return {'CANCELLED'}

        try:
            created = import_msh_to_blender(filepath)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.report({'ERROR'}, f"Failed to import: {e}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Imported {len(created)} objects from {os.path.basename(filepath)}")
        return {'FINISHED'}


def menu_func_import(self, context):
    self.layout.operator(IMPORT_OT_gmsh_msh.bl_idname, text="Gmsh (.msh) - Physical surfaces")


# -----------------------------
# Registration
# -----------------------------

classes = (
    IMPORT_OT_gmsh_msh,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == '__main__':
    register()
