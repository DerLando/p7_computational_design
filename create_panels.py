import rhinoscriptsyntax as rs
from topology import PanelTopology
from panel import Panel


def main():
    # Ask to select some panels from Rhino
    picked_ids = rs.GetObjects("Select panels", 8)

    if len(picked_ids) == 0:
        return

    topology = PanelTopology(picked_ids)

    for panel in topology.panels():
        neighbors = topology.panel_neighbors(panel.panel_index)
        for neighbor in neighbors:
            panel.add_neighbor(neighbor)

    for panel in topology.panels():
        panel.serialize()


if __name__ == "__main__":
    main()
