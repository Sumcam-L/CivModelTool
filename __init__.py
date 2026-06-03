import sys
import importlib

bl_info = {
    "name": "Civ6ModelTool",
    "author": "Sumcam",
    "version": (1, 0, 0),
    "blender": (5, 1, 0),
    "location": "View3D > Sidebar > Civ6ModelTool",
    "category": "Object",
}

package_name = __package__

def reload_packages():
    # 找出所有以当前包名开头的已加载模块
    # 例如: CivModelTool.ui, CivModelTool.cmt_shapekey_to_bone.operations 等
    modules_to_reload = [
        name for name in sys.modules 
        if name.startswith(package_name + ".")
    ]
    
    # 按照名称长度倒序排列，确保深层子模块先被重载，父级模块后重载
    for module_name in sorted(modules_to_reload, key=len, reverse=True):
        importlib.reload(sys.modules[module_name])

# 只有在 Blender 运行期间点击 "Reload Scripts" 时才会触发


import bpy
from . import cmt_shapekey_to_bone
from . import cmt_ordinary_tool
from . import cmt_exporter

from .cmt_translations import cmt_translations_dict

class Civ6ModelTool(bpy.types.PropertyGroup):
    S2BSettings:bpy.props.PointerProperty(type=cmt_shapekey_to_bone.properties.CMT_S2B_Settings)
    OTSettings:bpy.props.PointerProperty(type=cmt_ordinary_tool.properties.CMT_OT_Settings)
    ExporterSettings:bpy.props.PointerProperty(type=cmt_exporter.properties.CMT_Exporter_Settings)
    

def register() -> None:
    # 只要内存里有这个包，就说明“加载过”或者“上次坏掉了”
    try:
        ##注册子包
        cmt_shapekey_to_bone.register()
        cmt_ordinary_tool.register()
        cmt_exporter.register()
        ##注册插件基本类
        bpy.utils.register_class(Civ6ModelTool)
        bpy.types.Scene.CMT = bpy.props.PointerProperty(type=Civ6ModelTool)
        
        bpy.app.translations.register(__name__,cmt_translations_dict)
        
    except Exception as e:
        # 3. 如果注册过程中任何一个环节报错
        print(f"\n[Civ6ModelTool] 注册失败，正在自动回滚并清理缓存...\n错误信息: {e}")
        
        # 立即手动触发一次清理，确保 sys.modules 不会被卡死
        # 这样你修改代码后再次勾选，Python 才会重新读取文件
        cleanup_modules(package_name)
    
    

def unregister() -> None:
    del bpy.types.Scene.CMT
    bpy.utils.unregister_class(Civ6ModelTool)
    
    cmt_ordinary_tool.unregister()
    cmt_shapekey_to_bone.unregister()
    cmt_exporter.unregister()
    
    bpy.app.translations.unregister(__name__)
    
    cleanup_modules(package_name)

def cleanup_modules(pkg_name):
    """提取出的清理逻辑，方便多处调用"""
    print("卸载模块")
    for name in list(sys.modules.keys()):
        if name.startswith(pkg_name):
            del sys.modules[name]

if __name__ == "__main__":
    register()
