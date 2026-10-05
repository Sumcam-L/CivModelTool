"""把 Blender Action 的骨骼动画数据读成 NexusBuddy 需要的结构。

组装 Dictionary<int, float[]> 的动作放在 C# 侧（exportAnimationFlat）：
逐条跨 pythonnet 边界写一次要几十微秒，长动画里大部分时间都花在封送而
不是导出上。这里只算矩阵、把结果摊成连续的 float 列表交过去。
"""
import math
import re

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

from .civ6_data import Array, Single

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
    """返回 (slotNames, boneNames, boneFrameCounts, frameStart, loc, rot, sca)。

    boneNames 是每个 slot 一组骨骼名的锯齿列表，boneFrameCounts 是对应的
    每根骨骼帧数（0 表示这根骨骼没有解析到真实骨骼，对应一个空 BoneData）。
    loc/rot/sca 是扁平 float 列表，按 slot-major、bone-major、frame-major 排布。
    """
    action = bpy.data.actions.get(action_name)
    if not action:
        return None

    SCALE = 100.0

    frame_start = int(action.frame_range[0])
    frame_end = int(action.frame_range[1]) + 1
    # 除 frame_start..frame_end 外最后再多写一帧，内容是前一帧的拷贝。
    frames_per_bone = frame_end - frame_start + 2

    rotMat_x90 = Matrix.Rotation(math.radians(-90), 4, 'X')
    rotMat_y90 = Matrix.Rotation(math.radians(-90), 4, 'Y')
    P = Matrix.Rotation(math.radians(-120), 4, Vector([1, 1, 1]))
    P_inv = P.inverted()

    slot_names = []
    bone_names = []
    bone_counts = []
    locations = []
    rotations = []
    scales = []

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
                slot_names.append(slot_name)
                names_in_slot = []
                counts_in_slot = []
                bone_names.append(names_in_slot)
                bone_counts.append(counts_in_slot)

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

                for bone_name in sorted(group_channels):
                    channels = group_channels[bone_name]
                    pb = pose_bones.get(bone_name)
                    rb = rest_bones.get(bone_name)
                    if pb is None or rb is None:
                        # 通道对应的骨骼不在骨架上，留一个空 BoneData。
                        names_in_slot.append(bone_name)
                        counts_in_slot.append(0)
                        continue

                    # 与帧无关的量提到帧循环外。
                    bone_local = rb.matrix_local.copy()
                    if rb.parent:
                        transferMat = Matrix.Identity(4)
                        parentbone_local = rb.parent.matrix_local.copy()
                        parentbone_local.invert()
                    else:
                        transferMat = rotMat_y90 @ rotMat_x90 @ rotMat_x90
                        parentbone_local = Matrix.Identity(4)

                    has_rot_e = any(channels["rot_e"])
                    has_rot_q = any(channels["rot_q"])
                    loc_ch = channels["loc"]
                    rot_e_ch = channels["rot_e"]
                    rot_q_ch = channels["rot_q"]
                    sca_ch = channels["sca"]

                    for f in range(frame_start, frame_end + 1):
                        loc = [c.evaluate(f) if c else 0.0 for c in loc_ch]

                        if has_rot_e:
                            e = [c.evaluate(f) if c else 0.0 for c in rot_e_ch]
                            rot_q = Euler(e, 'XYZ').to_quaternion()
                        elif has_rot_q:
                            qv = [c.evaluate(f) if c else (1.0 if i == 0 else 0.0)
                                  for i, c in enumerate(rot_q_ch)]
                            rot_q = Quaternion((qv[0], qv[1], qv[2], qv[3]))
                        else:
                            rot_q = Quaternion((1.0, 0.0, 0.0, 0.0))

                        sca = [c.evaluate(f) if c else 1.0 for c in sca_ch]
                        action_mat = Matrix.LocRotScale(Vector(loc), rot_q, Vector(sca))

                        if rb.parent:
                            relative_m = P @ parentbone_local @ bone_local @ action_mat @ P_inv
                        else:
                            blender_transform = bone_local @ action_mat @ rotMat_x90
                            relative_m = blender_transform @ transferMat

                        loc_w, rot_w, sca_w = relative_m.decompose()

                        locations.append(loc_w.x * SCALE)
                        locations.append(loc_w.y * SCALE)
                        locations.append(loc_w.z * SCALE)
                        rotations.append(rot_w.x)
                        rotations.append(rot_w.y)
                        rotations.append(rot_w.z)
                        rotations.append(rot_w.w)
                        scales.append(sca_w.x)
                        scales.append(sca_w.y)
                        scales.append(sca_w.z)

                    # 收尾帧复用前一帧的值。
                    locations.extend(locations[-3:])
                    rotations.extend(rotations[-4:])
                    scales.extend(scales[-3:])

                    names_in_slot.append(bone_name)
                    counts_in_slot.append(frames_per_bone)

    return (slot_names, bone_names, bone_counts, frame_start,
            locations, rotations, scales)


def to_native_arrays(payload):
    """把 read_action_data 的结果摊成 pythonnet 能一次收下的 .NET 数组。"""
    if payload is None:
        return None
    slot_names, bone_names, bone_counts, frame_start, loc, rot, sca = payload
    return (Array[str](slot_names),
            Array[Array[str]](bone_names),
            Array[Array[int]](bone_counts),
            frame_start,
            Array[Single](loc),
            Array[Single](rot),
            Array[Single](sca))
