import bpy
import bmesh
def get_empyt_count(obj):
    if obj.type != "MESH":
        return 0
    vertex_groups = obj.vertex_groups
    groups = {r: None for r in range(len(vertex_groups))}
    for vert in obj.data.vertices:
        for vg in vert.groups:
            i = vg.group
            if i in groups:
                del groups[i]

    return len(groups)


# 获取与顶点组匹配的骨骼数量
def get_bone_binding_count(obj):
    if obj.type != "MESH":
        return 0

    # 查找骨骼修改器
    for modifier in obj.modifiers:
        if modifier.type == "ARMATURE":
            armature = modifier.object
            if armature and armature.type == "ARMATURE":
                # 获取骨骼数据
                bones = armature.data.bones
                vertex_groups = obj.vertex_groups

                # 统计顶点组名称与骨骼名称相同的数量
                count = 0
                for vgroup in vertex_groups:
                    if vgroup.name in bones:
                        count += 1
                return count
    return 0


# 删除空的顶点组
def remove_empty_vertex_groups(obj):

    vertex_groups = obj.vertex_groups
    groups = {r: None for r in range(len(vertex_groups))}
    armature = obj.parent
    for vert in obj.data.vertices:
        for vg in vert.groups:
            i = vg.group
            if i in groups:
                del groups[i]

    lis = [k for k in groups]
    lis.sort(reverse=True)
    for i in lis:
        if (
            True
            if bpy.context.scene.CMT.OTSettings.DeleteLockGroup
            else not vertex_groups[i].lock_weight
        ):
            vertex_groups.remove(vertex_groups[i])


def remove_unbinding_groups(obj):
    try:
        vertex_groups = obj.vertex_groups
        armature = obj.parent
        for group in vertex_groups:
            if group.name not in armature.data.bones:
                if (
                    True
                    if bpy.context.scene.Civ6_DeleteLockGroup
                    else not group.lock_weight
                ):
                    vertex_groups.remove(vertex_groups[group.index])
    except:
        pass


def remove_group_from_vertexs(obj):

    vertex_groups = obj.vertex_groups
    for vert in obj.data.vertices:
        for g in obj.data.vertices[vert.index].groups:
            if g.weight <= 0.001:
                vertex_groups[g.group].remove([vert.index])
                
def get_bind_count():
    obj = bpy.context.active_object

    mesh = bmesh.from_edit_mesh(obj.data)

    groups = {
        obj.vertex_groups[g.group].name: 1
        for v in mesh.verts
        for g in obj.data.vertices[v.index].groups
        if v.select
    }

    for modifier in obj.modifiers:
        if modifier.type == "ARMATURE":
            armature = modifier.object
            if armature and armature.type == "ARMATURE":
                # 获取骨骼数据
                bones = armature.data.bones

                # 统计顶点组名称与骨骼名称相同的数量
                count = 0
                for gName in groups.keys():
                    if gName in bones:
                        count += 1
                return count
            return None


def remove_empty_shape_keys(obj, threshold=0.0001):
    """删除物体上的空形态键（不影响网格的形态键）"""
    if obj.type != "MESH":
        return 0
    
    # 检查是否有形态键
    if not obj.data.shape_keys:
        return 0
    
    # 获取基础形态键
    basis_key = obj.data.shape_keys.key_blocks[0]
    removed_count = 0
    
    # 从后往前遍历，避免删除时索引变化
    for i in range(len(obj.data.shape_keys.key_blocks) - 1, 0, -1):
        key = obj.data.shape_keys.key_blocks[i]
        
        # 跳过基础形态键
        if key.name == "Basis":
            continue
        
        # 检查是否所有顶点位置都与基础形态键相同
        is_empty = True
        for j in range(len(key.data)):
            basis_co = basis_key.data[j].co
            key_co = key.data[j].co
            
            # 计算距离
            diff = (key_co - basis_co).length
            if diff > threshold:
                is_empty = False
                break
        
        # 如果是空形态键，则删除
        if is_empty:
            obj.shape_key_remove(key)
            removed_count += 1
    
    return removed_count
