import bpy
from .utils import g_DSGs_action
from .properties import CMT_Exporter_Settings,CMT_Exporter_PG_AstAnimationProperty

class CMT_Exporter_PT_Panel(bpy.types.Panel):
    bl_label = "导出fgx"
    bl_idname = "CMT_Exporter_PT_Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Civ6ModelTool"

    # 自定义界面布局
    def draw(self, context):
        layout = self.layout
        data = context.scene.CMT.ExporterSettings
        
        self.draw_general_options(layout,context)
        self.draw_model_options(layout,context)
        self.draw_animation_options(layout,context)
        self.draw_ref_options(layout,context)
        
        #绘制导出按钮
        column = layout.column()
        column.enabled = data.IsExportAnimation or data.IsExportModel or data.IsGenerateRef
        column.operator("cmt.exporter_ot_export")
        
    @staticmethod
    def draw_general_options(layout, context) -> None:
        data = context.scene.CMT.ExporterSettings
        box = layout.box()
        
        box.label(text = "常规设置",icon= "SETTINGS")
        column = box.column()
        column.prop(data,"ProjectPath")
        # column.prop(data,"ModelType")

    def draw_model_options(self,layout, context) -> None:
        data = context.scene.CMT.ExporterSettings
        box = layout.box()

        box.prop(data,"IsExportModel",icon = "OUTLINER_OB_MESH")
        box.enabled = data.ProjectPath != ""
        if data.IsExportModel:
            box1= box.split(factor=0.02)
            box1.column()
            column : bpy.types.UILayout = box1.column()
            column.label(text="模型导出列表",icon="MESH_DATA")
            
            innerBox = column.box()
            col = innerBox.column()
            # column.prop(data,"ModelFileName")
            
            addOrRemoveRow = col.row(align=True)
            addOrRemoveRow.operator("cmt.exporter_ot_addgeometry", icon="ADD")
            addOrRemoveRow.operator("cmt.exporter_ot_removegeometry", icon="REMOVE")
            if len(data.GeoList) > 0:
                curGeo = data.GeoList[data.CurrentGeoIndex]
                col.prop(data,"GeoName")
                col.prop(curGeo,"Class")
                row = col.row()
                row.template_list("CMT_Exporter_UL_MeshList", "", curGeo, "Geometries", curGeo, "ActivedPropertyIndex")
                sidebar = row.column(align = True)  
                sidebar.operator("cmt.exporter_ot_addmesh", text="", icon="ADD")
                sidebar.operator("cmt.exporter_ot_removemesh", text="", icon="REMOVE")
                column.separator()
                column.prop(data,"UVCount")
                column.prop(data,"IsTriangulation")
    @staticmethod
    def draw_animation_options(layout, context) -> None:
        data = context.scene.CMT.ExporterSettings
        box = layout.box()
        # box.label(text = "动画",icon= "ACTION")
        # row = box.row()
        box.prop(data,"IsExportAnimation",icon = "ACTION")
        box.enabled = data.ProjectPath != ""
        if data.IsExportAnimation:
            splited_box1= box.split(factor=0.02)
            splited_box1.column()
            column : bpy.types.UILayout = splited_box1.column()
            column.label(text="动画导出列表",icon="ACTION")
            row = column.row()
            row.template_list("CMT_Exporter_UL_AnimationList", "", data, "AnimationList", data, "ActivedAnimationIndex")
            sidebar = row.column(align = True)
            sidebar.operator("cmt.exporter_ot_addanimation", text="", icon="ADD")
            sidebar.operator("cmt.exporter_ot_removeanimation", text="", icon="REMOVE")
            underRow = column.row()
            underRow.prop(data,"ActionNameToAdd")
            underRow.operator("cmt.exporter_ot_addactionsbykeyword")
            column.separator()
            # column.prop(data,"OverSampling")
            column.prop(data,"Compress")
                
    @staticmethod
    def draw_ref_options(layout, context) -> None:
        data = context.scene.CMT.ExporterSettings
        box = layout.box()
        box.prop(data,"IsGenerateRef",icon = "FILE")
        box.enabled = data.ProjectPath != ""
        if data.IsGenerateRef:
            splited_box1= box.split(factor=0.02)
            splited_box1.column()
            col : bpy.types.UILayout = splited_box1.column()
            # col.label(text="Ast导出列表",icon="META_CUBE")
            col.prop(data,"IsExportAst",icon="META_CUBE")
            if  data.IsExportAst:
                astBox = col.box()
                astCol = astBox.column()
                addOrRemoveRow = astCol.row(align=True)
                addOrRemoveRow.operator("cmt.exporter_ot_addast", icon="ADD")
                addOrRemoveRow.operator("cmt.exporter_ot_removeast", icon="REMOVE")
                astFileRow = astCol.row()
                
                if len(data.AstList) > 0:
                    curAst = data.AstList[data.CurrentAstIndex]
                    astFileRow.prop(
                    data, "AstName",translate=False)
                    astCol.prop(curAst,"Class",translate=False)
                    astCol.prop(curAst,"DSG",translate=False)
                    # astCol.prop(data,"AstDSG",translate=False)
                    astProperties = astCol.row(align=True)
                    astProperties.prop(data,"AstShowProperty",expand=True)
                    

                    propName = data.AstShowProperty
                    templateRow = astCol.row()
                    
                    templateRow.template_list("CMT_Exporter_UL_AstPropertiesList", "", curAst, propName, curAst,  "ActivedPropertyIndex",maxrows=10)
                    sidebar = templateRow.column(align = True)
                    sidebar.operator("cmt.exporter_ot_addref", text="", icon="ADD")
                    sidebar.operator("cmt.exporter_ot_removeref", text="", icon="REMOVE")
                    if propName == "Animations":
                        sidebar.enabled = False
                    # col.separator()
                    
            col.prop(data,"IsExportMaterial",icon="MATERIAL")
            matCol = col.column()
            if data.IsExportMaterial:
                matCol.prop(data,"MaterialName") 
                if data.MaterialName:
                        curMat = data.MaterialList[data.CurrentMatIndex]
                        
                        matCol.prop(curMat,"Class")
                        
                        matCol.template_list("CMT_Exporter_UL_TextureList", "", curMat, "Textures", curMat,  "ActivedPropertyIndex",maxrows=10)
                        scriptCol = col.column()
                        scriptCol.prop(data,"TextureCompressionRate")
                        scriptCol.prop(data,"TexEmbededExportScript")
                        scriptCol.prop(data,"TexCustomExportScript")
                        scriptCol.enabled = data.IsExportMaterial
            col.prop(data,"IsExportArtdef",icon="ASSET_MANAGER")
            # col.prop(data,"IsExportArtdef")
            artdefCol = col.column()
            if data.IsExportArtdef:
                artdefCol.prop(data,"ArtdefName")
                curArtdef = data.ArtdefList[data.CurrentArtdefIndex]
                
                templateRow = artdefCol.row()
                
                templateRow.template_list("CMT_Exporter_UL_ArtdefReferenceList", "", curArtdef, "Instances", curArtdef,  "ActivedPropertyIndex",maxrows=10)
                sidebar = templateRow.column(align = True)
                sidebar.operator("cmt.exporter_ot_addartdefref", text="", icon="ADD")
                sidebar.operator("cmt.exporter_ot_removeartdefref", text="", icon="REMOVE")

                
                
        
