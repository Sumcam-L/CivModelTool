# CivModelTool 自动更新功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 CivModelTool Blender 插件添加自动更新:跟踪 GitHub main 分支,对比 bl_info 版本号,启动时自动检查,N 面板一键更新并热重载。

**Architecture:** 新增 `cmt_updater` 子包,遵循项目现有子包结构。`core.py` 为不依赖 bpy 的纯逻辑层(可在 Blender 外测试),`operations.py` 处理线程与 Operator,`preferences.py` 提供插件偏好设置,`ui.py` 提供 N 面板提示。根 `__init__.py` 接入注册流程。

**Tech Stack:** Python 标准库(urllib、zipfile、threading、hashlib)、Blender Python API(bpy.app.timers、AddonPreferences)。无第三方依赖。

## Global Constraints

- 仓库:`Sumcam-L/CivModelTool`,跟踪 `main` 分支
- 版本判断:对比远程 `__init__.py` 中 `bl_info["version"]` 与本地版本
- 覆盖安装时跳过:`.git`、`.gitignore`、`.serena`、`__pycache__`
- 覆盖前所有下载/解压在临时目录完成,不动原文件
- 更新生效方式:热重载(addon_disable + addon_enable)
- UI 文字使用中文,与项目现有风格一致
- 网络操作全部在后台线程执行,不阻塞 Blender 主线程
- 系统 Python 为 3.11(用于 Blender 外运行单元测试),测试框架用标准库 `unittest`(无 pytest)
- 项目根目录:`D:\blender\Common\scripts\addons\CivModelTool`(git 仓库所在);所有 git 命令在此目录执行

---

### Task 1: core.py 纯逻辑层(版本解析 + 覆盖安装)

**Files:**
- Create: `cmt_updater/core.py`
- Test: `tests/test_updater_core.py`

**Interfaces:**
- Produces(后续任务依赖):
  - `core.state`:`UpdaterState` 实例,字段 `status: str`(`"idle" | "checking" | "update_available" | "updating" | "up_to_date" | "error"`)、`remote_version: tuple | None`、`error_msg: str`、`error_source: str`(`"check"` 或 `"update"`)
  - `core.fetch_remote_version(timeout=10) -> tuple[int, int, int]`
  - `core.download_and_install(addon_dir: str) -> None`
  - `core.parse_version(text: str) -> tuple[int, int, int]`

**注意:** `core.py` 禁止 import bpy,保证可在 Blender 外测试。

- [ ] **Step 1: 写失败的测试**

创建 `tests/test_updater_core.py`:

