import bpy
from mathutils import Vector

from collections import defaultdict
import time
from collections import deque

from .utils import*

class CMT_S2B_OT_Convert(bpy.types.Operator):
    
    bl_idname = "cmt.s2b_ot_convert"
    bl_description ="将形态键动画转换为骨骼动画"
    bl_label = "Shape Key to Bone"
    bl_options = {"REGISTER", "UNDO"}
    name = "转换动画"

    def execute(self, context):
        settings = context.scene.CMT.S2BSettings
        obj = settings.TargetMesh
        currentArmature = settings.CurrentArmature
        abandonmentRate = settings.AbandonmentRate
        weightSharing = settings.WeightSharing
        actionName = settings.ActionName
        useExistAction = settings.UseExistAction
        start = bpy.context.scene.frame_start
        end = bpy.context.scene.frame_end

        startTime = time.time()
        startTime1 = startTime
        print("开始获取顶点数据")
        if not obj or not obj.data.shape_keys:
            print("请选中一个包含形态键的对象")
        else:
            shape_keys = obj.data.shape_keys
            shapekeyaction = (
                shape_keys.animation_data.action if shape_keys.animation_data else None
            )
            if not shapekeyaction:
                print("该对象的形态键没有动画数据！")
            else:
                print(f"找到动画: {shapekeyaction.name}")
                obj.hide_set(False)

                for fcu in shapekeyaction.fcurves:
                    if fcu.keyframe_points:
                        frame = max(
                            kp.co[0] for kp in fcu.keyframe_points
                        )  # kp.co[0] 是帧号
                        if end == bpy.context.scene.frame_end:
                            end = frame
                        if frame > end:
                            end = frame
                bpy.context.view_layer.objects.active = obj
                # 切换到对象模式
                bpy.ops.object.mode_set(mode="OBJECT")

                # 创建新的骨架
                if currentArmature == None:
                    bpy.ops.object.armature_add(enter_editmode=True)
                    armature = bpy.context.object
                    armature.name = "ShapeKey_Armature"
                else:
                    armature = currentArmature

                basis_key = shape_keys.key_blocks[0]

                sameOffset = defaultdict(int)
                influence_vertices = defaultdict(int)

                for fcurve in shapekeyaction.fcurves:
                    data_path = fcurve.data_path
                    if "key_blocks" in data_path:
                        shape_key_name = data_path.split('"')[1]
                        shape_key = shape_keys.key_blocks.get(shape_key_name)

                        if not shape_key:
                            continue

                        print(f"\n形态键: {shape_key_name}")

                        for index, vert in enumerate(shape_key.data):
                            shape_offset = vert.co - basis_key.data[index].co
                            if shape_offset.length > 1e-4:
                                # vector_tuple = tuple(round(component, 4) for component in vert.co)

                                if index not in influence_vertices:
                                    influence_vertices[index] = {
                                        "RelatedShapeKeyCount": 0,
                                        "RelatedShapeKeyInfo": {},
                                        "BoneName": "",
                                    }

                                bone_name = f"SKB_{round(vert.co.x,4)}{round(vert.co.y,4)}{round(vert.co.z,4)}"
                                influence_vertices[index]["RelatedShapeKeyInfo"][
                                    shape_key_name
                                ] = shape_offset
                                influence_vertices[index]["BoneName"] = bone_name
                                influence_vertices[index]["RelatedShapeKeyCount"] += 1
                                influence_vertices[index]["Dispose"] = False

                                vector_tuple1 = tuple(
                                    round(component, 4) for component in shape_offset
                                )
                                if vector_tuple1 not in sameOffset:
                                    sameOffset[vector_tuple1] = {}

                                if shape_key_name not in sameOffset[vector_tuple1]:
                                    sameOffset[vector_tuple1][shape_key_name] = []

                                sameOffset[vector_tuple1][shape_key_name].append(index)
                armature.hide_set(False)
                bpy.context.view_layer.objects.active = armature
                # bpy.context.view_layer.objects.active = bpy.data.objects[1]
                # armature.select_set(True)
                bpy.ops.object.mode_set(mode="EDIT")
                parentBone = None
                if "SKB_Root" not in armature.data.edit_bones:
                    parentBone = armature.data.edit_bones.new("SKB_Root")
                    parentBone.head = (0, 0, 0)  # 骨骼的起点
                    parentBone.tail = (0, 0, 1)  # 骨骼的终点
                else:
                    parentBone = armature.data.edit_bones["SKB_Root"]
                parentBone1 = None
                if bpy.context.scene.ShapeKeyToBone_ParentBone == "None":
                    parentBone1 = None
                else:
                    parentBone1 = currentArmature.data.edit_bones[
                        bpy.context.scene.ShapeKeyToBone_ParentBone
                    ]
                if parentBone1:
                    parentBone.parent = parentBone1

                if weightSharing:
                    for vector_tuple1, key in sameOffset.items():
                        for shape_key_name, vertexCoGroup in key.items():
                            combineName = ""
                            for i, index in enumerate(vertexCoGroup):
                                # print(influence_vertices[index]["RelatedShapeKeyCount"])
                                if (
                                    influence_vertices[index]["RelatedShapeKeyCount"]
                                    == 1
                                ):
                                    influence_vertices[index]["Dispose"] = True
                                    if combineName == "":
                                        influence_vertices[index]["Dispose"] = False
                                        combineName = influence_vertices[index][
                                            "BoneName"
                                        ]
                                    influence_vertices[index]["BoneName"] = combineName

                print(
                    f"获取顶点数据完成，共{len(influence_vertices)}个受影响顶点，耗时：{time.time() - startTime1:.4f}"
                )

                startTime1 = time.time()
                print("开始计算动画数据")

                transformations = {}
                abandonList = {}
                maxOffset = 0
                frameCount = 0
                frame = start
                while frame <= end:
                    bpy.context.scene.frame_set(frame)
                    depsgraph = bpy.context.evaluated_depsgraph_get()
                    obj_eval = obj.evaluated_get(depsgraph)
                    mesh_eval = obj_eval.to_mesh()
                    for v in mesh_eval.vertices:
                        if v.index in influence_vertices:
                            bone_name = influence_vertices[v.index]["BoneName"]
                            bone = armature.pose.bones.get(bone_name)
                            if not influence_vertices[v.index]["Dispose"]:
                                world_co = obj_eval.matrix_world @ v.co
                                relativeCo = world_co - basis_key.data[v.index].co
                                transformations.setdefault(bone_name, [])
                                if bone_name not in abandonList:
                                    abandonList[bone_name] = 0
                                abandonList[bone_name] += relativeCo.length
                                if frame == end and abandonList[bone_name] > maxOffset:
                                    maxOffset = abandonList[bone_name]
                                transformations[bone_name].append(
                                    {"Frame": frame, "Co": relativeCo}
                                )
                                # transformations[bone_name][frame] = relativeCo
                                frameCount += 1

                    obj_eval.to_mesh_clear()
                    frame = frame + 1

                print(f"计算动画数据完成，耗时：{time.time() - startTime1:.4f}")
                if abandonmentRate > 0:
                    startTime1 = time.time()
                    delCount = 0
                    print("开始舍弃数据")
                    for i, v in abandonList.items():
                        if v <= maxOffset * abandonmentRate / 100:
                            del transformations[i]
                            delCount += 1
                    print(
                        f"舍弃数据完成,共删除{delCount}根骨骼的数据，耗时：{time.time() - startTime1:.4f}"
                    )

                print("开始绑定骨骼")
                boneCount = 0
                startTime1 = time.time()
                for index, vertexInfo in influence_vertices.items():

                    if (
                        vertexInfo["BoneName"] not in armature.data.edit_bones
                        and vertexInfo["BoneName"] in transformations
                    ):
                        create_bone_for_vertex(
                            armature,
                            vertexInfo["BoneName"],
                            basis_key.data[index].co,
                            parentBone,
                        )
                        boneCount += 1

                    vg = obj.vertex_groups.get(vertexInfo["BoneName"])  # 获取已有顶点组
                    if vg is None:
                        vg = obj.vertex_groups.new(
                            name=vertexInfo["BoneName"]
                        )  # 创建顶点组
                    vg.add([index], 1.0, "REPLACE")  # 1.0 是权重
                    normalize(obj, index, armature)

                bpy.ops.object.mode_set(mode="POSE")
                print(
                    f"绑定骨骼完成，共新增{boneCount}根骨骼，耗时：{time.time() - startTime1:.4f}"
                )

                startTime1 = time.time()
                print("开始清理冗余数据")
                # 清理冗余关键帧

                threshold = 1e-4
                # transformations_backup = transformations
                for bone_name, value in transformations.items():
                    index1 = 0
                    while index1 < len(value):
                        FrameInfo = value[index1]
                        frame1 = FrameInfo["Frame"]
                        relativeCo = FrameInfo["Co"]
                        if frame1 != start and frame1 != end:
                            if (
                                relativeCo - value[index1 - 1]["Co"]
                            ).length_squared < threshold**2:
                                del transformations[bone_name][index1]
                                index1 -= 1
                                frameCount -= 1
                            else:
                                tRatio = 0.5
                                theoValue = (
                                    transformations[bone_name][index1 - 1]["Co"]
                                    + (
                                        transformations[bone_name][index1 + 1]["Co"]
                                        - transformations[bone_name][index1 - 1]["Co"]
                                    )
                                    * tRatio
                                )
                                if (
                                    relativeCo - theoValue
                                ).length_squared < threshold**2:
                                    del transformations[bone_name][index1]
                                    index1 -= 1
                                    frameCount -= 1

                        index1 += 1

                frameIndex = 1
                action = None
                print(f"清理冗余数据完成，耗时：{time.time() - startTime1:.4f}")
                startTime1 = time.time()

                print("开始插入关键帧")
                if actionName == "":
                    if useExistAction and armature.animation_data.action is not None:
                        actionName = armature.animation_data.action.name
                    else:
                        actionName = "Action"

                # 使用现有的动作还是新建一个动作
                if useExistAction and actionName in bpy.data.actions:
                    action = bpy.data.actions[actionName]
                else:
                    action = bpy.data.actions.new(name=actionName)
                    # 必须要手动设定 name，因为在 new 时，如果名字已存在，会因为自动规避而把自身改名为后缀为 .xxx 的动作，导致名字与需要的不一样
                    # 当主动设置name时，则会反过来自动把已存在名字的动作那个进行规避改名，从而保证当前新建的动作名字一定是指定的名字
                    action.name = actionName

                # all_bone_fcurves = []
                for bone_name, value in transformations.items():
                    fcurves = [None] * 3
                    data_path = f'pose.bones["{bone_name}"].location'
                    for axis_i in range(3):
                        channel_i = axis_i
                        fcurves[channel_i] = get_or_create_fcurve(
                            action, bone_name, channel_i, axis_i, data_path=data_path
                        )

                    # for frame1, relativeCo in value.items():
                    #     bone1 = armature.pose.bones.get(bone_name)

                    #     print(f"正在添加关键帧：{frameIndex}/{frameCount}")
                    #     add_keyframe(bone1, frame1, relativeCo)
                    #     frameIndex += 1
                    f_index = 0
                    for fc_i, fc in enumerate(fcurves):
                        # 支持就地插入
                        f_index += 1
                        start_kps = len(fc.keyframe_points)
                        fc.keyframe_points.add(len(value))
                        for frameInfo, kp2 in zip(
                            value, fc.keyframe_points[start_kps:]
                        ):
                            frame_id = frameInfo["Frame"]
                            valueY = frameInfo["Co"][fc_i]
                            # kp1 = [t[0], t[1], t[2]]

                            # 第一个值是帧号，第二个是值
                            kp2.co = (frame_id, valueY)
                            # 默认插值使用线性。
                            kp2.interpolation = "LINEAR"
                            if f_index == 1:
                                frameIndex += 1
                                if (frameIndex / frameCount) % 0.25 == 0:
                                    print(
                                        f"已完成{(frameIndex/frameCount) * 100}%  {frameIndex}/{frameCount}"
                                    )

                        # 自动排序关键帧，确保关键帧按时间顺序排列，这在clean时非常重要
                        fc.update()
                    # all_bone_fcurves.extend(fcurves)
                print(
                    f"插入关键帧完成，共插入{frameCount}个关键帧，耗时：{time.time() - startTime1:.4f}"
                )
                # startTime1 = time.time()

                print(
                    f"形态键动画已转换为骨骼动画，总耗时:{time.time() - startTime:.4f}"
                )

                try:
                    armature.animation_data.action = action
                except AttributeError as e:
                    # print("Catch exception.", str(e.with_traceback()))
                    # ！破坏性操作，但是符合多数人的直觉
                    # 激活新动作失败，多半是因为使用了NLA序列
                    # 直接清除掉只读的动作堆栈就行
                    armature.animation_data_clear()
                    armature.animation_data_create()
                    armature.animation_data.action = action

                # obj = bpy.context.scene.ShapeKeyToBone_TargetMesh
                shape_keys = obj.data.shape_keys
                if shape_keys:
                    if shape_keys.animation_data and shape_keys.animation_data.action:
                        shape_keys.animation_data.action = None
                    for i, key_block in enumerate(shape_keys.key_blocks):
                        if key_block.name != "Basis" or i != 0:
                            key_block.value = 0.0

        return {"FINISHED"}

