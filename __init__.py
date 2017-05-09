bl_info= {
    "name": "VMD Exporter",
    "author": "Takosuke",
    "version": (0, 0, 1),
    "blender": (2, 78, 0),
    "location": "Properties",
    "description": "Export VMD file.",
    "support": "COMMUNITY",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": 'Object'}

if "bpy" in locals():
    import imp
    imp.reload(properties)
    imp.reload(exporter)
    imp.reload(const)
    imp.reload(logutils)
else:
    from . import properties, exporter, const, logutils

import bpy
import logging

logger = logging.getLogger("vmd_exporter")

def register():
    bpy.utils.register_module(__name__)
    properties.register()

def unregister():
    properties.unregister()
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()
