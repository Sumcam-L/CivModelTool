"""Civ6 静态数据（DSG / MaterialInfo）与 .NET 依赖自举。

整个 cmt_exporter 包只有本模块：改 sys.path、加载 Firaxis .NET 程序集、在导入时读 assets/。
其它模块一律从这里取数据与 .NET 类型，不要在别处再写一遍 clr.AddReference。
"""
import json
import os
import sys
import xml.dom.minidom
from pathlib import Path

_ASSETS_DIR = Path(__file__).parent / "assets"
_DEPENDENCIES_DIR = Path(__file__).parent / "dependencies"
_DLLS_TO_CHECK = [
    "Firaxis.Utility",
    "Firaxis.Granny",
    "Firaxis.Granny.Impl",
    "CivNexus6",
]


def is_dll_loaded(dll_name):
    """
    检查指定名称的DLL是否已加载
    dll_name: DLL文件名（如 "Firaxis.Utility"）
    """
    loaded_assemblies = System.AppDomain.CurrentDomain.GetAssemblies()
    for assembly in loaded_assemblies:
        if assembly.GetName().Name == dll_name:
            return True
    return False


def _load_asset_json(filename):
    with open(_ASSETS_DIR / filename, encoding="utf-8") as file:
        return json.load(file)


def _load_dsg_action_slots(dsg_json):
    """解析每个 DSG，取出其中的 m_AnimationSlots 名称，供 AstDSG 枚举使用。"""
    action_slots = {}
    for tClass in dsg_json["Classes"]:
        for dsg in dsg_json[tClass]:
            dsg_path = str(_ASSETS_DIR / (dsg + ".dsg"))
            dom = xml.dom.minidom.parse(dsg_path)
            collection = dom.documentElement
            for line in collection.getElementsByTagName("m_AnimationSlots")[0].childNodes:
                if line.nodeType == xml.dom.Node.ELEMENT_NODE:
                    if dsg not in action_slots:
                        action_slots[dsg] = []
                    action_slots[dsg].append(line.getAttribute("text"))
    return action_slots


# --- 导入期自举 ------------------------------------------------------------
# 1) libs/ 进 sys.path（pythonnet 的 clr/cffi 依赖它）
libs_path = os.path.join(os.path.dirname(__file__), "libs")
if libs_path not in sys.path:
    sys.path.append(libs_path)

import clr
import System

# 以下 .NET 类型由 cmt_exporter 其它模块复用：统一从这里取，
# 别处不要再直接 import clr / System（否则会在自举之前执行而失败）。
from System.Collections.Generic import Dictionary, List
from System import Array, Single, ValueTuple

# 2) 加载 Firaxis 程序集；已加载则跳过，因此本模块被重复导入是幂等的
for dll in _DLLS_TO_CHECK:
    if is_dll_loaded(dll):
        print(f"{dll} 已加载")
    else:
        print(f"{dll} 未加载")
        clr.AddReference(str(_DEPENDENCIES_DIR / (dll + ".dll")))

# 3) 静态资源
g_DSG_json = _load_asset_json("DSGs.json")
g_DSGs_action = _load_dsg_action_slots(g_DSG_json)
g_Mat_json = _load_asset_json("MaterialInfo.json")

# 4) NexusBuddy 依赖上面已加载的程序集，必须最后导入
from NexusBuddy.FileOps import CN6FileOps, BoneData, AstInfo
