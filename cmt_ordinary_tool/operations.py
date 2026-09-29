import bpy

from ..mesh_utils import remove_empty_vertex_groups
from .utils import (
    remove_empty_shape_keys,
    remove_group_from_vertexs,
    remove_unbinding_groups,
)

class CMT_OT_RemoveEmptyVG(bpy.types.Operator):
    bl_idname = "cmt.ot_ot_removeemptyvertexgroups"
    bl_label = "删除空顶点组"
    bl_description ="删除没有分配任何顶点的顶点组"
    def execute(self, context):
        meshes = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not meshes:
            self.report({"WARNING"}, "请选中一个网格物体")
            return {"FINISHED"}

        for obj in meshes:
            remove_empty_vertex_groups(obj)
        return {"FINISHED"}


class CMT_OT_RemoveUnbindingVG(bpy.types.Operator):
    bl_idname = "cmt.ot_ot_removenotbindinggroups"
    bl_label = "删除无绑定组"
    bl_description ="删除包含顶点,但是所有顶点的权重皆为零的顶点组"
    
    def execute(self, context):
        meshes = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not meshes:
            self.report({"WARNING"}, "请选中一个网格物体")
            return {"FINISHED"}

        for obj in meshes:
            remove_unbinding_groups(obj)
        return {"FINISHED"}


class CMT_OT_RemoveZeroVGInVertex(bpy.types.Operator):
    bl_idname = "cmt.ot_ot_removegroupfromvertexs"
    bl_label = "清理顶点空绑定"
    bl_description ="删除顶点中的为权重为零的绑定"
    
    def execute(self, context):
        meshes = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not meshes:
            self.report({"WARNING"}, "请选中一个网格物体")
            return {"FINISHED"}

        for obj in meshes:
            remove_group_from_vertexs(obj)
        return {"FINISHED"}


class CMT_OT_RemoveEmptyMaterial(bpy.types.Operator):
    bl_idname = "cmt.ot_ot_removeemptymaterialslots"
    bl_label = "清理空材质"
    bl_description ="删除所有选中物体的所有未使用材质槽"
    
    def execute(self, context):
        selected_objects = [
            obj for obj in bpy.context.selected_objects if obj.type == "MESH"
        ]
        if not selected_objects:
            self.report({"WARNING"}, "请选中一个网格物体")
            return {"FINISHED"}

        for obj in selected_objects:
            bpy.context.view_layer.objects.active = obj
            # 无材质槽时该算子的 poll() 为 False,直接调用会报 context is incorrect
            if not bpy.ops.object.material_slot_remove_unused.poll():
                continue
            bpy.ops.object.material_slot_remove_unused()

        return {"FINISHED"}


class CMT_OT_RemoveEmptyShapeKeys(bpy.types.Operator):
    bl_idname = "cmt.ot_ot_removeemptyshapekeys"
    bl_label = "删除空形态键"
    bl_description = "删除不影响网格的形态键（保留基础形态键）"
    
    def execute(self, context):
        meshes = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not meshes:
            self.report({"WARNING"}, "请选中一个网格物体")
            return {"FINISHED"}

        total_removed = 0
        for obj in meshes:
            total_removed += remove_empty_shape_keys(obj)

        if total_removed > 0:
            self.report({"INFO"}, f"已删除 {total_removed} 个空形态键")
        else:
            self.report({"INFO"}, "没有找到空形态键")
        return {"FINISHED"}
