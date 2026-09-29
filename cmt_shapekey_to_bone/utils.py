import bpy
from mathutils import Vector

from ..mesh_utils import remove_empty_vertex_groups


def get_bone_items(self, context):
    items = []
    armature = context.scene.CMT.S2BSettings.CurrentArmature
    items = [("None", "None", "")]
    if armature and armature.type == "ARMATURE":
        for bone in armature.data.bones:
            items.append((bone.name, bone.name, ""))
    return items

def create_bone_for_vertex(armature, bone_name, rest_position, parentBone):
    bone = armature.data.edit_bones.new(bone_name)
    bone.parent = parentBone
    bone.head = rest_position

    bone.tail = Vector((rest_position.x, rest_position.y + 0.001, rest_position.z))

    # 使骨骼的 roll 方向对齐
    bone.align_roll(Vector((0, 0, 1)))
    return bone


def normalize(mesh, shapekeyVertexIndex, armature, influenced_indices=None):
    temp = -1
    tempGroup = []
    for g in mesh.data.vertices[shapekeyVertexIndex].groups:
        if mesh.vertex_groups[g.group].name in armature.data.bones:
            tempGroup.append(g)
        if "SKB_" in mesh.vertex_groups[g.group].name:
            temp = g.group
    if temp >= 0:
        for groupEle in tempGroup:
            if groupEle.group != temp:
                groupEle.weight = 0
                mesh.vertex_groups[groupEle.group].remove([shapekeyVertexIndex])

    vertex_groups = mesh.vertex_groups
    indices = influenced_indices if influenced_indices else [v.index for v in mesh.data.vertices]
    for idx in indices:
        for g in mesh.data.vertices[idx].groups:
            if g.weight <= 0.001:
                vertex_groups[g.group].remove([idx])

def get_or_create_fcurve(action, bone_name, channel_i, axis_i, data_path):
    if bone_name not in action.groups:
        g = action.groups.new(bone_name)
    g = action.groups[bone_name]

    # 如果已有的通道数量不够，就新增空的通道，直到通道数量满足需要
    while channel_i >= len(g.channels):
        action.fcurves.new("none", index=0, action_group=bone_name)

    # 获得指定通道
    fc = g.channels[channel_i]
    # 如果通道的数据路径不对，直接替换掉原来的
    # TODO 这里写成判断是为了在未来增加警告信息输出，目前没写
    if fc.data_path != data_path:
        fc.data_path = data_path
    if fc.array_index != axis_i:
        fc.array_index = axis_i

    return fc

def changeNormal(obj, normals):
    bpy.context.view_layer.objects.active = obj
    mesh = obj.data
    current_mode = bpy.context.mode
    if current_mode != 'OBJECT':
        bpy.ops.object.mode_set(mode="OBJECT")

    loop_normals = [loop.normal.copy() for loop in mesh.loops]

    for poly in mesh.polygons:
        center = tuple(round(c, 6) for c in poly.center)
        area = round(poly.area, 6)
        normal = tuple(round(n, 6) for n in poly.normal)
        start = poly.loop_start
        total = poly.loop_total
        key = (total, center, area, normal)
        if key in normals:
            for li in range(start, start + total):
                loop_normals[li] = (normals[key][li - start]).copy()

    mesh.normals_split_custom_set(loop_normals)
    mesh.update()

def clamp_dot_product(dot_product):
    """将点积限制在[-1, 1]范围内，避免浮点精度误差"""
    return max(-1.0, min(1.0, dot_product))


def remove_unused_materials_data(obj):
    mesh = obj.data

    used = set()
    for poly in mesh.polygons:
        used.add(poly.material_index)

    for i in reversed(range(len(obj.material_slots))):
        if i not in used:
            obj.active_material_index = i
            bpy.ops.object.material_slot_remove()

def separateSelectedPart(normals):
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.separate(type="SELECTED")
    # # 获取选中的物体
    selected_objects = bpy.context.selected_objects
    # # 获取活动物体
    active_object = bpy.context.active_object
    # # 过滤掉活动物体
    non_active_selected_objects = [
        obj for obj in selected_objects if obj != active_object
    ]

    bpy.ops.object.mode_set(mode="OBJECT")

    for obj1 in non_active_selected_objects:
    # 先设置上下文
        bpy.context.view_layer.objects.active = obj1
        obj1.select_set(True)
        

        changeNormal(obj1, normals)
        remove_empty_vertex_groups(obj1)
        remove_unused_materials_data(obj1)

    bpy.context.view_layer.objects.active = active_object
    changeNormal(active_object, normals)
    remove_empty_vertex_groups(active_object)
    # 无材质槽时该算子的 poll() 为 False,直接调用会报 context is incorrect
    if bpy.ops.object.material_slot_remove_unused.poll():
        bpy.ops.object.material_slot_remove_unused()
