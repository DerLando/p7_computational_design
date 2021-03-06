from helpers import algorithms, keys
from helpers.geometry import ClosedPolyline
import rhinoscriptsyntax as rs
import logging
import scriptcontext as sc
from components.beam import Beam
from components.plate import Plate
from components.panel import Panel
from components.dowel import Dowel
import Rhino.Geometry as rg
import components.repository as repo


def create_dowels(panels):

    dowels = []
    dowel_radius = panels[0].settings.get("dowel_radius")
    dowel_height = (
        panels[0].settings["beam_thickness"] * 3
        + panels[0].settings["plate_thickness"] / 2
    )
    dowel_z_shift = panels[0].settings["plate_thickness"] / 2

    for panel in panels:
        corner_count = panel.outline.corner_count
        edge_keys = keys.edge_keys(corner_count)
        beam_idents = [
            keys.panel_beam_identifier(panel.identifier, 2, key) for key in edge_keys
        ]
        lowest_beams = [
            repo.get_component_by_identifier(ident) for ident in beam_idents
        ]

        for i in range(len(lowest_beams)):
            next_i = (i + 1) % corner_count
            helper = rg.Line(
                lowest_beams[i]
                .outlines[keys.BOTTOM_OUTLINE_KEY]
                .corner_dict.get(keys.corner_key_from_index(1)),
                lowest_beams[next_i]
                .outlines[keys.BOTTOM_OUTLINE_KEY]
                .corner_dict.get(keys.corner_key_from_index(3)),
            )

            origin = helper.PointAt(0.5)
            origin.Transform(
                rg.Transform.Translation(panel.plane.ZAxis * -dowel_z_shift)
            )
            plane = rg.Plane(origin, panel.plane.ZAxis)

            # create dowel
            dowel = Dowel(plane, dowel_radius, dowel_height, panel.identifier)

            repo.create_component(dowel)
            dowels.append(dowel)

    return dowels


if __name__ == "__main__":

    picked_ids = rs.GetObjects("Select Panels to generate beams for", filter=8)
    picked_objs = [sc.doc.Objects.FindId(id) for id in picked_ids]

    group_ids = set()
    for obj in picked_objs:
        groups = obj.Attributes.GetGroupList()
        for group in groups:
            group_ids.add(group)

    panels = [repo.read_component(group_index) for group_index in group_ids]

    create_dowels(panels)
