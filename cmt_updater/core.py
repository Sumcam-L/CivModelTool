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
