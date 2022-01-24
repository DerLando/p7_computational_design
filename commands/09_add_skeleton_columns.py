from math import ceil
from components.dowel import Dowel
from components.screw import ScrewFactory
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
from System import Guid

SKELETON_THICKNESS = 3


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

        # for each neighbor, we will create one column
        columns = []

        # get panel skeleton part
        skeleton = repo.get_component_by_identifier(
            keys.panel_skeleton_identifier(panel.identifier)
        )
        if not skeleton:
            continue

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

            # create dowel plane
            dowel_plane = panel.plane
            dowel_plane.Origin = origin

            # create column
            column = ThreadedInsert.calculate_hollow_cylinder_volume(
                dowel_plane, 5, 100
            )

            # for some reason, column is wierd...
            column.Flip()

            # split column with skeleton geo
            result = rg.Brep.CreateBooleanDifference(
                column, skeleton.skeleton_geo, 0.001, True
            )
            if result is None:
                logging.error(
                    "Failed to split column with skeleton for panel {}!".format(
                        panel.identifier
                    )
                )
                break

            if result.Count != 2:
                logging.error(
                    "Failed to split column with skeleton for panel {}! Expected 2 parts but got {}".format(
                        panel.identifier, result.Count
                    )
                )
                # for part in result:
                #     sc.doc.Objects.AddBrep(part)
                continue

            column = result[0]

            # measure actual column height
            bbox = column.GetBoundingBox(dowel_plane)
            height = bbox.Corner(False, False, False).Z
            height = ceil(height)

            # move plane upwards and create a screw inside the column
            dowel_plane.Transform(
                rg.Transform.Translation(
                    dowel_plane.ZAxis * (height + SKELETON_THICKNESS)
                )
            )
            dowel_plane.Flip()
            screw = ScrewFactory.create_m_screw(
                dowel_plane, "M10x{}".format(height + 20 - 1), panel.identifier
            )
            repo.create_component(screw)

            columns.append(column)

        # TODO: Maybe cut out a flat plane for screw to rest on?

        # boolean union columns to skeleton part
        columns.append(skeleton.skeleton_geo)
        result = rg.Brep.CreateBooleanUnion(columns, 0.001, True)

        if not result:
            logging.error(
                "Failed to union skeleton with columns for panel {}".format(
                    panel.identifier
                )
            )
            continue
        if not result.Count == 1:
            logging.error(
                "Failed to union skeleton with columns for panel {}".format(
                    panel.identifier
                )
            )
            for part in columns[:-1]:
                sc.doc.Objects.AddBrep(part)
            continue

        # update skeleton part geo
        skeleton.skeleton_geo = result[0]
        repo.update_component(skeleton)

        # TODO: Since we know the column height, here would be a good place
        # To create the screws, holding the skeleton part in place...


picked_ids = rs.GetObjects("Select Panels to lay out in a grid", filter=8)
picked_objs = [sc.doc.Objects.FindId(id) for id in picked_ids]

group_ids = set()
for obj in picked_objs:
    groups = obj.Attributes.GetGroupList()
    for group in groups:
        group_ids.add(group)

panels = [repo.read_component(group_index) for group_index in group_ids]

create_skeleton_dowels(panels)
