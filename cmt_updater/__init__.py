import bpy

from . import operations
from . import preferences
from . import ui

from ..registration import register_modules, unregister_modules

modules = [operations, preferences, ui]


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
    register_modules(modules)
    bpy.app.timers.register(_startup_check, first_interval=3.0)


def unregister() -> None:
    if bpy.app.timers.is_registered(_startup_check):
        bpy.app.timers.unregister(_startup_check)
    unregister_modules(modules)
