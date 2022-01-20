import rhinoscriptsyntax as rs
from helpers.topology import PanelTopology
import components.repository as repo

# from helpers.settings import GeometrySettings


def create_panels():
    # Ask to select some panels from Rhino
    picked_ids = rs.GetObjects("Select panels", 8)

    if len(picked_ids) == 0:
        return

    topology = PanelTopology(picked_ids)
    # settings = GeometrySettings(60, 20, 20, 5, 15, 40)
    settings = {
        "beam_max_width": 60,
        "beam_thickness": 20,
        "plate_thickness": 25,
        "dowel_radius": 5,
        "sawtooth_depth": 15,
        "sawtooth_width": 40,
        "toolhead_radius": 4,
    }

    for panel in topology.panels():
        neighbors = topology.panel_neighbors(panel.panel_index)
        for neighbor in neighbors:
            panel.add_neighbor(neighbor)
        panel.settings = settings

    panel_ids = []

    for panel in topology.panels():
        id = repo.create_component(panel)
        panel_ids.append(id)

    return panel_ids


if __name__ == "__main__":
    create_panels()
