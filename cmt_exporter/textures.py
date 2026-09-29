"""贴图分辨率压缩与贴图文件导出。"""
import math
import time
from pathlib import Path

import bpy

def compress_texture_resolution(image, scale=0.5, output_path=None, max_width=4096, max_height=4096,
                               min_width=4, min_height=4, require_pow2=True, require_square=False,
                               log=print):
    """
    按倍率压缩贴图分辨率并保存

    image: Blender Image对象或图片路径
    scale: 缩放倍率 (0.5 = 一半, 0.25 = 四分之一)
    output_path: 输出路径，默认为原路径覆盖
    max_width/max_height: 最大尺寸
    min_width/min_height: 最小尺寸
    require_pow2: 是否需要2的幂次
    require_square: 是否需要正方形
    返回: 输出文件路径
    """
    total_start = time.time()
    if isinstance(image, str):
        image = bpy.data.images.load(image)
        is_loaded = False
    else:
        is_loaded = True
    scale = float(scale)
    orig_width, orig_height = image.size[0], image.size[1]
    width = int(orig_width * scale)
    height = int(orig_height * scale)
    
    if require_pow2:
        width = nearest_pow2(width)
        height = nearest_pow2(height)

    width = max(min_width, min(max_width, width))
    height = max(min_height, min(max_height, height))

    if require_square:
        size = max(width, height)
        width = size
        height = size

    if output_path is None:
        output_path = bpy.path.abspath(image.filepath)

    resized = image.copy()
    resized.scale(width, height)
    resized.filepath_raw = output_path
    resized.file_format = 'PNG'
    resized.save()

    if not is_loaded:
        bpy.data.images.remove(image)
    bpy.data.images.remove(resized)

    total_elapsed = time.time() - total_start
    log(f"压缩贴图耗时: {total_elapsed:.2f}s")
    return output_path

def nearest_pow2(value):
    """返回最接近的2的幂次值"""
    if value <= 0:
        return 1
    p = 1
    while p < value:
        p *= 2
    if p > 1 and abs(p - value) > abs(p // 2 - value):
        p //= 2
    return max(1, p)

def extract_packed_textures_to_file(input_path, output_dir=None, log=print):
    """
    从打包贴图文件提取所有贴图并保存

    input_path: 输入图片路径
    output_dir: 输出目录，默认为同目录
    返回: dict {"normal": path, "metallic": path, "gloss": path}
    """
    total_start = time.time()
    p = Path(input_path)
    if output_dir is None:
        output_dir = str(p.parent)

    image = bpy.data.images.load(input_path)
    width, height = image.size[0], image.size[1]
    pixels = list(image.pixels)

    log(f"源图: {input_path}, 尺寸: {width}x{height}")

    name_map = {"normal": "Normal", "metallic": "Metallic", "gloss": "Gloss"}
    result = {}

    for key, suffix in name_map.items():
        start = time.time()
        out_path = str(Path(output_dir) / (p.stem + f"_{suffix}" + p.suffix))
        img = bpy.data.images.new(p.stem + f"_{suffix}", width=width, height=height, alpha=True)
        img.colorspace_settings.name = 'Non-Color'

        if key == "normal":
            out_pixels = [0.0] * (width * height * 4)
            for i in range(width * height):
                idx = i * 4
                r, g = pixels[idx], pixels[idx+1]
                nx = r * 2.0 - 1.0
                ny = (1.0 - g) * 2.0 - 1.0
                nz = math.sqrt(max(0.0, 1.0 - nx*nx - ny*ny))
                out_pixels[idx] = nx * 0.5 + 0.5
                out_pixels[idx+1] = ny * 0.5 + 0.5
                out_pixels[idx+2] = nz * 0.5 + 0.5
                out_pixels[idx+3] = 1.0
        elif key == "metallic":
            out_pixels = [0.0] * (width * height * 4)
            for i in range(width * height):
                idx = i * 4
                b = pixels[idx+2]
                out_pixels[idx] = b
                out_pixels[idx+1] = b
                out_pixels[idx+2] = b
                out_pixels[idx+3] = 1.0
        else:
            out_pixels = [0.0] * (width * height * 4)
            for i in range(width * height):
                idx = i * 4
                gloss = 1 - pixels[idx+3]
                out_pixels[idx] = gloss
                out_pixels[idx+1] = gloss
                out_pixels[idx+2] = gloss
                out_pixels[idx+3] = 1.0

        img.pixels = out_pixels
        img.filepath_raw = out_path
        img.file_format = 'PNG'
        img.save()
        elapsed = time.time() - start
        log(f"已保存: {out_path} ({elapsed:.2f}s)")
        result[key] = out_path
        bpy.data.images.remove(img)

    bpy.data.images.remove(image)
    total_elapsed = time.time() - total_start
    log(f"分解鸣潮法线贴图耗时: {total_elapsed:.2f}s")
    return result
