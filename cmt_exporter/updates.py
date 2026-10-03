"""bpy.props 的 update 回调：重建列表、清理失效引用。"""
from pathlib import Path

import bpy

from .civ6_data import g_DSGs_action
from .enum_items import get_artdef_items, mat_poll

def ast_dsg_update(self,context):
    anmList = self.Animations
    anmList.clear()
    if len(anmList) == 0:
        for v in sorted(g_DSGs_action[self.DSG]):
            item = self.Animations.add()
            item.AstName = self.FileName
            item.text = v

def project_path_update(self,context):
    def draw(self, context):
        self.layout.label(text="项目路径不正确，请确保资产文件夹已生成（启动一次AssetEditor）")

    data = context.scene.CMT.ExporterSettings
    if data.ProjectPath != "":
        path = Path(data.ProjectPath)
        projName = path.name
        if Path(path / "Assets").exists():
            return 
        elif Path(path / projName / "Assets").exists():
            return
        else:
            data.ProjectPath = ""
            context.window_manager.popup_menu(draw, title="提示", icon='ERROR')

def customscript_path_update(self,context):
    def draw(self, context):
        self.layout.label(text="请选择Python脚本")

    data = context.scene.CMT.ExporterSettings
    if data.TexCustomExportScript != "":
        extension = Path(data.TexCustomExportScript).suffix
        if extension != ".py":
            data.TexCustomExportScript = ""
            context.window_manager.popup_menu(draw, title="提示", icon='ERROR')

def matlist_refresh(self, context):
    data = context.scene.CMT.ExporterSettings
    mats = bpy.data.materials
    
    # 获取符合条件的材质列表
    matlist = [mat for mat in mats if mat_poll(data, mat)]
    matNames = [mat.name for mat in matlist]
    # 先清理不存在的材质
    for i in range(len(data.MaterialList) - 1, -1, -1):
        if data.MaterialList[i].FileName not in matNames:
            data.MaterialList.remove(i)
            
    # 获取已存在的材质名称集合
    existing_names = {v.FileName for v in data.MaterialList}
    
    # 只添加不存在的材质
    for mat in matlist:
        if mat.name not in existing_names:
            item = data.MaterialList.add()
            item.FileName = mat.name

def export_material_update(self,context):
    
    matlist_refresh(self,context)

def export_artdef_update(self,context):
    if len(self.ArtdefList) == 0:
        for i in range(len(get_artdef_items(self,context))):
            self.ArtdefList.add()
