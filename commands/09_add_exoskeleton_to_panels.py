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


def assign_exoskeleton_to_panels(exoskeleton, panels):
    for panel in panels:
        skeleton_part = SkeletonFactory.create_skeletonpart(exoskeleton, panel)
        if not skeleton_part:
            logging.error(
                "Failed to assign exoskeleton to panel {}".format(panel.identifier)
            )
            continue

        repo.create_component(skeleton_part)
        print("Added skeleton to panel {}".format(panel.identifier))


def main():

    picked_ids = rs.GetObjects("Select Panels to generate beams for", filter=8)
    picked_objs = [sc.doc.Objects.FindId(id) for id in picked_ids]

    group_ids = set()
    for obj in picked_objs:
        groups = obj.Attributes.GetGroupList()
        for group in groups:
            group_ids.add(group)

    panels = [repo.read_component(group_index) for group_index in group_ids]

    exo_id = rs.GetObject("Select exoskeleton", filter=16)
    if exo_id is None:
        return
    exoskeleton = rs.coercebrep(exo_id)

    assign_exoskeleton_to_panels(exoskeleton, panels)


if __name__ == "__main__":
    main()
