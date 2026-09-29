import bpy

class CMT_OT_Settings(bpy.types.PropertyGroup):
    DeleteLockGroup : bpy.props.BoolProperty(
        name="影响锁定组", description="影响锁定组", default=False
    )
