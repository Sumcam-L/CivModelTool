"""共享的类注册逻辑。

各子包只负责声明「哪些模块里定义了要注册的类」，遍历与注册/注销的细节收在这里。

本模块刻意不在导入期 import bpy：只有真正注册时才导入，
因此可以在 Blender 之外被导入和测试。
"""


def iter_classes(module):
    """产出 module 中定义的类,按定义顺序。

    用 __module__ 过滤,排除模块里 import 进来的外来类
    (例如 bpy.types.Operator)。
    """
    return [
        obj for obj in vars(module).values()
        if isinstance(obj, type) and obj.__module__ == module.__name__
    ]


def register_modules(modules):
    """按 modules 的顺序注册其中定义的所有类。"""
    import bpy

    for module in modules:
        for tClass in iter_classes(module):
            bpy.utils.register_class(tClass)


def unregister_modules(modules):
    """按 modules 的顺序注销其中定义的所有类。"""
    import bpy

    for module in modules:
        for tClass in iter_classes(module):
            bpy.utils.unregister_class(tClass)
