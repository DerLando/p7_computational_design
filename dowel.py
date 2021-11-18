import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc


class Dowel:
    def __init__(self, plane, radius, height):
        self.plane = plane
        self.radius = radius
        self.height = height

        self.volume_geometry = self.calculate_rough_volume()

    def calculate_rough_volume(self):
        return rg.Cylinder(rg.Circle(self.plane, self.radius))