```python
import os
import sys
import shutil
import tempfile
import zipfile
import unittest

# 直接按文件路径加载 core.py,避免触发包 __init__.py 里的 bpy import
import importlib.util

_CORE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "cmt_updater", "core.py",
)
spec = importlib.util.spec_from_file_location("cmt_updater_core", _CORE_PATH)
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


class TestParseVersion(unittest.TestCase):
    def test_parse_normal(self):
        text = '''
bl_info = {
    "name": "Civ6ModelTool",
    "version": (1, 2, 3),
    "blender": (5, 1, 0),
}
'''
        self.assertEqual(core.parse_version(text), (1, 2, 3))

    def test_parse_with_spaces(self):
        text = '"version" : ( 10 ,  0 , 5 )'
        self.assertEqual(core.parse_version(text), (10, 0, 5))

    def test_parse_missing_raises(self):
        with self.assertRaises(ValueError):
            core.parse_version("no version here")


class TestInstallFromZip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addon_dir = os.path.join(self.tmp, "addon")
        os.makedirs(self.addon_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_zip(self, files):
        """files: dict 相对路径 -> 内容,打包进顶层目录 CivModelTool-main/"""
        zip_path = os.path.join(self.tmp, "update.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            for rel, content in files.items():
                zf.writestr("CivModelTool-main/" + rel, content)
        return zip_path

    def test_copies_new_files(self):
        zip_path = self._make_zip({
            "__init__.py": "new code",
            "cmt_updater/core.py": "core code",
        })
        core.install_from_zip(zip_path, self.addon_dir)
        with open(os.path.join(self.addon_dir, "__init__.py")) as f:
            self.assertEqual(f.read(), "new code")
        with open(os.path.join(self.addon_dir, "cmt_updater", "core.py")) as f:
            self.assertEqual(f.read(), "core code")

    def test_overwrites_existing_files(self):
        with open(os.path.join(self.addon_dir, "__init__.py"), "w") as f:
            f.write("old code")
        zip_path = self._make_zip({"__init__.py": "new code"})
        core.install_from_zip(zip_path, self.addon_dir)
        with open(os.path.join(self.addon_dir, "__init__.py")) as f:
            self.assertEqual(f.read(), "new code")

    def test_skips_protected_names(self):
        zip_path = self._make_zip({
            ".gitignore": "remote ignore",
            ".git/config": "remote git",
            ".serena/project.yml": "remote serena",
            "__init__.py": "new code",
        })
        # 本地已有 .gitignore,不应被覆盖
        with open(os.path.join(self.addon_dir, ".gitignore"), "w") as f:
            f.write("local ignore")
        core.install_from_zip(zip_path, self.addon_dir)
        with open(os.path.join(self.addon_dir, ".gitignore")) as f:
            self.assertEqual(f.read(), "local ignore")
        self.assertFalse(os.path.exists(os.path.join(self.addon_dir, ".git")))
        self.assertFalse(os.path.exists(os.path.join(self.addon_dir, ".serena")))

    def test_clears_pycache(self):
        pycache = os.path.join(self.addon_dir, "cmt_updater", "__pycache__")
        os.makedirs(pycache)
        with open(os.path.join(pycache, "core.cpython-311.pyc"), "w") as f:
            f.write("x")
        zip_path = self._make_zip({"__init__.py": "new code"})
        core.install_from_zip(zip_path, self.addon_dir)
        self.assertFalse(os.path.exists(pycache))

    def test_skips_identical_files(self):
        """内容相同的文件跳过覆盖(避免触碰被占用的 DLL)"""
        sub = os.path.join(self.addon_dir, "cmt_exporter", "dependencies")
        os.makedirs(sub)
        dll = os.path.join(sub, "some.dll")
        with open(dll, "wb") as f:
            f.write(b"same bytes")
        zip_path = self._make_zip({
            "cmt_exporter/dependencies/some.dll": "same bytes",
        })
        old_mtime = os.path.getmtime(dll)
        core.install_from_zip(zip_path, self.addon_dir)
        # 文件未被重写(mtime 不变)
        self.assertEqual(os.path.getmtime(dll), old_mtime)


class TestState(unittest.TestCase):
    def test_initial_state(self):
        s = core.UpdaterState()
        self.assertEqual(s.status, "idle")
        self.assertIsNone(s.remote_version)
        self.assertEqual(s.error_msg, "")
        self.assertEqual(s.error_source, "")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试,确认失败**

```powershell
python -m unittest tests.test_updater_core -v
```

工作目录:`D:\blender\Common\scripts\addons\CivModelTool`
预期:FAIL/ERROR(`cmt_updater/core.py` 不存在)

- [ ] **Step 3: 实现 core.py**

创建 `cmt_updater/core.py`:

```python
"""自动更新核心逻辑。禁止 import bpy,保证可在 Blender 外测试。"""
import hashlib
import os
import re
import shutil
import tempfile
import urllib.request
import zipfile

REPO_OWNER = "Sumcam-L"
REPO_NAME = "CivModelTool"
BRANCH = "main"

RAW_INIT_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/__init__.py"
ZIP_URL = f"https://codeload.github.com/{REPO_OWNER}/{REPO_NAME}/zip/refs/heads/{BRANCH}"

# 覆盖安装时跳过的目录/文件名(任意层级)
SKIP_NAMES = {".git", ".gitignore", ".serena", "__pycache__"}


class UpdaterState:
    """全局更新状态。status 取值:
    idle / checking / update_available / updating / up_to_date / error
    error_source: "check" 表示检查阶段出错, "update" 表示更新阶段出错
    """
    def __init__(self):
        self.status = "idle"
        self.remote_version = None
        self.error_msg = ""
        self.error_source = ""


