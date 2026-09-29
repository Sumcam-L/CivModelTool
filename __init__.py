import sys

import bpy

from . import cmt_shapekey_to_bone
from . import cmt_ordinary_tool
from . import cmt_exporter
from . import cmt_updater
from .cmt_translations import cmt_translations_dict

bl_info = {
    "name": "Civ6ModelTool",
    "author": "Sumcam",
    "version": (1, 0, 0),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar > Civ6ModelTool",
    "category": "Object",
}

package_name = __package__


class Civ6ModelTool(bpy.types.PropertyGroup):
    S2BSettings: bpy.props.PointerProperty(type=cmt_shapekey_to_bone.properties.CMT_S2B_Settings)
    OTSettings: bpy.props.PointerProperty(type=cmt_ordinary_tool.properties.CMT_OT_Settings)
    ExporterSettings: bpy.props.PointerProperty(type=cmt_exporter.properties.CMT_Exporter_Settings)


def register() -> None:
    try:
        cmt_updater.register()
        cmt_ordinary_tool.register()
        cmt_exporter.register()
        cmt_shapekey_to_bone.register()

        bpy.utils.register_class(Civ6ModelTool)
        bpy.types.Scene.CMT = bpy.props.PointerProperty(type=Civ6ModelTool)
        bpy.app.translations.register(__name__, cmt_translations_dict)
    except Exception:
        # 注册失败时清掉已加载的模块：否则 Blender 再次勾选插件时不会重新
        # 读取文件，修改无法生效。清理后重新抛出，让失败在界面上可见。
        cleanup_modules(package_name)
        raise


def unregister() -> None:
    # 与 register 严格逆序：先拆掉引用子包类的上层属性，再注销子包
    bpy.app.translations.unregister(__name__)

    del bpy.types.Scene.CMT
    bpy.utils.unregister_class(Civ6ModelTool)

    cmt_shapekey_to_bone.unregister()
    cmt_exporter.unregister()
    cmt_ordinary_tool.unregister()
    cmt_updater.unregister()

    cleanup_modules(package_name)


def cleanup_modules(pkg_name):
    """把本插件已加载的模块从 sys.modules 中移除，使下次导入重新读取文件。"""
    for name in list(sys.modules.keys()):
        if name.startswith(pkg_name):
            del sys.modules[name]


if __name__ == "__main__":
    register()
