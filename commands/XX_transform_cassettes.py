from components.dowel import Dowel
from components.screw import Screw
from components.threaded_insert import ThreadedInsert
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


def group_by_parent(volume_comps):
    parent_dict = dict()
    for comp in volume_comps:
        if comp.parent_identifier in parent_dict:
            parent_dict[comp.parent_identifier].append(comp)
        else:
            parent_dict[comp.parent_identifier] = [comp]

    return parent_dict


picked_ids = rs.GetObjects("Select Panels to lay out in a grid", filter=8)
picked_objs = [sc.doc.Objects.FindId(id) for id in picked_ids]

group_ids = set()
for obj in picked_objs:
    groups = obj.Attributes.GetGroupList()
    for group in groups:
        group_ids.add(group)

panels = [repo.read_component(group_index) for group_index in group_ids]

# get all screws
dowels = repo.get_all_components(Dowel)
screws = repo.get_all_components(Screw)
inserts = repo.get_all_components(ThreadedInsert)

# group by parents
dowels = group_by_parent(dowels)
screws = group_by_parent(screws)
inserts = group_by_parent(inserts)

for panel in panels:
    # get the panel plane
    plane = panel.plane

    # create a transformation from panel plane to world xy
    xform = rg.Transform.PlaneToPlane(plane, rg.Plane.WorldXY)

    # TODO: Transform panel to world xy
    # get cassette from panel
    cassette_components = repo.get_cassette_from_panel(panel)

    # iterate over cassette components and transform them
    for comp in cassette_components:
        comp.transform(xform)
        repo.update_component(comp)

    # iterate over matching dowels and transform them
    for dowel in dowels[panel.identifier]:
        dowel.transform(xform)

    # iterate over matching screws and transform them
    for screw in screws[panel.identifier]:
        screw.transform(xform)

    # iterate over matching inserts and transform them
    for insert in inserts[panel.identifier]:
        insert.transform(xform)

    # transfrom panel itself
    panel.transform(xform)
    repo.update_component(panel)