state = UpdaterState()


def parse_version(text):
    """从 __init__.py 源码文本中解析 bl_info 的 version 元组。"""
    m = re.search(
        r'"version"\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', text
    )
    if not m:
        raise ValueError("无法从远程 __init__.py 解析版本号")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def fetch_remote_version(timeout=10):
    """获取远程 main 分支的 bl_info 版本号。"""
    with urllib.request.urlopen(RAW_INIT_URL, timeout=timeout) as resp:
        text = resp.read().decode("utf-8")
    return parse_version(text)


def _same_file(path_a, path_b):
    """两个文件内容是否完全一致。"""
    if os.path.getsize(path_a) != os.path.getsize(path_b):
        return False

    def _digest(path):
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.digest()

    return _digest(path_a) == _digest(path_b)


def _copy_tree(src, dst):
    """递归覆盖复制,跳过 SKIP_NAMES;内容相同的文件不重写(避免触碰被占用的 DLL)。"""
    for name in os.listdir(src):
        if name in SKIP_NAMES:
            continue
        s = os.path.join(src, name)
        d = os.path.join(dst, name)
        if os.path.isdir(s):
            os.makedirs(d, exist_ok=True)
            _copy_tree(s, d)
        else:
            if os.path.isfile(d) and _same_file(s, d):
                continue
            shutil.copy2(s, d)


def _clear_pycache(root):
    for dirpath, dirnames, _filenames in os.walk(root):
        if "__pycache__" in dirnames:
            shutil.rmtree(os.path.join(dirpath, "__pycache__"), ignore_errors=True)
            dirnames.remove("__pycache__")


def download_zip(dest_dir, timeout=60):
    """下载 main 分支 zip 到 dest_dir,返回 zip 路径。"""
    zip_path = os.path.join(dest_dir, "update.zip")
    with urllib.request.urlopen(ZIP_URL, timeout=timeout) as resp, \
            open(zip_path, "wb") as f:
        shutil.copyfileobj(resp, f)
    return zip_path


def install_from_zip(zip_path, addon_dir):
    """解压 zip(在临时位置),然后覆盖复制到插件目录并清理 __pycache__。"""
    extract_dir = os.path.join(os.path.dirname(zip_path), "extracted")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    entries = [
        e for e in os.listdir(extract_dir)
        if os.path.isdir(os.path.join(extract_dir, e))
    ]
    if len(entries) != 1:
        raise RuntimeError(f"zip 结构异常: 顶层目录数为 {len(entries)}")
    src_root = os.path.join(extract_dir, entries[0])
    _copy_tree(src_root, addon_dir)
    _clear_pycache(addon_dir)


def download_and_install(addon_dir):
    """下载并安装更新。下载/解压全部在临时目录完成后才覆盖插件目录。"""
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = download_zip(tmp)
        install_from_zip(zip_path, addon_dir)
```

- [ ] **Step 4: 运行测试,确认通过**

```powershell
python -m unittest tests.test_updater_core -v
```

预期:全部 PASS(9 个测试)

- [ ] **Step 5: 冒烟测试真实网络请求(可选,需联网)**

```powershell
python -c "import importlib.util; spec = importlib.util.spec_from_file_location('c', 'cmt_updater/core.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print(m.fetch_remote_version())"
```

预期:输出远程版本元组,如 `(1, 0, 0)`

- [ ] **Step 6: 提交**

```powershell
git add cmt_updater/core.py tests/test_updater_core.py
git commit -m "添加自动更新核心逻辑(版本解析与覆盖安装)"
```

---

### Task 2: operations.py(后台线程 + Operator)

**Files:**
- Create: `cmt_updater/operations.py`

**Interfaces:**
- Consumes: `core.state`、`core.fetch_remote_version()`、`core.download_and_install(addon_dir)`(Task 1)
- Produces(后续任务依赖):
  - `operations.get_local_version() -> tuple`(从 `sys.modules` 根包的 `bl_info` 读取)
  - `operations.start_check() -> None`(后台检查)
  - Operator `cmt.updater_check`(类 `CMT_OT_CheckUpdate`)
  - Operator `cmt.updater_run`(类 `CMT_OT_RunUpdate`)

**说明:** 此文件依赖 bpy,无法在 Blender 外自动化测试。验证在 Task 5 的 Blender 手动测试中进行。

- [ ] **Step 1: 实现 operations.py**

创建 `cmt_updater/operations.py`:

```python
import os
import sys
import threading

