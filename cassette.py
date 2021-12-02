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
    char_range,
)
from beam import Beam
from collections import deque
from geometry import ClosedPolyline
import keys

# TODO: Would have been smarter to abstract cassette levels into own class
# f.e. CassetteLayer, which generates itself from a top_outline and geometry settings.
# This way we could just reverse the top_outline for the middle layer and everything just works nicely
class CassetteBeamLayer(object):
    def __init__(
        self,
        parent_ident,
        level,
        top_outline,
        normal,
        neighbor_angles,
        geometry_settings,
    ):
        # set immediate fields
        self.parent_identifier = parent_ident
        self.level = level
        self.neighbor_angles = neighbor_angles
        self.geometry_settings = geometry_settings

        # calculate and set plane
        self.plane = rg.Plane(top_outline.center_point(), normal)

        # calculate and set outlines
        self.outlines = {
            keys.TOP_OUTLINE_KEY: top_outline,
            keys.BOTTOM_OUTLINE_KEY: self.create_lower_outline(
                top_outline,
                self.plane,
                self.neighbor_angles,
                self.geometry_settings.beam_thickness,
            ),
        }

        # calculate and set inflection points
        self.inflection_points = self.create_inflection_points(
            self.outlines[keys.TOP_OUTLINE_KEY],
            self.plane.ZAxis,
            self.level,
            self.neighbor_angles,
            self.geometry_settings,
        )

        # initialize empty geometry fields
        self.beams = {}

    @property
    def corner_count(self):
        return self.outlines[keys.TOP_OUTLINE_KEY].corner_count

    def create_and_set_geometry(self):
        beams = self.create_beams()
        self.beams = {c: beam for c, beam in zip(char_range(len(beams)), beams)}

    @staticmethod
    def create_lower_outline(top_outline, plane, angles, layer_thickness):
        # duplicate top outline and move it to bottom position
        top_duplicate = top_outline.duplicate_inner()
        top_duplicate.Transform(
            rg.Transform.Translation(plane.ZAxis * -1 * layer_thickness)
        )

        # offset segments by calculated recess
        calc_width = lambda angle, thickness: math.tan(math.pi - angle / 2) * thickness
        return ClosedPolyline(top_duplicate).as_moved_segments(
            plane, [calc_width(angle, layer_thickness) for angle in angles]
        )

    @staticmethod
    def create_inflection_points(outline, normal, level, angles, geometry_settings):
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
            corner_name = keys.corner_key_from_index(i)
            prev_corner = points[(i - 1) % point_count]
            cur_corner = points[i]
            next_corner = points[(i + 1) % point_count]

            # calculate plane at corner oriented with it's x-axis towards the next corner
            x_axis = next_corner - cur_corner
            y_axis = prev_corner - cur_corner
            angle = rg.Vector3d.VectorAngle(x_axis, y_axis, normal)
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
                geometry_settings.beam_max_width
                + math.tan(math.pi - angles[i] / 2.0)
                * geometry_settings.beam_thickness
                * level
            )

            c = offset_amount / math.sin(angle / 2.0)
            gamma = math.pi - angle
            a = c / (2 * math.sin(gamma / 2.0))

            # evaluate inflection points on polar plane and add to corners dict
            corners[keys.inflection_key(corner_name, 0)] = point_polar(
                polar_plane, a, angle
            )
            corners[corner_name] = cur_corner
            corners[keys.inflection_key(corner_name, 2)] = point_polar(
                polar_plane, a, 0
            )
            corners[keys.inflection_key(corner_name, 1)] = point_polar(
                polar_plane, c, angle / 2
            )

        return corners

    def create_beams(self):

        outlines = CassetteBeamLayer.create_beam_outlines(
            self.inflection_points, self.corner_count, self.level % 2 == 0
        )

        beams = []
        for index, char in enumerate(keys.edge_keys(self.corner_count)):
            outline = outlines[index]
            ident = "{}_B{}{}".format(self.parent_identifier, self.level, char)

            if self.level % 2 == 0:
                beam_angles = [
                    self.neighbor_angles[index],
                    self.neighbor_angles[(index + 1) % self.corner_count],
                    None,
                    None,
                ]
            else:
                beam_angles = [
                    self.neighbor_angles[index],
                    self.neighbor_angles[(index - 1) % self.corner_count],
                    None,
                    None,
                ]

            beam = Beam(
                ident,
                self.plane,
                self.geometry_settings.beam_thickness,
                outline,
                beam_angles,
            )

            beams.append(beam)

        return beams

    @staticmethod
    def create_beam_outlines(inflection_points, corner_count, even=True):

        # get the corner names for the cassette
        corner_names = keys.corner_keys(corner_count)
        outlines = []

        # iterate over corners
        for i in range(corner_count):

            # extract current and next corner name
            cur_corner_name = corner_names[i]
            next_corner_name = corner_names[(i + 1) % corner_count]

            if even:
                # generate beam corners from known inflection point layout
                a = inflection_points[keys.inflection_key(cur_corner_name, 2)]  # right
                b = inflection_points[next_corner_name]
                c = inflection_points[keys.inflection_key(next_corner_name, 2)]  # right
                d = inflection_points[keys.inflection_key(cur_corner_name, 1)]  # inner
            else:
                a = inflection_points[keys.inflection_key(next_corner_name, 0)]  # left
                b = inflection_points[cur_corner_name]
                c = inflection_points[keys.inflection_key(cur_corner_name, 0)]  # left
                d = inflection_points[keys.inflection_key(next_corner_name, 1)]  # inner

            # create closed polyline from beam corners and add to outlines list
            beam_outline = ClosedPolyline(rg.Polyline([a, b, c, d]))
            outlines.append(beam_outline)

        return outlines


