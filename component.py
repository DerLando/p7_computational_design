import scriptcontext as sc
import Rhino
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
import Rhino.Collections as rc

COMPONENT_DIM_STYLE = Rhino.DocObjects.DimensionStyle()
COMPONENT_DIM_STYLE.TextOrientation = Rhino.DocObjects.TextOrientation.InPlane


class Component(object):
    def __init__(self, identifier, plane):
        self.__label = rg.TextEntity.Create(
            identifier, plane, COMPONENT_DIM_STYLE, False, 1.0, 0.0
        )
        self.label_id = None

    @property
    def label(self):
        return self.__label

    @property
    def identifier(self):
        return self.__label.PlainText

    @property
    def plane(self):
        return self.__label.Plane

    @classmethod
    def deserialize(cls, group_index, doc=None):
        raise NotImplementedError()

    def serialize(self, doc=None):
        raise NotImplementedError()
