import logging
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
from algorithms import move_polyline_segment, polyline_to_point_dict
import math


class Beam:
    def __init__(self, ident, plane, thickness, top_outline, neighbor_angles):
        """
        Initializes a new instance of the beam class

        Args:
            ident (str): The identifier of the beam
            plane (Plane): The plane of the beam
            thickness (float): The material thickness of the beam
            top_outline (Polyline): The outline of the beam geometry, at it's top face. Needs to be closed and aligned in such a way, that the first segment of the outline is outwards facing.
            neighbor_angle (float): The angle of the beam plane to the beam neighbour plane.
        """

        # initialize fields from input
        self.identifier = ident
        self.plane = plane
        self.thickness = thickness
        self.top_outline = top_outline
        self.neighbor_angles = neighbor_angles

        # create corner dict and fill with top corners
        self.corners = {"top": polyline_to_point_dict(self.top_outline)}

        # create bottom outline
        self.bottom_outline = self.create_bottom_outline()

        # add bottom corners to corner dict
        self.corners["bottom"] = polyline_to_point_dict(self.bottom_outline)

        # create volume geometry from top and bottom outline
        self.volume_geometry = self.create_volume_geometry()

    def create_bottom_outline(self):

        # set bottom outline to top_outline
        bottom_outline = self.top_outline

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

        return bottom_outline

    def create_volume_geometry(self):
        # loft between top and bottom
        results = rg.Brep.CreateFromLoft(
            [self.top_outline.ToPolylineCurve(), self.bottom_outline.ToPolylineCurve()],
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
