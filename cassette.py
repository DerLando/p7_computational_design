import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
from algorithms import polyline_to_point_dict


class Cassette:
    def __init__(
        self, ident, face_index, plane, top_outline, neighbors, geometry_settings
    ):
        self.identifier = ident
        self.face_index = face_index
        self.plane = plane
        self.top_outline = top_outline
        self.neighbors = neighbors
        self.geometry_settings = geometry_settings

        self.points = Cassette.create_inflection_points(
            self.top_outline, self.geometry_settings.beam_max_width
        )

    def sort_neighbors(self):
        """
        Sorts the cassette neighbors by it's outline
        """

        raise NotImplementedError()

    @staticmethod
    def create_inflection_points(outline, offset_amount):
        """
        Creates the inflection points around the polyline certices,
        basically the points before and after each corner, e.g. 'A_left', 'A', 'A_right'

        Args:
            outline (Polyline): The outline used to generate the inflection points
            offset_amount (float): The amount by which the outline should be offset inwards

        Returns:
            dict[str : Point3d]: A dictionary of named inflection and corner points.
        """

        raise NotImplementedError()

    def create_even_layer_beams(self):
        raise NotImplementedError()

    def create_odd_layer_beams(self):
        raise NotImplementedError()

    def create_plate(self):
        raise NotImplementedError()

    def create_dowels(self):
        raise NotImplementedError()
