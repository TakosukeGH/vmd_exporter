import bpy
import logging
import math
import mathutils
import os
import bpy.utils.previews
from . exporter import VmdExporter
from bpy.types import Panel, PropertyGroup
from . import const
from bpy.props import PointerProperty, StringProperty, CollectionProperty, IntProperty, BoolProperty, IntVectorProperty, FloatVectorProperty, FloatProperty, EnumProperty, BoolVectorProperty
from bpy.app.translations import pgettext

logger = logging.getLogger(const.ADDON_NAME)

# Properties
class VMDBoneProperties(bpy.types.PropertyGroup):
    export = BoolProperty(name="Export", description="Export bone data", default=False)
    mmd_name = StringProperty(name="MMD bone name", description="MMD bone name")
    mmd_parent = StringProperty(name="MMD parent bone", description="MMD parent bone")

class VMDArmatureProperties(bpy.types.PropertyGroup):
    def frame_start_update_event(self, context):
        if self.frame_start > self.frame_end:
            self.frame_end = self.frame_start

    def frame_end_update_event(self, context):
        if self.frame_start > self.frame_end:
            self.frame_start = self.frame_end

    property_type = EnumProperty(
        name="Property type",
        items=(('0', "Base Settings", ""),('1', "Expanded Settings", ""),('2', "Bone Settings", ""))
    )

    export_folder = StringProperty(name="Export folder", subtype='DIR_PATH', description="Export path")
    file_name = StringProperty(name="File name", description="File name", default="sample")
    frame_start = IntProperty(name="Start", default=1, update=frame_start_update_event)
    frame_end = IntProperty(name="End", default=60, update=frame_end_update_event)
    use_marker_mode = BoolProperty(name="Use merker mode", description="Use merker mode", default=False)
    scale = FloatProperty(name="Location scale", default=1.0/0.2)
    frame_offset = IntProperty(name="Frame offset", default=0)
    use_version = BoolProperty(name="Use version", description="Use version", default=False)
    auto_increment = BoolProperty(name="Auto increment version number", description="Auto increment version number", default=False)
    version_format = StringProperty(name="Version format", description="Version format", default="-${major}.${minor}.${build}")
    version = IntVectorProperty(name="Version", description="Version", min=0)
    active_bone_index = IntProperty()

# Operator
class VMDBoneSlotsActions(bpy.types.Operator):
    bl_idname = "vmd.bone_slots_actions"
    bl_label = "List Action"

    action = EnumProperty(items=(('ALL', "All", ""),('CLEAR', "Clear", "")))

    def invoke(self, context, event):
        arm = context.armature

        if self.action == 'ALL':
            for bone in arm.bones:
                bone.vmd_bone_properties.export = True
        elif self.action == 'CLEAR':
            for bone in arm.bones:
                bone.vmd_bone_properties.export = False

        return {"FINISHED"}

class SetMMDBoneNameAction(bpy.types.Operator):
    bl_idname = "vmd.set_mmd_bone_name"
    bl_label = "Convert L/R to Japanese"

    def invoke(self, context, event):
        arm = context.armature
        for bone in arm.bones:
            if bone.name.endswith("_L") or bone.name.endswith(".L"):
                bone.vmd_bone_properties.mmd_name = "左" + bone.name[:-2]
            elif bone.name.endswith("_R") or bone.name.endswith(".R"):
                bone.vmd_bone_properties.mmd_name = "右" + bone.name[:-2]

        return {"FINISHED"}

class ClearMMDBoneNameAction(bpy.types.Operator):
    bl_idname = "vmd.clear_mmd_bone_name"
    bl_label = "Clear all mmd bone name"

    def invoke(self, context, event):
        arm = context.armature
        for bone in arm.bones:
            bone.vmd_bone_properties.mmd_name = ""

        return {"FINISHED"}

class DATA_PT_bone_slots_specials(bpy.types.Menu):
    bl_label = "Bone Slots Specials"

    def draw(self, context):
        layout = self.layout
        layout.operator(SetMMDBoneNameAction.bl_idname, text=pgettext(SetMMDBoneNameAction.bl_label), icon='SORTALPHA')
        layout.operator(ClearMMDBoneNameAction.bl_idname, text=pgettext(ClearMMDBoneNameAction.bl_label), icon='SORTALPHA')

# UI
class ArmatureButtonsPanel:
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    @classmethod
    def poll(cls, context):
        return context.armature

