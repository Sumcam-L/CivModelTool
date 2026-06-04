import bpy
from .utils import *
import os
import clr
from .properties import CMT_Exporter_Settings
from .io_export_cn6 import *
import tempfile
from System.Collections.Generic import List
import importlib.util
import shutil
from System import ValueTuple

class CMT_Exporter_OT_Export(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_export"
    bl_label = "导出"
    bl_description ="导出"

    def export_models(self,context,data: CMT_Exporter_Settings):
        uvCount = data.UVCount
        script_dir = str(Path(__file__).parent)
        templatefile = os.path.join(script_dir,"templates","uv"+str(uvCount)+".fgx")
        
        
        isTriangulation = data.IsTriangulation
        temppath = Path(tempfile.gettempdir() , "tempmodelfile.cn6")
        projpath = get_real_project_path(self,context)
        
        for geo in data.GeoList:
            objSet = []
            for mesh in geo.Geometries:
                arm = get_parent_armature(mesh.value)
                objSet.append(mesh.value)
                if arm not in objSet:
                    objSet.append(arm)
            
            if len(objSet) == 0:
                continue
            do_export(str(temppath.absolute()),isTriangulation,objSet)
            CN6FileOps.exportModel(str(temppath),str(Path(projpath , "Geometries" , geo.FileName + ".fgx")),uvCount,templatefile,geo.Class)

        os.remove(str(temppath))
    def export_animations(self,context,data: CMT_Exporter_Settings):
        anmList = data.AnimationList
        projpath = get_real_project_path(self,context)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        templatefile = os.path.join(script_dir,"templates","uv1.fgx")
        
        for anm in anmList:
            action = bpy.data.actions.get(anm.value.name)
            frame_start = int(action.frame_range[0])
            frame_end = int(action.frame_range[1])
            globalInfo = List[int]()
            globalInfo.Add(int(bpy.context.scene.render.fps / bpy.context.scene.render.fps_base))
            globalInfo.Add(frame_end - frame_start + 1)
            animationData = read_action_data(anm.value.name)           
            CN6FileOps.exportAnimation(animationData,str(Path(projpath , "Animations" , anm.value.name + ".fgx")),templatefile,globalInfo,anm.value.name,anm.Class,data.Compress)

        return
    def export_refs(self,context,data: CMT_Exporter_Settings):
        anmList = data.AnimationList
        geoList = data.GeoList
        astList = data.AstList
        projpath = get_real_project_path(self,context)
        
        script_dir = str(Path(__file__).parent)
        
        exportList = Dictionary[str, AstInfo]()
        fps = int(bpy.context.scene.render.fps / bpy.context.scene.render.fps_base)
        
        for ast in astList:
            if len(ast.Geometries) == 0: continue
            if ast.FileName not in exportList:
                exportList[ast.FileName] = AstInfo()
            exportList[ast.FileName].geometry = ast.Geometries[0].value
            exportList[ast.FileName].ClassName = ast.Class
            exportList[ast.FileName].DSG = ast.DSG
            anms = Dictionary[str, ValueTuple[str,str]]()
            behs = Dictionary[str, str]()
            for anm in ast.Animations:
                if anm.value != None:
                    frame_start = int(anm.value.frame_range[0])
                    frame_end = int(anm.value.frame_range[1]) + 1
                    count = frame_end - frame_start
                    duration_str = f"{count/fps:.6f}"
                    
                    tuple_value = ValueTuple[str, str](anm.value.name, duration_str)
                    anms[anm.text] = tuple_value
            # for anm in ast.Animations:
            #     anms[anm.text] = anm.value.name
            exportList[ast.FileName].animations = anms
            exportList[ast.FileName].behaviors = behs
        
            CN6FileOps.generateAst(exportList,projpath)
        return
    
    def export_materials(self,context,data: CMT_Exporter_Settings):
        projpath = get_real_project_path(self,context)
        matlist_refresh(self,context)
        customscript = None
        if data.TexCustomExportScript:
            spec = importlib.util.spec_from_file_location("dynamic_mod", data.TexCustomExportScript)
            customscript = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(customscript)
        geoList = data.GeoList
        materialList = Dictionary[str, Dictionary[str, str]]()
        textureDict = Dictionary[str, str]()
        deleteList = []
            
                
        for mat in data.MaterialList:
            for tex in mat.Textures:
                texName = str(Path(tex.value).stem) if tex.value != "" and tex.value != "None" else ""
                if tex.value != "None":
                    absPath = getAbsPathByImage(bpy.data.materials[mat.FileName],tex.value)
                    if data.TextureCompressionRate != "1":
                       p = Path(absPath)
                       absPath = compress_texture_resolution(absPath,scale=data.TextureCompressionRate,output_path=str(Path(projpath,p.name)))
                       texName = str(Path(absPath).stem)
                       deleteList.append(absPath)
                    if absPath and  data.TexEmbededExportScript != None:
                        if "Normal" in tex.text and data.TexEmbededExportScript == "WuwaNormal" :
                            unpackedTexs = extract_packed_textures_to_file(absPath,projpath)
                            absPath = unpackedTexs["normal"]
                            texName = str(Path(absPath).stem)
                            
                            deleteList.append(unpackedTexs["normal"])
                            deleteList.append(unpackedTexs["metallic"])
                            deleteList.append(unpackedTexs["gloss"])
                            if mat.FileName not in materialList:
                                materialList[mat.FileName] = Dictionary[str, str]()
                            ##金属度实际上似乎是粗糙度
                            if "Metalness" in g_Mat_json[tex.Class]:
                                textureDict[unpackedTexs["metallic"]] = g_Mat_json[tex.Class]["Metalness"]
                                materialList[mat.FileName]["Metalness"] = str(Path(unpackedTexs["metallic"]).stem)
                                
                            ##光泽是金属度
                            if "Gloss" in g_Mat_json[tex.Class]:
                                textureDict[unpackedTexs["gloss"]] = g_Mat_json[tex.Class]["Gloss"]
                                materialList[mat.FileName]["Gloss"] = str(Path(unpackedTexs["gloss"]).stem)
                                
                                
                        
                    textureDict[absPath] = g_Mat_json[tex.Class][tex.text]
                if mat.FileName not in materialList:
                    materialList[mat.FileName] = Dictionary[str, str]()
                if tex.value != "None":
                    materialList[mat.FileName][tex.text] = texName

        tempDict = dict(materialList)
        #补齐未包含的属性,包含非贴图项
        for key, mat in tempDict.items():
            tC = [ x for x in data.MaterialList if x.FileName == key][0].Class
            for propName, v in g_Mat_json[tC].items():
                if propName not in mat:
                   materialList[key][propName] = v if "AssetObjects.." in v else ""
        
        classList = Dictionary[str, str]()
        for key, mat in materialList.items():
            tC = [ x for x in data.MaterialList if x.FileName == key][0].Class
            classList[key] = tC
        CN6FileOps.exportTextures(textureDict,projpath)
        CN6FileOps.exportMaterials(materialList,classList,projpath)
        ## 删除临时文件
        for file in deleteList:
            print("删除临时文件",file)
            os.remove(file)

    def export_artdefs(self,context,data:CMT_Exporter_Settings):
        def fill_bins(self,parentnode,doc,bin,assetname):
            if find_element_by_collection_name(root,"Element",
                                               "m_Name","text",
                                               bin): return
            temptext = get_bins_template(bin,"Body","Any",assetname)
            fragment = xml.dom.minidom.parseString(temptext)
            node = doc.importNode(fragment.documentElement, deep=True)
            parentnode.appendChild(node)
        def fill_members(self,parentnode,doc,binpath,membername):
            if find_element_by_collection_name(root,"Element",
                                               "m_Name","text",
                                               membername): return
            temptext = get_members_template(membername,binpath)
            fragment = xml.dom.minidom.parseString(temptext)
            node = doc.importNode(fragment.documentElement, deep=True)
            parentnode.appendChild(node)
            
        def fill_untis(self,parentnode,doc,unittype,membername):
            if find_element_by_collection_name(root,"Element",
                                               "m_Name","text",
                                               unittype): return
            temptext = get_units_template(unittype,membername)
            fragment = xml.dom.minidom.parseString(temptext)
            node = doc.importNode(fragment.documentElement, deep=True)
            parentnode.appendChild(node)
            
        def find_element_by_collection_name(parent_node,label, attrName,subName,target_name):
            """根据 m_CollectionName 的 text 属性查找 Element"""
            for element in parent_node.getElementsByTagName(label):
                # 查找子节点 m_CollectionName
                collection_names = element.getElementsByTagName(attrName)
                if collection_names:
                    name_attr = collection_names[0].getAttribute(subName)
                    if name_attr == target_name:
                        return element
            return None

        supportedArtdefs = get_artdef_items(self,context)
        projPath = get_real_project_path(self,context)
        for index ,artdef in enumerate(data.ArtdefList):
            for inst in artdef.Instances:
                artdefName = next(x[0] for i,x in enumerate(supportedArtdefs) if i == index)
                targetFile = str(Path(projPath,"ArtDefs",artdefName))
                artdeftemplate_path = str(Path(os.path.dirname(__file__),"templates",artdefName))
                if os.path.exists(targetFile):
                    artdeftemplate_path = targetFile
                else:
                    shutil.copy2(artdeftemplate_path, targetFile)
                    artdeftemplate_path = targetFile
                    
                dom = xml.dom.minidom.parse(artdeftemplate_path)
                collection = dom.documentElement
                if artdefName == "Units.artdef":
                    root = collection.getElementsByTagName("m_RootCollections")[0]
                    
                    pNode = find_element_by_collection_name(root,"Element","m_CollectionName","text","UnitAttachmentBins")
                    fill_bins(self,pNode,dom,inst.Type,inst.value)
                    
                    pNode = find_element_by_collection_name(root,"Element","m_CollectionName","text","UnitMemberTypes")
                    fill_members(self,pNode,dom,inst.Type + "/Body",inst.Type)
                    
                    pNode = find_element_by_collection_name(root,"Element","m_CollectionName","text","Units")
                    fill_untis(self,pNode,dom,inst.Type,inst.Type)
                    
                    save_xml(dom,artdeftemplate_path)
                        
    def execute(self, context : bpy.types.Context):
        data : CMT_Exporter_Settings = context.scene.CMT.ExporterSettings

        if data.IsExportModel:
            self.export_models(context,data)

            
        if data.IsExportAnimation:
            self.export_animations(context,data)

        
        if data.IsGenerateRef:
            self.export_refs(context,data)

            
        if data.IsExportMaterial:
            self.export_materials(context,data)
        
        if data.IsExportArtdef:
            self.export_artdefs(context,data)
            
        

        return {"FINISHED"}

class CMT_Exporter_OT_AddGeometry(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_addgeometry"
    bl_label = "新建模型文件"
    bl_description ="新建模型文件"

    Name: bpy.props.StringProperty(
        name="文件名",
        default=""
    )
    error: bpy.props.StringProperty(default="")
    def execute(self, context : bpy.types.Context):
        if self.error:
            self.report({'ERROR'}, "名字不合法")
            return {'CANCELLED'}
        data = context.scene.CMT.ExporterSettings
        geoList = data.GeoList
        item = geoList.add()
        item.FileName = self.Name
        index = len(geoList) - 1
        data.CurrentGeoIndex = index
        data.GeoName = self.Name

        
                
        return {"FINISHED"}
    def invoke(self, context, event):
        self.Name = ""
        self.error = ""
        return context.window_manager.invoke_props_dialog(self)
    
    def check(self, context):
            items = context.scene.CMT.ExporterSettings.GeoList

            if self.Name == "":
                self.error = "名称不能为空"
            elif any(item.FileName == self.Name for item in items):
                self.error = "名称已存在"
            else:
                self.error = ""
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "Name")

        if self.error:
            layout.label(text=self.error, icon='ERROR')
    
class CMT_Exporter_OT_RemoveGeometry(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_removegeometry"
    bl_label = "删除模型文件"
    bl_description ="删除模型文件"

    def execute(self, context : bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        geoList = data.GeoList
        geoList.remove(data.CurrentGeoIndex)
        if data.CurrentGeoIndex >= len(geoList) and len(geoList) > 0:
            data.CurrentGeoIndex = len(geoList) - 1
            data.GeoName = geoList[data.CurrentGeoIndex].FileName
            
        return {"FINISHED"}

class CMT_Exporter_OT_AddMesh(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_addmesh"
    bl_label = ""
    bl_description ="将所有选中的网格模型添加到导出列表"

    def execute(self, context : bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        meshList = data.GeoList[data.CurrentGeoIndex].Geometries
        if len(context.selected_objects) == 0:
            item = meshList.add()
        else:
            for obj in context.selected_objects:
                exists = False
                item = meshList.add()
                for property in meshList:
                    if property.value == obj:
                        exists = True
                if not exists and obj.type == "MESH":
                     
                    item.value = obj     
        return {"FINISHED"}
    
class CMT_Exporter_OT_RemoveMesh(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_removemesh"
    bl_label = ""
    bl_description ="将选中的项目从导出列表中移除"

    def execute(self, context:bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        meshList = data.GeoList[data.CurrentGeoIndex].Geometries
        meshList.remove(data.GeoList[data.CurrentGeoIndex].ActivedPropertyIndex)
        return {"FINISHED"}
    
class CMT_Exporter_OT_AddAnimation(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_addanimation"
    bl_label = ""
    bl_description ="添加动画"

    def execute(self, context : bpy.types.Context):
        animationList  = context.scene.CMT.ExporterSettings.AnimationList
        item = animationList.add()

        return {"FINISHED"}
    
class CMT_Exporter_OT_RemoveAnimation(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_removeanimation"
    bl_label = ""
    bl_description ="移除动画"

    def execute(self, context:bpy.types.Context):

        context.scene.CMT.ExporterSettings.AnimationList.remove(context.scene.CMT.ExporterSettings.ActivedAnimationIndex)
        return {"FINISHED"}

class CMT_Exporter_OT_AddActionsByKeyword(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_addactionsbykeyword"
    bl_label = "添加所有包含关键字的动作"
    bl_description ="添加所有包含关键字的动作"

    def execute(self, context:bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        keyword = data.ActionNameToAdd
        animationList = data.AnimationList
        if keyword != "":
            for action in bpy.data.actions:
                if keyword in action.name:
                    if not any( action  is anm.value for anm in data.AnimationList):
                        animationList.add().value = action
        return {"FINISHED"}
    
class CMT_Exporter_OT_AddAst(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_addast"
    bl_label = "新建Ast"
    bl_description ="新建Ast"
    
    AstName: bpy.props.StringProperty(
        name="文件名",
        default=""
    )
    error: bpy.props.StringProperty(default="")
    def execute(self, context : bpy.types.Context):
        if self.error:
            self.report({'ERROR'}, "名字不合法")
            return {'CANCELLED'}
        data = context.scene.CMT.ExporterSettings
        astList = data.AstList
        item = astList.add()
        item.FileName = self.AstName
        index = len(astList) - 1
        data.CurrentAstIndex = index
        data.AstName = self.AstName
        ast_dsg_update(item,context)
        
                
        return {"FINISHED"}
    def invoke(self, context, event):
        self.AstName = ""
        self.error = ""
        return context.window_manager.invoke_props_dialog(self)
    
    def check(self, context):
            items = context.scene.CMT.ExporterSettings.AstList

            if self.AstName == "":
                self.error = "名称不能为空"
            elif any(item.FileName == self.AstName for item in items):
                self.error = "名称已存在"
            else:
                self.error = ""
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "AstName")

        if self.error:
            layout.label(text=self.error, icon='ERROR')
            
class CMT_Exporter_OT_RemoveAst(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_removeast"
    bl_label = "删除Ast"
    bl_description ="删除当前Ast"

    def execute(self, context : bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        astList = data.AstList
        astList.remove(data.CurrentAstIndex)
        if data.CurrentAstIndex >= len(astList) and len(astList) >0  :
            data.CurrentAstIndex = len(astList) - 1
            data.AstName = astList[data.CurrentAstIndex].FileName
        return {"FINISHED"}
    
class CMT_Exporter_OT_AddRef(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_addref"
    bl_label = ""
    bl_description ="添加引用"

    def execute(self, context : bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        instance = data.AstList[data.CurrentAstIndex]
        type = data.AstShowProperty
        if type=="Geometries":
            if len(instance.Geometries) == 0:
                instance.Geometries.add()
        elif type=="Animations":
            instance.Animations.add()
        elif type=="Behaviors":
            instance.Behaviors.add()

        return {"FINISHED"}
    
class CMT_Exporter_OT_RemoveRef(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_removeref"
    bl_label = ""
    bl_description ="移除选中的引用"

    def execute(self, context:bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        instance = data.AstList[data.CurrentAstIndex]
        type = data.AstShowProperty
        if type=="Geometries":
            instance.Geometries.remove(instance.ActivedPropertyIndex)
        elif type=="Animations":
            instance.Animations.remove(instance.ActivedPropertyIndex)
        elif type=="Behaviors":
            instance.Behaviors.remove(instance.ActivedPropertyIndex)
        
        return {"FINISHED"}

class CMT_Exporter_OT_AddArtdefRef(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_addartdefref"
    bl_label = ""
    bl_description ="添加引用"

    def execute(self, context : bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        artdef = data.ArtdefList[data.CurrentArtdefIndex]
        artdef.Instances.add()
        

        return {"FINISHED"}
    
class CMT_Exporter_OT_RemoveArtdefRef(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_removeartdefref"
    bl_label = ""
    bl_description ="移除选中的引用"

    def execute(self, context:bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        artdef = data.ArtdefList[data.CurrentArtdefIndex]
        artdef.Instances.remove(artdef.ActivedPropertyIndex)
        
        return {"FINISHED"}

