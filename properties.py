import bpy
import logging
import math
import mathutils
import os
import bpy.utils.previews
from bpy.types import Panel, PropertyGroup
from . import const
from bpy.props import PointerProperty, StringProperty, CollectionProperty, IntProperty, BoolProperty, IntVectorProperty, FloatVectorProperty, FloatProperty, EnumProperty, BoolVectorProperty
from bpy.app.translations import pgettext

logger = logging.getLogger("vmd_exporter")

# Properties
class VMDBoneProperties(bpy.types.PropertyGroup):
    export = BoolProperty(name="Export", description="Export bone data", default=False)
    mmd_name = StringProperty(name="MMD bone name", description="MMD bone name")
    parent = StringProperty(name="MMD parent bone", description="MMD parent bone")


class VMDArmatureProperties(bpy.types.PropertyGroup):
    file_name = StringProperty(name="File name", description="File name", default="sample")
    active_bone_index = IntProperty()

# UI
class ArmatureButtonsPanel:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return context.armature

class PMXArmaturePanel(ArmatureButtonsPanel, Panel):
    bl_idname = "OBJECT_PT_vmd"
    bl_label = "VMD"

    def draw(self, context):
        arm = context.armature
        vmd_armature_properties = arm.vmd_armature_properties

        layout = self.layout
        layout.template_list("OBJECT_UL_bone_slots", "", arm, "bones", vmd_armature_properties, "active_bone_index", rows=8)

        if len(arm.bones) <= 0:
            return

        bone_names = [bone.name for bone in arm.bones]
        active_bone_name = bone_names[vmd_armature_properties.active_bone_index]
        bone = arm.bones[active_bone_name]
        vmd_bone_properties = bone.vmd_bone_properties

        layout.label(bone.name, translate=False, icon='BONE_DATA')
        layout.prop(vmd_bone_properties, "mmd_name")
        layout.prop_search(vmd_bone_properties, "parent", arm, "bones", icon='CONSTRAINT_BONE')


class OBJECT_UL_bone_slots(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        vmd_bone_properties = item.vmd_bone_properties
        column = layout.column()
        column.label(item.name, translate=False, icon='BONE_DATA')

        if vmd_bone_properties.mmd_name:
            column = layout.column()
            column.label(text="", icon='FORWARD')

            icon = 'BONE_DATA' if not vmd_bone_properties.parent else 'CONSTRAINT_BONE'
            column = layout.column()
            column.label(vmd_bone_properties.mmd_name, translate=False, icon=icon)

        column = layout.column()
        column.alignment = 'RIGHT'
        column.prop(vmd_bone_properties, "export", text="")

    def invoke(self, context, event):
        pass

translations = {
    "ja_JP": {
        ("*", "MMD bone name"): "MMDボーン名",
        ("*", "MMD parent bone"): "親ボーン",
    }
}

def register():
    bpy.types.Bone.vmd_bone_properties = PointerProperty(type=VMDBoneProperties)
    bpy.types.Armature.vmd_armature_properties = PointerProperty(type=VMDArmatureProperties)
    bpy.app.translations.register(__name__, translations)

def unregister():
    bpy.app.translations.unregister(__name__)
    del bpy.types.Armature.vmd_armature_properties
    del bpy.types.Bone.vmd_bone_properties
