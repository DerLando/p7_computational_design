from components.dowel import Dowel
from components.screw import Screw
from components.skeleton_part import SkeletonPart
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
from System.Collections.Generic import List


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
    # get cassette from panel
    cassette_components = repo.get_cassette_from_panel(panel)

    # get cutout geos
    cutouts = List[rg.Brep]()
    for dowel in dowels[panel.identifier]:
        cutouts.Add(dowel.volume_geometry)
    for screw in screws[panel.identifier]:
        cutouts.Add(screw.volume_geometry)
    for insert in inserts[panel.identifier]:
        cutouts.Add(insert.volume_geometry)

    # iterate over cassette components and transform them
    for comp in cassette_components:
        if isinstance(comp, SkeletonPart):
            continue
        volume = List[rg.Brep]()
        volume.Add(comp.detailed_volume_geometry)
        result = rg.Brep.CreateBooleanDifference(volume, cutouts, 0.001)
        print(comp.identifier, result.Count)
        if result.Count == 0:
            continue
        if result.Count == 1:
            comp.detailed_volume_geometry = result[0]
            repo.update_component(comp)
        if result.Count == 2:
            comp.detailed_volume_geometry = result[0]
            repo.update_component(comp)
