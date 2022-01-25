import logging
import Rhino
import Rhino.Geometry as rg
import Rhino.Collections as rc
import scriptcontext as sc
from helpers import serde
from component import Component

PLANE_KEY = "plane"
RADIUS_KEY = "radius"
HEIGHT_KEY = "height"
PARENT_KEY = "parent"

# TODO: Derive from Component
class CylinderBase(object):
    """
    Abstract base class for cylinder components
    """

    _LAYER_NAME = "CylinderBase"
    _GEO_LAYER_NAME = "Geometry"

    def __init__(self, plane, radius, height, parent_identifier=None):
        self.plane = plane
        self.radius = radius
        self.height = height

        if not parent_identifier:
            self.parent_identifier = ""
        else:
            self.parent_identifier = parent_identifier

        self.volume_geometry = self.calculate_rough_volume(plane, radius, height)
        self.volume_id = None

    @staticmethod
    def calculate_rough_volume(plane, radius, height):
        raise NotImplementedError()

    def serialize(self, doc=None):
        if doc is None:
            doc = sc.doc

        # get the dowl layer and create attributes from it
        main_layer_id = serde.add_or_find_layer(self._LAYER_NAME, doc=doc)

        # create a volume layer as a child of the main Screw layer
        parent = doc.Layers.FindIndex(main_layer_id)
        volume_layer_id = serde.add_or_find_layer(
            "{}{}volume".format(self._GEO_LAYER_NAME, serde.SEPERATOR),
            doc,
            serde.VOLUME_COLOR,
            parent,
        )

        # create rhino attributes for the volume layer
        attrs = Rhino.DocObjects.ObjectAttributes()
        attrs.Name = str(self)
        attrs.LayerIndex = volume_layer_id
        if self.volume_id:
            attrs.ObjectId = self.volume_id

        # create an `ArchivableDictionary` to store fields
        arch_dict = attrs.UserDictionary
        arch_dict.Set(PLANE_KEY, self.plane)
        arch_dict.Set(RADIUS_KEY, self.radius)
        arch_dict.Set(HEIGHT_KEY, self.height)
        arch_dict.Set(PARENT_KEY, self.parent_identifier)

        assembly_ids = [
            serde.serialize_geometry_with_attrs(self.volume_geometry, attrs, doc)
        ]

        # TODO: Cylinders will serialize multiple times to new geo, that's bad
        return doc.Groups.Add(assembly_ids)

    @classmethod
    def deserialize(cls, group_index, doc=None):
        if doc is None:
            doc = sc.doc

        # create a new instance of self
        self = cls.__new__(cls)

        # find the volume object from the group index
        volume_obj = doc.Groups.GroupMembers(group_index)[0]

        # retrieve arch_dict from volume_id
        arch_dict = volume_obj.Attributes.UserDictionary

        # restore fields on self
        self.plane = arch_dict.GetPlane(PLANE_KEY)
        self.radius = arch_dict.Item[
            RADIUS_KEY
        ]  # C# number types don't play nice with python number types
        self.height = arch_dict.Item[HEIGHT_KEY]  # So get the element directly instead
        self.volume_id = volume_obj.Id
        self.volume_geometry = volume_obj.Geometry
        parent_ident = arch_dict.GetString(PARENT_KEY)
        if parent_ident:
            self.parent_identifier = parent_ident

        return self

    def transform(self, xform):

        self.plane.Transform(xform)

        if self.volume_geometry:
            self.volume_geometry.Transform(xform)
