"""网格自动分割的划分算法。

旧实现按连通分量生长，凑到骨骼上限就断开，碎片化严重：
一个 4316 面的 Face 合并体（602 根骨骼）会被切成 62 块，平均每块只有 17 根骨骼。

新实现把「块」当成可装多个互不相连碎片的桶，分三步：
  1. 求面邻接的连通分量（只用来决定装箱顺序，不限制同一块必须相连）；
  2. 逐面装箱：按骨骼集从大到小，首次适应，优先塞进当前最满的桶；
  3. 重平衡：把小桶的面挪进别的桶，挪不动就做交换，反复直到桶数不再下降。

骨骼集用 Python 大整数做位掩码（第 i 位 = 第 i 根骨骼），并集是按位或，
计数是 int.bit_count()。这比 set 快两个数量级，是在 6.7 万面上跑得完的前提。
"""
from collections import deque


def collect_masks(obj):
    """返回 (位序号 -> 骨骼名, 每面的骨骼位掩码)。"""
    groups = obj.vertex_groups
    index_of = {}
    name_of = []
    for g in groups:
        if g.name not in index_of:
            index_of[g.name] = len(name_of)
            name_of.append(g.name)

    vert_masks = [0] * len(obj.data.vertices)
    for v in obj.data.vertices:
        mask = 0
        for g in v.groups:
            mask |= 1 << index_of[groups[g.group].name]
        vert_masks[v.index] = mask

    face_masks = [0] * len(obj.data.polygons)
    for poly in obj.data.polygons:
        mask = 0
        for vi in poly.vertices:
            mask |= vert_masks[vi]
        face_masks[poly.index] = mask
    return name_of, face_masks


def face_adjacency(mesh):
    """面邻接表：两个面共享至少一个顶点即相邻。"""
    vert_to_faces = {}
    for poly in mesh.polygons:
        for vi in poly.vertices:
            vert_to_faces.setdefault(vi, []).append(poly.index)

    adjacency = []
    for poly in mesh.polygons:
        neighbors = set()
        for vi in poly.vertices:
            neighbors.update(vert_to_faces[vi])
        neighbors.discard(poly.index)
        adjacency.append(frozenset(neighbors))
    return adjacency


def connected_components(mesh, adjacency, face_masks):
    """按面邻接求连通分量，骨骼多的在前。"""
    seen = set()
    components = []
    for poly in mesh.polygons:
        if poly.index in seen:
            continue
        queue = deque([poly.index])
        seen.add(poly.index)
        faces = []
        mask = 0
        while queue:
            fi = queue.popleft()
            faces.append(fi)
            mask |= face_masks[fi]
            for nb in adjacency[fi]:
                if nb not in seen:
                    seen.add(nb)
                    queue.append(nb)
        components.append((faces, mask))
    components.sort(key=lambda c: -c[1].bit_count())
    return components


def _mask_of(faces, face_masks):
    mask = 0
    for fi in faces:
        mask |= face_masks[fi]
    return mask


def _pack(order, face_masks, max_bones):
    """逐面装箱，每块的骨骼并集不超过 max_bones。返回 [[面索引...], 掩码]。"""
    bins = []
    for fi in order:
        mask = face_masks[fi]
        target = -1
        for i, (_, bm) in enumerate(bins):
            if (bm | mask).bit_count() <= max_bones and (
                target < 0 or bins[target][1].bit_count() < bm.bit_count()
            ):
                target = i
        if target < 0:
            bins.append([[fi], mask])
        else:
            bins[target][0].append(fi)
            bins[target][1] |= mask
    return bins


