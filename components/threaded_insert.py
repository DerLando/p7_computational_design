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

# TODO: Derive from Component
class ThreadedInsert(object):
    def __init__(self, plane, radius, height):
        self.plane = plane
        self.radius = radius
        self.height = height

        self.volume_geometry = self.calculate_rough_volume(plane, radius, height)
        self.volume_id = None

    def __str__(self):
        return "threaded insert: {}x{}".format(int(self.radius), int(self.height))

    @staticmethod
    def calculate_rough_volume(plane, radius, height):

        # create wall base curves
        inner_wall = rg.Circle(plane, radius)
        outer_wall = rg.Circle(plane, radius + 1.1)

        # create base surface for extrusion
        result = rg.Brep.CreatePlanarBreps(
            [inner_wall.ToNurbsCurve(), outer_wall.ToNurbsCurve()], 0.001
        )
        if result.Count != 1:
            logging.error("Failed to create base surface for threaded insert!")
            return

        # extrude base surface
        path = rg.LineCurve(
            rg.Line(plane.Origin, rg.Point3d(plane.Origin + plane.ZAxis * height))
        )
        result = result[0].Faces[0].CreateExtrusion(path, True)
        if not result:
            logging.error("Failed to extrude base surface for threaded insert!")
            return

        return result

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
        main_layer_id = serde.add_or_find_layer(serde.INSERT_LAYER_NAME, doc=doc)

        # create a volume layer as a child of the main dowel layer
        parent = doc.Layers.FindIndex(main_layer_id)
        volume_layer_id = serde.add_or_find_layer(
            "{}{}volume".format(serde.INSERT_LAYER_NAME, serde.SEPERATOR),
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

    def transform(self, xform):

        self.plane.Transform(xform)

        if self.volume_geometry:
            self.volume_geometry.Transform(xform)


if __name__ == "__main__":
    dowel = ThreadedInsert(rg.Plane.WorldXY, 5, 20)
    group_idx = dowel.serialize()
    dowel = ThreadedInsert.deserialize(group_idx)

    print(dowel)
