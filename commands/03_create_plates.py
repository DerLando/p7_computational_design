from helpers import algorithms, keys
from helpers.geometry import ClosedPolyline
import rhinoscriptsyntax as rs
import logging
import scriptcontext as sc
from components.beam import Beam
from components.plate import Plate
from components.panel import Panel
import Rhino.Geometry as rg
from components.repository import Repository

PLATE_THICKNES = 0.025

logging.basicConfig(
    filename="03_create_plates.log",
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

repo = Repository()

for panel in panels:
    identifier = "{}_P".format(panel.identifier)
    outline = ClosedPolyline(
        algorithms.draft_angle_offset(
            panel.outline,
            panel.plane,
            panel.neighbor_angles,
            panel.settings["beam_thickness"] * 3,
        )
    )
    plane = rg.Plane(panel.plane)
    plane.Origin = outline.center_point()
    plate = Plate(identifier, plane, outline, panel.neighbor_angles, PLATE_THICKNES)

    repo.update_component(plate)
