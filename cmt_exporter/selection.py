"""选择项与列表下标之间的换算。禁止 import bpy，保证可在 Blender 外测试。"""

def index_of_filename(collection, filename):
    """返回 collection 中 FileName 等于 filename 的条目下标；找不到时返回 0。"""
    for index, item in enumerate(collection):
        if item.FileName == filename:
            return index
    return 0

def index_of_name(names, name):
    """返回 names 中等于 name 的下标；找不到时返回 0。"""
    for index, value in enumerate(names):
        if value == name:
            return index
    return 0
