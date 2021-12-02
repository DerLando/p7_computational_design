import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc


class Dowel(object):
    def __init__(self, plane, radius, height):
        self.plane = plane
        self.radius = radius
        self.height = height

        self.volume_geometry = self.calculate_rough_volume()

    def __str__(self):
        return "dowel: {}x{}".format(int(self.radius * 1000), int(self.height * 1000))

    def calculate_rough_volume(self):
        return rg.Cylinder(rg.Circle(self.plane, self.radius), self.height)

    @property
    def bottom_circle(self):
        return self.volume_geometry.CircleAt(0.0)

    @property
    def top_circle(self):
        return self.volume_geometry.CircleAt(self.height)
