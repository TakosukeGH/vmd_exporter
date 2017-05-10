import bpy
import collections
import configparser
import datetime
import mathutils
import os
import struct
import logging
from . import const

logger = logging.getLogger(const.ADDON_NAME)

class VmdExporter(bpy.types.Operator):
    bl_idname = "vmd.exporter"
    bl_label = "Export VMD"

    # vmd data prop
    ipo_list = []

    # internal data struct
    BonePair = collections.namedtuple("BonePair", "child parent")

    # log text
    log = []

    def __init__(self):
        self.scene = bpy.context.scene
        self.timeline_markers = self.scene.timeline_markers
        self.obj = bpy.context.object
        self.arm = bpy.context.armature
        self.pose = self.obj.pose

        self.export_bones = [self.pose.bones[bone.name] for bone in self.arm.bones if bone.vmd_bone_properties.export]

        vmd_armature_properties = self.arm.vmd_armature_properties

        self.use_marker_mode = vmd_armature_properties.use_marker_mode
        self.frame_start = vmd_armature_properties.frame_start
        self.frame_end = vmd_armature_properties.frame_end
        if vmd_armature_properties.use_marker_mode:
            self.marker_frames = [marker.frame for marker in self.timeline_markers if (self.frame_start <= marker.frame and marker.frame <= self.frame_end)]
            self.frame_size = len(marker_frames)
        else:
            self.frame_size = self.frame_end - self.frame_start + 1

        self.frame_offset = vmd_armature_properties.frame_offset
        self.scale = vmd_armature_properties.scale

        self.export_folder = bpy.path.abspath(vmd_armature_properties.export_folder)
        self.file_name = vmd_armature_properties.file_name

        # TODO: 謎のプロパティ
        self.joint_opt = False

    def invoke(self, context, event):
        self.export_vmd()

        return {"FINISHED"}

    def export_vmd(self):
        if self.check_data() is False: return
        self.init_ipo_list()
        self.init_path()

        with open(self.path, "wb") as file:
            self.write_str(file, 30, const.META)
            self.write_str(file, 20, self.arm.name)
            self.export_all_bone_data(file)
            self.write_long(file, 0) # 表情キーフレーム数
            self.write_long(file, 0) # カメラキーフレーム数
            self.write_long(file, 0) # 照明キーフレーム数
            self.write_long(file, 0) # セルフ影キーフレーム数
            self.write_long(file, 0) # モデル表示・IK on/offキーフレーム数

    def check_data(self):
        logger.info("start")

        if len(self.export_bones) <= 0:
            logger.info("export bone size : " + str(len(self.export_bones)))
            return False

        if self.frame_size <= 0:
            logger.info("export frame size : " + str(self.frame_size))
            return False

        if not self.export_folder:
            logger.error("export folder does not exist.")
            return False
        logger.debug("export folder : " + self.export_folder)

        if not self.file_name:
            logger.error("file name does not exist.")
            return False
        logger.debug("file name : " + self.file_name)

        logger.info("end")

    def init_ipo_list(self):
        self.ipo_list = [20] * 2
        self.ipo_list.extend([0] * 2)
        self.ipo_list.extend([20] * 4)
        self.ipo_list.extend([107] * 8)
        self.ipo_list.extend([20] * 7)
        self.ipo_list.extend([107] * 8)
        self.ipo_list.extend([0])
        self.ipo_list.extend([20] * 6)
        self.ipo_list.extend([107] * 8)
        self.ipo_list.extend([0] * 2)
        self.ipo_list.extend([20] * 5)
        self.ipo_list.extend([107] * 8)
        self.ipo_list.extend([0] * 3)

    def init_path(self):
        vmd_armature_properties = self.arm.vmd_armature_properties

        if vmd_armature_properties.use_version:
            major = vmd_armature_properties.version[0]
            minor = vmd_armature_properties.version[1]
            build = vmd_armature_properties.version[2]
            version_map = {"major":major, "minor":minor, "build":build}

            fromat = vmd_armature_properties.version_format

            self.file_name += string.Template(fromat).safe_substitute(version_map)
            logger.debug("file name : " + self.file_name)

        self.path = os.path.join(self.export_folder, self.file_name) + ".pmx"

    def export_all_bone_data(self, file):
        logger.info("start")

        self.write_long(file, self.frame_size * len(self.export_bones))

        # データ出力するボーンをリスト化
        export_bones_isolated = []

        for i in range(self.frame_start, self.frame_end + 1):
            if self.use_marker_mode:
                if i not in self.marker_frames:
                    logger.debug("skip bone frame : " + str(i))
                    continue

            self.scene.frame_set(i)

            for bone in self.export_bones:
                self.export_bone_data(file, i, bone)

        logger.info("end")

    def export_bone_data(self, file, frame, bone_child):

        location_local = bone_child.matrix.to_translation()
        offset = bone_child.bone.matrix_local.to_translation()
        location_mmd =  location_local - offset
        quaternion_mmd = (bone_child.matrix * bone_child.bone.matrix_local.inverted()).to_quaternion()

        vmd_bone_properties = bone_child.bone.vmd_bone_properties
        bone_parent = None
        if vmd_bone_properties.mmd_parent in self.arm.bones:
            bone_parent = self.arm.bones[vmd_bone_properties.mmd_parent]
        elif bone_child.parent is not None:
            bone_parent = bone_child.parent

        if bone_parent:
            location_local = (bone_parent.matrix.inverted() * bone_child.matrix).to_translation() * bone_parent.bone.matrix_local.inverted()
            offset = (bone_parent.bone.matrix_local.inverted() * bone_child.bone.matrix_local).to_translation() * bone_parent.bone.matrix_local.inverted()
            location_mmd =  location_local - offset

            quaternion_parent = (bone_parent.matrix * bone_parent.bone.matrix_local.inverted()).to_quaternion()
            quaternion_mmd = quaternion_parent.rotation_difference(quaternion_mmd)

        self.write_bone_data(file, bone_child.bone, frame, location_mmd, quaternion_mmd)

    def write_bone_data(self, file, bone, frame, vector, quaternion):

        self.write_bone_name(file, bone) # ボーン名
        self.write_long(file, frame + self.frame_offset) # フレーム番号
        self.write_location(file, vector)
        self.write_quaternion(file, quaternion)
        self.write_ipo(file) # 補間

    def write_location(self, file, vector):
        # self.print_all(vector)
        self.write_float(file, vector.x * self.scale)
        self.write_float(file, vector.z * self.scale)
        self.write_float(file, vector.y * self.scale)

    def write_quaternion(self, file, quaternion):
        # self.print_all(quaternion)
        self.write_float(file, -quaternion.x)
        self.write_float(file, -quaternion.z)
        self.write_float(file, -quaternion.y)
        self.write_float(file, quaternion.w)

    def write_ipo(self, file):
        for i in self.ipo_list:
            file.write(struct.pack("b", i))

    def write_float(self, file, float):
        file.write(struct.pack("f", float))

    def write_long(self, file, long):
        # unsigned long(DWORD)
        file.write(struct.pack("L", long))

    def write_int(self, file, int):
        file.write(struct.pack("i", int))

    def write_bone_name(self, file, bone):
        bone_name = bone.name
        if not bone.vmd_bone_properties.mmd_name:
            bone_name = bone.vmd_bone_properties.mmd_name
        barray = bytearray(bone_name.encode('shift_jis'))
        self.write_bytearray(file, 15, barray)

    def write_str(self, file, array_size, str):
        barray = bytearray(str.encode('shift_jis'))
        self.write_bytearray(file, array_size, barray)

    def write_bytearray(self, file, array_size, barray):
        ba_base = bytearray(array_size)
        ba_base[:len(barray)] = barray
        file.write(ba_base)
