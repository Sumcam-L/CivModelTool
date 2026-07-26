import os
import sys
import threading

import bpy

from . import core

ROOT_PACKAGE = __package__.split(".")[0]
# cmt_updater/operations.py -> cmt_updater -> 插件根目录
ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_local_version():
    return tuple(sys.modules[ROOT_PACKAGE].bl_info["version"])


def _redraw():
    """在主线程刷新所有区域,让面板显示最新状态。"""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()
    return None  # 一次性 timer


def request_redraw():
    """线程安全:通过 timer 请求主线程重绘。"""
    bpy.app.timers.register(_redraw, first_interval=0.0)


def _check_worker():
    try:
        remote = core.fetch_remote_version()
        core.state.remote_version = remote
        if remote > get_local_version():
            core.state.status = "update_available"
        else:
            core.state.status = "up_to_date"
    except Exception as e:
        core.state.status = "error"
        core.state.error_msg = str(e)
        core.state.error_source = "check"
    request_redraw()


def start_check():
    if core.state.status in ("checking", "updating"):
        return
    core.state.status = "checking"
    core.state.error_msg = ""
    core.state.error_source = ""
    threading.Thread(target=_check_worker, daemon=True).start()


def _do_reload():
    """主线程执行热重载。"""
    print("[Civ6ModelTool] 更新完成,正在热重载插件...")
    try:
        bpy.ops.preferences.addon_disable(module=ROOT_PACKAGE)
        bpy.ops.preferences.addon_enable(module=ROOT_PACKAGE)
        print("[Civ6ModelTool] 热重载完成")
    except Exception as e:
        print(f"[Civ6ModelTool] 热重载失败,请手动重启 Blender: {e}")
    return None


def _update_worker():
    try:
        core.download_and_install(ADDON_DIR)
    except Exception as e:
        core.state.status = "error"
        core.state.error_msg = str(e)
        core.state.error_source = "update"
        request_redraw()
        return
    core.state.status = "idle"
    # 热重载必须在主线程执行
    bpy.app.timers.register(_do_reload, first_interval=0.5)


def start_update():
    if core.state.status == "updating":
        return
    core.state.status = "updating"
    core.state.error_msg = ""
    core.state.error_source = ""
    request_redraw()
    threading.Thread(target=_update_worker, daemon=True).start()


class CMT_OT_CheckUpdate(bpy.types.Operator):
    bl_idname = "cmt.updater_check"
    bl_label = "检查更新"
    bl_description = "从 GitHub 检查是否有新版本"

    def execute(self, context):
        start_check()
        return {"FINISHED"}


class CMT_OT_RunUpdate(bpy.types.Operator):
    bl_idname = "cmt.updater_run"
    bl_label = "立即更新"
    bl_description = "下载最新代码并热重载插件"

    def execute(self, context):
        start_update()
        return {"FINISHED"}
