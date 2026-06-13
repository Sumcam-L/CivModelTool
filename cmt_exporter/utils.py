import bpy


from pathlib import Path
from mathutils import Euler

import os
import json
from xml.dom.minidom import parse
import xml.dom.minidom
import re
import sys

# 添加依赖库路径到sys.path
libs_path = os.path.join(os.path.dirname(__file__), "libs")
if libs_path not in sys.path:
    sys.path.append(libs_path)
    
import clr 
import System
from System.Collections.Generic import Dictionary
from System import Array, Single

def is_dll_loaded(dll_name):
    """
    检查指定名称的DLL是否已加载
    dll_name: DLL文件名（如 "Firaxis.Utility"）
    """
    loaded_assemblies = System.AppDomain.CurrentDomain.GetAssemblies()
    for assembly in loaded_assemblies:
        if assembly.GetName().Name == dll_name:
            return True
    return False


dll_directory = os.path.dirname(__file__) + r"\dependencies"
dlls_to_check = [
    "Firaxis.Utility",
    "Firaxis.Granny", 
    "Firaxis.Granny.Impl",
    "CivNexus6"
]

firstLoad = False

# 检查哪些DLL已加载
for dll in dlls_to_check:
    if is_dll_loaded(dll):
        print(f"{dll} 已加载")
    else:
        firstLoad = True
        print(f"{dll} 未加载")
        # 如果未加载，则加载它
        clr.AddReference(dll_directory + rf"\{dll}.dll")

#加载DSGInfo
g_DSG_json = None
with open(str(Path(os.path.dirname(__file__),"assets","DSGs.json")), 'r') as file:
    g_DSG_json = json.load(file)

#加载DSG
g_DSGs_action = {}
for tClass in g_DSG_json["Classes"]:
    for dsg in g_DSG_json[tClass]:
        dsg_path = str(Path(os.path.dirname(__file__),"assets",dsg+".dsg"))
        dom = xml.dom.minidom.parse(dsg_path)
        collection = dom.documentElement
        for line in collection.getElementsByTagName("m_AnimationSlots")[0].childNodes:
            if line.nodeType == xml.dom.Node.ELEMENT_NODE:
                if dsg not in g_DSGs_action:
                    g_DSGs_action[dsg] = []
                g_DSGs_action[dsg].append(line.getAttribute("text"))

#加载materialinfo
g_Mat_json = None
with open(str(Path(os.path.dirname(__file__),"assets","MaterialInfo.json")), 'r') as file:
    g_Mat_json = json.load(file)

g_Texture_ExtraReferenceTable = {
    
}


from NexusBuddy.FileOps import CN6FileOps,BoneData,AstInfo


def get_geotype_items(self,context):
    geoClasses = ["DecalGeometry","LandmarkModel","LandmarkObstructionProfile","Leader","Leader_ShadowVolume","UILensModel","Unit","VFXModel","WonderMovieModel"]
    # geoClasses.sort()
    items = []
    for tClass in geoClasses:
        items.append((tClass,tClass,""))
    return items


def get_anmtype_items(self,context):
    anmClasses = ["CameraAnimation","Landmark","Leader","Unit","VFX","WonderMovie"]
    # geoClasses.sort()
    items = []
    for tClass in anmClasses:
        items.append((tClass,tClass,""))
    return items

def get_parent_armature(obj):
    """获取对象的父级骨架"""
    if obj.parent and obj.parent.type == 'ARMATURE':
        return obj.parent
    return None

def copy_pg(src,dst):
    for prop in src.bl_rna.properties:
        id = prop.identifier

        # 跳过内置属性
        if id == "rna_type":
            continue

        # 跳过只读属性
        if prop.is_readonly:
            continue
        try:
            setattr(dst, id, getattr(src, id))
        except Exception as e:
            print(f"跳过 {id}: {e}")

def get_geo_files(self,context):
    items = []
    for property in self.GeoList:
        items.append((property.FileName, property.FileName, ""))
    return items

def geo_index_update(self,context):
    self.GeoName = self.GeoList[self.CurrentGeoIndex].FileName
    
