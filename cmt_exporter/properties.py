import bpy
from .utils import *

def geometry_poll(self,obj):
    # data = bpy.context.scene.CMT.ExporterSettings
    data = bpy.context.scene.CMT.ExporterSettings
    meshList = data.GeoList[data.CurrentGeoIndex].Geometries
    if obj.type == "MESH":
        if not any( obj  is mesh.value for mesh in meshList):
            return True
    return False

def animation_poll(self,obj):
    data = bpy.context.scene.CMT.ExporterSettings
    return not any( obj  is anm.value for anm in data.AnimationList)

class CMT_Exporter_PG_GeometryProperty(bpy.types.PropertyGroup):
    value : bpy.props.PointerProperty(type=bpy.types.Object,
                                      poll=geometry_poll)
    
class CMT_Exporter_PG_GeometryList(bpy.types.PropertyGroup):
    FileName : bpy.props.StringProperty()
    Class : bpy.props.EnumProperty(
        name="类型", description="类型",items=get_geotype_items,translation_context = "CMT",default=6
    )
    Geometries:bpy.props.CollectionProperty(type=CMT_Exporter_PG_GeometryProperty)
    ActivedPropertyIndex:bpy.props.IntProperty(default=0)

class CMT_Exporter_PG_Animationlist(bpy.types.PropertyGroup):
    value:bpy.props.PointerProperty(
        type=bpy.types.Action,poll=animation_poll )
    Class:bpy.props.EnumProperty(name="",description="类型",items=get_anmtype_items,translation_context = "CMT",default=3)

class CMT_Exporter_PG_Texture(bpy.types.PropertyGroup):
    
    def textureInstance_automatch_texture(self,context):
        data = context.scene.CMT.ExporterSettings
        def find_target_input(node,target):
            def find_to_rigth(node):
                linkedNodes = []
                for o in node.outputs:
                    if o.is_linked:
                        for link in o.links:
                            linkedNodes.append(link.to_socket)
                return linkedNodes

            while True:
                nodes = find_to_rigth(node)
                if len(nodes):
                    if any(x.node.type == target for x in nodes):
                        for x in nodes:
                            if x.node.type== target:
                                return x.name
                    else:
                        for x in  nodes:
                            linkTarget = find_target_input(x.node,target)
                            if linkTarget:
                                return linkTarget
                        break
                else:
                    break
            return None 
        for node in bpy.data.materials[self.matName].node_tree.nodes:
            if node.type == "TEX_IMAGE":
                target = find_target_input(node,"BSDF_PRINCIPLED")
                
                if not target: continue
                if self.text == target.replace(" ",""):
                        
                    self.value = node.image.name
                    break
    def get_texture_items(self,context):
    
        data = context.scene.CMT.ExporterSettings
        items = []
        items.append(("None","None",""))
        for node in bpy.data.materials[self.matName].node_tree.nodes:
            if node.type == "TEX_IMAGE":
                name = node.image.name
                items.append((name,name,os.path.normpath(bpy.path.abspath(node.image.filepath))))
        return items
                
    matName : bpy.props.StringProperty()
    Class : bpy.props.StringProperty()
    text:bpy.props.StringProperty(update=textureInstance_automatch_texture)
    value:bpy.props.EnumProperty(name="贴图",description="选择贴图",items=get_texture_items)
    
    
                    
                
class CMT_Exporter_PG_Material(bpy.types.PropertyGroup):
    
    def get_parentgeo_class(self,context,target):
        data = context.scene.CMT.ExporterSettings
        for geo in data.GeoList:
            for prop in geo.Geometries:
                for mat in prop.value.data.materials:
                        if mat.name == target:
                            return geo.Class
    
    def materialInstance_name_update(self,context):

        if len(self.Textures) == 0:
            for key,v in g_Mat_json[self.Class].items():
                if "AssetObject" not in v:
                    # tex = self.Textures.add()
                    parentClass = self.get_parentgeo_class(context,self.FileName)
                    self.Class = parentClass if parentClass else self.Class
                    print(1111111111,self.FileName,self.Class)

                    # tex.matName = self.FileName
                    # tex.Class = parentClass if parentClass else self.Class
                    # tex.text = key
    def mat_class_update(self,context):
        self.Textures.clear()
        for key,v in g_Mat_json[self.Class].items():
            if "AssetObject" not in v:
                tex = self.Textures.add()
                tex.matName = self.FileName
                tex.Class = self.Class
                tex.text = key
    FileName:bpy.props.StringProperty(update=materialInstance_name_update)
    Class:bpy.props.EnumProperty(name="类型",description="选择材质类型",translation_context="CMT",items=get_material_class_items,update=mat_class_update,default=0)
    Textures:bpy.props.CollectionProperty(type=CMT_Exporter_PG_Texture)
    ActivedPropertyIndex:bpy.props.IntProperty(default=0)
    
    
                
    
        
                
                

