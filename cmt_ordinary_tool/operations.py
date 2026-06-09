import bpy
from .utils import *

class CMT_OT_RemoveEmptyVG(bpy.types.Operator):
    bl_idname = "cmt.ot_ot_removeemptyvertexgroups"
    bl_label = "删除空顶点组"
    bl_description ="删除没有分配任何顶点的顶点组"
    def execute(self, context):
        obj = context.object
        if obj and obj.type == "MESH":
            # 调用删除空顶点组的函数
            for obj in bpy.context.selected_objects:
                remove_empty_vertex_groups(obj)
        else:
            self.report({"WARNING"}, "请选中一个网格物体")
        return {"FINISHED"}


class CMT_OT_RemoveUnbindingVG(bpy.types.Operator):
    bl_idname = "cmt.ot_ot_removenotbindinggroups"
    bl_label = "删除无绑定组"
    bl_description ="删除包含顶点,但是所有顶点的权重皆为零的顶点组"
    
    def execute(self, context):
        obj = context.object
        if obj and obj.type == "MESH":
            for obj in bpy.context.selected_objects:
                remove_unbinding_groups(obj)
        else:
            self.report({"WARNING"}, "请选中一个网格物体")
        return {"FINISHED"}


class CMT_OT_RemoveZeroVGInVertex(bpy.types.Operator):
    bl_idname = "cmt.ot_ot_removegroupfromvertexs"
    bl_label = "清理顶点空绑定"
    bl_description ="删除顶点中的为权重为零的绑定"
    
    def execute(self, context):
        obj = context.object
        if obj and obj.type == "MESH":
            for obj in bpy.context.selected_objects:
                remove_group_from_vertexs(obj)
        else:
            self.report({"WARNING"}, "请选中一个网格物体")
        return {"FINISHED"}


class CMT_OT_RemoveEmptyMaterial(bpy.types.Operator):
    bl_idname = "cmt.ot_ot_removeemptymaterialslots"
    bl_label = "清理空材质"
    bl_description ="删除所有选中物体的所有未使用材质槽"
    
    def execute(self, context):
        selected_objects = [
            obj for obj in bpy.context.selected_objects if obj.type == "MESH"
        ]
        for obj in selected_objects:

            bpy.context.view_layer.objects.active = obj

            bpy.ops.object.material_slot_remove_unused()

        return {"FINISHED"}


class CMT_OT_RemoveEmptyShapeKeys(bpy.types.Operator):
    bl_idname = "cmt.ot_ot_removeemptyshapekeys"
    bl_label = "删除空形态键"
    bl_description = "删除不影响网格的形态键（保留基础形态键）"
    
    def execute(self, context):
        obj = context.object
        if obj and obj.type == "MESH":
            total_removed = 0
            for obj in bpy.context.selected_objects:
                if obj.type == "MESH":
                    removed = remove_empty_shape_keys(obj)
                    total_removed += removed
            
            if total_removed > 0:
                self.report({"INFO"}, f"已删除 {total_removed} 个空形态键")
            else:
                self.report({"INFO"}, "没有找到空形态键")
        else:
            self.report({"WARNING"}, "请选中一个网格物体")
        return {"FINISHED"}