class CMT_Exporter_UL_MeshList(bpy.types.UIList):
    def draw_item(self, context, layout, data : CMT_Exporter_Settings, item, icon, active_data, active_propname,index):

        # You should always start your row layout by a label (icon + text), or a non-embossed text field,
        # this will also make the row easily selectable in the list! The later also enables ctrl-click rename.
        # We use icon_value of label, as our given icon is an integer value, not an enum ID.
        # Note "data" names should never be translated!
        row = layout.row()

        split = row.split(factor=0.1 )
        split.label(text="   "+ str(index+1))
        split.prop(item,"value",text="",icon ="MESH_DATA")
        
        
class CMT_Exporter_UL_AnimationList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname,index):
        # You should always start your row layout by a label (icon + text), or a non-embossed text field,
        # this will also make the row easily selectable in the list! The later also enables ctrl-click rename.
        # We use icon_value of label, as our given icon is an integer value, not an enum ID.
        # Note "data" names should never be translated!
        row = layout.row()

        split = row.split(factor=0.1 )
        split.label(text="   "+ str(index+1))
        split.prop(item,"value",text="")
        split.prop(item,"Class",text="")

class CMT_Exporter_UL_AstPropertiesList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname,index):
        # You should always start your row layout by a label (icon + text), or a non-embossed text field,
        # this will also make the row easily selectable in the list! The later also enables ctrl-click rename.
        # We use icon_value of label, as our given icon is an integer value, not an enum ID.
        # Note "data" names should never be translated!
        row = layout.row()

        split = row.split(factor=0.15 )
        if type(item) == CMT_Exporter_PG_AstAnimationProperty:
            split.label(text=item.text)
        else:
            split.label(text="   "+ str(index+1))
        split.prop(item,"value",text="")
        
class CMT_Exporter_UL_TextureList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname,index):
        # You should always start your row layout by a label (icon + text), or a non-embossed text field,
        # this will also make the row easily selectable in the list! The later also enables ctrl-click rename.
        # We use icon_value of label, as our given icon is an integer value, not an enum ID.
        # Note "data" names should never be translated!
        row = layout.row()

        split = row.split(factor=0.15 )

        split.label(text=item.text,text_ctxt = "CMT")
        split.prop(item,"value",text="")
        
class CMT_Exporter_UL_ArtdefReferenceList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname,index):
        # You should always start your row layout by a label (icon + text), or a non-embossed text field,
        # this will also make the row easily selectable in the list! The later also enables ctrl-click rename.
        # We use icon_value of label, as our given icon is an integer value, not an enum ID.
        # Note "data" names should never be translated!
        row = layout.row()

        split = row.split(factor=0.5)
        
        split.prop(item,"Type")
        # split.label(text=item.text,text_ctxt = "CMT")
        split.prop(item,"value")