class CMT_S2B_OT_ClearShapeKey(bpy.types.Operator):

    bl_idname = "cmt.s2b_ot_clearshapekey"
    bl_description ="卸载形态键动画并恢复基型"
    bl_label = "Shape Key to Bone"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        obj = bpy.context.scene.ShapeKeyToBone_TargetMesh
        shape_keys = obj.data.shape_keys
        if shape_keys:
            if shape_keys.animation_data and shape_keys.animation_data.action:
                shape_keys.animation_data.action = None
            for i, key_block in enumerate(shape_keys.key_blocks):
                if key_block.name != "Basis" or i != 0:
                    key_block.value = 0.0
        return {"FINISHED"}

class CMT_S2B_OT_EditSeparateMesh(bpy.types.Operator):
    bl_idname = "cmt.s2b_ot_editseparatemesh"
    bl_label = "Separate Mesh"
    bl_description ="分离选中的顶点"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):

        # obj = bpy.context.scene.ShapeKeyToBone_TargetMesh
        obj = bpy.context.active_object

        if obj == None:
            self.report("请选择一个网格")
            return

        normals = {}
        bpy.ops.object.mode_set(mode="OBJECT")  # 确保在对象模式

        obj.data.use_auto_smooth = True  # 启用自动平滑
        obj.data.calc_normals_split()  # 计算默认法线

        for polyIndex, poly in enumerate(obj.data.polygons):
            center = tuple(round(c, 6) for c in poly.center)
            area = round(poly.area, 6)
            normal = tuple(round(n, 6) for n in poly.normal)
            start = poly.loop_start
            total = poly.loop_total
            key = (total, center, area, normal)
            normals.setdefault(key, [])
            for li in range(start, start + total):
                loop = obj.data.loops[li]
                normals[key].append(loop.normal.copy())

        separateSelectedPart(normals)

        return {"FINISHED"}