def _rebalance(bins, face_masks, max_bones, rounds=64):
    """把小桶拆散并入其它桶；挪不动就做交换。反复到桶数不再下降。"""
    for _ in range(rounds):
        alive = [b for b in bins if b[0]]
        if len(alive) < 2:
            bins[:] = alive
            break
        alive.sort(key=lambda b: b[1].bit_count())
        bins[:] = alive

        moved = False
        small = bins[0]
        others = bins[1:]

        # 1) 小桶的面逐个塞进别的桶，优先塞进目前最满的那个
        keep = []
        for fi in sorted(small[0], key=lambda f: -face_masks[f].bit_count()):
            mask = face_masks[fi]
            target = None
            for b in others:
                if (b[1] | mask).bit_count() <= max_bones and (
                    target is None or target[1].bit_count() < b[1].bit_count()
                ):
                    target = b
            if target is None:
                keep.append(fi)
            else:
                target[0].append(fi)
                target[1] |= mask
                moved = True
        small[0] = keep
        small[1] = _mask_of(keep, face_masks)

        # 2) 从某个大桶里挑一个面搬过来，正好把小桶填满
        if small[0]:
            for b in others:
                if b[1].bit_count() <= small[1].bit_count():
                    continue
                picked = None
                for fi in sorted(list(b[0]), key=lambda f: face_masks[f].bit_count()):
                    if (small[1] | face_masks[fi]).bit_count() <= max_bones:
                        picked = fi
                        break
                if picked is not None:
                    small[0].append(picked)
                    small[1] |= face_masks[picked]
                    b[0].remove(picked)
                    b[1] = _mask_of(b[0], face_masks)
                    moved = True
                    break

        # 3) 交换：腾出大桶里的面，换进小桶的面，只要总数不超标
        if small[0] and not moved:
            for b in others:
                if len(b[0]) < 2:
                    continue
                hit = None
                for gi in b[0]:
                    without = b[1] & ~face_masks[gi]
                    for fi in small[0]:
                        if (without | face_masks[fi]).bit_count() <= max_bones:
                            hit = (fi, gi)
                            break
                    if hit:
                        break
                if hit:
                    fi, gi = hit
                    small[0].remove(fi)
                    b[0].remove(gi)
                    small[0].append(gi)
                    b[0].append(fi)
                    b[1] = _mask_of(b[0], face_masks)
                    small[1] = _mask_of(small[0], face_masks)
                    moved = True
                    break

        if not moved:
            break
    return [b for b in bins if b[0]]


def names_of(mask, name_of):
    """位掩码 -> 骨骼名列表。"""
    out = []
    bit = 0
    while mask:
        if mask & 1:
            out.append(name_of[bit])
        mask >>= 1
        bit += 1
    return out


def plan_parts(obj, max_bones):
    """把 obj 的面划分成若干块。

    返回 [(面索引列表, 该块用到的骨骼名列表), ...]，骨骼多的块在前。
    每块用到的骨骼数不超过 max_bones；块与块之间可以互不相连。
    """
    total = len(obj.data.polygons)
    if total == 0:
        return []

    name_of, face_masks = collect_masks(obj)
    if max_bones <= 0:
        mask = _mask_of(range(total), face_masks)
        return [(list(range(total)), names_of(mask, name_of))]

    by_weight = []
    plain = []
    for faces, _ in connected_components(
        obj.data, face_adjacency(obj.data), face_masks
    ):
        plain.extend(faces)
        by_weight.extend(sorted(faces, key=lambda f: -face_masks[f].bit_count()))

    # 装箱顺序对结果影响很大，而且没有哪种顺序处处最优：
    # 连通分量顺序通常块数最少，全局按骨骼数排序则常在「最后剩一小撮」时更好。
    # 三种都跑一遍，挑块数最少、块数相同则最小块最大的那个。
    orders = [plain]
    if by_weight != plain:
        orders.append(by_weight)
    orders.append(sorted(range(total), key=lambda f: -face_masks[f].bit_count()))

    best = None
    best_key = None
    for order in orders:
        bins = _rebalance(
            _pack(order, face_masks, max_bones), face_masks, max_bones
        )
        sizes = [b[1].bit_count() for b in bins]
        key = (len(sizes), -min(sizes))
        if best_key is None or key < best_key:
            best_key = key
            best = bins

    best.sort(key=lambda b: -b[1].bit_count())
    return [(faces, names_of(mask, name_of)) for faces, mask in best]


def prune_vertex_groups(obj, keep_names):
    """删掉 obj 上不在 keep_names 里的顶点组。

    分离时 Blender 会把交界顶点复制给相邻的块，副本带着邻块的顶点组，
    于是这个块「继承」了本来不属于它的骨骼，实际骨骼数会超过上限。
    每块分离出来后按自己那份骨骼表裁一次即可。
    """
    keep = set(keep_names)
    groups = obj.vertex_groups
    for index in range(len(groups) - 1, -1, -1):
        if groups[index].name not in keep:
            groups.remove(groups[index])
