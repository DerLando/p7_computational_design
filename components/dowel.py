import Rhino
import Rhino.Geometry as rg
import Rhino.Collections as rc
from components.cylinder_base import CylinderBase
import scriptcontext as sc
from helpers import serde
from component import Component


class Dowel(CylinderBase):
    def __init__(self, plane, radius, height, parent_identifier=None):
        super(Dowel, self).__init__(plane, radius, height, parent_identifier)

    def __str__(self):
        return "dowel: {}x{}".format(int(self.radius), int(self.height))

    @staticmethod
    def calculate_rough_volume(plane, radius, height):
        return rg.Cylinder(rg.Circle(plane, radius), height).ToBrep(True, True)


if __name__ == "__main__":
    dowel = Dowel(rg.Plane.WorldXY, 3, 20, "test")
    group_idx = dowel.serialize()
    dowel = Dowel.deserialize(group_idx)

    print(dowel)