import bpy

from . import core

ROOT_PACKAGE = __package__.split(".")[0]
# cmt_updater/operations.py -> cmt_updater -> 插件根目录
ADDON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_local_version():
    return tuple(sys.modules[ROOT_PACKAGE].bl_info["version"])


def _redraw():
    """在主线程刷新所有区域,让面板显示最新状态。"""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()
    return None  # 一次性 timer


def request_redraw():
    """线程安全:通过 timer 请求主线程重绘。"""
    bpy.app.timers.register(_redraw, first_interval=0.0)


def _check_worker():
    try:
        remote = core.fetch_remote_version()
        core.state.remote_version = remote
        if remote > get_local_version():
            core.state.status = "update_available"
        else:
            core.state.status = "up_to_date"
    except Exception as e:
        core.state.status = "error"
        core.state.error_msg = str(e)
        core.state.error_source = "check"
    request_redraw()


def start_check():
    if core.state.status in ("checking", "updating"):
        return
    core.state.status = "checking"
    core.state.error_msg = ""
    core.state.error_source = ""
    threading.Thread(target=_check_worker, daemon=True).start()


def _do_reload():
    """主线程执行热重载。"""
    print(f"[Civ6ModelTool] 更新完成,正在热重载插件...")
    try:
        bpy.ops.preferences.addon_disable(module=ROOT_PACKAGE)
        bpy.ops.preferences.addon_enable(module=ROOT_PACKAGE)
        print("[Civ6ModelTool] 热重载完成")
    except Exception as e:
        print(f"[Civ6ModelTool] 热重载失败,请手动重启 Blender: {e}")
    return None


def _update_worker():
    try:
        core.download_and_install(ADDON_DIR)
    except Exception as e:
        core.state.status = "error"
        core.state.error_msg = str(e)
        core.state.error_source = "update"
        request_redraw()
        return
    core.state.status = "idle"
    # 热重载必须在主线程执行
    bpy.app.timers.register(_do_reload, first_interval=0.5)


def start_update():
    if core.state.status == "updating":
        return
    core.state.status = "updating"
    core.state.error_msg = ""
    core.state.error_source = ""
    request_redraw()
    threading.Thread(target=_update_worker, daemon=True).start()


class CMT_OT_CheckUpdate(bpy.types.Operator):
    bl_idname = "cmt.updater_check"
    bl_label = "检查更新"
    bl_description = "从 GitHub 检查是否有新版本"

    def execute(self, context):
        start_check()
        return {"FINISHED"}


class CMT_OT_RunUpdate(bpy.types.Operator):
    bl_idname = "cmt.updater_run"
    bl_label = "立即更新"
    bl_description = "下载最新代码并热重载插件"

    def execute(self, context):
        start_update()
        return {"FINISHED"}
```

- [ ] **Step 2: 语法检查**

```powershell
python -m py_compile cmt_updater/operations.py
```

预期:无输出(编译通过)

- [ ] **Step 3: 提交**

```powershell
git add cmt_updater/operations.py
git commit -m "添加更新检查与执行 Operator"
```

---

### Task 3: preferences.py + ui.py(偏好设置与 N 面板提示)

**Files:**
- Create: `cmt_updater/preferences.py`
- Create: `cmt_updater/ui.py`

**Interfaces:**
- Consumes: `core.state`、`operations.get_local_version()`、Operator `cmt.updater_check` / `cmt.updater_run`(Task 1、2)
- Produces: `CMT_AddonPreferences`(含 `auto_check_update: BoolProperty`)、`CMT_Updater_PT_Panel`

- [ ] **Step 1: 实现 preferences.py**

创建 `cmt_updater/preferences.py`:

```python
import bpy

from . import core
from .operations import get_local_version


def _version_str(v):
    return f"{v[0]}.{v[1]}.{v[2]}"


