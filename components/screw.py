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
PARENT_KEY = "parent"
HEAD_THICKNESS = 6.4


class ScrewFactory(object):
    @staticmethod
    def create_m_screw(plane, name, parent_identifier):
        # hardcoded garbo...
        name = name[1:]
        diameter, length = [float(part) for part in name.split("x")]

        return Screw(plane, diameter / 2.0, length, parent_identifier)


# TODO: Derive from Component
class Screw(CylinderBase):
    """
    For now, only MXxX screws are supported
    """

    _LAYER_NAME = "Screws"

    def __init__(self, plane, radius, height, parent_identifier=None):
        super(Screw, self).__init__(plane, radius, height, parent_identifier)

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


if __name__ == "__main__":
    Screw = ScrewFactory.create_m_screw(rg.Plane.WorldXY, "M10x50", "test")
    group_idx = Screw.serialize()
    Screw = Screw.deserialize(group_idx)

    print(Screw)
