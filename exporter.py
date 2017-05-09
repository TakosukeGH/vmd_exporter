import bpy
import collections
import configparser
import datetime
import mathutils
import os
import struct

class VmdExporter():

	# config file prop
	config_file_name = "config.ini"
	Section = collections.namedtuple("Section", "config bone bone_isolated")
	section = Section("config", "bone", "bone_isolated")
	ConfigKey = collections.namedtuple("ConfigKey", "folder file")
	config_key = ConfigKey("folder", "file")
	config_section_bone = []
	config_section_bone_with_constraints = []
	config_section_bone_isolated = {}
	export_bone_number = 0

	# vmd data prop
	ipo_list = []
	path = None
	meta = "Vocaloid Motion Data 0002"
	name = ""

	# internal data struct
	BonePair = collections.namedtuple("BonePair", "child parent")

	# option
	frame_offset = 0
	option_marker_mode = False
	option_export_log = True

	# log text
	log = []

	def __init__(self):
		self.scene = bpy.context.scene
		self.timeline_markers = bpy.context.scene.timeline_markers
		self.obj = bpy.context.active_object
		self.arm = None

		# export prop
		self.frame_start = scene.frame_start
		self.frame_end = scene.frame_end
		self.frame_size = frame_end - frame_start + 1
		self.scale = 1.0 / 0.2
		self.joint_opt = False

	def execute(self):
		self.export_vmd()
		if self.option_export_log:
			if self.path is not None:
				self.export_log()

	def export_vmd(self):
		if self.check() is False: return
		if self.get_config() is False: return
		self.init_ipo_list()

		with open(self.path, "wb") as file:
			self.write_str(file, 30, self.meta)
			self.write_str(file, 20, self.name)
			self.export_all_bone_data(file)
			self.write_long(file, 0) # 表情キーフレーム数
			self.write_long(file, 0) # カメラキーフレーム数
			self.write_long(file, 0) # 照明キーフレーム数
			self.write_long(file, 0) # セルフ影キーフレーム数
			self.write_long(file, 0) # モデル表示・IK on/offキーフレーム数

	def check(self):
		if self.obj is None:
			self.print_all('can not find object')
			return False

		if self.obj.type != 'ARMATURE':
			self.print_all('selected object is not armature : ' + self.obj.type)
			return False

		if self.obj.mode == 'EDIT':
			self.print_all('selected object is edit mode')
			return False

		self.arm = self.obj.pose
		# オブジェクト名じゃなくアーマチュア名を使用
		self.name = self.obj.data.name

		if self.arm is None:
			self.print_all('can not find armature')
			return False

		if self.config_file_name not in bpy.context.blend_data.texts:
			self.print_all('can not find config file : name=' + self.config_file_name)
			return False

		print("check process : OK")
		return True

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

	def get_config(self):
		text = bpy.context.blend_data.texts[self.config_file_name]
		config = configparser.ConfigParser(allow_no_value=True)
		config.optionxform = str

		try:
			config.read_string(text.as_string())
		except Exception as ex:
			print("read config file error : " + str(ex))
			return False

		# セクション存在確認
		for section_name in self.section:
			if section_name not in config.sections():
				print("can not find section : " + section_name)
				return False

		# configセクション取得
		folder = config[self.section.config][self.config_key.folder]
		file = config[self.section.config][self.config_key.file]

		if not folder:
			print("can not find folder")
			return False
		if not file:
			print("can not find file")
			return False

		# フォルダ権限チェック
		if os.access(folder, os.W_OK) is False:
			print("permission denied : " + folder)
			return False

		# if os.path.exists(folder) is False:
		# 	os.makedirs(folder)

		self.path = os.path.join(folder, file)
		self.print_all("export file path : " + self.path)

		# ボーン名取得
		self.config_section_bone = config[self.section.bone]
		self.config_section_bone_isolated = config[self.section.bone_isolated]

		# セクション間重複チェック
		bone_names_all = list(self.config_section_bone.keys()) + list(self.config_section_bone_isolated.keys())
		if self.check_duplicate(bone_names_all) is False: return False

		# ボーン存在確認
		if self.check_bone_exist(self.config_section_bone) is False: return False
		if self.check_bone_exist(self.config_section_bone_isolated) is False: return False
		if self.check_bone_exist(self.config_section_bone_isolated.values()) is False: return False

		self.export_bone_number = len(bone_names_all)
		self.print_all("export bone number : " + str(self.export_bone_number))

		print("get config process : OK")
		return True

	def check_bone_exist(self, bone_names):
		for bone_name in bone_names:
			if bone_name not in self.arm.bones:
				self.print_all("can not find bone : " + bone_name)
				return False

		return True

	def check_duplicate(self, name_list):
		names_tmp = set()
		duplicated_names = [x for x in name_list if x in names_tmp or names_tmp.add(x)]
		if len(duplicated_names) > 0:
			for name in duplicated_names:
				self.print_all("duplicate name exists : " + name)

			return False

		return True

	def export_all_bone_data(self, file):
		if self.option_marker_mode:
			export_markers = [marker for marker in self.timeline_markers if (self.frame_start <= marker.frame and marker.frame <= self.frame_end)]
			self.write_long(file, len(export_markers) * self.export_bone_number)
		else:
			self.write_long(file, self.frame_size * self.export_bone_number)

		if self.export_bone_number <= 0: return # 出力するボーンが無い場合は、出力フレーム数(0)だけ出力して終了

		# データ出力するボーンをリスト化
		export_bones = []
		export_bones_isolated = []

		for bone_name in self.config_section_bone:
			export_bones.append(self.arm.bones[bone_name])
		for bone_name in self.config_section_bone_isolated:
			export_bones_isolated.append(self.BonePair(self.arm.bones[bone_name], self.arm.bones[self.config_section_bone_isolated[bone_name]]))

		export_marker_frame = []
		if self.option_marker_mode:
			export_marker_frame = [marker.frame for marker in self.timeline_markers if (self.frame_start <= marker.frame and marker.frame <= self.frame_end)]

		for i in range(self.frame_start, self.frame_end + 1):
			if self.option_marker_mode:
				if i not in export_marker_frame:
					self.print_all("skip bone frame : " + str(i))
					continue

			self.scene.frame_set(i)
			self.print_all("export bone frame : " + str(self.scene.frame_current))

			for bone in export_bones:
				self.export_bone_data(file, i, bone)
			for bone_pair in export_bones_isolated:
				self.export_bone_data_isolated(file, i, bone_pair)

	def export_bone_data(self, file, frame, bone):
		mat_edit_bone_local_inv = bone.bone.matrix_local.inverted()

		location_local = bone.matrix.to_translation()
		offset = bone.bone.matrix_local.to_translation()
		location_mmd =  location_local - offset
		quaternion_mmd = (bone.matrix * mat_edit_bone_local_inv).to_quaternion()

		if bone.parent is not None:
			bone_parent = bone.parent
			mat_edit_bone_local_inv_parent = bone_parent.bone.matrix_local.inverted()

			location_local = (bone.parent.matrix.inverted() * bone.matrix).to_translation() * bone.parent.bone.matrix_local.inverted()
			offset = (bone.parent.bone.matrix_local.inverted() * bone.bone.matrix_local).to_translation() * bone.parent.bone.matrix_local.inverted()
			location_mmd =  location_local - offset

			quaternion_parent = (bone_parent.matrix * mat_edit_bone_local_inv_parent).to_quaternion()
			quaternion_mmd = quaternion_parent.rotation_difference(quaternion_mmd)

		self.write_bone_data(file, bone.name, frame, location_mmd, quaternion_mmd)

	def export_bone_data_isolated(self, file, frame, bone_pair):
		bone_child = bone_pair.child
		quaternion_child = (bone_child.matrix * bone_child.bone.matrix_local.inverted()).to_quaternion()

		bone_parent = bone_pair.parent
		quaternion_parent = (bone_parent.matrix * bone_parent.bone.matrix_local.inverted()).to_quaternion()

		quaternion_mmd = quaternion_parent.rotation_difference(quaternion_child)

		location_mmd = None
		if self.joint_opt:
			location_mmd = mathutils.Vector((0.0, 0.0, 0.0))
		else:
			location_local = (bone_parent.matrix.inverted() * bone_child.matrix).to_translation() * bone_parent.bone.matrix_local.inverted()
			offset = (bone_parent.bone.matrix_local.inverted() * bone_child.bone.matrix_local).to_translation() * bone_parent.bone.matrix_local.inverted()
			location_mmd =  location_local - offset

		self.write_bone_data(file, bone_child.name, frame, location_mmd, quaternion_mmd)

	def write_bone_data(self, file, name, frame, vector, quaternion):
		self.print_log(name + " : " + str(vector) + " : " + str(quaternion))

		self.write_bone_name(file, name) # ボーン名
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

	def write_bone_name(self, file, name):
		barray = bytearray(self.change_bone_name_to_mmd(name).encode('shift_jis'))
		self.write_bytearray(file, 15, barray)

	def write_str(self, file, array_size, str):
		barray = bytearray(str.encode('shift_jis'))
		self.write_bytearray(file, array_size, barray)

	def write_bytearray(self, file, array_size, barray):
		ba_base = bytearray(array_size)
		ba_base[:len(barray)] = barray
		file.write(ba_base)

	def change_bone_name_to_mmd(self, name):
		if name.endswith(".L"):
			return "左" + name[:-2]
		elif name.endswith(".R"):
			return "右" + name[:-2]
		else:
			return name

	def print_log(self, str):
		self.log.append(str)

	def print_all(self, str):
		print(str)
		self.print_log(str)

	def export_log(self):
		with open(self.path + ".log", "w", encoding="utf-8") as log:
			for line in self.log:
				print(line, sep=' : ', file=log)
