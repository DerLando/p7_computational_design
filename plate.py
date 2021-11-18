import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc


class Plate:
    def __init__(self, ident, plane, top_outline):
        self.ident = ident
        self.plane = plane
        self.top_outline = top_outline

        self.volume_geometry = self.calculate_rough_volume()

    def calculate_rough_volume(self):
        raise NotImplementedError()
