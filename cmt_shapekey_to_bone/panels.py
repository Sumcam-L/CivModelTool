import bpy

class CMT_S2B_UL_ShapeKeyAnimList(bpy.types.UIList):
    bl_idname = "CMT_S2B_UL_ShapeKeyAnimList"

    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        if item.action:
            layout.prop(item, "action", text="", icon="ACTION")

class CMT_S2B_OT_AddShapeKeyAnim(bpy.types.Operator):
    bl_idname = "cmt.s2b_ot_addshapekeyanim"
    bl_label = "添加动作"
    bl_description = "从已有动作中添加需要转换的形态键动画"

    def execute(self, context):
        settings = context.scene.CMT.S2BSettings
        for action in bpy.data.actions:
            has_shape_key_fcurve = any("key_blocks" in fc.data_path for fc in action.fcurves)
            if not has_shape_key_fcurve:
                continue
            if any(item.action == action for item in settings.ShapeKeyAnimList):
                continue
            item = settings.ShapeKeyAnimList.add()
            item.action = action
        return {"FINISHED"}

class CMT_S2B_OT_RemoveShapeKeyAnim(bpy.types.Operator):
    bl_idname = "cmt.s2b_ot_removeshapekeyanim"
    bl_label = "移除形态键"
    bl_description = "从列表中移除选中的形态键"

    def execute(self, context):
        settings = context.scene.CMT.S2BSettings
        index = settings.ShapeKeyAnimListIndex
        if 0 <= index < len(settings.ShapeKeyAnimList):
            settings.ShapeKeyAnimList.remove(index)
            settings.ShapeKeyAnimListIndex = max(0, index - 1)
        return {"FINISHED"}

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
        column.prop(data,"WeightSharing")
        column.prop(data,"DirectionTolerance")

        box2 = box.box()
        box2.label(text="形态键动画列表（留空则转换全部）", icon="ACTION")
        row = box2.row()
        row.template_list("CMT_S2B_UL_ShapeKeyAnimList", "", data, "ShapeKeyAnimList", data, "ShapeKeyAnimListIndex", rows=3)
        col = row.column(align=True)
        col.operator("cmt.s2b_ot_addshapekeyanim", icon="ADD", text="")
        col.operator("cmt.s2b_ot_removeshapekeyanim", icon="REMOVE", text="")

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