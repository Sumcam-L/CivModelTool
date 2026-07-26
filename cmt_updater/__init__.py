import bpy

from . import core
from . import operations
from . import preferences
from . import ui

modules = [operations, preferences, ui]


def get_classes_from_module(module):
    classes = []
    for name, obj in module.__dict__.items():
        if isinstance(obj, type) and obj.__module__ == module.__name__:
            classes.append(obj)
    return classes


def _startup_check():
    """启动后延迟执行:若偏好设置开启,则后台检查更新。"""
    try:
        root = __package__.split(".")[0]
        prefs = bpy.context.preferences.addons[root].preferences
        if prefs.auto_check_update:
            operations.start_check()
    except Exception as e:
        print(f"[Civ6ModelTool] 启动更新检查失败: {e}")
    return None  # 一次性 timer


def register() -> None:
    for module in modules:
        for tClass in get_classes_from_module(module):
            bpy.utils.register_class(tClass)
    bpy.app.timers.register(_startup_check, first_interval=3.0)


def unregister() -> None:
    if bpy.app.timers.is_registered(_startup_check):
        bpy.app.timers.unregister(_startup_check)
    for module in modules:
        for tClass in get_classes_from_module(module):
            bpy.utils.unregister_class(tClass)
