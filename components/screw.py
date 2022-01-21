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
HEAD_THICKNESS = 6.4


class ScrewFactory(object):
    @staticmethod
    def create_m_screw(plane, name):
        # hardcoded garbo...
        name = name[1:]
        diameter, length = [float(part) for part in name.split("x")]

        return Screw(plane, diameter / 2.0, length)


# TODO: Derive from Component
class Screw(object):
    """
    For now, only MXxX screws are supported
    """

    def __init__(self, plane, radius, height):
        self.plane = plane
        self.radius = radius
        self.height = height

        self.volume_geometry = self.calculate_rough_volume(plane, radius, height)
        self.volume_id = None

    def __str__(self):
        return "Screw: M{}x{}".format(int(self.radius), int(self.height))

    @staticmethod
    def calculate_rough_volume(plane, radius, height):
        # create the screw body
        screw_cylinder = rg.Cylinder(rg.Circle(plane, radius), height)

        # create the screw head
        plane.Flip()
        screw_hex_base = rg.Polyline.CreateInscribedPolygon(
            rg.Circle(plane, radius * 1.9), 6
        )
        screw_head = rg.Extrusion.Create(
            screw_hex_base.ToPolylineCurve(), HEAD_THICKNESS, True
        )

        # union body and head
        result = rg.Brep.CreateBooleanUnion(
            [screw_cylinder.ToBrep(True, True), screw_head.ToBrep()], 0.001
        )
        if not result:
            logging.error("Failed to boolean screw head and body!")
            return
        if not result.Count == 1:
            logging.error("Failed to boolean union screw head and body!")
            return

        return result[0]

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
        main_layer_id = serde.add_or_find_layer(serde.SCREW_LAYER_NAME, doc=doc)

        # create a volume layer as a child of the main Screw layer
        parent = doc.Layers.FindIndex(main_layer_id)
        volume_layer_id = serde.add_or_find_layer(
            "{}{}volume".format(serde.SCREW_LAYER_NAME, serde.SEPERATOR),
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
            serde.serialize_geometry_with_attrs(self.volume_geometry, attrs, doc)
        ]

        # assembly_ids = [
        #     doc.Objects.AddBrep(self.volume_geometry.ToBrep(True, True), attrs)
        # ]

        # TODO: Screws will serialize multiple times to new geo, that's bad
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

    def transform(self, xform):

        self.plane.Transform(xform)

        if self.volume_geometry:
            self.volume_geometry.Transform(xform)


if __name__ == "__main__":
    Screw = ScrewFactory.create_m_screw(rg.Plane.WorldXY, "M10x50")
    group_idx = Screw.serialize()
    Screw = Screw.deserialize(group_idx)

    print(Screw)
