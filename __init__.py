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

logger = logging.getLogger(const.ADDON_NAME)

if not logger.handlers:
    hdlr = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)-7s %(asctime)s %(message)s (%(funcName)s)", datefmt="%H:%M:%S")
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.DEBUG) # DEBUG, INFO, WARNING, ERROR, CRITICAL

logger.debug("init logger") # debug, info, warning, error, critical

def register():
    bpy.utils.register_module(__name__)
    properties.register()

def unregister():
    properties.unregister()
    bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()
