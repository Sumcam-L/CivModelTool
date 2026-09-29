"""Blender 枚举项（EnumProperty items=）与 poll 回调，以及材质类名模糊匹配。"""
from .allowed_classes import get_allowed_anm_classes, get_allowed_geo_classes
from .civ6_data import g_DSG_json, g_Mat_json

def get_geotype_items(self,context):
    geoClasses = ["DecalGeometry","LandmarkModel","LandmarkObstructionProfile","Leader","Leader_ShadowVolume","UILensModel","Unit","VFXModel","WonderMovieModel"]
    items = []
    for tClass in geoClasses:
        items.append((tClass,tClass,""))
    return items

def get_anmtype_items(self,context):
    anmClasses = ["CameraAnimation","Landmark","Leader","Unit","VFX","WonderMovie"]
    items = []
    for tClass in anmClasses:
        items.append((tClass,tClass,""))
    return items

def get_geo_files(self,context):
    items = []
    for property in self.GeoList:
        items.append((property.FileName, property.FileName, ""))
    return items

def get_ast_files(self,context):
    data = context.scene.CMT.ExporterSettings
    items = []
    for property in data.AstList:
        items.append((property.FileName, property.FileName, ""))
    return items

def resolve_enum(prop_group, prop_name, items_func):
    try:
        raw = prop_group[prop_name]
    except KeyError:
        raw = prop_group.bl_rna.properties[prop_name].default
    if isinstance(raw, str):
        return raw
    items = items_func(None, None)
    if isinstance(raw, int) and 0 <= raw < len(items):
        return items[raw][0]
    return ""

def get_astgeometries_items(self,context):
    data = context.scene.CMT.ExporterSettings
    if len(data.AstList) == 0:
        return [("", "无可用模型", "")]
    curAst = data.AstList[data.CurrentAstIndex]
    ast_class = resolve_enum(curAst, "Class", get_ast_class_items)
    allowed = get_allowed_geo_classes(ast_class)
    items = []
    for property in data.GeoList:
        geo_class = resolve_enum(property, "Class", get_geotype_items)
        if geo_class in allowed:
            items.append((property.FileName, property.FileName, ""))
    if not items:
        items.append(("", "无可用模型", ""))
    return items

def get_ast_class_items(self,context):
    items = []
    for lClass in g_DSG_json["Classes"]:
        items.append((lClass,lClass,""))
    return items

def get_ast_DSG_items(self,context):
    data = context.scene.CMT.ExporterSettings
    curAst = data.AstList[data.CurrentAstIndex]
    items = []
    for lDSG in g_DSG_json[curAst.Class]:
        items.append((lDSG,lDSG,""))
    return items

def get_material_class_items(self,context):
    items = []
    for v in g_Mat_json:
        items.append((v,v,""))
    return items

def fuzzy_match_material_class(geo_class):
    if not geo_class:
        return None
    if geo_class in g_Mat_json:
        return geo_class
    best = None
    for mat_class in g_Mat_json:
        if geo_class.startswith(mat_class):
            if best is None or len(mat_class) > len(best):
                best = mat_class
    if best:
        return best
    for suffix in ["Model", "Geometry", "ObstructionProfile", "ShadowVolume"]:
        if geo_class.endswith(suffix):
            stripped = geo_class[:-len(suffix)].rstrip("_")
            if stripped in g_Mat_json:
                return stripped
            for mat_class in g_Mat_json:
                if mat_class.startswith(stripped) or stripped in mat_class:
                    return mat_class
    return None


def mat_poll(self,obj):
    data = self
    refGeos = []
    for ast in data.AstList:
        for geo in ast.Geometries:
            refGeos.append(geo.value)
    for geo in data.GeoList:
        if geo.FileName in refGeos:
            for prop in geo.Geometries:
                if prop.value is None:
                    continue
                for mat in prop.value.data.materials:
                    if mat is obj:
                        return True
    return False

ARTDEF_FILES = ("Units.artdef", "Leaders.artdef")


def default_anm_class(data):
    """当前 Ast 允许的第一个动画类型；无 Ast 或不允许任何动画时返回 None。"""
    if len(data.AstList) == 0:
        return None
    curAst = data.AstList[data.CurrentAstIndex]
    allowed = get_allowed_anm_classes(resolve_enum(curAst, "Class", get_ast_class_items))
    return allowed[0] if allowed else None

def get_artdef_items(self,context):
    return [(name, name, name) for name in ARTDEF_FILES]
