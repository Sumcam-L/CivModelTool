import bpy
from .panels import CMT_S2B_PT_Panel, CMT_S2B_UL_ShapeKeyAnimList, CMT_S2B_OT_AddShapeKeyAnim, CMT_S2B_OT_RemoveShapeKeyAnim
from .properties import CMT_S2B_Settings, CMT_S2B_ShapeKeyAnimItem
from .operations import CMT_S2B_OT_Convert,CMT_S2B_OT_ClearShapeKey,CMT_S2B_OT_EditSeparateMesh,CMT_S2B_OT_AutoSeparateMesh


classes = [
    CMT_S2B_ShapeKeyAnimItem,
    CMT_S2B_UL_ShapeKeyAnimList,
    CMT_S2B_OT_AddShapeKeyAnim,
    CMT_S2B_OT_RemoveShapeKeyAnim,
    CMT_S2B_PT_Panel,
    CMT_S2B_Settings,
    CMT_S2B_OT_Convert,
    CMT_S2B_OT_ClearShapeKey,
    CMT_S2B_OT_EditSeparateMesh,
    CMT_S2B_OT_AutoSeparateMesh,
]
def get_classes_from_module(module):
    classes = []

    for name, obj in module.__dict__.items():
        if isinstance(obj, type) and obj.__module__ == module.__name__:
            classes.append(obj)

    return classes
def register() -> None:
    for tClass in classes:
        bpy.utils.register_class(tClass)


def unregister() -> None:
    for tClass in classes:
        bpy.utils.unregister_class(tClass)


if __name__ == "__main__":
    register()