def ast_index_update(self,context):
    self.AstName = self.AstList[self.CurrentAstIndex].FileName

def geo_filename_update(self,context):
    for index, geoInstance in enumerate(self.GeoList):
        if geoInstance.FileName == self.GeoName:
            self.CurrentGeoIndex = index
    self.GeoClass = self.GeoList[self.CurrentGeoIndex].Class

def geo_class_update(self,context):
    data = context.scene.CMT.ExporterSettings
    data.GeoList[data.CurrentGeoIndex].Class = data.GeoClass

def get_ast_files(self,context):
    data = context.scene.CMT.ExporterSettings
    items = []
    # ("None", "None", "")
    for property in data.AstList:
        items.append((property.FileName, property.FileName, ""))
    return items

def get_astgeometries_items(self,context):
    data = context.scene.CMT.ExporterSettings
    items = []
    # ("None", "None", "")
    for property in data.GeoList:
        items.append((property.FileName, property.FileName, ""))
    return items


def ast_filename_update(self,context):
    data = context.scene.CMT.ExporterSettings
    
    for index, astInstance in enumerate(data.AstList):
        if astInstance.FileName == data.AstName:
            data.CurrentAstIndex = index


def ast_class_update(self,context):
    data = context.scene.CMT.ExporterSettings
    data.AstList[data.CurrentAstIndex].Class = data.AstClass

def ast_dsg_update(self,context):
    anmList = self.Animations
    anmList.clear()
    if len(anmList) == 0:
        for v in g_DSGs_action[self.DSG]:
            item = self.Animations.add()
            item.AstName = self.FileName
            item.text = v
            


def project_path_update(self,context):
    def draw(self, context):
        self.layout.label(text="项目路径不正确，请确保资产文件夹已生成（启动一次AssetEditor）")

    data = context.scene.CMT.ExporterSettings
    if data.ProjectPath != "":
        path = Path(data.ProjectPath)
        projName = path.name
        if Path(path / "Assets").exists():
            return 
        elif Path(path / projName / "Assets").exists():
            return
        else:
            data.ProjectPath = ""
            context.window_manager.popup_menu(draw, title="提示", icon='ERROR')
            
def customscript_path_update(self,context):
    def draw(self, context):
        self.layout.label(text="请选择Python脚本")

    data = context.scene.CMT.ExporterSettings
    if data.TxtCustomExportScript != "":
        extension = str(Path(data.ProjectPath).suffix)
        if extension != ".py":
            data.TxtCustomExportScript = ""
            context.window_manager.popup_menu(draw, title="提示", icon='ERROR')

def getAbsPathByImage(mat,target):
    for node in mat.node_tree.nodes:
        
        if node.type == "TEX_IMAGE":
            if node.image.name == target:
                return os.path.normpath(bpy.path.abspath(node.image.filepath))

def get_ast_class_items(self,context):
    items = []
    for lClass in g_DSG_json["Classes"]:
        items.append((lClass,lClass,""))
    return items
    
    
            
def get_ast_DSG_items(self,context):
    data = context.scene.CMT.ExporterSettings
    curAst = data.AstList[data.CurrentAstIndex]
    items = []
    for lDSG in g_DSG_json[curAst.Class]:
        items.append((lDSG,lDSG,""))
    return items



def get_material_class_items(self,context):
    items = []
    for v in g_Mat_json:
        items.append((v,v,""))
    return items

def get_material_items(self,context):
    data = context.scene.CMT.ExporterSettings
    items = []
    refGeos = []
    for ast in data.AstList:
        for geo in ast.Geometries:
            refGeos.append(geo.FileName)
    for geo in data.GeoList:
        if geo.FileName in refGeos:
            for prop in geo.Geometries:
                for mat in prop.value.data.materials:
                    items.append((mat.name,mat.name,""))
    return items
def mat_poll(self,obj):
    data = self
    refGeos = []
    ojbs = bpy.data.objects
    for ast in data.AstList:
        for geo in ast.Geometries:
            refGeos.append(geo.value)
    for geo in data.GeoList:
        if geo.FileName in refGeos:
            for prop in geo.Geometries:
                for mat in prop.value.data.materials:
                    if mat is obj:
                        return True
    return False
