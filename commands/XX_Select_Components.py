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


def main():
    result = rs.GetString("Input search pattern", defaultString="P_?_B??")
    if not result:
        return

    component_ids = repo.search_components(result)

    for id in component_ids:
        repo.select_component(id)

    sc.doc.Views.Redraw()


if __name__ == "__main__":
    main()
