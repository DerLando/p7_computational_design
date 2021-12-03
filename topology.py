import logging
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import rhinoscriptsyntax as rs


class Panel(object):
    """
    A single panel of arbitrary vertex count.
    """

    def __init__(self, id, index, plane, outline):
        """
        Initialize a new Panel instance

        Args:
            index (int): The index of the panel in the panelbuffer it is extracted from
            plane (Plane): The plane of the panel, centered at the panel center, with normal in panel-normal direction
            outline (Polyline): The panel edges as a closed polyline
        """
        self.__id = id
        self.__index = index
        self.__plane = plane
        self.__outline = outline

    @property
    def id(self):
        return self.__id

    @property
    def index(self):
        """
        The index of the panel in the panelbuffer it is extracted from

        Returns:
            int: The index
        """
        return self.__index

    @property
    def plane(self):
        return self.__plane

    @property
    def outline(self):
        return self.__outline


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
            panels.append(
                Panel(
                    panel_id,
                    self.__get_panel_index(panel_id),
                    self.__get_panel_plane(panel_id),
                    self.__get_panel_outline(panel_id),
                )
            )

            self.__neighbor_dict[panels[-1].index] = set(
                self.__get_panel_neighbor_indices(panel_id)
            )

        panels.sort(key=lambda x: x.index)

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
