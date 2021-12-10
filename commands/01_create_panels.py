import rhinoscriptsyntax as rs
from helpers.topology import PanelTopology
from components.repository import Repository
from helpers.settings import GeometrySettings


def main():
    # Ask to select some panels from Rhino
    picked_ids = rs.GetObjects("Select panels", 8)

    if len(picked_ids) == 0:
        return

    topology = PanelTopology(picked_ids)
    repo = Repository()
    settings = GeometrySettings(0.06, 0.02, 0.02, 0.005, 0.015, 0.04)

    for panel in topology.panels():
        neighbors = topology.panel_neighbors(panel.panel_index)
        for neighbor in neighbors:
            panel.add_neighbor(neighbor)
        panel.settings = vars(settings)

    for panel in topology.panels():
        repo.update_component(panel)


if __name__ == "__main__":
    main()
