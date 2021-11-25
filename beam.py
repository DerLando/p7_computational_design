import logging
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
from algorithms import move_polyline_segment, polyline_to_point_dict
from geometry import ClosedPolyline
import math


class Beam:
    def __init__(self, ident, plane, thickness, top_outline, neighbor_angles):
        """
        Initializes a new instance of the beam class

        Args:
            ident (str): The identifier of the beam
            plane (Plane): The plane of the beam
            thickness (float): The material thickness of the beam
            top_outline (ClosedPolyline): The outline of the beam geometry, at it's top face. Needs to be closed and aligned in such a way, that the first segment of the outline is outwards facing.
            neighbor_angle (float): The angle of the beam plane to the beam neighbour plane.
        """

        # initialize fields from input
        self.identifier = ident
        self.plane = plane
        self.thickness = thickness
        self.top_outline = top_outline
        self.neighbor_angles = neighbor_angles

        # create corner dict and fill with top corners
        self.corners = {"top": self.top_outline.corner_dict}

        # create bottom outline
        self.bottom_outline = self.create_bottom_outline()

        # add bottom corners to corner dict
        self.corners["bottom"] = self.bottom_outline.corner_dict

        # create volume geometry from top and bottom outline
        self.volume_geometry = self.create_volume_geometry()

    def create_bottom_outline(self):

        # set bottom outline to top_outline
        bottom_outline = self.top_outline.duplicate_inner()

        for i in range(2):
            # calculate outline offset
            offset_amount = math.tan(self.neighbor_angles[i] / 2.0) * self.thickness

            # TODO: How do we define the outer segment?
            outer_segment_index = i
            bottom_outline = move_polyline_segment(
                bottom_outline, self.plane, outer_segment_index, offset_amount
            )

        # move to bottom position
        bottom_outline.Transform(
            rg.Transform.Translation(self.plane.ZAxis * -self.thickness)
        )

        return ClosedPolyline(bottom_outline)

    def add_sawtooths_to_outlines(
        self,
        depth,
        width,
        top_guide,
        bottom_guide,
        tooth_count=None,
        flip_direction=False,
    ):
        """
        Adds sawtooths to the top and bottom outlines, using guides.

        Args:
            depth (float): The depth of the sawtooths
            width (float): The width of the sawtooths
            top_guide (Line): The linear guide at the top
            bottom_guide (Line): The linear guide at the bottom
        """

        # TODO: Check guide direction parallel to first segment
        if (
            top_guide.Direction.IsParallelTo(self.top_outline.get_segment(0).Direction)
            != 1
        ):
            top_guide.Flip()
            bottom_guide.Flip()

        # safety hardcoded for now
        safety = 0.1

        def divide_guide(guide, safety, width, tooth_count=None):
            width /= 2
            length = guide.Length
            if not tooth_count:
                tooth_count = (
                    int(math.floor((length - 2 * safety) / (2 * width))) * 2 + 1
                )
            total_tooth_width = (tooth_count) * width
            start_length = (length - total_tooth_width) / 2
            end_length = length - start_length

            # print(length, tooth_count, total_tooth_width, start_length, end_length)

            helper_guide = rg.Line(
                guide.PointAtLength(start_length), guide.PointAtLength(end_length)
            )
            divisions = tooth_count * 2
            division_params = [float(i) / divisions for i in range(divisions + 1)]
            division_points = [helper_guide.PointAt(t) for t in division_params]

            return (division_points, tooth_count)

        top_divisions, tooth_count = divide_guide(top_guide, safety, width, tooth_count)
        bottom_divisions, _ = divide_guide(bottom_guide, safety, width, tooth_count)

        trans_dir = top_guide.Direction
        trans_dir.Unitize()
        trans_dir.Rotate(math.pi / 2.0, self.plane.ZAxis)

        inner_trans = rg.Transform.Translation(trans_dir * depth)
        outer_trans = rg.Transform.Translation(trans_dir * -depth)

        if flip_direction:
            (inner_trans, outer_trans) = (outer_trans, inner_trans)
        inner = True

        for i in range(0, len(top_divisions), 1):
            if i % 2 == 1:
                if inner:
                    trans = inner_trans
                    inner = False
                else:
                    trans = outer_trans
                    inner = True

                top_divisions[i].Transform(trans)
                bottom_divisions[i].Transform(trans)

        top_corners = self.top_outline.corner_dict
        bottom_corners = self.bottom_outline.corner_dict
        self.top_outline = self.top_outline.as_inserted_range(1, top_divisions)
        self.bottom_outline = self.bottom_outline.as_inserted_range(1, bottom_divisions)
        self.top_outline.corner_dict = top_corners
        self.bottom_outline.corner_dict = bottom_corners

        return tooth_count

    def create_volume_geometry(self):
        # loft between top and bottom
        results = rg.Brep.CreateFromLoft(
            [self.top_outline.as_curve(), self.bottom_outline.as_curve()],
            rg.Point3d.Unset,
            rg.Point3d.Unset,
            rg.LoftType.Straight,
            False,
        )

        # check if loft succeeded
        if results is None:
            logging.error("Beam.create_volume_geometry: Loft result is None!")
            return

        # test if we got a valid result, meaning only one brep in the returned buffer
        if results.Count != 1:
            logging.error("Beam.create_volume_geometry: Loft result is multiple breps!")
            return

        # cap result
        capped = results[0].CapPlanarHoles(sc.doc.ModelAbsoluteTolerance)
        if capped is None:
            logging.error("Beam.create_volume_geometry: Failed to cap loft!")
            return

        return capped
