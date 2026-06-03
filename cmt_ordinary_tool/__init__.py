import bpy
import inspect
from . import panels
from . import properties
from . import operations


modules = [panels,properties,operations]

def get_classes_from_module(module):
    classes = []

    for name, obj in module.__dict__.items():
        if isinstance(obj, type) and obj.__module__ == module.__name__:
            classes.append(obj)

    return classes


def register() -> None:
    for module in modules:
        classes = get_classes_from_module(module)
        for tClass in classes:
            # print("注册：",module.__name__ + " " + tClass.__name__)
            bpy.utils.register_class(tClass)


def unregister() -> None:
    for module in modules:
        classes = get_classes_from_module(module)
        for tClass in classes:
            bpy.utils.unregister_class(tClass)


if __name__ == "__main__":
    register()
