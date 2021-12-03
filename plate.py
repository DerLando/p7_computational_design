import Rhino
import Rhino.Geometry as rg
from geometry import ClosedPolyline
import scriptcontext as sc
import math
import keys
import logging


class Plate(object):
    def __init__(self, ident, plane, top_outline, angles, thickness):
        self.identifier = ident
        self.plane = plane

        self.outlines = {
            keys.TOP_OUTLINE_KEY: top_outline,
            keys.BOTTOM_OUTLINE_KEY: self.create_bottom_outline(
                plane, top_outline, thickness, angles
            ),
        }

        self.volume_geometry = self.create_volume_geometry(
            self.outlines[keys.TOP_OUTLINE_KEY], self.outlines[keys.BOTTOM_OUTLINE_KEY]
        )

    @staticmethod
    def create_bottom_outline(plane, top_outline, thickness, angles):
        get_offset = lambda angle, t: math.tan(math.pi - angle / 2.0) * t
        # for key, _ in top_outline.get_edges():
        #     top_outline = top_outline.as_moved_edge(
        #         plane, key, get_offset(angles[key], thickness)
        #     )

        # inner = top_outline.duplicate_inner()

        offset_amounts = {key: get_offset(angles[key], thickness) for key in angles}
        inner = top_outline.as_moved_edges(plane, offset_amounts).duplicate_inner()
        inner.Transform(rg.Transform.Translation(plane.ZAxis * -thickness))
        return ClosedPolyline(inner)

    @staticmethod
    def create_volume_geometry(top_outline, bottom_outline):
        # loft between top and bottom
        results = rg.Brep.CreateFromLoft(
            [top_outline.as_curve(), bottom_outline.as_curve()],
            rg.Point3d.Unset,
            rg.Point3d.Unset,
            rg.LoftType.Straight,
            False,
        )

        # check if loft succeeded
        if results is None:
            logging.error("Plate.create_volume_geometry: Loft result is None!")
            return

        # test if we got a valid result, meaning only one brep in the returned buffer
        if results.Count != 1:
            logging.error(
                "Plate.create_volume_geometry: Loft result is multiple breps!"
            )
            return

        # cap result
        capped = results[0].CapPlanarHoles(sc.doc.ModelAbsoluteTolerance)
        if capped is None:
            logging.error("Plate.create_volume_geometry: Failed to cap loft!")
            return

        return capped
