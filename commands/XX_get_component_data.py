from helpers import algorithms, keys
from helpers.geometry import ClosedPolyline
import rhinoscriptsyntax as rs
import logging
import scriptcontext as sc
from components.beam import Beam
from components.plate import Plate
from components.panel import Panel
import Rhino.Geometry as rg
import components.repository as repo


picked_ids = rs.GetObjects("Select Panels to generate beams for")
picked_objs = [sc.doc.Objects.FindId(id) for id in picked_ids]

group_ids = set()
for obj in picked_objs:
    groups = obj.Attributes.GetGroupList()
    for group in groups:
        group_ids.add(group)

for id in group_ids:
    component = repo.read_component(id)
    # retrieve arch_dict from volume_id
    arch_dict = sc.doc.Objects.FindId(component.volume_id).Attributes.UserDictionary

    for key in arch_dict.Keys:
        print(key, arch_dict.Item[key])
