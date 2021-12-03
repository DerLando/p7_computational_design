import logging
from toy_topology import MeshTopology
from cassette import Cassette
from topology import PanelTopology


class GeometrySettings(object):
    """
    Full set of geometry settings, like width, heigh, radius of different building elements,
    used for geometry generation.
    """

    def __init__(
        self,
        beam_max_width,
        beam_thickness,
        plate_thickness,
        dowel_radius,
        sawtooth_depth,
        sawtooth_width,
    ):
        self.beam_max_width = beam_max_width
        self.beam_thickness = beam_thickness
        self.plate_thickness = plate_thickness
        self.dowel_radius = dowel_radius
        self.sawtooth_depth = sawtooth_depth
        self.sawtooth_width = sawtooth_width


class Building(object):
    """
    The main building class handling generating fabrication geometry from a mesh input.
    The mesh needs to have all planar faces (or ngons).
    """

    def __init__(self, panel_ids, geometry_settings, create_geoemtry=False):
        self.topology = PanelTopology(panel_ids)
        self.geometry_settings = geometry_settings

        self.cassettes = Building.create_cassettes(
            self.topology, self.geometry_settings
        )

        for ident, cassette in self.cassettes.items():
            for neighbor in self.find_cassette_neighbors(ident):
                cassette.add_neighbor(neighbor)

        if create_geoemtry:
            for cassette in self.cassettes.values():
                cassette.create_geometry()

    @staticmethod
    def create_cassettes(topology, geometry_settings):
        """
        Create cassettes from the given topology.
        For every topology-face, one cassette will be generated.
        The generated cassettes do not have any neigbor information assigned yet.

        Args:
            topology (MeshTopology): The topology to extract face information from
            geometry_settings(GeometrySettings): The settings for geometry calculation

        Returns:
            dict[str:Cassette]: The generated cassettes, in a dictionary, with their identifiers as keys
        """
        cassettes = {}
        for panel in topology.panels():
            cassette = Cassette(
                str(panel.index),
                panel.index,
                panel.plane,
                panel.outline,
                geometry_settings,
            )
            cassettes[cassette.identifier] = cassette

        return cassettes

    def find_cassette_neighbors(self, identifier):
        """
        Find the neighboring cassettes for a given cassette

        Args:
            identifier (str): The identifier of the cassette

        Returns:
            List[Cassette]: The cassette neighbors (unordered)
        """
        if self.cassettes is None:
            logging.warn(
                "Building.find_cassette_neighbors: Called without cassettes defined!"
            )
            return

        neighbor_panels = self.topology.panel_neighbors(
            self.cassettes[identifier].face_index
        )

        neighbor_cassettes = []
        for panel in neighbor_panels:
            neighbor_cassettes.append(self.cassettes[str(panel.index)])

        return neighbor_cassettes
