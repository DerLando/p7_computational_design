import logging
import Rhino
import Rhino.Geometry as rg
import Rhino.Collections as rc
from components.cylinder_base import CylinderBase
import scriptcontext as sc
from helpers import serde
from component import Component

PLANE_KEY = "plane"
RADIUS_KEY = "radius"
HEIGHT_KEY = "height"

# TODO: Derive from Component
class ThreadedInsert(CylinderBase):
    def __init__(self, plane, radius, height, parent_identifier=None):
        super(ThreadedInsert, self).__init__(plane, radius, height, parent_identifier)

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


if __name__ == "__main__":
    dowel = ThreadedInsert(rg.Plane.WorldXY, 5, 20)
    group_idx = dowel.serialize()
    dowel = ThreadedInsert.deserialize(group_idx)

    print(dowel)
