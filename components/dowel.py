import Rhino
import Rhino.Geometry as rg
import Rhino.Collections as rc
import scriptcontext as sc
from helpers import serde
from component import Component

PLANE_KEY = "plane"
RADIUS_KEY = "radius"
HEIGHT_KEY = "height"

# TODO: Derive from Component
class Dowel(object):
    def __init__(self, plane, radius, height):
        self.plane = plane
        self.radius = radius
        self.height = height

        self.volume_geometry = self.calculate_rough_volume(plane, radius, height)
        self.volume_id = None

    def __str__(self):
        return "dowel: {}x{}".format(int(self.radius * 1000), int(self.height * 1000))

    @staticmethod
    def calculate_rough_volume(plane, radius, height):
        return rg.Cylinder(rg.Circle(plane, radius), height)

    @property
    def bottom_circle(self):
        return self.volume_geometry.CircleAt(0.0)

    @property
    def top_circle(self):
        return self.volume_geometry.CircleAt(self.height)

    def serialize(self, doc=None):
        if doc is None:
            doc = sc.doc

        # get the dowl layer and create attributes from it
        main_layer_id = serde.add_or_find_layer(serde.DOWEL_LAYER_NAME, doc=doc)

        # create a volume layer as a child of the main dowel layer
        parent = doc.Layers.FindIndex(main_layer_id)
        volume_layer_id = serde.add_or_find_layer(
            "{}{}volume".format(serde.DOWEL_LAYER_NAME, serde.SEPERATOR),
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

        assembly_ids = [
            serde.serialize_geometry_with_attrs(
                self.volume_geometry.ToBrep(True, True), attrs, doc
            )
        ]

        # assembly_ids = [
        #     doc.Objects.AddBrep(self.volume_geometry.ToBrep(True, True), attrs)
        # ]

        # TODO: Dowels will serialize multiple times to new geo, that's bad
        return doc.Groups.Add(assembly_ids)

    @classmethod
    def deserialize(cls, group_index, doc=None):
        if doc is None:
            doc = sc.doc

        # create a new instance of self
        self = cls.__new__(cls)

        # find the volume_id from group_index
        volume_id = doc.Groups.GroupMembers(group_index)[0].Id

        # retrieve arch_dict from volume_id
        arch_dict = doc.Objects.FindId(volume_id).Attributes.UserDictionary

        # restore fields on self
        self.plane = arch_dict.GetPlane(PLANE_KEY)
        self.radius = arch_dict.Item[
            RADIUS_KEY
        ]  # C# number types don't play nice with python number types
        self.height = arch_dict.Item[HEIGHT_KEY]  # So get the element directly instead
        self.volume_id = volume_id
        self.volume_geometry = cls.calculate_rough_volume(
            self.plane, self.radius, self.height
        )

        return self


if __name__ == "__main__":
    dowel = Dowel(rg.Plane.WorldXY, 0.1, 1.0)
    group_idx = dowel.serialize()
    dowel = Dowel.deserialize(group_idx)

    print(dowel)
