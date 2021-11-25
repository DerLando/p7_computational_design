import logging
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import math
from algorithms import polyline_to_point_dict, polyline_angles, point_polar
from beam import Beam
from collections import deque
from geometry import ClosedPolyline


class Cassette:
    CORNER_NAMES = ["A", "B", "C", "D", "E", "F", "G", "H"]

    def __init__(
        self, ident, face_index, plane, top_outline, neighbors, geometry_settings
    ):
        # store init arguments in public fields
        self.identifier = ident
        self.face_index = face_index
        self.plane = plane
        self.top_outline = ClosedPolyline(top_outline)
        self.neighbors = neighbors
        self.geometry_settings = geometry_settings

        # initialize empty buffers
        self.beam_corner_points = {}
        self.beams = {}

        # TODO: FIXME
        self.neighbors = [None for _ in range(self.top_outline.corner_count - 1)]

    @property
    def corner_count(self):
        """
        The number of unique corners of the cassette.
        Since the top_outline of the cassette is a closed polyline,
        it's first and last point are not unique.

        Returns:
            int: The corner count
        """
        return self.top_outline.corner_count

    def create_geometry(self):
        """
        Wrapper function to handle all steps of geometry generation, in correct order.
        """

        # DEBUG!!
        angle = math.pi / 10

        # create the upper inflection points for the first beam layer
        self.beam_corner_points["TopUpper"] = Cassette.create_inflection_points(
            self.top_outline, self.plane, self.geometry_settings.beam_max_width
        )

        # generate a layer of beam outlines
        top_beam_outlines = self.create_even_layer_beam_outlines(
            self.beam_corner_points["TopUpper"], self.corner_count
        )

        # generate top beams
        top_beams = self.create_beams_from_outlines(top_beam_outlines, level=0)

        # generate middle outline from beam corners
        lower_corners = []
        for beam in top_beams:
            lower_corners.append(beam.corners["bottom"]["B"])

        # TODO: Figure out why we need to rotate here!
        lower_corners = deque(lower_corners)
        lower_corners.rotate(1)

        middle_outline = ClosedPolyline(rg.Polyline(lower_corners))

        # TODO: Better planes!
        middle_plane = rg.Plane(self.plane)
        middle_plane.Origin = middle_outline.center_point()

        # TODO: Calculate new offset amount here, depending on neigbor angle and beam thickness
        # x = math.tan()
        self.beam_corner_points["MiddleUpper"] = Cassette.create_inflection_points(
            middle_outline,
            middle_plane,
            self.geometry_settings.beam_max_width
            + math.tan(math.pi - angle / 2.0) * self.geometry_settings.beam_thickness,
        )
        middle_beam_outlines = Cassette.create_odd_layer_beam_outlines(
            self.beam_corner_points["MiddleUpper"], self.corner_count
        )

        middle_beams = self.create_beams_from_outlines(middle_beam_outlines, 1)

        # generate lower outline from beam corners
        lower_corners = []
        for beam in middle_beams:
            lower_corners.append(beam.corners["bottom"]["B"])
        bottom_outline = ClosedPolyline(rg.Polyline(lower_corners))
        bottom_plane = rg.Plane(self.plane)
        bottom_plane.Origin = middle_outline.center_point()

        # generate bottom inflection points
        self.beam_corner_points["BottomUpper"] = Cassette.create_inflection_points(
            bottom_outline,
            bottom_plane,
            self.geometry_settings.beam_max_width
            + math.tan(math.pi - angle / 2.0)
            * self.geometry_settings.beam_thickness
            * 2,
        )

        # generate bottom beam outlines
        bottom_beam_outlines = Cassette.create_even_layer_beam_outlines(
            self.beam_corner_points["BottomUpper"], self.corner_count
        )

        # generate bottom beams
        bottom_beams = self.create_beams_from_outlines(bottom_beam_outlines, 2)

        # generate lowest outline from beam corners
        lowest_corners = []
        for beam in bottom_beams:
            lowest_corners.append(beam.corners["bottom"]["B"])
        lowest_corners = deque(lowest_corners)
        lowest_corners.rotate(1)
        lowest_outline = ClosedPolyline(rg.Polyline(lowest_corners))

        # generate tooths for all beams
        # TODO: Implement joint class that handles sawtooth generation instead
        # This class can calculate exact safety values for any given edge
        tooth_counts = self.add_sawtooths_to_beams(
            top_beams,
            self.top_outline,
            middle_outline,
            self.geometry_settings.sawtooth_depth,
            self.geometry_settings.sawtooth_width,
        )
        self.add_sawtooths_to_beams(
            middle_beams,
            middle_outline,
            bottom_outline,
            self.geometry_settings.sawtooth_depth,
            self.geometry_settings.sawtooth_width,
            tooth_counts,
            flip_direction=True,
        )
        self.add_sawtooths_to_beams(
            bottom_beams,
            bottom_outline,
            lowest_outline,
            self.geometry_settings.sawtooth_depth,
            self.geometry_settings.sawtooth_width,
            tooth_counts,
        )

        beams = []
        beams.extend(top_beams)
        beams.extend(middle_beams)
        beams.extend(bottom_beams)
        self.beams = beams

    def sort_neighbors(self):
        """
        Sorts the cassette neighbors by it's outline
        """

        raise NotImplementedError()

    def get_neighbor_angle(self, neighbour_index):
        # TODO: a real implementation
        return math.pi / 10.0

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
        Creates the inflection points around the polyline vertices,
        basically the points before and after each corner, e.g. 'A_left', 'A', 'A_right'

        Args:
            outline (ClosedPolyline): The outline used to generate the inflection points
            plane (Plane): The plane of the outline
            offset_amount (float): The amount by which the outline should be offset inwards

        Returns:
            dict[str : Point3d]: A dictionary of named inflection and corner points.
        """

        # initialize corner names and corners
        corners = {}
        point_count = outline.corner_count
        points = outline.corners

        # iterate over angles
        for i in range(point_count):

            # get current angle, corner name, corner and next corner
            corner_name = Cassette.CORNER_NAMES[i]
            prev_corner = points[(i - 1) % point_count]
            cur_corner = points[i]
            next_corner = points[(i + 1) % point_count]

            # calculate plane at corner oriented with it's x-axis towards the next corner
            x_axis = next_corner - cur_corner
            y_axis = prev_corner - cur_corner
            angle = rg.Vector3d.VectorAngle(x_axis, y_axis, plane.ZAxis)
            polar_plane = rg.Plane(
                # cur_corner, x_axis, rg.Vector3d.CrossProduct(x_axis, plane.ZAxis)
                cur_corner,
                x_axis,
                y_axis,
            )
            # polar_plane.Rotate(math.pi, polar_plane.ZAxis)

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
            beam_outline = ClosedPolyline(rg.Polyline([a, b, c, d]))
            outlines.append(beam_outline)

        return outlines

    @staticmethod
    def create_odd_layer_beam_outlines(inflection_points, corner_count):
        # get the corner names for the cassette
        corner_names = Cassette.CORNER_NAMES[:corner_count]
        outlines = []

        # iterate over corners
        for i in range(corner_count):

            # extract current and next corner name
            cur_corner_name = corner_names[i]
            next_corner_name = corner_names[(i + 1) % corner_count]

            # generate beam corners from known inflection point layout
            a = inflection_points[Cassette.__get_left_inflection(next_corner_name)]
            b = inflection_points[cur_corner_name]
            c = inflection_points[Cassette.__get_left_inflection(cur_corner_name)]
            d = inflection_points[Cassette.__get_inner_inflection(next_corner_name)]

            # create closed polyline from beam corners and add to outlines list
            beam_outline = ClosedPolyline(rg.Polyline([a, b, c, d]))
            outlines.append(beam_outline)

        return outlines

    @staticmethod
    def __get_level_name(level):
        if level == 0:
            return "T"
        elif level == 1:
            return "M"
        elif level == 2:
            return "B"
        else:
            logging.error(
                "Cassette.__get_level_name: Requested level {} out of range".format(
                    level
                )
            )
            return

    def create_beams_from_outlines(self, outlines, level):

        level_name = self.__get_level_name(level)
        beams = []
        for index, outline in enumerate(outlines):
            beam_ident = "{}_Beam_{}{}".format(
                self.identifier, level_name, self.CORNER_NAMES[index]
            )
            cur_angle = self.get_neighbor_angle(index)
            next_angle = self.get_neighbor_angle((index + 1) % len(self.neighbors))
            beam = Beam(
                beam_ident,
                self.plane,
                self.geometry_settings.beam_thickness,
                outline,
                [cur_angle, next_angle],
            )

            beams.append(beam)

        return beams

    @staticmethod
    def add_sawtooths_to_beams(
        beams,
        top_outline,
        bottom_outline,
        tooth_depth,
        tooth_width,
        tooth_counts=[],
        flip_direction=False,
    ):
        fixed_tooth_numbers = len(tooth_counts) > 2
        if not fixed_tooth_numbers:
            tooth_counts = [None for _ in range(len(beams))]
        for index, beam in enumerate(beams):
            tooth_count = beam.add_sawtooths_to_outlines(
                tooth_depth,
                tooth_width,
                top_outline.get_segment(index),
                bottom_outline.get_segment(index),
                tooth_counts[index],
                flip_direction,
            )
            beam.volume_geometry = beam.create_volume_geometry()

            if not fixed_tooth_numbers:
                continue
            tooth_counts[index] = tooth_count

        return tooth_counts

    def create_plate(self):
        raise NotImplementedError()

    def create_dowels(self):
        raise NotImplementedError()