def matlist_refresh(self, context):
    data = context.scene.CMT.ExporterSettings
    mats = bpy.data.materials
    
    # 获取符合条件的材质列表
    matlist = [mat for mat in mats if mat_poll(data, mat)]
    matNames = [mat.name for mat in matlist]
    # 先清理不存在的材质
    for i in range(len(data.MaterialList) - 1, -1, -1):
        if data.MaterialList[i].FileName not in matNames:
            data.MaterialList.remove(i)
            
    # 获取已存在的材质名称集合
    existing_names = {v.FileName for v in data.MaterialList}
    
    # 只添加不存在的材质
    for mat in matlist:
        if mat.name not in existing_names:
            item = data.MaterialList.add()
            item.FileName = mat.name
        
            
                

def mat_name_update(self,context):
    mats = bpy.data.materials
    
    # 获取符合条件的材质列表
    matlist = [mat for mat in mats if mat_poll(self, mat)]
    for i, mat in enumerate(matlist):
        if mat is self.MaterialName:
            self.CurrentMatIndex = i
            break
    matlist_refresh(self,context)

def export_material_update(self,context):
    
    matlist_refresh(self,context)
            
def get_real_project_path(self,context):
    data = context.scene.CMT.ExporterSettings
    if data.ProjectPath != "":
        path = Path(data.ProjectPath)
        projName = path.name
        if Path(path / "Assets").exists():
            return str(path.absolute())
        elif Path(path / projName / "Assets").exists():
            return str(Path(path / projName).absolute())
    
    return ""

def export_artdef_update(self,context):
    if len(self.ArtdefList) == 0:
        for i in range(len(get_artdef_items(self,context))):
            self.ArtdefList.add()
            

def get_artdef_items(self,context):
    return [("Units.artdef","Units.artdef","Units.artdef"),
               ("Leaders.artdef","Leaders.artdef","Leaders.artdef")]
def artdef_name_update(self,context):
    items = get_artdef_items(self,context)
    index = next(i for i,x in enumerate(items) if x[0] == self.ArtdefName)
    self.CurrentArtdefIndex = index

def get_textures_by_material(mat):
    if mat is None or not mat.use_nodes or mat.node_tree is None:
        return {}

    def _find_image_from_socket(socket, visited_sockets, visited_nodes):
        if socket is None:
            return None
        if socket in visited_sockets:
            return None
        visited_sockets.add(socket)

        for link in socket.links:
            from_socket = link.from_socket
            from_node = link.from_node
            image = _find_image_from_node(from_node, visited_sockets, visited_nodes)
            if image is not None:
                return image
            image = _find_image_from_socket(from_socket, visited_sockets, visited_nodes)
            if image is not None:
                return image
        return None

    def _find_image_from_node(node, visited_sockets, visited_nodes):
        if node is None:
            return None
        if node in visited_nodes:
            return None
        visited_nodes.add(node)

        if node.type == "TEX_IMAGE":
            return node.image

        for input_socket in node.inputs:
            image = _find_image_from_socket(input_socket, visited_sockets, visited_nodes)
            if image is not None:
                return image
        return None

    result = {}
    for node in mat.node_tree.nodes:
        if node.type != "BSDF_PRINCIPLED":
            continue

        for input_socket in node.inputs:
            image = _find_image_from_socket(input_socket, set(), set())
            result[input_socket.name] = os.path.normpath(bpy.path.abspath(image.filepath)) if image else None
        break

    return result


from mathutils import Vector, Quaternion
from mathutils import Matrix
import math


