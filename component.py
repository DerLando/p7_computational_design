import scriptcontext as sc
import Rhino
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
import Rhino.Collections as rc
import serde


class Component(object):
    __COMPONENT_DIM_STYLE = Rhino.DocObjects.DimensionStyle()
    __COMPONENT_DIM_STYLE.TextOrientation = Rhino.DocObjects.TextOrientation.InPlane
    __PROPERTIES_KEY = "PROPERTIES"

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

    def _serialize_label(self, layer_index, doc=None, properties=None):
        if doc is None:
            doc = sc.doc

        # create attrs for the label, as we need to store additional data on the label UserDictionary
        attrs = Rhino.DocObjects.ObjectAttributes()
        attrs.LayerIndex = layer_index
        attrs.Name = self.identifier
        if self.label_id is not None:
            attrs.ObjectId = self.label_id

        # serialize props on attrs UserDictionary
        if properties is not None:
            attr_dict = serde.serialize_pydict(properties)
            attrs.UserDictionary.Set(self.__PROPERTIES_KEY, attr_dict)

        # serialize label
        return serde.serialize_geometry_with_attrs(self.label, attrs, doc)

    @classmethod
    def _deserialize_properties(cls, label_obj, doc=None):
        if doc is None:
            doc = sc.doc

        return serde.deserialize_pydict(
            label_obj.Attributes.UserDictionary.GetDictionary(cls.__PROPERTIES_KEY)
        )
