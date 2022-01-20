import rhinoscriptsyntax as rs
import scriptcontext as sc
from components.panel import Panel
from helpers.beam_layer import CassetteBeamLayer
from helpers.settings import GeometrySettings
from helpers import keys
import logging
from bake import Baker
import components.repository as repo


def create_beams(panels):

    for panel in panels:
        layers = []
        layers.append(
            CassetteBeamLayer(
                panel.identifier,
                0,
                panel.outline,
                panel.plane.ZAxis,
                panel.neighbor_angles,
                panel.settings,
            )
        )
        layers.append(
            CassetteBeamLayer(
                panel.identifier,
                1,
                layers[0].outlines[keys.BOTTOM_OUTLINE_KEY],
                panel.plane.ZAxis,
                panel.neighbor_angles,
                panel.settings,
            )
        )
        layers.append(
            CassetteBeamLayer(
                panel.identifier,
                2,
                layers[1].outlines[keys.BOTTOM_OUTLINE_KEY],
                panel.plane.ZAxis,
                panel.neighbor_angles,
                panel.settings,
            )
        )

        beams = []

        for layer in layers:
            layer.create_and_set_geometry()
            for beam in layer.beams.values():
                repo.create_component(beam)
                beams.append(beam)

    return beams


if __name__ == "__main__":

    picked_ids = rs.GetObjects("Select Panels to generate beams for", filter=8)
    picked_objs = [sc.doc.Objects.FindId(id) for id in picked_ids]

    group_ids = set()
    for obj in picked_objs:
        groups = obj.Attributes.GetGroupList()
        for group in groups:
            group_ids.add(group)

    panels = [repo.read_component(group_index) for group_index in group_ids]

    create_beams(panels)
