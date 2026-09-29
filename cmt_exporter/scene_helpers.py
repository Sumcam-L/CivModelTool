"""场景对象与工程路径的小工具。"""
import os
from pathlib import Path

import bpy

def get_parent_armature(obj):
    """获取对象的父级骨架"""
    if obj.parent and obj.parent.type == 'ARMATURE':
        return obj.parent
    return None

def getAbsPathByImage(mat,target):
    for node in mat.node_tree.nodes:
        
        if node.type == "TEX_IMAGE":
            if node.image.name == target:
                return os.path.normpath(bpy.path.abspath(node.image.filepath))

def get_real_project_path(self,context):
    data = context.scene.CMT.ExporterSettings
    if data.ProjectPath != "":
        path = Path(data.ProjectPath)
        projName = path.name
        if Path(path / "Assets").exists():
            return str(path.absolute())
        elif Path(path / projName / "Assets").exists():
            return str(Path(path / projName).absolute())
    
    return ""
