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
