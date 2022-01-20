from components.dowel import Dowel
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
from System import Guid


def create_skeleton_dowels(panels):
    for panel in panels:

        # get the panel neighbors
        neighbor_ids = panel.neighbor_ids
        neighbors = dict()
        for key, value in neighbor_ids.items():
            if value == Guid.Empty:
                neighbors[key] = None
            else:
                neighbors[key] = repo.get_component_by_part_id(value)

        # iterate over neighbor-edge pairs
        for edge_key, neighbor in neighbors.items():

            if neighbor is None:
                continue

            # draw a helper line between panel center and neighbor center
            helper = rg.Line(panel.plane.Origin, neighbor.plane.Origin)

            # intersect the line with the neighbor edge
            edge = panel.outline.get_edge(edge_key)

            helper_crv = rg.LineCurve(helper)
            edge_crv = rg.LineCurve(edge)

            success, pt_helper, pt_edge = helper_crv.ClosestPoints(edge_crv)

            if not success:
                logging.error(
                    "Failed to intersect edge bisector with edge for panel {}".format(
                        panel.identifier
                    )
                )
                break

            # compute location of dowel plane for current neighbor
            vptx = pt_edge - panel.plane.Origin
            dist = vptx.Length
            vptx.Unitize()
            origin = panel.plane.Origin
            origin.Transform(
                rg.Transform.Translation(
                    vptx * (dist - panel.settings.get("beam_max_width") / 2.0)
                )
            )

            # move dowel plane downwards, so it is properly embedded in plate
            z_shift = (
                panel.settings.get("beam_thickness") * 3
                + panel.settings.get("plate_thickness") / 2.0
            )
            origin.Transform(rg.Transform.Translation(panel.plane.ZAxis * -z_shift))

            # create dowel plane
            dowel_plane = panel.plane
            dowel_plane.Origin = origin

            # create dowel on plane
            dowel = Dowel(dowel_plane, panel.settings.get("dowel_radius"), z_shift + 10)

            # bake dowel into repo
            repo.create_component(dowel)


picked_ids = rs.GetObjects("Select Panels to lay out in a grid", filter=8)
picked_objs = [sc.doc.Objects.FindId(id) for id in picked_ids]

group_ids = set()
for obj in picked_objs:
    groups = obj.Attributes.GetGroupList()
    for group in groups:
        group_ids.add(group)

panels = [repo.read_component(group_index) for group_index in group_ids]

create_skeleton_dowels(panels)
