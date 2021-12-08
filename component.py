import scriptcontext as sc
import Rhino
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
import Rhino.Collections as rc


class Component(object):
    __COMPONENT_DIM_STYLE = Rhino.DocObjects.DimensionStyle()
    __COMPONENT_DIM_STYLE.TextOrientation = Rhino.DocObjects.TextOrientation.InPlane

    def __init__(self, identifier, plane):
        self.label = rg.TextEntity.Create(
            identifier, plane, self.__COMPONENT_DIM_STYLE, False, 1.0, 0.0
        )
        self.label_id = None

    @property
    def identifier(self):
        return self.label.PlainText

    @property
    def plane(self):
        return self.label.Plane

    @classmethod
    def deserialize(cls, group_index, doc=None):
        raise NotImplementedError()

    def serialize(self, doc=None):
        raise NotImplementedError()
