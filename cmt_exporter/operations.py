import bpy
from .utils import *
import os
import clr
from .properties import CMT_Exporter_Settings, _report
from .allowed_classes import get_allowed_geo_classes, get_allowed_anm_classes
from .utils import resolve_enum, get_ast_class_items, get_geotype_items, get_anmtype_items
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
        wigfile = os.path.join(script_dir,"templates","emptywig.wig")
        
        
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
            CN6FileOps.exportModel(str(temppath),str(Path(projpath , "Geometries" , geo.FileName + ".fgx")),uvCount,templatefile,wigfile,geo.Class)

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
            if ast.FileName not in exportList:
                exportList[ast.FileName] = AstInfo()
            if len(ast.Geometries) > 0:
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

                            if "Metalness" in g_Mat_json[tex.Class]:
                                textureDict[unpackedTexs["metallic"]] = g_Mat_json[tex.Class]["Metalness"]
                                materialList[mat.FileName]["Metalness"] = str(Path(unpackedTexs["metallic"]).stem)
                                

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
            if os.path.exists(file):
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

    def validate_ast_references(self, data: CMT_Exporter_Settings):
        errors = []
        for ast in data.AstList:
            ast_class = resolve_enum(ast, "Class", get_ast_class_items)
            allowed_geo = get_allowed_geo_classes(ast_class)
            allowed_anm = get_allowed_anm_classes(ast_class)

            for geo_ref in ast.Geometries:
                geoClass = None
                for geo in data.GeoList:
                    if geo.FileName == geo_ref.value:
                        geoClass = resolve_enum(geo, "Class", get_geotype_items)
                        break
                if geoClass and geoClass not in allowed_geo:
                    errors.append(
                        f"Ast [{ast.FileName}] 模型引用 [{geo_ref.value}] "
                        f"类型 {geoClass} 不被允许 (允许: {', '.join(allowed_geo) or '无'})"
                    )

            for anm_ref in ast.Animations:
                if not anm_ref.value:
                    continue
                anmClass = None
                for anm in data.AnimationList:
                    if anm.value is anm_ref.value:
                        anmClass = resolve_enum(anm, "Class", get_anmtype_items)
                        break
                if anmClass and anmClass not in allowed_anm:
                    errors.append(
                        f"Ast [{ast.FileName}] 动画引用 [{anm_ref.text}] "
                        f"类型 {anmClass} 不被允许 (允许: {', '.join(allowed_anm) or '无'})"
                    )
        return errors

    def show_validation_errors(self, context, errors):
        def draw(self, context):
            for err in errors:
                self.layout.label(text=err, icon='ERROR')
        context.window_manager.popup_menu(draw, title="Ast 引用类型不匹配，导出已中止", icon='ERROR')

    def execute(self, context : bpy.types.Context):
        data : CMT_Exporter_Settings = context.scene.CMT.ExporterSettings

        if data.IsGenerateRef and data.IsExportAst:
            errors = self.validate_ast_references(data)
            if errors:
                self.show_validation_errors(context, errors)
                return {"CANCELLED"}

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
        item.Class = "DecalGeometry"
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
        geoIndex = data.CurrentGeoIndex
        geoFileName = geoList[geoIndex].FileName

        savedAstIndex = data.CurrentAstIndex
        for ast_idx, ast in enumerate(data.AstList):
            data.CurrentAstIndex = ast_idx
            to_remove = []
            for i, geo_ref in enumerate(ast.Geometries):
                if geo_ref.value == geoFileName:
                    to_remove.append(i)
            for i in reversed(to_remove):
                ast.Geometries.remove(i)
            if to_remove:
                _report(f"已删除 Ast [{ast.FileName}] 中对模型 [{geoFileName}] 的引用")
        data.CurrentAstIndex = savedAstIndex

        geoList.remove(geoIndex)
        if geoIndex >= len(geoList) and len(geoList) > 0:
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
            matlist_refresh(data, context)
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
            matlist_refresh(data, context)
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
    
class CMT_Exporter_OT_RemoveArtdefRef(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_modifymattypebykeywords"
    bl_label = ""
    bl_description ="按关键字修改材质类型"

    def execute(self, context:bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        matlist_refresh(data, context)
        for mat in data.MaterialList:
            if data.MaterialTargetClass:
                keywords = data.MaterialKeywords.lower()
                if keywords in mat.FileName.lower():
                    mat.Class = data.MaterialTargetClass
                    print("修改材质类型",mat.FileName)
            
        
        
        return {"FINISHED"}


class CMT_Exporter_OT_MatchAnimations(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_matchanimations"
    bl_label = ""
    bl_description = "根据Ast名称和动画槽位名称自动匹配动画"

    def execute(self, context: bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        curAst = data.AstList[data.CurrentAstIndex]
        astName = curAst.FileName.lower()
        ast_class = resolve_enum(curAst, "Class", get_ast_class_items)
        allowed = get_allowed_anm_classes(ast_class)
        matched = 0
        for anm in curAst.Animations:
            for action in bpy.data.actions:
                actionName = action.name.lower()
                if (astName + "_") in actionName:
                    if actionName.replace(astName + "_", "") in anm.text.lower():
                        anm_entry = None
                        for entry in data.AnimationList:
                            if entry.value is action:
                                anm_entry = entry
                                break
                        if anm_entry:
                            anm_class = resolve_enum(anm_entry, "Class", get_anmtype_items)
                            if anm_class in allowed:
                                anm.value = action
                                matched += 1
                        break
        if matched:
            self.report({'INFO'}, f"已匹配 {matched} 个动画")
        else:
            self.report({'WARNING'}, "未找到匹配的动画")
        return {"FINISHED"}

