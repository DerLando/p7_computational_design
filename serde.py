import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import System.Drawing as draw
import keys
import math

BEAM_LAYER_NAME = "BEAMS"
CASSETTE_LAYER_NAME = "CASSETTES"
DOWEL_LAYER_NAME = "DOWELS"
PLATE_LAYER_NAME = "PLATES"
SEPERATOR = "_"
CURVE_COLOR = draw.Color.FromArgb(230, 79, 225)
DOT_COLOR = draw.Color.FromArgb(55, 230, 206)
VOLUME_COLOR = draw.Color.FromArgb(230, 203, 101)
LABEL_COLOR = draw.Color.FromArgb(254, 0, 0)


def add_or_find_layer(name, doc=None, color=None, parent=None):
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


def serialize_geometry(geo, layer_index, doc=None, name=None, old_id=None):
    attrs = Rhino.DocObjects.ObjectAttributes()
    attrs.LayerIndex = layer_index

    if name is not None:
        attrs.Name = name

    if old_id is not None:
        attrs.Id = old_id

    if doc is None:
        doc = sc.doc

    return doc.Objects.Add(geo, attrs)