class CMT_S2B_OT_AutoSeparateMesh(bpy.types.Operator):
    bl_idname = "cmt.s2b_ot_autoseparatemesh"
    bl_label = "Separate Mesh"
    bl_description ="按照设置的每个网格骨骼上限自动分离模型"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bpy.ops.object.mode_set(mode="EDIT")
        obj = context.scene.ShapeKeyToBone_TargetMesh
        arm = context.scene.ShapeKeyToBone_CurrentArmature
        max_bones = context.scene.S2B_MaxBones
        bone_names = [b.name for b in arm.data.bones]

        mesh = obj.data
        verts = mesh.vertices
        polys = mesh.polygons

        # 1. 建邻接表
        vertex_to_polys = {v.index: set() for v in verts}
        for poly in polys:
            for vi in poly.vertices:
                vertex_to_polys[vi].add(poly.index)

        # 2️⃣ 建立面邻接表
        poly_adjacency = {p.index: set() for p in polys}

        for poly in polys:
            # 对当前面的每个顶点，找到与它相连的其他面
            neighbor_polys = set()
            for vi in poly.vertices:
                neighbor_polys.update(vertex_to_polys[vi])

            # 移除自身
            neighbor_polys.discard(poly.index)
            poly_adjacency[poly.index] = neighbor_polys

        visited = set()
        groups = []

        # 2. 遍历所有顶点
        for poly in polys:
            if poly.index in visited:
                continue

            # BFS 找连通分量
            queue = deque([poly.index])
            region = []
            bones = {}

            while queue:
                vi = queue.popleft()
                if vi in visited:
                    continue
                if len(bones) >= max_bones:
                    break

                needBreak = False
                # 顶点骨骼
                for vid in polys[vi].vertices:
                    v_bones = {
                        obj.vertex_groups[g.group].name: 1
                        for g in verts[vid].groups
                        if obj.vertex_groups[g.group].name in bone_names
                        and obj.vertex_groups[g.group].name not in bones
                    }
                    if len(bones) + len(v_bones) > max_bones:
                        needBreak = True
                        break
                    bones.update(v_bones)

                if needBreak:
                    break

                visited.add(vi)
                region.append(vi)

                # 如果超过限制，停止扩展
                # print(len(bones))

                # verts[vi].select = True
                # 扩展邻居
                for nei in poly_adjacency[vi]:
                    if nei not in visited:
                        queue.append(nei)

            groups.append((region, bones))

        for index, part in enumerate(groups):
            bones = {}
            for i, pid in enumerate(part[0]):
                for vid in polys[pid].vertices:
                    v_bones = {
                        obj.vertex_groups[g.group].name: 1
                        for g in verts[vid].groups
                        if obj.vertex_groups[g.group].name in bone_names
                        and obj.vertex_groups[g.group].name not in bones
                    }
                    bones.update(v_bones)
            print(index, len(part[0]), len(part[1]), len(bones))

        normals = {}
        bpy.ops.object.mode_set(mode="OBJECT")  # 确保在对象模式
        bpy.ops.object.select_all(action="DESELECT")
        obj.data.use_auto_smooth = True  # 启用自动平滑
        obj.data.calc_normals_split()  # 计算默认法线

        for polyIndex, poly in enumerate(obj.data.polygons):
            center = tuple(round(c, 6) for c in poly.center)
            area = round(poly.area, 6)
            normal = tuple(round(n, 6) for n in poly.normal)
            start = poly.loop_start
            total = poly.loop_total
            key = (total, center, area, normal)
            normals.setdefault(key, [])
            for li in range(start, start + total):
                loop = obj.data.loops[li]
                normals[key].append(loop.normal.copy())

        for index, part in enumerate(groups):
            groupName = "AutoSeparatePart" + str(index)
            vg = obj.vertex_groups.get(groupName)  # 获取已有顶点组
            if vg is None:
                vg = obj.vertex_groups.new(name=groupName)  # 创建顶点组

            vertList = []
            for pId in part[0]:
                for v1 in polys[pId].vertices:
                    vertList.append(v1)

            vg.add(vertList, 1.0, "REPLACE")  # 1.0 是权重

        index1 = 0
        while index1 < len(groups):
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="DESELECT")
            # bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type="FACE")
            obj.vertex_groups.active = obj.vertex_groups[
                "AutoSeparatePart" + str(index1)
            ]
            bpy.ops.object.vertex_group_select()
            vg = obj.vertex_groups.get("AutoSeparatePart" + str(index1))
            obj.vertex_groups.remove(vg)
            separateSelectedPart(normals)

            index1 += 1
        return {"FINISHED"}

