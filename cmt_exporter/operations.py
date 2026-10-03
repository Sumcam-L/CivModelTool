import importlib.util
import os
import shutil
import tempfile
import xml.dom.minidom
from pathlib import Path

import bpy

from .civ6_data import AstInfo, CN6FileOps, Dictionary, List, ValueTuple, g_Mat_json
from .enum_items import (
    default_anm_class,
    get_anmtype_items,
    get_artdef_items,
    get_ast_class_items,
    get_geotype_items,
    resolve_enum,
)
from .properties import CMT_Exporter_Settings, _report
from .allowed_classes import get_allowed_geo_classes, get_allowed_anm_classes
from .action_data import read_action_data
from .scene_helpers import get_parent_armature, getAbsPathByImage, get_real_project_path
from .templates import get_bins_template, get_members_template, get_units_template
from .textures import compress_texture_resolution, extract_alpha_to_file, extract_packed_textures_to_file
from .updates import ast_dsg_update, matlist_refresh
from .xml_utils import append_xml_fragment, find_element_by_collection_name, save_xml
from .io_export_cn6 import do_export
from .item_dialogs import NamedItemDialogOperator

class CMT_Exporter_OT_Export(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_export"
    bl_label = "导出"
    bl_description ="导出"

    def _log(self, message) -> None:
        """供无 operator 上下文的辅助函数回传进度：报告到 Blender 界面。"""
        self.report({'INFO'}, str(message))

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
            skipped = []
            for slot in geo.Geometries:
                obj = slot.value
                if obj is None:
                    skipped.append("(空槽位)")
                    continue
                arm = get_parent_armature(obj)
                if arm is None:
                    skipped.append(obj.name)
                    continue
                objSet.append(obj)
                if arm not in objSet:
                    objSet.append(arm)
            if skipped:
                self.report({"WARNING"}, f"模型 [{geo.FileName}] 跳过未绑定骨架的网格: {', '.join(skipped)}")
            for obj in objSet:
                if obj.type != "MESH":
                    continue
                slots = obj.material_slots
                if len(slots) == 0 or any(slot.material is None for slot in slots):
                    self.report(
                        {"WARNING"},
                        f"网格 [{obj.name}] 缺少材质: Civ6 模型要求每个网格至少有一个材质",
                    )
                    if temppath.exists():
                        os.remove(str(temppath))
                    return False
            if len(objSet) == 0:
                continue
            do_export(str(temppath.absolute()),isTriangulation,objSet,log=self._log)
            CN6FileOps.exportModel(str(temppath),str(Path(projpath , "Geometries" , geo.FileName + ".fgx")),uvCount,templatefile,wigfile,geo.Class)

        if temppath.exists():
            os.remove(str(temppath))
        return True
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
        astList = data.AstList
        projpath = get_real_project_path(self,context)
        
        
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
                       absPath = compress_texture_resolution(
                           absPath,scale=data.TextureCompressionRate,
                           output_path=str(Path(projpath,p.name)),log=self._log)
                       texName = str(Path(absPath).stem)
                       deleteList.append(absPath)
                    if absPath and tex.Channel == "Alpha":
                       # 槽位要的是这张图的 alpha：抽成独立灰度图再导。
                       # 放在压缩之后，让压缩率对灰度图同样生效。
                       unpackedAlpha = extract_alpha_to_file(absPath, projpath, log=self._log)
                       if unpackedAlpha:
                           absPath = unpackedAlpha
                           texName = str(Path(absPath).stem)
                           deleteList.append(unpackedAlpha)
                    if absPath and  data.TexEmbededExportScript != None:
                        if "Normal" in tex.text and data.TexEmbededExportScript == "WuwaNormal" and tex.Channel != "Alpha":
                            unpackedTexs = extract_packed_textures_to_file(absPath,projpath,log=self._log)
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
                self.report({'INFO'}, f"删除临时文件: {file}")
                os.remove(file)

    def export_artdefs(self,context,data:CMT_Exporter_Settings):
        def insert_artdef_element(parentnode,guard_name,temptext):
            """已存在同名 Element 则跳过，否则插入模板片段。"""
            if find_element_by_collection_name(root,"Element","m_Name","text",guard_name): return
            append_xml_fragment(dom,parentnode,temptext)

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
                    insert_artdef_element(pNode,inst.Type,get_bins_template(inst.Type,"Body","Any",inst.value))
                    
                    pNode = find_element_by_collection_name(root,"Element","m_CollectionName","text","UnitMemberTypes")
                    insert_artdef_element(pNode,inst.Type,get_members_template(inst.Type,inst.Type + "/Body"))
                    
                    pNode = find_element_by_collection_name(root,"Element","m_CollectionName","text","Units")
                    insert_artdef_element(pNode,inst.Type,get_units_template(inst.Type,inst.Type))
                    
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

        if data.IsExportModel and not self.export_models(context,data):
            return {"CANCELLED"}

            
        if data.IsExportAnimation:
            self.export_animations(context,data)

        
        if data.IsGenerateRef:
            self.export_refs(context,data)

            
        if data.IsExportMaterial:
            self.export_materials(context,data)
        
        if data.IsExportArtdef:
            self.export_artdefs(context,data)
            
        

        return {"FINISHED"}

class CMT_Exporter_OT_AddGeometry(NamedItemDialogOperator):
    bl_idname = "cmt.exporter_ot_addgeometry"
    bl_label = "新建模型文件"
    bl_description = "新建模型文件"

    name_field = "Name"
    list_attr = "GeoList"

    Name: bpy.props.StringProperty(
        name="文件名",
        default=""
    )

    def item_added(self, context, data, item, name):
        item.Class = "DecalGeometry"
        data.GeoName = name
    
class CMT_Exporter_OT_RemoveGeometry(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_removegeometry"
    bl_label = "删除模型文件"
    bl_description ="删除模型文件"

    def execute(self, context : bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        geoList = data.GeoList
        geoIndex = data.CurrentGeoIndex
        geoFileName = geoList[geoIndex].FileName

        for ast in data.AstList:
            to_remove = []
            for i, geo_ref in enumerate(ast.Geometries):
                if geo_ref.value == geoFileName:
                    to_remove.append(i)
            for i in reversed(to_remove):
                ast.Geometries.remove(i)
            if to_remove:
                _report(f"已删除 Ast [{ast.FileName}] 中对模型 [{geoFileName}] 的引用")

        geoList.remove(geoIndex)
        if len(geoList) > 0:
            data.GeoName = geoList[min(geoIndex, len(geoList) - 1)].FileName

        return {"FINISHED"}

class CMT_Exporter_OT_AddMesh(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_addmesh"
    bl_label = ""
    bl_description ="将所有选中的网格模型添加到导出列表"

    def execute(self, context : bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        meshList = data.GeoList[data.CurrentGeoIndex].Geometries

        selectedMeshes = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not selectedMeshes:
            meshList.add()  # 留一个空槽位，供用户在下拉列表中手动指定网格
            return {"FINISHED"}

        alreadyListed = {item.value for item in meshList if item.value is not None}
        for obj in selectedMeshes:
            if obj not in alreadyListed:
                meshList.add().value = obj
                alreadyListed.add(obj)
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
        data = context.scene.CMT.ExporterSettings
        item = data.AnimationList.add()
        default_class = default_anm_class(data)
        if default_class:
            item.Class = default_class

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
        default_class = default_anm_class(data)
        if keyword != "":
            for action in bpy.data.actions:
                if keyword in action.name:
                    if not any( action  is anm.value for anm in data.AnimationList):
                        item = animationList.add()
                        item.value = action
                        if default_class:
                            item.Class = default_class
        return {"FINISHED"}
    
class CMT_Exporter_OT_AddAst(NamedItemDialogOperator):
    bl_idname = "cmt.exporter_ot_addast"
    bl_label = "新建Ast"
    bl_description = "新建Ast"

    name_field = "AstName"
    list_attr = "AstList"

    AstName: bpy.props.StringProperty(
        name="文件名",
        default=""
    )

    def item_added(self, context, data, item, name):
        data.AstName = name
        ast_dsg_update(item, context)
            
class CMT_Exporter_OT_RemoveAst(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_removeast"
    bl_label = "删除Ast"
    bl_description ="删除当前Ast"

    def execute(self, context : bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        astList = data.AstList
        removedIndex = data.CurrentAstIndex
        astList.remove(removedIndex)
        if len(astList) > 0:
            data.AstName = astList[min(removedIndex, len(astList) - 1)].FileName
        return {"FINISHED"}
    
class CMT_Exporter_OT_AddRef(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_addref"
    bl_label = ""
    bl_description ="添加引用"

    def execute(self, context : bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        instance = data.AstList[data.CurrentAstIndex]
        refType = data.AstShowProperty
        refs = getattr(instance, refType)
        if refType == "Geometries":
            # 几何引用最多一条：列表为空时才新增。
            if len(refs) == 0:
                refs.add()
            matlist_refresh(data, context)
        else:
            refs.add()

        return {"FINISHED"}
    
class CMT_Exporter_OT_RemoveRef(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_removeref"
    bl_label = ""
    bl_description ="移除选中的引用"

    def execute(self, context:bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        instance = data.AstList[data.CurrentAstIndex]
        refType = data.AstShowProperty
        getattr(instance, refType).remove(instance.ActivedPropertyIndex)
        if refType == "Geometries":
            matlist_refresh(data, context)

        return {"FINISHED"}

class CMT_Exporter_OT_AddArtdefRef(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_addartdefref"
    bl_label = ""
    bl_description ="添加引用"

    def execute(self, context : bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        if len(data.ArtdefList) == 0:
            self.report({"WARNING"}, "Artdef 列表尚未初始化：请取消勾选后再勾选「是否导出Artdef」")
            return {"CANCELLED"}
        artdef = data.ArtdefList[data.CurrentArtdefIndex]
        artdef.Instances.add()
        

        return {"FINISHED"}
    
class CMT_Exporter_OT_RemoveArtdefRef(bpy.types.Operator):
    bl_idname = "cmt.exporter_ot_removeartdefref"
    bl_label = ""
    bl_description ="移除选中的引用"

    def execute(self, context:bpy.types.Context):
        data = context.scene.CMT.ExporterSettings
        if len(data.ArtdefList) == 0:
            self.report({"WARNING"}, "Artdef 列表尚未初始化：请取消勾选后再勾选「是否导出Artdef」")
            return {"CANCELLED"}
        artdef = data.ArtdefList[data.CurrentArtdefIndex]
        if len(artdef.Instances) == 0:
            self.report({"WARNING"}, "没有可移除的引用")
            return {"CANCELLED"}
        artdef.Instances.remove(artdef.ActivedPropertyIndex)
        
        return {"FINISHED"}
    
class CMT_Exporter_OT_ModifyMatTypeByKeywords(bpy.types.Operator):
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
                    self.report({'INFO'}, f"修改材质类型: {mat.FileName}")
            
        
        
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

