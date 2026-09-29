"""「新建条目」对话框算子的公共基类。

本模块不在 cmt_exporter/__init__.py 的注册白名单（modules）里，
因此基类本身不会被 bpy.utils.register_class 注册。
"""
import bpy


class NamedItemDialogOperator(bpy.types.Operator):
    """弹窗输入名称，在 CollectionProperty 中新建一个带 FileName 的条目。

    子类需给出 bl_idname / bl_label 与输入属性，并按需覆写 item_added；
    name_field 与 list_attr 决定读写的是哪个输入属性与哪个集合。
    """

    name_field = "Name"
    list_attr = "GeoList"

    error: bpy.props.StringProperty(default="")

    def item_added(self, context, data, item, name):
        """条目创建后的钩子，默认无动作。"""

    def execute(self, context: bpy.types.Context):
        if self.error:
            self.report({"ERROR"}, "名字不合法")
            return {"CANCELLED"}
        data = context.scene.CMT.ExporterSettings
        name = getattr(self, self.name_field)
        item = getattr(data, self.list_attr).add()
        item.FileName = name
        self.item_added(context, data, item, name)
        return {"FINISHED"}

    def invoke(self, context, event):
        setattr(self, self.name_field, "")
        self.error = ""
        return context.window_manager.invoke_props_dialog(self)

    def check(self, context):
        items = getattr(context.scene.CMT.ExporterSettings, self.list_attr)
        name = getattr(self, self.name_field)
        if name == "":
            self.error = "名称不能为空"
        elif any(item.FileName == name for item in items):
            self.error = "名称已存在"
        else:
            self.error = ""

    def draw(self, context):
        layout = self.layout
        layout.prop(self, self.name_field)
        if self.error:
            layout.label(text=self.error, icon="ERROR")