def compress_texture_resolution(image, scale=0.5, output_path=None, max_width=4096, max_height=4096, min_width=4, min_height=4, require_pow2=True, require_square=False):
    """
    按倍率压缩贴图分辨率并保存

    image: Blender Image对象或图片路径
    scale: 缩放倍率 (0.5 = 一半, 0.25 = 四分之一)
    output_path: 输出路径，默认为原路径覆盖
    max_width/max_height: 最大尺寸
    min_width/min_height: 最小尺寸
    require_pow2: 是否需要2的幂次
    require_square: 是否需要正方形
    返回: 输出文件路径
    """
    import time
    total_start = time.time()
    if isinstance(image, str):
        image = bpy.data.images.load(image)
        is_loaded = False
    else:
        is_loaded = True
    scale = float(scale)
    orig_width, orig_height = image.size[0], image.size[1]
    width = int(orig_width * scale)
    height = int(orig_height * scale)
    
    if require_pow2:
        width = nearest_pow2(width)
        height = nearest_pow2(height)

    width = max(min_width, min(max_width, width))
    height = max(min_height, min(max_height, height))

    if require_square:
        size = max(width, height)
        width = size
        height = size

    if output_path is None:
        output_path = bpy.path.abspath(image.filepath)

    resized = image.copy()
    resized.scale(width, height)
    resized.filepath_raw = output_path
    resized.file_format = 'PNG'
    resized.save()

    if not is_loaded:
        bpy.data.images.remove(image)
    bpy.data.images.remove(resized)

    total_elapsed = time.time() - total_start
    print(f"压缩贴图耗时: {total_elapsed:.2f}s")
    return output_path


