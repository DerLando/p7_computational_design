import logging
import Rhino
import Rhino.Geometry as rg
from geometry import ClosedPolyline
import scriptcontext as sc
import rhinoscriptsyntax as rs
from panel import Panel


class PanelTopology(object):
    """
    A topology helper class extracted from a Rhino.Geometry.Mesh instance,
    that allows for convenient neigbor queries, as well as generalizes
    over panels and ngons present in the base mesh.
    """

    PANEL_INDEX_KEY = "Panel_Index"
    PANEL_NEIGHBOR_INDICES_KEY = "neighbors"

    def __init__(self, panel_ids):
        self.panel_ids = panel_ids

        # TODO: Extract topology
        self.__neighbor_dict = {}

        panels = []
        for panel_id in panel_ids:
            panel_index = self.__get_panel_index(panel_id)
            plane = self.__get_panel_plane(panel_id)
            outline = ClosedPolyline(self.__get_panel_outline(panel_id))
            panels.append(
                Panel("P_{}".format(panel_index), plane, panel_id, panel_index, outline)
            )

            self.__neighbor_dict[panels[-1].panel_index] = set(
                self.__get_panel_neighbor_indices(panel_id)
            )

        panels.sort(key=lambda x: x.panel_index)

        self.__panels = panels

    @staticmethod
    def __get_panel_index(panel_id):
        return int(rs.GetUserText(panel_id, PanelTopology.PANEL_INDEX_KEY))

    @staticmethod
    def __get_panel_plane(panel_id):
        brep = rs.coercebrep(panel_id)
        panel = brep.Faces[0]
        success, plane = panel.FrameAt(panel.Domain(0).Mid, panel.Domain(1).Mid)
        if not success:
            logging.error("PanelTopology.__get_panel_plane: Failed to get panel plane")
            return
        return plane

    @staticmethod
    def __get_panel_outline(panel_id):
        brep = rs.coercebrep(panel_id)
        edges = brep.DuplicateNakedEdgeCurves(True, False)
        joined = rg.Curve.JoinCurves(edges, 0.01)
        if joined.Count != 1:
            logging.error("PanelTopology.__get_panel_outline: Failed to join outlines!")
            return

        return joined[0].ToPolyline()

    @staticmethod
    def __get_panel_neighbor_indices(panel_id):
        neighbor_keys = [key for key in rs.GetUserText(panel_id) if key[0:4] == "Edge"]

        return [
            int(value)
            for value in [rs.GetUserText(panel_id, key) for key in neighbor_keys]
        ]

    def panel(self, index):
        """
        Get the panel at the given index from the internal panel buffer

        Args:
            index (int): The index of the panel

        Returns:
            Panel: The panel
        """
        return self.__panels[index]

    def panels(self):
        """
        Return all panels in the internal panel buffer

        Returns:
            List[Panel]: The panels
        """
        return self.__panels[::]

    def panel_neighbors(self, index):
        """
        Get the panels that share an edge with the given panel

        Args:
            panel (Panel): The panel to get the neighbors off

        Returns:
            List[Panel]: The neighboring panels
        """
        return (self.panel(i) for i in self.__neighbor_dict.get(index))
