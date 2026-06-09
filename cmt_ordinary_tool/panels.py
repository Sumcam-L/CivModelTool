import bpy
from .utils import *
class CMT_OT_PT_Panel(bpy.types.Panel):
    bl_label = "工具"
    bl_idname = "CMT_OT_PT_Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Civ6ModelTool"

    @staticmethod
    def draw_info_panel(self, context) -> None:
        scene = context.scene
        layout = self.layout
        obj = context.object
        
        box = layout.box()
        box.label(text="模型信息",icon = "INFO")
        column = box.column()
        # column.use_property_split = True
        column.label(text="单位模型骨骼绑定限制: 60")
        column.label(text="领袖模型骨骼绑定限制: 256")
        if obj and obj.type == "MESH":
            column.label(text=f"当前物体顶点组数量: {len(obj.vertex_groups)}")
            # 计算与骨骼绑定的次数
            bone_binding_count = get_bone_binding_count(obj)
            if bone_binding_count > 0:
                column.label(text=f"当前物体骨骼绑定数: {bone_binding_count}")
            else:
                column.label(text="无匹配的绑定骨骼")
            empty_count = get_empyt_count(obj)
            column.label(text=f"当前物体空顶点组数量: {empty_count}")
            if bpy.context.mode != "EDIT_MESH":
                column.label(text="当前不处于网格编辑模式")
            else:
                bindCount = get_bind_count()
                if bindCount == None:
                    column.label(text="当前活动物体没有骨架")
                else:
                    column.label(text=f"当前选中部分绑定骨骼数量: {bindCount}")
        else:
            column.label(text="未选中网格物体")
    @staticmethod
    def draw_operation_panel(self, context) -> None:
        data =  context.scene.CMT.OTSettings
        layout = self.layout
        obj = context.object
        
        box = layout.box()
        box.label(text="操作",icon="MODIFIER")
        column = box.column()
        # column.use_property_split = True
        if obj and obj.type == "MESH":
            column.prop(data, "DeleteLockGroup")
            column.operator("cmt.ot_ot_removeemptyvertexgroups", text="删除空顶点组")
            column.operator("cmt.ot_ot_removenotbindinggroups", text="删除零权重顶点组")
            column.operator("cmt.ot_ot_removegroupfromvertexs", text="清理顶点空绑定")
            column.operator("cmt.ot_ot_removeemptymaterialslots", text="清理未使用的材质槽")
            column.operator("cmt.ot_ot_removeemptyshapekeys", text="删除空形态键")
    # 自定义界面布局
    def draw(self, context):
        layout = self.layout
        obj = context.object
        self.draw_info_panel(self,context)
        self.draw_operation_panel(self,context)