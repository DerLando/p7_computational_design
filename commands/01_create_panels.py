import rhinoscriptsyntax as rs
from helpers.topology import PanelTopology
from components.repository import Repository

# from helpers.settings import GeometrySettings


def main():
    # Ask to select some panels from Rhino
    picked_ids = rs.GetObjects("Select panels", 8)

    if len(picked_ids) == 0:
        return

    topology = PanelTopology(picked_ids)
    repo = Repository()
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

    for panel in topology.panels():
        repo.update_component(panel)


if __name__ == "__main__":
    main()
