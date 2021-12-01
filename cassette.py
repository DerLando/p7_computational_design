import logging
import Rhino
import Rhino.Geometry as rg
from dowel import Dowel
import scriptcontext as sc
import math
from algorithms import (
    polyline_to_point_dict,
    polyline_angles,
    point_polar,
    are_lines_equal,
)
from beam import Beam
from collections import deque
from geometry import ClosedPolyline

# TODO: Would have been smarter to abstract cassette levels into own class
# f.e. CassetteLayer, which generates itself from a top_outline and geometry settings.
# This way we could just reverse the top_outline for the middle layer and everything just works nicely
class CassetteBeamLayer(object):
    def __init__(self, top_outline, normal, neighbor_angles, geometry_settings):
        self.top_outline = top_outline
        self.normal = (normal,)
        self.neighbor_angles = (neighbor_angles,)
        self.geometry_settings = geometry_settings


class Cassette(object):
    CORNER_NAMES = ["A", "B", "C", "D", "E", "F", "G", "H"]

    def __init__(self, ident, face_index, plane, top_outline, geometry_settings):
        # store init arguments in public fields
        self.identifier = ident
        self.face_index = face_index
        self.plane = plane
        self.top_outline = ClosedPolyline(top_outline)
        self.geometry_settings = geometry_settings

        # initialize empty buffers
        self.beam_corner_points = {}
        self.beams = {}

        # TODO: FIXME
        self.__neighbors = [None for _ in range(self.top_outline.corner_count)]

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

    @property
    def neighbors(self):
        return self.__neighbors

    @property
    def existing_neighbors(self):
        return [neighbor for neighbor in self.__neighbors if neighbor]

    def create_geometry(self):
        """
        Wrapper function to handle all steps of geometry generation, in correct order.
        """

        # get angles to neighbors
        angles = [self.get_neighbor_angle(index) for index in range(self.corner_count)]

        # generate cassette outlines per level
        middle_outline = self.get_beams_boundary(1)
        bottom_outline = self.get_beams_boundary(2)
        lowest_outline = self.get_beams_boundary(3)

        # create the upper inflection points for the first beam layer
        self.beam_corner_points["TopUpper"] = self.create_inflection_points(angles, 0)

        # generate a layer of beam outlines
        top_beam_outlines = self.create_even_layer_beam_outlines(
            self.beam_corner_points["TopUpper"], self.corner_count
        )

        # generate top beams
        top_beams = self.create_beams_from_outlines(top_beam_outlines, level=0)

        self.beam_corner_points["MiddleUpper"] = self.create_inflection_points(
            angles, 1
        )

        middle_beam_outlines = Cassette.create_odd_layer_beam_outlines(
            self.beam_corner_points["MiddleUpper"], self.corner_count
        )

        middle_beams = self.create_beams_from_outlines(middle_beam_outlines, 1)

        # generate bottom inflection points
        self.beam_corner_points["BottomUpper"] = self.create_inflection_points(
            angles, 2
        )

        # generate bottom beam outlines
        bottom_beam_outlines = Cassette.create_even_layer_beam_outlines(
            self.beam_corner_points["BottomUpper"], self.corner_count
        )

        # generate bottom beams
        bottom_beams = self.create_beams_from_outlines(bottom_beam_outlines, 2)

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

        self.beams = {}
        self.beams["bottom"] = bottom_beams
        self.beams["middle"] = middle_beams
        self.beams["top"] = top_beams

        beams = []
        beams.extend(top_beams)
        beams.extend(middle_beams)
        beams.extend(bottom_beams)
        self.all_beams = beams

        self.dowels = self.create_dowels()

    def add_neighbor(self, neighbor):
        """
        Adds a neighbor at the correct index in the neighbor buffer.
        Basically alinged at the same index, the connecting edge has

        Args:
            neighbor (Cassette): The neighbor to add

        Returns:
            int: The index of the neighbor inside the cassette
        """

        # find the connecting edge
        neighbor_index = -1
        for edge_index, edge in enumerate(self.top_outline.get_segments()):
            for neighbor_edge in neighbor.top_outline.get_segments():
                if not are_lines_equal(edge, neighbor_edge):
                    continue

                neighbor_index = edge_index

        if neighbor_index == -1:
            logging.error(
                "Cassette.add_neighbor: Tried to add neighbor {} to cassette {}, but they do not share an edge!".format(
                    neighbor.identifier, self.identifier
                )
            )
            return -1

        self.__neighbors[neighbor_index] = neighbor

        return neighbor_index

    def get_neighbor_angle(self, neighbour_index):
        # TODO: a real implementation

        neighbour = self.neighbors[neighbour_index]
        if neighbour is None:
            return 0.0

        return rg.Vector3d.VectorAngle(
            self.plane.Normal,
            neighbour.plane.Normal,
            self.top_outline.get_segment(neighbour_index).Direction,
        )

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

    def get_beams_boundary(self, level):
        """
        Gets the boundary curve enclosing the beams top faces at the given level

        Args:
            level (int): An int representing the level, 0 is top, 2 is bottom
        """

        if level == 0:
            return self.top_outline

        if level < 0:
            return

        get_width = lambda t, angle: math.tan(math.pi - angle / 2.0) * t
        angles = [
            self.get_neighbor_angle(index) for index in range(len(self.neighbors))
        ]
        top_duplicate = self.top_outline.duplicate_inner()
        top_duplicate.Transform(
            rg.Transform.Translation(
                self.plane.ZAxis * self.geometry_settings.beam_thickness * level * -1
            )
        )
        return ClosedPolyline(top_duplicate).as_moved_segments(
            self.plane,
            [
                get_width(self.geometry_settings.beam_thickness * level, angle)
                for angle in angles
            ],
        )

    def get_plane_at_level(self, level):
        plane = rg.Plane(self.plane)
        origin = rg.Point3d(plane.Origin)
        origin.Transform(
            rg.Transform.Translation(
                self.plane.ZAxis * -1 * self.geometry_settings.beam_thickness * level
            )
        )
        plane.Origin = origin

        return plane

    def create_inflection_points(self, angles, level):
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
        point_count = self.corner_count
        outline = self.get_beams_boundary(level)
        points = outline.corners
        plane = self.get_plane_at_level(level)

        # iterate over angles
        for i in range(point_count):

            # get current angle, corner name, corner and next corner
            corner_name = self.CORNER_NAMES[i]
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
            offset_amount = (
                self.geometry_settings.beam_max_width
                + math.tan(math.pi - angles[i] / 2.0)
                * self.geometry_settings.beam_thickness,
            )[0]

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

        # TODO: Documentation
        level_name = self.__get_level_name(level)
        beams = []
        for index, outline in enumerate(outlines):
            beam_ident = "{}_Beam_{}{}".format(
                self.identifier, level_name, self.CORNER_NAMES[index]
            )
            cur_angle = self.get_neighbor_angle(index)
            next_angle = self.get_neighbor_angle(
                (index + 1) % len(self.existing_neighbors)
            )
            beam = Beam(
                beam_ident,
                self.get_plane_at_level(level),
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
        # TODO: Documentation
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

    def create_dowels(self):
        # TODO: Documentation
        dowel_planes = []
        beams = self.beams["bottom"]
        for index, cur_beam in enumerate(beams):
            next_beam = beams[(index + 1) % (self.corner_count)]
            plane = rg.Plane(self.plane)
            helper = rg.Line(
                cur_beam.corners["bottom"]["B"], next_beam.corners["bottom"]["D"]
            )
            plane.Origin = helper.PointAt(0.5)
            dowel_planes.append(plane)

        return [
            Dowel(
                plane,
                self.geometry_settings.dowel_radius,
                self.geometry_settings.beam_thickness * 3,
            )
            for plane in dowel_planes
        ]

    def mark_dowel_centers_on_beams(self):
        """
        Marks the center point of the dowels on all beams,
        this is needed for cnc drilling of holes, a point and a radius
        """
        raise NotImplementedError()

    def create_plate(self):
        raise NotImplementedError()
