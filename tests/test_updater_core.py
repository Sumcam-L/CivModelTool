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
