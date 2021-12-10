import rhinoscriptsyntax as rs
import scriptcontext as sc
from components.panel import Panel
from helpers.beam_layer import CassetteBeamLayer
from helpers.settings import GeometrySettings
from helpers import keys
import logging
from bake import Baker

logging.basicConfig(
    filename="logs/XX_update_panels.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%d/%m/%Y %I:%M:%S",
)

picked_ids = rs.GetObjects("Select Panels to update", filter=8)
picked_objs = [sc.doc.Objects.FindId(id) for id in picked_ids]

group_ids = set()
for obj in picked_objs:
    groups = obj.Attributes.GetGroupList()
    for group in groups:
        group_ids.add(group)

panels = [Panel.deserialize(group_index) for group_index in group_ids]

settings = GeometrySettings(0.06, 0.02, 0.02, 0.005, 0.015, 0.04)

for panel in panels:
    panel.settings = settings
    panel.serialize()