class CMT_AddonPreferences(bpy.types.AddonPreferences):
    # bl_idname 必须等于插件顶层包名
    bl_idname = __package__.split(".")[0]

    auto_check_update: bpy.props.BoolProperty(
        name="启动时自动检查更新",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        s = core.state

        layout.prop(self, "auto_check_update")

        box = layout.box()
        row = box.row()
        row.label(text=f"当前版本: {_version_str(get_local_version())}")
        if s.remote_version:
            row.label(text=f"远程版本: {_version_str(s.remote_version)}")

        if s.status == "checking":
            box.label(text="正在检查更新...")
        elif s.status == "updating":
            box.label(text="正在下载更新...")
        elif s.status == "up_to_date":
            box.label(text="已是最新版本", icon="CHECKMARK")
        elif s.status == "update_available":
            box.label(text="发现新版本", icon="INFO")
        elif s.status == "error":
            box.label(text=f"出错: {s.error_msg}", icon="ERROR")

        row = box.row()
        sub = row.row()
        sub.enabled = s.status not in ("checking", "updating")
        sub.operator("cmt.updater_check", text="检查更新")
        if s.status == "update_available" or (
            s.status == "error" and s.error_source == "update"
        ):
            sub2 = row.row()
            sub2.operator("cmt.updater_run", text="下载并更新")
```

- [ ] **Step 2: 实现 ui.py**

创建 `cmt_updater/ui.py`:

```python
import bpy

from . import core


class CMT_Updater_PT_Panel(bpy.types.Panel):
    bl_label = "插件更新"
    bl_idname = "CMT_Updater_PT_Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Civ6ModelTool"
    bl_order = 0

    @classmethod
    def poll(cls, context):
        s = core.state
        # 仅在有新版本、更新中、或更新出错时显示
        return s.status in ("update_available", "updating") or (
            s.status == "error" and s.error_source == "update"
        )

    def draw(self, context):
        layout = self.layout
        s = core.state
        if s.status == "update_available":
            v = s.remote_version
            layout.label(
                text=f"发现新版本 v{v[0]}.{v[1]}.{v[2]}", icon="INFO"
            )
            layout.operator("cmt.updater_run", text="立即更新")
        elif s.status == "updating":
            row = layout.row()
            row.enabled = False
            row.operator("cmt.updater_run", text="更新中...")
        elif s.status == "error":
            layout.label(text="更新失败", icon="ERROR")
            layout.label(text=s.error_msg)
            layout.operator("cmt.updater_run", text="重试更新")
```

- [ ] **Step 3: 语法检查**

```powershell
python -m py_compile cmt_updater/preferences.py cmt_updater/ui.py
```

预期:无输出

- [ ] **Step 4: 提交**

```powershell
git add cmt_updater/preferences.py cmt_updater/ui.py
git commit -m "添加更新偏好设置界面与 N 面板更新提示"
```

---

### Task 4: 子包注册 + 根 __init__.py 接入 + 启动检查

**Files:**
- Create: `cmt_updater/__init__.py`
- Modify: `__init__.py`(项目根)

**Interfaces:**
- Consumes: Task 1-3 的全部模块
- Produces: `cmt_updater.register()` / `cmt_updater.unregister()`

- [ ] **Step 1: 实现 cmt_updater/__init__.py**

遵循项目现有子包模式(参考 `cmt_ordinary_tool/__init__.py` 的 `get_classes_from_module`):

```python
import bpy

from . import core
from . import operations
from . import preferences
from . import ui

modules = [operations, preferences, ui]


def get_classes_from_module(module):
    classes = []
    for name, obj in module.__dict__.items():
        if isinstance(obj, type) and obj.__module__ == module.__name__:
            classes.append(obj)
    return classes


def _startup_check():
    """启动后延迟执行:若偏好设置开启,则后台检查更新。"""
    try:
        root = __package__.split(".")[0]
        prefs = bpy.context.preferences.addons[root].preferences
        if prefs.auto_check_update:
            operations.start_check()
    except Exception as e:
        print(f"[Civ6ModelTool] 启动更新检查失败: {e}")
    return None  # 一次性 timer


def register() -> None:
    for module in modules:
        for tClass in get_classes_from_module(module):
            bpy.utils.register_class(tClass)
    bpy.app.timers.register(_startup_check, first_interval=3.0)


def unregister() -> None:
    if bpy.app.timers.is_registered(_startup_check):
        bpy.app.timers.unregister(_startup_check)
    for module in modules:
        for tClass in get_classes_from_module(module):
            bpy.utils.unregister_class(tClass)
```

注意 `get_classes_from_module` 只收集 `obj.__module__ == module.__name__` 的类,所以 `preferences.py` 中 import 的 Operator 类不会被重复注册。

- [ ] **Step 2: 修改根 __init__.py**

三处修改:

1. import 处(`from . import cmt_exporter` 之后)添加:

```python
from . import cmt_updater
```

2. `register()` 中,`cmt_shapekey_to_bone.register()` **之前**添加(先注册使更新面板排在 N 面板最上方):

```python
        cmt_updater.register()
```

3. `unregister()` 中,`cmt_exporter.unregister()` 之后添加:

```python
    cmt_updater.unregister()
```

修改后 `register()` 的 try 块开头为:

```python
    try:
        ##注册子包
        cmt_updater.register()
        cmt_shapekey_to_bone.register()
        cmt_ordinary_tool.register()
        cmt_exporter.register()
```

- [ ] **Step 3: 语法检查**

```powershell
python -m py_compile cmt_updater/__init__.py __init__.py
```

预期:无输出

- [ ] **Step 4: 重新运行 Task 1 单元测试(确认无回归)**

```powershell
python -m unittest tests.test_updater_core -v
```

预期:全部 PASS

- [ ] **Step 5: 提交**

```powershell
git add cmt_updater/__init__.py __init__.py
git commit -m "接入自动更新子包与启动检查"
```

---

### Task 5: Blender 内手动端到端验证

**Files:** 无新文件(验证任务)

需要用户配合在 Blender 中操作。逐项验证:

- [ ] **Step 1: 加载验证**

启动 Blender(或在已开启的 Blender 中 Reload Scripts),确认:
- 控制台无报错,插件正常启用
- 编辑 > 偏好设置 > 插件 > Civ6ModelTool 展开后能看到:"启动时自动检查更新"开关、当前版本、"检查更新"按钮

- [ ] **Step 2: 手动检查(已是最新)**

偏好设置中点击"检查更新",几秒后显示"已是最新版本"(本地版本 ≥ 远程版本时)。N 面板不出现"插件更新"面板。

- [ ] **Step 3: 模拟新版本 → 启动检查 → 一键更新**

1. 把本地 `__init__.py` 的 `bl_info["version"]` 临时改为 `(0, 9, 0)`
2. 重启 Blender
3. 约 3 秒后,3D 视图 N 面板 "Civ6ModelTool" 分类顶部出现"插件更新"面板,显示"发现新版本 vX.Y.Z"和"立即更新"按钮
4. 点击"立即更新",按钮变为"更新中..."(禁用)
5. 下载完成后插件自动热重载,面板提示消失
6. 检查偏好设置中当前版本已变为远程版本;本地 `.git`、`.gitignore` 未被覆盖(`git status` 确认 `.git` 完好)

- [ ] **Step 4: 断网错误处理**

1. 再次把版本改低、断网(或临时改 `core.RAW_INIT_URL` 为无效地址)
2. 点击"检查更新" → 偏好设置显示"出错: ..."、N 面板不显示更新错误面板
3. 恢复网络,检查更新 → 点立即更新前断网 → 更新失败时 N 面板显示"更新失败"与"重试更新"按钮
4. 恢复网络点"重试更新" → 更新成功

- [ ] **Step 5: 收尾提交**

若验证中修改过版本号/URL,恢复后:

```powershell
git status
git diff
git add -A
git commit -m "自动更新功能验证完成"
```

(若无改动可跳过 commit)

---

## 发布流程备忘(开发者)

推送更新给用户:改根 `__init__.py` 的 `bl_info["version"]`(调高)→ push 到 main。用户下次启动 Blender 即收到提示。
