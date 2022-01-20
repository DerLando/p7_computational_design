from components.joint import JointFactory
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


<<<<<<< HEAD
def panel_from_id(id):
    return Panel.deserialize(sc.doc.Objects.FindId(id).GetGroupList()[0])


PLATE_THICKNES = 0.025


picked_ids = rs.GetObjects("Select Panels to generate beams for", filter=8)
picked_objs = [sc.doc.Objects.FindId(id) for id in picked_ids]

group_ids = set()
for obj in picked_objs:
    groups = obj.Attributes.GetGroupList()
    for group in groups:
        group_ids.add(group)

panels = sorted(
    [repo.read_component(group_index) for group_index in group_ids],
    key=lambda x: x.panel_index,
)

neighbor_sets = set()
for panel in panels:
    for neighbor_id in panel.get_existing_neighbor_ids():
        neighbor_sets.add(frozenset([panel.panel_id, neighbor_id]))

for neighbor_set in neighbor_sets:
    panels = [panel_from_id(id) for id in neighbor_set]
    joint = JointFactory.create_joint(panels[0], panels[1])

    repo.create_component(joint)
=======
def create_joints(panels):
    neighbor_sets = set()
    for panel in panels:
        for neighbor_id in panel.get_existing_neighbor_ids():
            neighbor_sets.add(frozenset([panel.panel_id, neighbor_id]))

    joints = []

    for neighbor_set in neighbor_sets:
        panels = [repo.get_component_by_part_id(id) for id in neighbor_set]
        joint = JointFactory.create_joint(panels[0], panels[1])

        id = repo.create_component(joint)

        joints.append(id)

    return joints


if __name__ == "__main__":

    picked_ids = rs.GetObjects("Select Panels to generate beams for", filter=8)
    picked_objs = [sc.doc.Objects.FindId(id) for id in picked_ids]

    group_ids = set()
    for obj in picked_objs:
        groups = obj.Attributes.GetGroupList()
        for group in groups:
            group_ids.add(group)

    panels = sorted(
        [repo.read_component(group_index) for group_index in group_ids],
        key=lambda x: x.panel_index,
    )

    create_joints(panels)
>>>>>>> 9232948ef733a6cb85614d7e1deb78da31ca675d
