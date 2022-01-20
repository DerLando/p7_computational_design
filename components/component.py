try:
    import scriptcontext as sc
except:
    import inside_doc as sc

import Rhino
import Rhino.Geometry as rg
import Rhino.Collections as rc
from helpers import serde
from System import Guid
import copy


class Component(object):
    __COMPONENT_DIM_STYLE = sc.doc.DimStyles.Current
    _PROPERTIES_KEY = "PROPERTIES"
    _LABEL_HEIGHT = 1.0
    _LAYER_NAME = "Component"
    """The parent layer name of the component. Override this in child classes"""
    label = None
    """The label geometry"""
    label_id = Guid.Empty
    """The id of the identifier label in the rhino doc"""
    settings = {}
    """All possible geometry settings. Child classes can do whatever here"""

    def __init__(self, identifier, plane):
        label = rg.TextEntity.Create(
            identifier, plane, self.__COMPONENT_DIM_STYLE, False, 1000, 0.0
        )
        label.Justification = rg.TextJustification.MiddleCenter
        label.TextHeight = self._LABEL_HEIGHT

        self.label = label
        self.label_id = None

    @property
    def identifier(self):
        return self.label.PlainText

    @property
    def plane(self):
        return self.label.Plane

    @classmethod
    def deserialize(cls, group_index, doc=None):
        """
        Deserializes label geometry and settings.
        Child classes need to make sure to also deserialize their other geometries
        """
        if doc is None:
            doc = sc.doc

        # create a new, empty instance of self
        self = cls.__new__(cls)

        # find out what identifier we are working with
        identifier = doc.Groups.GroupName(group_index)
        if identifier is None:
            return

        # get group members for given index
        members = doc.Groups.GroupMembers(group_index)

        # get the label object
        label_obj = [member for member in members if member.Name == identifier][0]
        self.label = label_obj.Geometry
        self.label_id = label_obj.Id

        # extract properties from label object
        prop_dict = copy.deepcopy(cls._deserialize_properties(label_obj, doc))
        for key, value in prop_dict.items():
            self.__setattr__(key, value)

        return self

    def serialize(self, doc=None):
        if doc is None:
            doc = sc.doc

        main_layer = self._main_layer(doc)
        label_layer_index = serde.add_or_find_layer(
            self._child_layer_name("Label"),
            doc,
            color=serde.LABEL_COLOR,
            parent=main_layer,
        )
        return self._serialize_label(label_layer_index, doc, self.settings)

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
            attrs.UserDictionary.Set(self._PROPERTIES_KEY, attr_dict)

        # serialize label
        return serde.serialize_geometry_with_attrs(self.label, attrs, doc)

    @classmethod
    def _deserialize_properties(cls, label_obj, doc=None):
        if doc is None:
            doc = sc.doc

        return serde.deserialize_pydict(
            label_obj.Attributes.UserDictionary.GetDictionary(cls._PROPERTIES_KEY)
        )

    @classmethod
    def _child_layer_name(cls, name):
        return "{}{}{}".format(cls._LAYER_NAME, serde.SEPERATOR, name)

    def _main_layer(self, doc):
        return doc.Layers.FindIndex(serde.add_or_find_layer(self._LAYER_NAME, doc))

    def transform(self, xform):
        """
        Transforms the component and all it's geometry by the given transformation matrix
        """

        self.label.Transform(xform)
        pass