class CMT_Exporter_PG_AstProperty(bpy.types.PropertyGroup):
    value:bpy.props.EnumProperty(items=[("","","")])



def astgeometry_poll(self,obj):
    data = bpy.context.scene.CMT.ExporterSettings
    for geo in data.GeoList:
        for mesh in geo.Geometries:
            if mesh.value is obj:
                return True   
    return False

def astanimation_poll(self,obj):
    data = bpy.context.scene.CMT.ExporterSettings
    for anm in data.AnimationList:
        if anm.value is obj:
            return True       
    return False

class CMT_Exporter_PG_ArtdefInstance(bpy.types.PropertyGroup):
    def get_artdefinstance_value_items(self,context):
        data = context.scene.CMT.ExporterSettings
        items = []
        for ast in data.AstList:
            items.append((ast.FileName,ast.FileName,ast.FileName))
        return items
    Type:bpy.props.StringProperty(translation_context="CMT")
    value:bpy.props.EnumProperty(name="", description="选择Ast文件",items=get_artdefinstance_value_items)


class CMT_Exporter_PG_Artdef(bpy.types.PropertyGroup):
    Instances:bpy.props.CollectionProperty(type=CMT_Exporter_PG_ArtdefInstance)
    ActivedPropertyIndex:bpy.props.IntProperty(default=0)
    

class CMT_Exporter_PG_AstGeometryProperty(bpy.types.PropertyGroup):
    value:bpy.props.EnumProperty(name="", description="选择模型",items=get_astgeometries_items)
    
class CMT_Exporter_PG_AstAnimationProperty(bpy.types.PropertyGroup):
    def anim_text_update(self,context):
        astName = self.AstName.lower()
        for action in bpy.data.actions:
            name = action.name.lower()
            if (astName + "_") in name:
                if name.replace(astName + "_","") in self.text.lower():
                    self.value = action
    AstName:bpy.props.StringProperty()
    text:bpy.props.StringProperty(update=anim_text_update)
    value:bpy.props.PointerProperty(type=bpy.types.Action,poll=astanimation_poll)

class CMT_Exporter_PG_Ast(bpy.types.PropertyGroup):
    FileName : bpy.props.StringProperty()
    # Class : bpy.props.StringProperty(default="Unit")
    Class : bpy.props.EnumProperty(name="类型", description="类型", translation_context = "CMT",items=get_ast_class_items)
    DSG : bpy.props.EnumProperty(name="DSG", description="DSG", translation_context="", items=get_ast_DSG_items,update=ast_dsg_update)
    # DSG : bpy.props.StringProperty(default="potential_any_graph")
    Geometries:bpy.props.CollectionProperty(type=CMT_Exporter_PG_AstGeometryProperty)
    Animations:bpy.props.CollectionProperty(type=CMT_Exporter_PG_AstAnimationProperty)
    Behaviors:bpy.props.CollectionProperty(type=CMT_Exporter_PG_AstProperty)
    ActivedPropertyIndex:bpy.props.IntProperty(default=0)
    

