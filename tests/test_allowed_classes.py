import os
import importlib.util
import unittest

_MOD_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "cmt_exporter", "allowed_classes.py",
)
spec = importlib.util.spec_from_file_location("allowed_classes", _MOD_PATH)
allowed_classes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(allowed_classes)


class TestGetAllowedGeoClasses(unittest.TestCase):
    def test_unit_allows_only_unit(self):
        result = allowed_classes.get_allowed_geo_classes("Unit")
        self.assertEqual(result, ["Unit"])

    def test_landmark_allows_three(self):
        result = allowed_classes.get_allowed_geo_classes("Landmark")
        self.assertEqual(result, ["DecalGeometry", "LandmarkModel", "LandmarkObstructionProfile"])

    def test_unknown_class_returns_empty(self):
        result = allowed_classes.get_allowed_geo_classes("NonExistent")
        self.assertEqual(result, [])

    def test_empty_class_returns_empty(self):
        result = allowed_classes.get_allowed_geo_classes("StrategicView_Route")
        self.assertEqual(result, [])


class TestGetAllowedAnmClasses(unittest.TestCase):
    def test_unit_allows_unit(self):
        result = allowed_classes.get_allowed_anm_classes("Unit")
        self.assertEqual(result, ["Unit"])

    def test_uilens_allows_no_anm(self):
        result = allowed_classes.get_allowed_anm_classes("UILensAsset")
        self.assertEqual(result, [])

    def test_firefx_allows_vfx(self):
        result = allowed_classes.get_allowed_anm_classes("FireFX")
        self.assertEqual(result, ["VFX"])

    def test_unknown_class_returns_empty(self):
        result = allowed_classes.get_allowed_anm_classes("NonExistent")
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
