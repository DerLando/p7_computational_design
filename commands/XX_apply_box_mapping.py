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
import Rhino


def apply_box_mapping(component):
    bbox = component.detailed_volume_geometry.GetBoundingBox(component.plane)

    x = (bbox.Corner(True, True, True) - bbox.Corner(False, True, True)).Length
    y = (bbox.Corner(True, True, True) - bbox.Corner(True, False, True)).Length
    z = (bbox.Corner(True, True, True) - bbox.Corner(True, True, False)).Length

    x_interval = rg.Interval(-x / 2.0, x / 2.0)
    y_interval = rg.Interval(-y / 2.0, y / 2.0)
    z_interval = rg.Interval(0.0, -z)

    mapping = Rhino.Render.TextureMapping.CreateBoxMapping(
        component.plane, x_interval, y_interval, z_interval, True
    )

    rhobj = sc.doc.Objects.FindId(component.detailed_volume_id)
    rhobj.SetTextureMapping(1, mapping)
    rhobj.CommitChanges()


# get all screws
beams = repo.get_all_components(Beam)
plates = repo.get_all_components(Plate)

for beam in beams:
    apply_box_mapping(beam)

for plate in plates:
    apply_box_mapping(plate)