class PMXArmaturePanel(ArmatureButtonsPanel, Panel):
    bl_idname = "DATA_PT_vmd"
    bl_label = "VMD Exporter"

    def draw(self, context):
        arm = context.armature
        vmd_armature_properties = arm.vmd_armature_properties
        layout = self.layout
        layout.prop(vmd_armature_properties, "property_type", expand=True)
        if vmd_armature_properties.property_type == "2":
            self.draw_bone_slots(context)
        else:
            self.draw_export(context)

    def draw_export(self, context):
        arm = context.armature
        vmd_armature_properties = arm.vmd_armature_properties
        layout = self.layout

        row = layout.row()
        if not vmd_armature_properties.export_folder:
            row.alert = True
        row.prop(vmd_armature_properties, "export_folder")
        row = layout.row()
        if not vmd_armature_properties.file_name:
            row.alert = True
        row.prop(vmd_armature_properties, "file_name")

        if vmd_armature_properties.property_type == "1":
            layout.prop(vmd_armature_properties, "use_marker_mode")

        row = layout.row(align=True)
        row.prop(vmd_armature_properties, "frame_start")
        row.prop(vmd_armature_properties, "frame_end")

        if vmd_armature_properties.property_type == "1":
            layout.prop(vmd_armature_properties, "frame_offset")
            layout.prop(vmd_armature_properties, "scale")
            self.draw_version(layout, vmd_armature_properties)

        row = layout.row(align=True)
        row.operator(VmdExporter.bl_idname, text=pgettext(VmdExporter.bl_label))
        row.scale_y = 1.5

        if not vmd_armature_properties.export_folder or not vmd_armature_properties.file_name:
            row.enabled = False


        if len(arm.bones) <= 0:
            layout.enabled = False

    def draw_version(self, layout, properties):
            box = layout.box()
            row = box.row()
            row.prop(properties, "use_version")
            column = row.column()
            column.prop(properties, "auto_increment")
            column.enabled = properties.use_version

            row = box.row()
            row.prop(properties, "version_format")
            row.enabled = properties.use_version

            split = box.split(percentage=1.0/3.0)
            split.label("Version")
            row = split.row()
            row.prop(properties, "version", text="")
            split.enabled = properties.use_version

    def draw_bone_slots(self, context):
        arm = context.armature
        vmd_armature_properties = arm.vmd_armature_properties
        layout = self.layout

        row = layout.row()
        row.template_list("OBJECT_UL_bone_slots", "", arm, "bones", vmd_armature_properties, "active_bone_index", rows=8)

        col = row.column(align=True)
        col.operator(VMDBoneSlotsActions.bl_idname, icon='CHECKBOX_HLT', text="").action = 'ALL'
        col.operator(VMDBoneSlotsActions.bl_idname, icon='CHECKBOX_DEHLT', text="").action = 'CLEAR'
        col.menu("DATA_PT_bone_slots_specials", icon='DOWNARROW_HLT', text="")

        if len(arm.bones) <= 0:
            return
        if len(arm.bones) <= vmd_armature_properties.active_bone_index:
            return

        bone_names = [bone.name for bone in arm.bones]
        active_bone_name = bone_names[vmd_armature_properties.active_bone_index]
        bone = arm.bones[active_bone_name]
        vmd_bone_properties = bone.vmd_bone_properties

        layout.label(bone.name, translate=False, icon='BONE_DATA')
        layout.prop(vmd_bone_properties, "mmd_name")
        row = layout.row()
        if bone.name == vmd_bone_properties.mmd_parent:
            logger.debug(vmd_bone_properties.mmd_parent)
        row.prop_search(vmd_bone_properties, "mmd_parent", arm, "bones", icon='CONSTRAINT_BONE')


class OBJECT_UL_bone_slots(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        vmd_bone_properties = item.vmd_bone_properties
        column = layout.column()
        column.label(item.name, translate=False, icon='BONE_DATA')

        if vmd_bone_properties.mmd_name:
            column = layout.column()
            column.label(text="", icon='RIGHTARROW_THIN')

            icon = 'BONE_DATA' if not vmd_bone_properties.mmd_parent else 'CONSTRAINT_BONE'
            column = layout.column()
            column.label(vmd_bone_properties.mmd_name, translate=False, icon=icon)

        column = layout.column()
        column.alignment = 'RIGHT'
        column.prop(vmd_bone_properties, "export", text="")

    def invoke(self, context, event):
        pass

translations = {
    "ja_JP": {
        # Armature
        ("*", "Base Settings"): "基本設定",
        ("*", "Expanded Settings"): "拡張設定",
        ("*", "Use version"): "バージョンNo.を使う",
        ("*", "Auto increment version number"): "自動更新",
        ("*", "Version format"): "フォーマット形式",
        ("*", "Export folder"): "エクスポートフォルダ",
        ("*", "Use merker mode"): "マーカーモードを使用",
        ("*", "Frame offset"): "フレームオフセット",
        ("*", "Location scale"): "スケール",
        # Bone Slots
        ("*", "MMD bone name"): "MMDボーン名",
        ("*", "MMD parent bone"): "MMD親ボーン",
        ("*", "Convert L/R to Japanese"): "L/R を 左/右 に変換",
        ("*", "Clear all mmd bone name"): "MMDボーン名を全てクリア",
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
