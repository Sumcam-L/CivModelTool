import bpy

from collections import defaultdict
import time

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
        directionTolerance = settings.DirectionTolerance

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

                actions_to_process = []
                for item in settings.ShapeKeyAnimList:
                    if item.action:
                        actions_to_process.append(item.action)
                if not actions_to_process:
                    actions_to_process.append(shapekeyaction)

                animated_shape_keys = set()
                for action in actions_to_process:
                    for fcu in action.fcurves:
                        if "key_blocks" in fcu.data_path:
                            sk_name = fcu.data_path.split('"')[1]
                            animated_shape_keys.add(sk_name)
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

                influence_vertices = defaultdict(int)

                # Phase 1: 收集所有受影响顶点的形态键偏移数据
                for shape_key_name in animated_shape_keys:
                    shape_key = shape_keys.key_blocks.get(shape_key_name)

                    if not shape_key:
                        continue

                    print(f"\n形态键: {shape_key_name}")

                    for index, vert in enumerate(shape_key.data):
                        shape_offset = vert.co - basis_key.data[index].co
                        if shape_offset.length > 1e-4:
                            if index not in influence_vertices:
                                influence_vertices[index] = {
                                    "RelatedShapeKeyCount": 0,
                                    "RelatedShapeKeyInfo": {},
                                    "BoneName": "",
                                }

                            bone_name = f"SKB_{round(vert.co.x,4)}{round(vert.co.y,4)}{round(vert.co.z,4)}"
                            direction = shape_offset.normalized()
                            influence_vertices[index]["RelatedShapeKeyInfo"][
                                shape_key_name
                            ] = {"offset": shape_offset, "direction": direction}
                            influence_vertices[index]["BoneName"] = bone_name
                            influence_vertices[index]["RelatedShapeKeyCount"] += 1
                            influence_vertices[index]["Dispose"] = False
                            influence_vertices[index]["MaxOffsetLength"] = shape_offset.length
                armature.hide_set(False)
                bpy.context.view_layer.objects.active = armature
                bpy.ops.object.mode_set(mode="EDIT")
                parentBone = None
                if "SKB_Root" not in armature.data.edit_bones:
                    parentBone = armature.data.edit_bones.new("SKB_Root")
                    parentBone.head = (0, 0, 0)  # 骨骼的起点
                    parentBone.tail = (0, 0, 1)  # 骨骼的终点
                else:
                    parentBone = armature.data.edit_bones["SKB_Root"]
                parentBone1 = None
                if settings.ParentBone == "None":
                    parentBone1 = None
                else:
                    parentBone1 = currentArmature.data.edit_bones[
                        settings.ParentBone
                    ]
                if parentBone1:
                    parentBone.parent = parentBone1

                if weightSharing:
                    # 第一步：按形态键签名分组（哪些形态键影响这个顶点）
                    signature_groups = defaultdict(list)
                    for index, vinfo in influence_vertices.items():
                        sk_names = tuple(sorted(vinfo["RelatedShapeKeyInfo"].keys()))
                        signature_groups[sk_names].append(index)

                    for sk_names, vertex_indices in signature_groups.items():
                        # 同签名只有一个顶点，无法合并
                        if len(vertex_indices) <= 1:
                            continue

                        # 第二步：同签名内按方向相似性再分组
                        direction_groups = []
                        for idx in vertex_indices:
                            # 取该顶点在每个形态键下的归一化方向，组成方向元组
                            dir_tuple = tuple(
                                influence_vertices[idx]["RelatedShapeKeyInfo"][sk]["direction"]
                                for sk in sk_names
                            )
                            # 检查是否与已有方向组匹配（所有形态键方向都需在容差内）
                            matched = False
                            for group in direction_groups:
                                representative_dir = group["representative_dir"]
                                all_match = True
                                for d1, d2 in zip(dir_tuple, representative_dir):
                                    if clamp_dot_product(d1.dot(d2)) < (1.0 - directionTolerance):
                                        all_match = False
                                        break
                                if all_match:
                                    group["vertices"].append(idx)
                                    matched = True
                                    break
                            if not matched:
                                direction_groups.append({
                                    "representative_dir": dir_tuple,
                                    "vertices": [idx]
                                })

                        for dir_group in direction_groups:
                            group_verts = dir_group["vertices"]
                            # 同方向组只有一个顶点，无需合并
                            if len(group_verts) <= 1:
                                continue

                            # 第三步：找组内总偏移最大的顶点作为代表骨骼
                            max_vertex_index = -1
                            max_offset_total = 0
                            for idx in group_verts:
                                total = sum(
                                    influence_vertices[idx]["RelatedShapeKeyInfo"][sk]["offset"].length
                                    for sk in sk_names
                                )
                                if total > max_offset_total:
                                    max_offset_total = total
                                    max_vertex_index = idx

                            if max_vertex_index == -1 or max_offset_total == 0:
                                continue

                            combineName = influence_vertices[max_vertex_index]["BoneName"]

                            # 第四步：组内所有顶点合并到代表骨骼，按偏移比例分配权重
                            for idx in group_verts:
                                total = sum(
                                    influence_vertices[idx]["RelatedShapeKeyInfo"][sk]["offset"].length
                                    for sk in sk_names
                                )
                                influence_vertices[idx]["Dispose"] = True
                                if idx == max_vertex_index:
                                    influence_vertices[idx]["Dispose"] = False
                                influence_vertices[idx]["BoneName"] = combineName
                                influence_vertices[idx]["WeightRatio"] = total / max_offset_total

                print(
                    f"获取顶点数据完成，共{len(influence_vertices)}个受影响顶点，耗时：{time.time() - startTime1:.4f}"
                )

                print("开始绑定骨骼")
                boneCount = 0
                startTime1 = time.time()
                for index, vertexInfo in influence_vertices.items():
                    if not vertexInfo["Dispose"] and vertexInfo["BoneName"] not in armature.data.edit_bones:
                        create_bone_for_vertex(
                            armature,
                            vertexInfo["BoneName"],
                            basis_key.data[index].co,
                            parentBone,
                        )
                        boneCount += 1

                    vg = obj.vertex_groups.get(vertexInfo["BoneName"])
                    if vg is None:
                        vg = obj.vertex_groups.new(name=vertexInfo["BoneName"])

                    weight = vertexInfo.get("WeightRatio", 1.0)
                    vg.add([index], weight, "REPLACE")
                    normalize(obj, index, armature, set(influence_vertices.keys()))
                    if weight < 1.0 and parentBone:
                        parent_vg = obj.vertex_groups.get(parentBone.name)
                        if parent_vg is None:
                            parent_vg = obj.vertex_groups.new(name=parentBone.name)
                        parent_vg.add([index], 1.0 - weight, "REPLACE")

                bpy.ops.object.mode_set(mode="POSE")
                print(
                    f"绑定骨骼完成，共新增{boneCount}根骨骼，耗时：{time.time() - startTime1:.4f}"
                )

                bone_dependents = {}
                for index, vertexInfo in influence_vertices.items():
                    bn = vertexInfo["BoneName"]
                    if vertexInfo.get("Dispose", False):
                        bone_dependents.setdefault(bn, True)
                    elif bn not in bone_dependents:
                        bone_dependents[bn] = False

                last_action = None
                for action in actions_to_process:
                    action_fcurves = {}
                    action_frame_start = float('inf')
                    action_frame_end = float('-inf')
                    for fcu in action.fcurves:
                        if "key_blocks" in fcu.data_path:
                            sk_name = fcu.data_path.split('"')[1]
                            action_fcurves[sk_name] = fcu
                    for sk_name, fcu in action_fcurves.items():
                        for kp in fcu.keyframe_points:
                            if kp.co[0] < action_frame_start:
                                action_frame_start = kp.co[0]
                            if kp.co[0] > action_frame_end:
                                action_frame_end = kp.co[0]

                    if not action_fcurves:
                        continue

                    action_frame_start = int(action_frame_start)
                    action_frame_end = int(action_frame_end)
                    print(f"\n处理动画: {action.name} (帧 {action_frame_start}-{action_frame_end})")

                    startTime1 = time.time()
                    transformations = {}
                    abandonList = {}
                    maxOffset = 0
                    frameCount = 0
                    frame = action_frame_start

                    # Phase 3: 逐帧计算骨骼动画（直接从fcurve值×偏移量，无需depsgraph评估）
                    while frame <= action_frame_end:
                        for idx, vinfo in influence_vertices.items():
                            bone_name = vinfo["BoneName"]
                            if not vinfo["Dispose"]:
                                # 累加该顶点在所有当前动作形态键下的位移
                                displacement = Vector((0, 0, 0))
                                for sk_name, fcu in action_fcurves.items():
                                    if sk_name in vinfo["RelatedShapeKeyInfo"]:
                                        offset = vinfo["RelatedShapeKeyInfo"][sk_name]["offset"]
                                        displacement += fcu.evaluate(frame) * offset

                                transformations.setdefault(bone_name, [])
                                if bone_name not in abandonList:
                                    abandonList[bone_name] = 0
                                abandonList[bone_name] += displacement.length
                                if frame == action_frame_end and abandonList[bone_name] > maxOffset:
                                    maxOffset = abandonList[bone_name]
                                transformations[bone_name].append({"Frame": frame, "Co": displacement})
                                frameCount += 1

                        frame += 1

                    print(f"计算动画数据完成，骨骼数={len(transformations)}，耗时：{time.time() - startTime1:.4f}")

                    if abandonmentRate > 0:
                        delCount = 0
                        for i, v in abandonList.items():
                            if v <= maxOffset * abandonmentRate / 100:
                                if not bone_dependents.get(i, False):
                                    del transformations[i]
                                    delCount += 1
                        print(f"舍弃数据完成,共删除{delCount}根骨骼的数据")

                    #简化数据
                    threshold = 1e-4
                    # for bone_name, value in transformations.items():
                    #     index1 = 0
                    #     while index1 < len(value):
                    #         FrameInfo = value[index1]
                    #         frame1 = FrameInfo["Frame"]
                    #         relativeCo = FrameInfo["Co"]
                    #         if frame1 != action_frame_start and frame1 != action_frame_end:
                    #             same_as_prev = (
                    #                 relativeCo - value[index1 - 1]["Co"]
                    #             ).length_squared < threshold**2
                    #             same_as_next = (
                    #                 relativeCo - value[index1 + 1]["Co"]
                    #             ).length_squared < threshold**2
                    #             if same_as_prev and same_as_next:
                    #                 del transformations[bone_name][index1]
                    #                 index1 -= 1
                    #                 frameCount -= 1
                    #             else:
                    #                 theoValue = (
                    #                     transformations[bone_name][index1 - 1]["Co"]
                    #                     + (
                    #                         transformations[bone_name][index1 + 1]["Co"]
                    #                         - transformations[bone_name][index1 - 1]["Co"]
                    #                     ) * 0.5
                    #                 )
                    #                 if (
                    #                     relativeCo - theoValue
                    #                 ).length_squared < threshold**2:
                    #                     del transformations[bone_name][index1]
                    #                     index1 -= 1
                    #                     frameCount -= 1
                    #         index1 += 1

                    output_action_name = f"SKB_{action.name}"
                    if output_action_name in bpy.data.actions:
                        action_out = bpy.data.actions[output_action_name]
                        for fc in action_out.fcurves:
                            fc.keyframe_points.clear()
                    else:
                        action_out = bpy.data.actions.new(name=output_action_name)
                        action_out.name = output_action_name

                    for bone_name, value in transformations.items():
                        fcurves = [None] * 3
                        data_path = f'pose.bones["{bone_name}"].location'
                        for axis_i in range(3):
                            fcurves[axis_i] = get_or_create_fcurve(
                                action_out, bone_name, axis_i, axis_i, data_path=data_path
                            )
                        for fc_i, fc in enumerate(fcurves):
                            start_kps = len(fc.keyframe_points)
                            fc.keyframe_points.add(len(value))
                            
                            for frameInfo, kp2 in zip(
                                value, fc.keyframe_points[start_kps:]
                            ):
                                kp2.co = (frameInfo["Frame"], frameInfo["Co"][fc_i])
                                kp2.interpolation = "LINEAR"
                            fc.update()

                    last_action = action_out
                    print(f"动画 {action.name} 处理完成，共插入{frameCount}个关键帧")

                if last_action:
                    try:
                        armature.animation_data.action = last_action
                    except AttributeError:
                        armature.animation_data_clear()
                        armature.animation_data_create()
                        armature.animation_data.action = last_action

                shape_keys = obj.data.shape_keys
                if shape_keys:
                    if shape_keys.animation_data and shape_keys.animation_data.action:
                        shape_keys.animation_data.action = None
                    for i, key_block in enumerate(shape_keys.key_blocks):
                        if key_block.name != "Basis" or i != 0:
                            key_block.value = 0.0

                print(f"形态键动画已转换为骨骼动画，总耗时:{time.time() - startTime:.4f}")

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

