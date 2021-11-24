import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import math
from algorithms import polyline_to_point_dict, polyline_angles, point_polar
from beam import Beam


class Cassette:
    CORNER_NAMES = ["A", "B", "C", "D", "E", "F", "G", "H"]

    def __init__(
        self, ident, face_index, plane, top_outline, neighbors, geometry_settings
    ):
        # store init arguments in public fields
        self.identifier = ident
        self.face_index = face_index
        self.plane = plane
        self.top_outline = top_outline
        self.neighbors = neighbors
        self.geometry_settings = geometry_settings

        # initialize empty buffers
        self.beam_corner_points = {}
        self.beams = {}

    @property
    def corner_count(self):
        """
        The number of unique corners of the cassette.
        Since the top_outline of the cassette is a closed polyline,
        it's first and last point are not unique.

        Returns:
            int: The corner count
        """
        return self.top_outline.Count - 1

    def create_geometry(self):
        """
        Wrapper function to handle all steps of geometry generation, in correct order.
        """

        # create the upper inflection points for the first beam layer
        self.beam_corner_points["TopUpper"] = Cassette.create_inflection_points(
            self.top_outline, self.plane, self.geometry_settings.beam_max_width
        )

        # generate a layer of beam outlines
        top_beam_outlines = self.create_even_layer_beam_outlines(
            self.beam_corner_points["TopUpper"], self.corner_count
        )

        # generate beams from the outlines
        beams = []
        for index, outline in enumerate(top_beam_outlines):
            beam_ident = "{}_Beam_T{}".format(self.identifier, self.CORNER_NAMES[index])
            beam = Beam(
                beam_ident,
                self.plane,
                self.geometry_settings.beam_thickness,
                outline,
                0.0,
            )

            beams.append(beam)

        # DEBUG!!
        self.beams = beams

    def sort_neighbors(self):
        """
        Sorts the cassette neighbors by it's outline
        """

        raise NotImplementedError()

    @staticmethod
    def __get_left_inflection(corner_name):
        return corner_name + "_left"

    @staticmethod
    def __get_right_inflection(corner_name):
        return corner_name + "_right"

    @staticmethod
    def __get_inner_inflection(corner_name):
        return corner_name + "_inner"

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
        corners = {}
        point_count = len(outline)

        # iterate over angles
        for i in range(len(angles)):

            # get current angle, corner name, corner and next corner
            angle = angles[i]
            corner_name = Cassette.CORNER_NAMES[i]
            cur_corner = outline[i]
            next_corner = outline[(i + 1) % point_count]

            # calculate plane at corner oriented with it's x-axis towards the next corner
            x_axis = next_corner - cur_corner
            polar_plane = rg.Plane(
                cur_corner, x_axis, rg.Vector3d.CrossProduct(x_axis, plane.ZAxis)
            )
            polar_plane.Rotate(math.pi, polar_plane.ZAxis)

            # sin(alpha) = a / c => sin(angle / 2) = offset_amount / c => c = offset_amount / sin(angle / 2)

            # calculate c, gamma and a
            c = offset_amount / math.sin(angle / 2.0)
            gamma = math.pi - angle
            a = c / (2 * math.sin(gamma / 2.0))

            # evaluate inflection points on polar plane and add to corners dict
            corners[Cassette.__get_left_inflection(corner_name)] = point_polar(
                polar_plane, a, angle
            )
            corners[corner_name] = cur_corner
            corners[Cassette.__get_right_inflection(corner_name)] = point_polar(
                polar_plane, a, 0
            )
            corners[Cassette.__get_inner_inflection(corner_name)] = point_polar(
                polar_plane, c, angle / 2
            )

        return corners

    @staticmethod
    def create_even_layer_beam_outlines(inflection_points, corner_count):

        # get the corner names for the cassette
        corner_names = Cassette.CORNER_NAMES[:corner_count]
        outlines = []

        # iterate over corners
        for i in range(corner_count):

            # extract current and next corner name
            cur_corner_name = corner_names[i]
            next_corner_name = corner_names[(i + 1) % corner_count]

            # generate beam corners from known inflection point layout
            a = inflection_points[Cassette.__get_right_inflection(cur_corner_name)]
            b = inflection_points[next_corner_name]
            c = inflection_points[Cassette.__get_right_inflection(next_corner_name)]
            d = inflection_points[Cassette.__get_inner_inflection(cur_corner_name)]

            # create closed polyline from beam corners and add to outlines list
            beam_outline = rg.Polyline([a, b, c, d, a])
            outlines.append(beam_outline)

        return outlines

    def create_odd_layer_beams(self):
        raise NotImplementedError()

    def create_plate(self):
        raise NotImplementedError()

    def create_dowels(self):
        raise NotImplementedError()