class Cassette(object):
    def __init__(self, ident, face_index, plane, top_outline, geometry_settings):
        # store init arguments in public fields
        self.identifier = ident
        self.face_index = face_index
        self.plane = plane
        self.top_outline = ClosedPolyline(top_outline)
        self.geometry_settings = geometry_settings

        # create edges dict
        self.edges = {
            keys.edge_key_from_index(index): segment
            for index, segment in zip(
                range(self.top_outline.corner_count), self.top_outline.get_segments()
            )
        }

        # initialize empty buffers
        self.beam_corner_points = {}
        self.beams = {}

        # initialize neighbors buffer to all None
        self.__neighbors = {key: None for key in self.edges}

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
        return self.__neighbors.values()

    @property
    def existing_neighbors(self):
        return [neighbor for neighbor in self.__neighbors if neighbor]

    def create_geometry(self):
        # get angles to neighbors
        angles = [
            self.get_neighbor_angle(key) for key in keys.edge_keys(self.corner_count)
        ]

        layers = []
        layers.append(
            CassetteBeamLayer(
                self.identifier,
                0,
                self.top_outline,
                self.plane.ZAxis,
                angles,
                self.geometry_settings,
            )
        )
        layers.append(
            CassetteBeamLayer(
                self.identifier,
                1,
                layers[0].outlines[keys.BOTTOM_OUTLINE_KEY],
                self.plane.ZAxis,
                angles,
                self.geometry_settings,
            )
        )
        layers.append(
            CassetteBeamLayer(
                self.identifier,
                2,
                layers[1].outlines[keys.BOTTOM_OUTLINE_KEY],
                self.plane.ZAxis,
                angles,
                self.geometry_settings,
            )
        )

        for layer in layers:
            layer.create_and_set_geometry()

        self.layers = layers

        self.dowels = self.create_dowels(
            self.layers[-1].beams,
            self.plane.ZAxis,
            self.geometry_settings.dowel_radius,
            self.geometry_settings.beam_thickness * 3,
        )

    # def __old_create_geometry(self):
    #     """
    #     Wrapper function to handle all steps of geometry generation, in correct order.
    #     """

    #     # get angles to neighbors
    #     angles = [self.get_neighbor_angle(index) for index in range(self.corner_count)]

    #     # generate cassette outlines per level
    #     middle_outline = self.get_beams_boundary(1)
    #     bottom_outline = self.get_beams_boundary(2)
    #     lowest_outline = self.get_beams_boundary(3)

    #     # create the upper inflection points for the first beam layer
    #     self.beam_corner_points["TopUpper"] = self.create_inflection_points(angles, 0)

    #     # generate a layer of beam outlines
    #     top_beam_outlines = self.create_even_layer_beam_outlines(
    #         self.beam_corner_points["TopUpper"], self.corner_count
    #     )

    #     # generate top beams
    #     top_beams = self.create_beams_from_outlines(top_beam_outlines, level=0)

    #     self.beam_corner_points["MiddleUpper"] = self.create_inflection_points(
    #         angles, 1
    #     )

    #     middle_beam_outlines = Cassette.create_odd_layer_beam_outlines(
    #         self.beam_corner_points["MiddleUpper"], self.corner_count
    #     )

    #     middle_beams = self.create_beams_from_outlines(middle_beam_outlines, 1)

    #     # generate bottom inflection points
    #     self.beam_corner_points["BottomUpper"] = self.create_inflection_points(
    #         angles, 2
    #     )

    #     # generate bottom beam outlines
    #     bottom_beam_outlines = Cassette.create_even_layer_beam_outlines(
    #         self.beam_corner_points["BottomUpper"], self.corner_count
    #     )

    #     # generate bottom beams
    #     bottom_beams = self.create_beams_from_outlines(bottom_beam_outlines, 2)

    #     # generate tooths for all beams
    #     # TODO: Implement joint class that handles sawtooth generation instead
    #     # This class can calculate exact safety values for any given edge
    #     tooth_counts = self.add_sawtooths_to_beams(
    #         top_beams,
    #         self.top_outline,
    #         middle_outline,
    #         self.geometry_settings.sawtooth_depth,
    #         self.geometry_settings.sawtooth_width,
    #     )
    #     self.add_sawtooths_to_beams(
    #         middle_beams,
    #         middle_outline,
    #         bottom_outline,
    #         self.geometry_settings.sawtooth_depth,
    #         self.geometry_settings.sawtooth_width,
    #         tooth_counts,
    #         flip_direction=True,
    #     )
    #     self.add_sawtooths_to_beams(
    #         bottom_beams,
    #         bottom_outline,
    #         lowest_outline,
    #         self.geometry_settings.sawtooth_depth,
    #         self.geometry_settings.sawtooth_width,
    #         tooth_counts,
    #     )

    #     self.beams = {}
    #     self.beams["bottom"] = bottom_beams
    #     self.beams["middle"] = middle_beams
    #     self.beams["top"] = top_beams

    #     beams = []
    #     beams.extend(top_beams)
    #     beams.extend(middle_beams)
    #     beams.extend(bottom_beams)
    #     self.all_beams = beams

    #     self.dowels = self.__create_dowels()

    def add_neighbor(self, neighbor):
        """
        Adds a neighbor at the correct index in the neighbor buffer.
        Basically alinged at the same index, the connecting edge has

        Args:
            neighbor (Cassette): The neighbor to add

        Returns:
            str: The edge key the neighbor connects to this cassette at
        """

        # find the connecting edge
        neighbor_key = None
        for key, edge in self.top_outline.get_edges():
            for neighbor_segment in neighbor.top_outline.get_segments():
                if not are_lines_equal(edge, neighbor_segment):
                    continue
                neighbor_key = key

        if neighbor_key is None:
            logging.error(
                "Cassette.add_neighbor: Tried to add neighbor {} to cassette {}, but they do not share an edge!".format(
                    neighbor.identifier, self.identifier
                )
            )
            return None

        if self.__neighbors.get(neighbor_key) is not None:
            logging.warn(
                "Cassette.add_neighbor: found key {} which was already occupied!".format(
                    neighbor_key
                )
            )
        self.__neighbors[neighbor_key] = neighbor

        return neighbor_key

    def get_neighbor_angle(self, edge_key):
        """
        Gets the angle between this cassette and the neighbor at the given index

        Args:
            neighbor_index (int): The index of the neighbor inside of the cassette list
        """

        # TODO: Instead of indices, use edge keys

        neighbour = self.__neighbors.get(edge_key)
        if neighbour is None:
            return 0.0

        return rg.Vector3d.VectorAngle(
            self.plane.Normal,
            neighbour.plane.Normal,
            self.top_outline.get_edge(edge_key).Direction,
        )

    # @staticmethod
    # def add_sawtooths_to_beams(
    #     beams,
    #     top_outline,
    #     bottom_outline,
    #     tooth_depth,
    #     tooth_width,
    #     tooth_counts=[],
    #     flip_direction=False,
    # ):
    #     # TODO: Documentation
    #     fixed_tooth_numbers = len(tooth_counts) > 2
    #     if not fixed_tooth_numbers:
    #         tooth_counts = [None for _ in range(len(beams))]
    #     for index, beam in enumerate(beams):
    #         tooth_count = beam.add_sawtooths_to_outlines(
    #             tooth_depth,
    #             tooth_width,
    #             top_outline.get_segment(index),
    #             bottom_outline.get_segment(index),
    #             tooth_counts[index],
    #             flip_direction,
    #         )
    #         beam.volume_geometry = beam.create_volume_geometry()

    #         if not fixed_tooth_numbers:
    #             continue
    #         tooth_counts[index] = tooth_count

    #     return tooth_counts

    @staticmethod
    def create_dowels(beams, normal, radius, height):
        """
        Create dowels for the given beams dictionary

        Args:
            beams (dict): A dictionary of beams, with their corresponding edge name as keys
            normal (Vector3d): The normal direction of the dowels to create
        """
        # empty buffer for dowel planes
        dowel_planes = []

        # lambda to retrieve corner from beam by keys
        get_corner = (
            lambda edge_key, corner_key: beams[edge_key]
            .outlines[keys.BOTTOM_OUTLINE_KEY]
            .corner_dict[corner_key]
        )

        # iterate over beams keys
        for key in beams:

            # get the key of the next beam
            next_key = keys.offset_edge_key(key, 1, len(beams))

            # create a helper line spanning from 'B' to 'D' on the next beam
            helper = rg.Line(
                get_corner(key, keys.corner_key_from_index(1)),
                get_corner(next_key, keys.corner_key_from_index(3)),
            )

            # create a plane for the dowel centered at the mid-point of the helper line, in normal direction
            dowel_planes.append(rg.Plane(helper.PointAt(0.5), normal))

        return [Dowel(plane, radius, height) for plane in dowel_planes]

    def __mark_dowel_centers_on_beams(self):
        """
        Marks the center point of the dowels on all beams,
        this is needed for cnc drilling of holes, a point and a radius
        """
        raise NotImplementedError()

    def __create_plate(self):
        raise NotImplementedError()
