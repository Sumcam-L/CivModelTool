"""顶点组的公共处理。不在导入期 import bpy，保证可在 Blender 外测试。"""


def empty_vertex_group_indices(obj):
    """没有分配任何顶点的顶点组下标（升序）；非网格对象返回空列表。"""
    if obj.type != "MESH":
        return []
    groups = {r: None for r in range(len(obj.vertex_groups))}
    for vert in obj.data.vertices:
        for vg in vert.groups:
            i = vg.group
            if i in groups:
                del groups[i]
    return [k for k in groups]


def remove_empty_vertex_groups(obj):
    """删除空顶点组；是否忽略锁定由 CMT.OTSettings.DeleteLockGroup 决定。"""
    import bpy

    vertex_groups = obj.vertex_groups
    ignore_lock = bpy.context.scene.CMT.OTSettings.DeleteLockGroup
    for i in sorted(empty_vertex_group_indices(obj), reverse=True):
        if ignore_lock or not vertex_groups[i].lock_weight:
            vertex_groups.remove(vertex_groups[i])
