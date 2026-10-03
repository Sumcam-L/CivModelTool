"""把 Blender Action 的骨骼动画数据读成 NexusBuddy 需要的结构。"""
import math
import re

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

from .civ6_data import Array, BoneData, Dictionary, Single

# Blender 的 slot 显示名默认跟随它绑定的 ID（这里是骨架对象）。
# 但自己建 slot 时它会保持成 "Slot_" 开头的自定义名，
# 那种名字只是 slot 的命名，不是骨架名，去掉前缀才是目标骨架。
SLOT_NAME_PREFIX = "Slot_"


def resolve_skeleton_name(slot_name):
    """把动画 slot 的显示名解析成目标骨架对象名。"""
    if slot_name.startswith(SLOT_NAME_PREFIX) and len(slot_name) > len(SLOT_NAME_PREFIX):
        return slot_name[len(SLOT_NAME_PREFIX):]
    return slot_name


def read_action_data(action_name):
    action = bpy.data.actions.get(action_name)
    if not action:
        return None

    SCALE = 100.0
    cs_root = Dictionary[str, Dictionary[str, BoneData]]()

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
                arm_name = resolve_skeleton_name(slot_name)
                arm_obj = bpy.data.objects.get(arm_name)
                if (not arm_obj or arm_obj.type != 'ARMATURE') and arm_name != slot_name:
                    # 去前缀后找不到骨架，退回原名再试一次，
                    # 免得真有骨架就叫 "Slot_xxx" 时反而导不出来。
                    arm_name = slot_name
                    arm_obj = bpy.data.objects.get(arm_name)
                if not arm_obj or arm_obj.type != 'ARMATURE':
                    continue

                # 键名必须是骨架对象名，模型侧的世界骨就是用对象名写的，
                # 两边不一致动画绑不到模型上。
                slot_name = arm_name
                cs_bones_dict = Dictionary[str, BoneData]()
                cs_root[slot_name] = cs_bones_dict

                pose_bones = arm_obj.pose.bones
                rest_bones = arm_obj.data.bones

                # 找 root bone（无父骨）
                root_bone = next((b for b in rest_bones if b.parent is None), None)
                if root_bone is None:
                    continue

                
                # 预提取每根骨骼的通道
                group_channels = {}
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