def nearest_pow2(value):
    """返回最接近的2的幂次值"""
    if value <= 0:
        return 1
    p = 1
    while p < value:
        p *= 2
    if p > 1 and abs(p - value) > abs(p // 2 - value):
        p //= 2
    return max(1, p)


def extract_packed_textures_to_file(input_path, output_dir=None):
    """
    从打包贴图文件提取所有贴图并保存

    input_path: 输入图片路径
    output_dir: 输出目录，默认为同目录
    返回: dict {"normal": path, "metallic": path, "gloss": path}
    """
    import time
    total_start = time.time()
    p = Path(input_path)
    if output_dir is None:
        output_dir = str(p.parent)

    image = bpy.data.images.load(input_path)
    width, height = image.size[0], image.size[1]
    pixels = list(image.pixels)

    print(f"源图: {input_path}, 尺寸: {width}x{height}")

    name_map = {"normal": "Normal", "metallic": "Metallic", "gloss": "Gloss"}
    result = {}

    for key, suffix in name_map.items():
        start = time.time()
        out_path = str(Path(output_dir) / (p.stem + f"_{suffix}" + p.suffix))
        img = bpy.data.images.new(p.stem + f"_{suffix}", width=width, height=height, alpha=True)
        img.colorspace_settings.name = 'Non-Color'

        if key == "normal":
            out_pixels = [0.0] * (width * height * 4)
            for i in range(width * height):
                idx = i * 4
                r, g = pixels[idx], pixels[idx+1]
                nx = r * 2.0 - 1.0
                ny = (1.0 - g) * 2.0 - 1.0
                nz = math.sqrt(max(0.0, 1.0 - nx*nx - ny*ny))
                out_pixels[idx] = nx * 0.5 + 0.5
                out_pixels[idx+1] = ny * 0.5 + 0.5
                out_pixels[idx+2] = nz * 0.5 + 0.5
                out_pixels[idx+3] = 1.0
        elif key == "metallic":
            out_pixels = [0.0] * (width * height * 4)
            for i in range(width * height):
                idx = i * 4
                b = pixels[idx+2]
                out_pixels[idx] = b
                out_pixels[idx+1] = b
                out_pixels[idx+2] = b
                out_pixels[idx+3] = 1.0
        else:
            out_pixels = [0.0] * (width * height * 4)
            for i in range(width * height):
                idx = i * 4
                gloss = 1 - pixels[idx+3]
                out_pixels[idx] = gloss
                out_pixels[idx+1] = gloss
                out_pixels[idx+2] = gloss
                out_pixels[idx+3] = 1.0

        img.pixels = out_pixels
        img.filepath_raw = out_path
        img.file_format = 'PNG'
        img.save()
        elapsed = time.time() - start
        print(f"已保存: {out_path} ({elapsed:.2f}s)")
        result[key] = out_path
        bpy.data.images.remove(img)

    bpy.data.images.remove(image)
    total_elapsed = time.time() - total_start
    print(f"分解鸣潮法线贴图耗时: {total_elapsed:.2f}s")
    return result
def create_mat(loc,rot,sca):
    return Matrix.LocRotScale(Vector(loc), rot, Vector(sca))

def read_action_data(action_name):
    action = bpy.data.actions.get(action_name)
    if not action:
        return None

    SCALE = 100.0
    cs_root = Dictionary[str, Dictionary[str, BoneData]]()

    # frame_start = int(bpy.context.scene.frame_start)
    # frame_end = int(bpy.context.scene.frame_end)
    frame_start = int(action.frame_range[0])
    frame_end = int(action.frame_range[1]) + 1
    
    rotMat_x90 = Matrix.Rotation(math.radians(-90), 4, 'X')
    rotMat_y90 = Matrix.Rotation(math.radians(-90), 4, 'Y')
    for layer in action.layers:
        for strip in layer.strips:
            if strip.type != 'KEYFRAME':
                continue

            for bag in strip.channelbags:

                
                slot_name = bag.slot.name_display
                cs_bones_dict = Dictionary[str, BoneData]()
                cs_root[slot_name] = cs_bones_dict

                arm_obj = bpy.data.objects.get(slot_name)
                if not arm_obj or arm_obj.type != 'ARMATURE':
                    continue
                pose_bones = arm_obj.pose.bones
                rest_bones = arm_obj.data.bones

                # 找 root bone（无父骨）
                root_bone = next((b for b in rest_bones if b.parent is None), None)
                if root_bone is None:
                    continue

                root_local = root_bone.matrix_local.copy()
                root_local_inv = root_local.inverted()
                
                # 预提取每根骨骼的通道
                group_channels = {}
                # for group in bag.groups:
                #     channels = {
                #         "loc": [None] * 3,
                #         "rot_e": [None] * 3,
                #         "rot_q": [None] * 4,
                #         "sca": [None] * 3
                #     }
                    
                #     for c in group.channels:
                        
                #         path = c.data_path
                #         idx = c.array_index
                #         if "location" in path:
                #             channels["loc"][idx] = c
                #         elif "rotation_euler" in path:
                #             channels["rot_e"][idx] = c
                #         elif "rotation_quaternion" in path:
                #             channels["rot_q"][idx] = c
                #         elif "scale" in path:
                #             channels["sca"][idx] = c
                #     group_channels[group.name] = channels
                for f in bag.fcurves:
                    channels = {
                        "loc": [None] * 3,
                        "rot_e": [None] * 3,
                        "rot_q": [None] * 4,
                        "sca": [None] * 3
                    }
                    
                    
                    path = f.data_path
                    idx = f.array_index
                    temp = re.search(r'\["(.*?)"\]', path)
                    if temp:
                        boneName = temp.group(1)
                        if boneName in group_channels:
                            channels = group_channels[boneName]
                        if "location" in path:
                            channels["loc"][idx] = f
                        elif "rotation_euler" in path:
                            channels["rot_e"][idx] = f
                        elif "rotation_quaternion" in path:
                            channels["rot_q"][idx] = f
                        elif "scale" in path:
                            channels["sca"][idx] = f
                        group_channels[boneName] = channels

                for bone_name in sorted(group_channels.keys()):
                    cs_bones_dict[bone_name] = BoneData()

                for f in range(frame_start, frame_end + 2):
                    if f == frame_end + 1:
                        for bone_name in group_channels.keys():
                            cs_bone = cs_bones_dict[bone_name]
                            cs_bone.location[f] = cs_bone.location[f - 1]
                            cs_bone.rotation[f] = cs_bone.rotation[f - 1]
                            cs_bone.scale[f] = cs_bone.scale[f - 1]
                        continue

                    # 先算所有骨骼的 action matrix（TRS）
                    action_mats = {}
                    for bone_name, channels in group_channels.items():
                        loc = [c.evaluate(f) if c else 0.0 for c in channels["loc"]]
                        
                        if any(channels["rot_e"]):
                            e = [c.evaluate(f) if c else 0.0 for c in channels["rot_e"]]
                            rot_q = Euler(e, 'XYZ').to_quaternion()
                        elif any(channels["rot_q"]):
                            qv = [c.evaluate(f) if c else (1.0 if i == 0 else 0.0) for i, c in enumerate(channels["rot_q"])]
                            rot_q = Quaternion((qv[0], qv[1], qv[2], qv[3]))
                        else:
                            rot_q = Quaternion((1.0, 0.0, 0.0, 0.0))

                        sca = [c.evaluate(f) if c else 1.0 for c in channels["sca"]]
                        action_mats[bone_name] = Matrix.LocRotScale(Vector(loc), rot_q, Vector(sca))

                    # 再按公式算世界矩阵并分解
                    for bone_name in group_channels.keys():
                        cs_bone = cs_bones_dict[bone_name]
                        pb = pose_bones.get(bone_name)
                        rb = rest_bones.get(bone_name)
                        if pb is None or rb is None:
                            continue
                        
                        parentbone_local = Matrix.Identity(4)
                        bone_local = rb.matrix_local.copy()
                        transferMat = rotMat_y90 @ rotMat_x90 @ rotMat_x90 
                        
                        if rb.parent:
                            transferMat = Matrix.Identity(4)

                            parentbone_local = rb.parent.matrix_local.copy()
                            parentbone_local.invert()

                        transferMat_inv = transferMat.inverted()
                        
                        P = Matrix.Rotation(math.radians(-120), 4, Vector([1,1,1]))
                        P_inv = P.inverted()
                        
                        relative_m = None
                        if rb.parent:
                            relative_m =  P @ parentbone_local @ bone_local    @ action_mats[bone_name] @ P_inv
                        else:
                            blender_transform = bone_local  @ action_mats[bone_name] @ rotMat_x90
                            relative_m =   blender_transform @ transferMat
                            
                        loc_w, rot_w, sca_w = relative_m.decompose()   

                        cs_bone.location[f] = Array[Single]([
                            float(loc_w.x * SCALE),
                            float(loc_w.y * SCALE),
                            float(loc_w.z * SCALE)
                        ])
                        cs_bone.rotation[f] = Array[Single]([
                             float(rot_w.x), float(rot_w.y), float(rot_w.z),float(rot_w.w)
                        ])
                        cs_bone.scale[f] = Array[Single]([
                            float(sca_w.x), float(sca_w.y), float(sca_w.z)
                        ])

    return cs_root
def clean_xml(doc):
    """清理XML中的空白文本节点"""
    for node in doc.childNodes:
        if node.nodeType == node.TEXT_NODE:
            if node.nodeValue.strip() == "":
                node.nodeValue = ""
        # 递归处理子节点
        if node.hasChildNodes():
            clean_xml(node)
def save_xml(doc, filepath, indent="  "):
    """完全重新格式化XML，无多余空白"""
    # 获取根元素
    root = doc.documentElement
    
    def format_node(node, level=0):
        """递归格式化节点"""
        indent_str = indent * level
        
        # 开始标签
        attrs = ""
        if node.attributes:
            attrs = " " + " ".join([f'{k}="{v}"' for k, v in node.attributes.items()])
        
        result = [f"{indent_str}<{node.tagName}{attrs}>"]
        
        # 处理子节点
        has_text = False
        for child in node.childNodes:
            if child.nodeType == child.TEXT_NODE:
                text = child.nodeValue.strip()
                if text:
                    # 有文本内容
                    result.append(f"{indent_str}{indent}{text}")
                    has_text = True
            elif child.nodeType == child.ELEMENT_NODE:
                result.extend(format_node(child, level + 1))
        
        # 结束标签
        result.append(f"{indent_str}</{node.tagName}>")
        
        return result
    
    # 生成格式化后的XML
    lines = ['<?xml version="1.0" encoding="utf-8"?>']
    lines.extend(format_node(root))
    
    # 保存
    with open(filepath, "w", encoding="utf-8") as f:
        f.write('\n'.join(lines))

def get_bins_template(bin,group,culture,assetname):
    return f"""<Element>
				<m_Fields>
					<m_Values/>
				</m_Fields>
				<m_ChildCollections>
					<Element>
						<m_CollectionName text="Groups"/>
						<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
						<Element>
							<m_Fields>
								<m_Values/>
							</m_Fields>
							<m_ChildCollections>
								<Element>
									<m_CollectionName text="Cultures"/>
									<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
									<Element>
										<m_Fields>
											<m_Values>
												<Element class="AssetObjects..ArtDefReferenceValue">
													<m_ElementName text=""/>
													<m_RootCollectionName text="UnitTintTypes"/>
													<m_ArtDefPath text=""/>
													<m_CollectionIsLocked>true</m_CollectionIsLocked>
													<m_TemplateName text=""/>
													<m_ParamName text="Tint"/>
												</Element>
											</m_Values>
										</m_Fields>
										<m_ChildCollections>
											<Element>
												<m_CollectionName text="Assets"/>
												<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
												<Element>
													<m_Fields>
														<m_Values>
															<Element class="AssetObjects..BLPEntryValue">
																<m_EntryName text="{assetname}"/>
																<m_XLPClass text="Unit"/>
																<m_XLPPath text="units.xlp"/>
																<m_BLPPackage text="units/units"/>
																<m_LibraryName text="Unit"/>
																<m_ParamName text="Asset"/>
															</Element>
															<Element class="AssetObjects..FloatValue">
																<m_fValue>1.000000</m_fValue>
																<m_ParamName text="Scale"/>
															</Element>
														</m_Values>
													</m_Fields>
													<m_ChildCollections/>
													<m_Name text="asset1"/>
													<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
												</Element>
											</Element>
										</m_ChildCollections>
										<m_Name text="{culture}"/>
										<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
									</Element>
								</Element>
							</m_ChildCollections>
							<m_Name text="{group}"/>
							<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
						</Element>
					</Element>
				</m_ChildCollections>
				<m_Name text="{bin}"/>
				<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
			</Element>"""
def get_members_template(MemberType,BinPath):
    return f"""<Element>
				<m_Fields>
					<m_Values>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text="Warrior"/>
							<m_RootCollectionName text="UnitMovementTypes"/>
							<m_ArtDefPath text="Units.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text="Units"/>
							<m_ParamName text="Movement"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text="WarriorCombat"/>
							<m_RootCollectionName text="MemberCombat"/>
							<m_ArtDefPath text="Units.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text="Units"/>
							<m_ParamName text="Combat"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text="DEFAULT"/>
							<m_RootCollectionName text="MaterialTypes"/>
							<m_ArtDefPath text="VFX.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text="VFX"/>
							<m_ParamName text="VFXMaterialType"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text="DEFAULT"/>
							<m_RootCollectionName text="MaterialTypes"/>
							<m_ArtDefPath text="VFX.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text="VFX"/>
							<m_ParamName text="VFXWeaponImpact"/>
						</Element>
						<Element class="AssetObjects..FloatValue">
							<m_fValue>0.000000</m_fValue>
							<m_ParamName text="ImpactHeightOverride"/>
						</Element>
					</m_Values>
				</m_Fields>
				<m_ChildCollections>
					<Element>
						<m_CollectionName text="Cultures"/>
						<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
						<Element>
							<m_Fields>
								<m_Values/>
							</m_Fields>
							<m_ChildCollections>
								<Element>
									<m_CollectionName text="Variations"/>
									<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
									<Element>
										<m_Fields>
											<m_Values>
												<Element class="AssetObjects..FloatValue">
													<m_fValue>1.000000</m_fValue>
													<m_ParamName text="Scale"/>
												</Element>
												<Element class="AssetObjects..BoolValue">
													<m_bValue>false</m_bValue>
													<m_ParamName text="IsAttachment"/>
												</Element>
											</m_Values>
										</m_Fields>
										<m_ChildCollections>
											<Element>
												<m_CollectionName text="Attachments"/>
												<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
												<Element>
													<m_Fields>
														<m_Values>
															<Element class="AssetObjects..StringValue">
																<m_Value text="Root"/>
																<m_ParamName text="Point"/>
															</Element>
															<Element class="AssetObjects..ArtDefReferenceValue">
																<m_ElementName text=""/>
																<m_RootCollectionName text="UnitTintTypes"/>
																<m_ArtDefPath text=""/>
																<m_CollectionIsLocked>true</m_CollectionIsLocked>
																<m_TemplateName text=""/>
																<m_ParamName text="Tint"/>
															</Element>
														</m_Values>
													</m_Fields>
													<m_ChildCollections>
														<Element>
															<m_CollectionName text="Bins"/>
															<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
															<Element>
																<m_Fields>
																	<m_Values/>
																</m_Fields>
																<m_ChildCollections/>
																<m_Name text="{BinPath}"/>
																<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
															</Element>
														</Element>
													</m_ChildCollections>
													<m_Name text="Body"/>
													<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
												</Element>
											</Element>
										</m_ChildCollections>
										<m_Name text="A"/>
										<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
									</Element>
								</Element>
							</m_ChildCollections>
							<m_Name text="Any"/>
							<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
						</Element>
					</Element>
				</m_ChildCollections>
				<m_Name text="{MemberType}"/>
				<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
			</Element>"""
   
def get_units_template(UnitType,MemberType):
    return f"""<Element>
				<m_Fields>
					<m_Values>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text="Warrior"/>
							<m_RootCollectionName text="UnitFormationTypes"/>
							<m_ArtDefPath text="Units.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text="Units"/>
							<m_ParamName text="Formation"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text="Warrior"/>
							<m_RootCollectionName text="UnitCombat"/>
							<m_ArtDefPath text="Units.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text="Units"/>
							<m_ParamName text="UnitCombat"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text="Warrior"/>
							<m_RootCollectionName text="UnitFormationTypes"/>
							<m_ArtDefPath text="Units.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text="Units"/>
							<m_ParamName text="EscortFormation"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text=""/>
							<m_RootCollectionName text="Units"/>
							<m_ArtDefPath text="Units.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text=""/>
							<m_ParamName text="EmbarkedUnit"/>
						</Element>
						<Element class="AssetObjects..BoolValue">
							<m_bValue>false</m_bValue>
							<m_ParamName text="DoNotDisplayCharges"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text=""/>
							<m_RootCollectionName text="UnitCulture"/>
							<m_ArtDefPath text="Cultures.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text=""/>
							<m_ParamName text="Culture"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text=""/>
							<m_RootCollectionName text="Era"/>
							<m_ArtDefPath text="Eras.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text=""/>
							<m_ParamName text="Era"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text=""/>
							<m_RootCollectionName text="Units"/>
							<m_ArtDefPath text="Units.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text=""/>
							<m_ParamName text="ProxyUnit"/>
						</Element>
						<Element class="AssetObjects..BoolValue">
							<m_bValue>false</m_bValue>
							<m_ParamName text="PlayDeathOnDestroy"/>
						</Element>
						<Element class="AssetObjects..IntValue">
							<m_nValue>0</m_nValue>
							<m_ParamName text="DisplayLevel"/>
						</Element>
					</m_Values>
				</m_Fields>
				<m_ChildCollections>
					<Element>
						<m_CollectionName text="Members"/>
						<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
						<Element>
							<m_Fields>
								<m_Values>
									<Element class="AssetObjects..FloatValue">
										<m_fValue>1.000000</m_fValue>
										<m_ParamName text="Scale"/>
									</Element>
									<Element class="AssetObjects..IntValue">
										<m_nValue>1</m_nValue>
										<m_ParamName text="Count"/>
									</Element>
									<Element class="AssetObjects..ArtDefReferenceValue">
										<m_ElementName text="{MemberType}"/>
										<m_RootCollectionName text="UnitMemberTypes"/>
										<m_ArtDefPath text="Units.artdef"/>
										<m_CollectionIsLocked>true</m_CollectionIsLocked>
										<m_TemplateName text="Units"/>
										<m_ParamName text="Type"/>
									</Element>
								</m_Values>
							</m_Fields>
							<m_ChildCollections/>
							<m_Name text="Member1"/>
							<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
						</Element>
					</Element>
					<Element>
						<m_CollectionName text="Audio"/>
						<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
					</Element>
					<Element>
						<m_CollectionName text="AttachmentVisibility"/>
						<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
					</Element>
				</m_ChildCollections>
				<m_Name text="{UnitType}"/>
				<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
			</Element>"""