class CMT_Exporter_Settings(bpy.types.PropertyGroup):
    ProjectPath:bpy.props.StringProperty(
        name="项目路径",
        description="使用前请先启动一次AssetEditor以创建资产文件夹",
        default = "",
        subtype = "DIR_PATH",
        update=project_path_update
    )
    
    ##导出设置
    IsExportModel: bpy.props.BoolProperty(
        name="模型导出设置", description="是否导出选中的模型", default=False
    )
    IsExportAnimation: bpy.props.BoolProperty(
        name="动画导出设置", description="是否导出被选中骨架的动画", default=False
    )
    IsGenerateRef : bpy.props.BoolProperty(
        name="引用文件设置", description="是否生成引用所导出资产的文件",default=False
    )
    ModelType:bpy.props.EnumProperty(name="模型导出类型", translation_context = "CMT" ,description="模型导出类型",items=get_geotype_items,default=6)
    
    ##模型设置
    UVCount: bpy.props.IntProperty(
        name="导出UV数量",
        description="控制导出的fgx文件中保存的UV的数量，一般情况导出一层UV即可。第一层UV用于基础颜色、金属度、粗糙度、光泽度、法线贴图等；第二层UV用于环境光遮蔽、光照贴图；第三层UV用于自发光贴图。另外，使用两层UV导出的fgx会丢失骨骼绑定，因为我懒得改了，如果需要用第二层UV的功能并且需要保留骨骼绑定，请直接导出三层UV。",
        default=1,
        min=1,
        max=3,
    )
    IsTriangulation: bpy.props.BoolProperty(
        name="三角化",
        description="是否在导出前对模型三角化，模型已是三角面的情况无需勾选",
        default=False
    )
    # MeshList:bpy.props.CollectionProperty(type=CMT_Exporter_PG_GeometryList)
    GeoList:bpy.props.CollectionProperty(type=CMT_Exporter_PG_GeometryList)
    
    GeoName : bpy.props.EnumProperty(name="文件名", description="文件名", translation_context="",items=get_geo_files,update = geo_filename_update)
    # GeoClass : bpy.props.EnumProperty(
    #     name="类型", description="类型",items=get_geotype_items,update = geo_class_update,translation_context = "CMT",default=6
    # )
    CurrentGeoIndex: bpy.props.IntProperty(default=0 )
    
    
    ModelFileName : bpy.props.StringProperty(
        name="模型文件名", description="模型文件名"
    )
    
    ##动画设置
    OverSampling: bpy.props.IntProperty(
        name="采样率",
        description="控制采样数据的精度，每(1/采样率)帧采样一次数据，一般默认即可",
        default=1,
        min=0,
        max=10,
    )
    Compress: bpy.props.BoolProperty(
        name="压缩动画",
        description="压缩动画",
        default=True
    )
    AnimationList:bpy.props.CollectionProperty(type=CMT_Exporter_PG_Animationlist)
    ActivedAnimationIndex: bpy.props.IntProperty(default=0)
    ActionNameToAdd : bpy.props.StringProperty(
        name="关键字", description=""
    )
    
    #引用文件设置
    
    #Ast部分
    CurrentAstIndex : bpy.props.IntProperty(default=0)
    AstList : bpy.props.CollectionProperty(type=CMT_Exporter_PG_Ast)
    AstName : bpy.props.EnumProperty(name="文件名", description="文件名", translation_context="",items=get_ast_files,update = ast_filename_update)
    AstClass : bpy.props.EnumProperty(
        name="类型", description="类型", translation_context = "CMT",items=get_ast_class_items,update = ast_class_update
    )
    AstDSG : bpy.props.EnumProperty(
        name="DSG", description="DSG", translation_context="", items=get_ast_DSG_items,
    update = ast_dsg_update)
    AstShowProperty: bpy.props.EnumProperty(
        name="选择引用类型", description="选择引用类型", items=[("Geometries","模型引用",""),("Animations","动画引用",""),("Behaviors","行为引用","")])
    
    IsExportAst:bpy.props.BoolProperty(
        name="Ast导出设置", description="是否导出Ast",default=False
    )
    IsExportMaterial:bpy.props.BoolProperty(
        name="材质导出设置", description="是否导出材质(请保证已经正确连接贴图,否则贴图不能够正常导出)",default=False,update=export_material_update
    )
    IsExportArtdef:bpy.props.BoolProperty(
        name="是否导出Artdef", description="是否导出Artdef",default=False,update=export_artdef_update
    )
    ArtdefName:bpy.props.EnumProperty(
        name="Artdef文件名", description="支持的Artdef", translation_context="", 
        items=get_artdef_items,
        update = artdef_name_update)
    
    CurrentArtdefIndex : bpy.props.IntProperty(default=0)
    
    ArtdefList:bpy.props.CollectionProperty(type=CMT_Exporter_PG_Artdef)
    
    MaterialName :bpy.props.PointerProperty(
        name="材质名", description="材质名",type=bpy.types.Material,poll = mat_poll,update = mat_name_update
    )
    CurrentMatIndex : bpy.props.IntProperty(default=0)
    
    MaterialList:bpy.props.CollectionProperty(type=CMT_Exporter_PG_Material)
    
    
    
    MaterialKeywords:bpy.props.StringProperty(name="材质关键字", description="材质关键字",default="")
    MaterialTargetClass:bpy.props.EnumProperty(name="目标材质类型",description="选择目标材质类型",translation_context="CMT",items=get_material_class_items,default=0)
    
    
    
    TexCustomExportScript:bpy.props.StringProperty(
        name="自定义贴图导出脚本",
        description="自定义贴图导出脚本",
        subtype = "FILE_PATH",
        default="",
        update=customscript_path_update
    )
    TexEmbededExportScript:bpy.props.EnumProperty(
        name="内置贴图导出脚本",
        description="内置贴图导出脚本",
        items=[("None","None",""),("WuwaNormal","鸣潮法线贴图","")],
        default="None"
    )
    TextureCompressionRate:bpy.props.EnumProperty(
        name="贴图压缩率",
        description="贴图压缩率",
        items=[("1","1.0",""),("0.75","0.75",""),("0.5","0.5",""),("0.25","0.25",""),("0.125","0.125",""),("0.1","0.1","")],
        default="1"
    )
    
    
    
    # AstList: bpy.props.CollectionProperty(type=FgxExporter)
    

