import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import math
from algorithms import polyline_to_point_dict, polyline_angles, point_polar


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
            self.top_outline, self.plane, self.geometry_settings.beam_max_width
        )

    def sort_neighbors(self):
        """
        Sorts the cassette neighbors by it's outline
        """

        raise NotImplementedError()

    @staticmethod
    def create_inflection_points(outline, plane, offset_amount):
        """
        Creates the inflection points around the polyline certices,
        basically the points before and after each corner, e.g. 'A_left', 'A', 'A_right'

        Args:
            outline (Polyline): The outline used to generate the inflection points
            plane (Plane): The plane of the outline
            offset_amount (float): The amount by which the outline should be offset inwards

        Returns:
            dict[str : Point3d]: A dictionary of named inflection and corner points.
        """

        # get polyline angles
        angles = polyline_angles(outline, plane)

        # initialize corner names and corners
        corner_names = ["A", "B", "C", "D", "E", "F", "G", "H"]
        corners = {}

        point_count = len(outline)

        # iterate over angles
        for i in range(len(angles)):

            # get current angle, corner name, corner and next corner
            angle = angles[i]
            corner_name = corner_names[i]
            cur_corner = outline[i]
            next_corner = outline[(i + 1) % point_count]

            # calculate plane at corner orientet with it's x-axis towards the next corner
            x_axis = next_corner - cur_corner
            polar_plane = rg.Plane(
                cur_corner, x_axis, rg.Vector3d.CrossProduct(x_axis, plane.ZAxis)
            )

            # calculate c, gamma and a
            c = math.tan(angle / 2.0) * offset_amount
            gamma = math.pi - angle
            a = c / (2 * math.sin(gamma / 2.0))

            # evaluate inflection points on polar plane and add to corners dict
            corners[corner_name + "_left"] = point_polar(polar_plane, a, angle)
            corners[corner_name] = cur_corner
            corners[corner_name + "_right"] = point_polar(polar_plane, a, 0)
            corners[corner_name + "'"] = point_polar(polar_plane, c, angle / 2)

        return corners

    def create_even_layer_beams(self):
        raise NotImplementedError()

    def create_odd_layer_beams(self):
        raise NotImplementedError()

    def create_plate(self):
        raise NotImplementedError()

    def create_dowels(self):
        raise NotImplementedError()
