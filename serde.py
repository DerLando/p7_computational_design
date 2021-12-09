import Rhino
import Rhino.Geometry as rg
import Rhino.Collections as rc
import scriptcontext as sc
import System.Drawing as draw
import keys
import math

BEAM_LAYER_NAME = "BEAMS"
CASSETTE_LAYER_NAME = "CASSETTES"
DOWEL_LAYER_NAME = "DOWELS"
PLATE_LAYER_NAME = "PLATES"
PANEL_LAYER_NAME = "PANELS"
SEPERATOR = "_"
CURVE_COLOR = draw.Color.FromArgb(230, 79, 225)
DOT_COLOR = draw.Color.FromArgb(55, 230, 206)
VOLUME_COLOR = draw.Color.FromArgb(230, 203, 101)
LABEL_COLOR = draw.Color.FromArgb(230, 0, 0)


def add_or_find_layer(name, doc=None, color=None, parent=None):
    """
    Adds or finds the given layer and returns it's index.
    If the layer is found, it will be returned as is,
    so the color and parent overwrites will do nothing.

    Args:
        name (str): The name of the layer
        doc (RhinoDoc, optional): The RhinoDoc to search for the layer.
        If none is specified, the currently active doc will be used.
        color (System.Drawing.Color, optional): The color for the layer, if it is newly created.
        Default is black
        parent (Layer): An optional parent layer, if the layer is newly created.

    Returns:
        int: The index of the layer in the layer table
    """
    if doc is None:
        doc = sc.doc

    layer = doc.Layers.FindName(name)

    if layer is not None:
        return layer.Index

    layer = Rhino.DocObjects.Layer()
    layer.Name = name

    if color:
        layer.Color = color

    if parent:
        layer.ParentLayerId = parent.Id

    return doc.Layers.Add(layer)


def serialize_geometry_with_attrs(geo, attrs, doc=None):
    if doc is None:
        doc = sc.doc

    if attrs.ObjectId is not None:
        doc.Objects.Delete(attrs.ObjectId, False)

    return doc.Objects.Add(geo, attrs)


def serialize_geometry(geo, layer_index, doc=None, name=None, old_id=None):
    """
    Serialize a given geometry to the given rhino document.

    Args:
        geo (GeometryBase): Some geometry that inherits from GeometryBase.
        layer_index (int): The layer to put the geometry on.
        doc (RhinoDoc, optional): The document to serialize to.
        If none is given, the currently active doc will be chosen
        name (str, optional): A name for the serialized geometry.
        old_id (System.Guid, optional): If given, the geo will have the same id after serialization.

    Returns:
        System.Guid: The id of the geo in the rhino document
    """
    attrs = Rhino.DocObjects.ObjectAttributes()
    attrs.LayerIndex = layer_index

    if name is not None:
        attrs.Name = name

    if old_id is not None:
        attrs.ObjectId = old_id

    return serialize_geometry_with_attrs(geo, attrs, doc)


def serialize_pydict(py_dict):
    arch_dict = rc.ArchivableDictionary()
    for key, value in py_dict.items():
        if isinstance(value, dict):
            arch_dict.Set(key, serialize_pydict(value))
        else:
            arch_dict.Set(key, value)

    return arch_dict


def deserialize_pydict(arch_dict):
    py_dict = {}
    for key in arch_dict.Keys:
        item = arch_dict.Item[key]
        if isinstance(item, rc.ArchivableDictionary):
            py_dict[key] = deserialize_pydict(item)
        else:
            py_dict[key] = item

    return py_dict


if __name__ == "__main__":

    py_dict = {str(i): float(i) for i in range(5)}
    py_dict = {"name": "HI", "thickness": 3.147, "nested": py_dict}
    main_dict = rc.ArchivableDictionary()

    main_dict.Set("test", serialize_pydict(py_dict))

    deserialized = deserialize_pydict(main_dict.GetDictionary("test"))

    print(deserialized)
