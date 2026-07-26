import json
import os

_JSON_PATH = os.path.join(os.path.dirname(__file__), "assets", "AllowedClasses.json")

with open(_JSON_PATH, "r", encoding="utf-8") as _f:
    _ALLOWED_CLASSES = json.load(_f)


def get_allowed_geo_classes(ast_class):
    return _ALLOWED_CLASSES.get(ast_class, {}).get("geo", [])


def get_allowed_anm_classes(ast_class):
    return _ALLOWED_CLASSES.get(ast_class, {}).get("anm", [])
