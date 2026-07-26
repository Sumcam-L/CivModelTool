import bpy

from . import core
from .operations import get_local_version


def _version_str(v):
    return f"{v[0]}.{v[1]}.{v[2]}"


class CMT_AddonPreferences(bpy.types.AddonPreferences):
    # bl_idname 必须等于插件顶层包名
    bl_idname = __package__.split(".")[0]

    auto_check_update: bpy.props.BoolProperty(
        name="启动时自动检查更新",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        s = core.state

        layout.prop(self, "auto_check_update")

        box = layout.box()
        row = box.row()
        row.label(text=f"当前版本: {_version_str(get_local_version())}")
        if s.remote_version:
            row.label(text=f"远程版本: {_version_str(s.remote_version)}")

        if s.status == "checking":
            box.label(text="正在检查更新...")
        elif s.status == "updating":
            box.label(text="正在下载更新...")
        elif s.status == "up_to_date":
            box.label(text="已是最新版本", icon="CHECKMARK")
        elif s.status == "update_available":
            box.label(text="发现新版本", icon="INFO")
        elif s.status == "error":
            box.label(text=f"出错: {s.error_msg}", icon="ERROR")

        row = box.row()
        sub = row.row()
        sub.enabled = s.status not in ("checking", "updating")
        sub.operator("cmt.updater_check", text="检查更新")
        if s.status == "update_available" or (
            s.status == "error" and s.error_source == "update"
        ):
            sub2 = row.row()
            sub2.operator("cmt.updater_run", text="下载并更新")
