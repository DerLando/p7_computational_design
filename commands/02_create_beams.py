import rhinoscriptsyntax as rs
import scriptcontext as sc
from components.panel import Panel
from helpers.beam_layer import CassetteBeamLayer
from helpers.settings import GeometrySettings
from helpers import keys
import logging
from bake import Baker
from components.repository import Repository

logging.basicConfig(
    filename="02_create_beams.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%d/%m/%Y %I:%M:%S",
)

picked_ids = rs.GetObjects("Select Panels to generate beams for", filter=8)
picked_objs = [sc.doc.Objects.FindId(id) for id in picked_ids]

group_ids = set()
for obj in picked_objs:
    groups = obj.Attributes.GetGroupList()
    for group in groups:
        group_ids.add(group)

panels = [Panel.deserialize(group_index) for group_index in group_ids]

settings = GeometrySettings(0.06, 0.02, 0.02, 0.005, 0.015, 0.04)
repo = Repository()

for panel in panels:
    layers = []
    layers.append(
        CassetteBeamLayer(
            panel.identifier,
            0,
            panel.outline,
            panel.plane.ZAxis,
            panel.neighbor_angles,
            settings,
        )
    )
    layers.append(
        CassetteBeamLayer(
            panel.identifier,
            1,
            layers[0].outlines[keys.BOTTOM_OUTLINE_KEY],
            panel.plane.ZAxis,
            panel.neighbor_angles,
            settings,
        )
    )
    layers.append(
        CassetteBeamLayer(
            panel.identifier,
            2,
            layers[1].outlines[keys.BOTTOM_OUTLINE_KEY],
            panel.plane.ZAxis,
            panel.neighbor_angles,
            settings,
        )
    )

    for layer in layers:
        layer.create_and_set_geometry()
        for beam in layer.beams.values():
            repo.update_component(beam)
