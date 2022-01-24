from helpers import algorithms, keys
from helpers.geometry import ClosedPolyline
import rhinoscriptsyntax as rs
import logging
import scriptcontext as sc
from components.beam import Beam
from components.plate import Plate
from components.panel import Panel
from components.skeleton_part import SkeletonFactory
import Rhino.Geometry as rg
import components.repository as repo

CUTOUT_DISTANCE = 100
SEGMENT_DIVISIONS = 2


def add_plate_cutout(panels):
    for panel in panels:

        # get plate
        plate = repo.get_component_by_identifier(
            keys.panel_plate_identifier(panel.identifier)
        )

        # get plate top outline
        outline = plate.outlines.get(keys.TOP_OUTLINE_KEY)
        if not outline:
            continue

        # offset outline inwards by distance
        offset = algorithms.offset_pline_wards(
            outline.duplicate_inner(), plate.plane, CUTOUT_DISTANCE, True
        )

        # empty container for control points
        ctrl_points = []

        # iterate over offset pline segments
        for i in range(offset.Count - 1):
            # add segment start point to ctrl points
            ctrl_points.append(offset[i])

            # divide segment by count and add those points, too
            segment = rg.LineCurve(offset.SegmentAt(i))
            additional_points = segment.DivideByCount(SEGMENT_DIVISIONS, False)
            additional_points = [segment.PointAt(t) for t in additional_points]
            ctrl_points.extend(additional_points)

        # create an inner outline from the control points
        # ctrl_points.append(ctrl_points[0])
        inner_outline = rg.NurbsCurve.Create(True, 3, ctrl_points)
        inner_outline.Reverse()

        # extrude inner outline downwards (in plane z)
        negative_volume = rg.Extrusion.Create(
            inner_outline, panel.settings.get("plate_thickness"), True
        )

        # boolean difference from detailed plate and negative volume
        result = rg.Brep.CreateBooleanDifference(
            plate.detailed_volume_geometry, negative_volume.ToBrep(), 0.001
        )
        if result.Count != 1:
            logging.error(
                "Failed to boolean new plate geometry for {}".format(panel.identifier)
            )
            continue

        plate.detailed_volume_geometry = result[0]

        repo.update_component(plate)


def main():

    picked_ids = rs.GetObjects("Select Panels to generate beams for", filter=8)
    picked_objs = [sc.doc.Objects.FindId(id) for id in picked_ids]

    group_ids = set()
    for obj in picked_objs:
        groups = obj.Attributes.GetGroupList()
        for group in groups:
            group_ids.add(group)

    panels = [repo.read_component(group_index) for group_index in group_ids]

    add_plate_cutout(panels)


if __name__ == "__main__":
    main()
