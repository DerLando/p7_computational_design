import Rhino.Geometry as rg
import math
from algorithms import (
    point_polar,
    char_range,
)
from components.beam import Beam
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
    def create_lower_outline(top_outline, plane, angles, thickness):
        get_offset = lambda angle, t: math.tan(math.pi - angle / 2.0) * t
        offset_amounts = {key: get_offset(angles[key], thickness) for key in angles}
        inner = top_outline.as_moved_edges(plane, offset_amounts).duplicate_inner()
        inner.Transform(rg.Transform.Translation(plane.ZAxis * -thickness))
        return ClosedPolyline(inner)

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

        # TODO: Re-write to work with angle dict

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
                + math.tan(math.pi - angles[keys.edge_key_from_index(i)] / 2.0)
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
        """
        Create the beams for the layer

        Returns:
            list[Beam]: The generated beams
        """

        # Create the beam outlines from inflection points
        outlines = CassetteBeamLayer.create_beam_outlines(
            self.inflection_points, self.corner_count, self.level % 2 == 0
        )

        # create an empty buffer for the beams
        beams = []

        # iterate over edge keys together with their indices
        for index, char in enumerate(keys.edge_keys(self.corner_count)):

            prev_key = keys.offset_edge_key(char, -1, self.corner_count)
            next_key = keys.offset_edge_key(char, 1, self.corner_count)

            # grab the fitting outline
            outline = outlines[index]

            # create an identifier for the beam
            ident = "{}_B{}{}".format(self.parent_identifier, self.level, char)

            #
            if self.level % 2 == 0:
                beam_angles = {
                    "a": self.neighbor_angles[char],
                    "b": self.neighbor_angles[next_key],
                    "c": 0.0,
                    "d": 0.0,
                }
            else:
                beam_angles = {
                    "a": self.neighbor_angles[char],
                    "b": 0.0,
                    "c": 0.0,
                    "d": self.neighbor_angles[prev_key],
                }

            plane = rg.Plane(
                outline.center_point(),
                outline.get_edge("a").Direction,
                -outline.get_edge("d").Direction,
            )
            beam = Beam(
                ident,
                plane,
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
                a = inflection_points[cur_corner_name]
                b = inflection_points[keys.inflection_key(next_corner_name, 0)]  # left
                c = inflection_points[keys.inflection_key(next_corner_name, 1)]  # inner
                d = inflection_points[keys.inflection_key(cur_corner_name, 0)]  # left

            # create closed polyline from beam corners and add to outlines list
            beam_outline = ClosedPolyline(rg.Polyline([a, b, c, d]))
            outlines.append(beam_outline)

        return outlines
