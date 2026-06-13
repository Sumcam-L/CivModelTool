import bpy
from .utils import get_bone_items

def poll_shape_key_action(self, action):
    return any("key_blocks" in fc.data_path for fc in action.fcurves)

class CMT_S2B_ShapeKeyAnimItem(bpy.types.PropertyGroup):
    action: bpy.props.PointerProperty(
        type=bpy.types.Action,
        poll=poll_shape_key_action
    )

class CMT_S2B_Settings(bpy.types.PropertyGroup):
    AbandonmentRate : bpy.props.IntProperty(
        name="舍弃率（%）",
        description="当顶点的位移量小于最大位移顶点的位移乘以该值时，将被忽略",
        default=0,
        min=0,
        max=100,
    )
    CurrentArmature : bpy.props.PointerProperty(
        name="目标骨架",
        type=bpy.types.Object,
        description="选择现有骨架",
        poll=lambda self, obj: obj.type == "ARMATURE",
    )

    ParentBone : bpy.props.EnumProperty(
        name="父骨骼（可留空）", description="父骨骼名称", items=get_bone_items
    )
    TargetMesh : bpy.props.PointerProperty(
        name="目标网格",
        type=bpy.types.Object,
        description="目标网格",
        poll=lambda self, obj: obj.type == "MESH",
    )
    WeightSharing : bpy.props.BoolProperty(
        name="权重合并",
        description="偏移量相同的顶点共用一根骨骼，可以减少骨骼数量",
        default=True,
    )
    DirectionTolerance : bpy.props.FloatProperty(
        name="方向容差",
        description="方向容差值，值越大同方向的顶点越容易被合并（0.0-1.0）",
        default=0.01,
        min=0.0,
        max=1.0,
    )
    MaxBones : bpy.props.IntProperty(
        name="骨骼数量限制",
        description="自动分割网格时的单个网格最大骨骼数量",
        default=256,
        min=0,
    )
    ShapeKeyAnimList : bpy.props.CollectionProperty(
        type=CMT_S2B_ShapeKeyAnimItem
    )
    ShapeKeyAnimListIndex : bpy.props.IntProperty(
        name="当前形态键索引", default=0
    )