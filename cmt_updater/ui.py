import bpy

from . import core


class CMT_Updater_PT_Panel(bpy.types.Panel):
    bl_label = "插件更新"
    bl_idname = "CMT_Updater_PT_Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Civ6ModelTool"
    bl_order = 0

    @classmethod
    def poll(cls, context):
        s = core.state
        # 仅在有新版本、更新中、或更新出错时显示
        return s.status in ("update_available", "updating") or (
            s.status == "error" and s.error_source == "update"
        )

    def draw(self, context):
        layout = self.layout
        s = core.state
        if s.status == "update_available":
            v = s.remote_version
            layout.label(
                text=f"发现新版本 v{v[0]}.{v[1]}.{v[2]}", icon="INFO"
            )
            layout.operator("cmt.updater_run", text="立即更新")
        elif s.status == "updating":
            row = layout.row()
            row.enabled = False
            row.operator("cmt.updater_run", text="更新中...")
        elif s.status == "error":
            layout.label(text="更新失败", icon="ERROR")
            layout.label(text=s.error_msg)
            layout.operator("cmt.updater_run", text="重试更新")
