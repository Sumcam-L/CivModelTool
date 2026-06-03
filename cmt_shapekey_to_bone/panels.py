import bpy

class CMT_S2B_PT_Panel(bpy.types.Panel):
    bl_label = "型态键转骨"
    bl_idname = "CMT_S2B_PT_Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Civ6ModelTool"
    
    @staticmethod
    def draw_covertion_options(layout, context) -> None:
        data = context.scene.CMT.S2BSettings
        box = layout.box()
        box.label(text = "自动转换",icon= "FRAME_NEXT")
        column = box.column()
        column.use_property_split = True
        column.prop(data,"TargetMesh")
        column.prop(data,"CurrentArmature")
        column.prop(data,"ParentBone")
        column.prop(data,"AbandonmentRate")
        column.prop(data,"ActionName")
        column.prop(data,"WeightSharing")
        column.prop(data,"UseExistAction")
        column1 = box.column()
        column1.enabled = bool(data.TargetMesh and data.CurrentArmature)
        column1.operator("cmt.s2b_ot_convert", text="转换动画")
        column1.operator(
            "cmt.s2b_ot_clearshapekey", text="卸载形态键动画并恢复形态键"
        )
            
    @staticmethod
    def draw_separation_options(layout, context) -> None:
        data = context.scene.CMT.S2BSettings
        box = layout.box()
        box.label(text = "分割模型",icon= "OUTLINER_OB_MESH")
        
        column = box.column()
        column.use_property_split = True
        column.prop(data,"MaxBones")
        column1 = box.column()
        column1.enabled = data.TargetMesh!=None
        column1.operator("cmt.s2b_ot_autoseparatemesh", text="自动分割模型")
        column2 = box.column()
        column2.enabled = context.mode == "EDIT_MESH"
        column2.operator("cmt.s2b_ot_editseparatemesh", text="分割模型（编辑模式）")
    # 自定义界面布局
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        self.draw_covertion_options(layout,context)
        self.draw_separation_options(layout,context)