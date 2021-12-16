from components.repository import Repository
import rhinoscriptsyntax as rs


def main():

    repo = Repository()

    picked_label_ids = rs.GetObjects(
        "Select joints to generate sawtooths from", filter=512
    )
    if picked_label_ids is None:
        return

    picked_components = [repo.get_component_by_part_id(id) for id in picked_label_ids]

    for component in picked_components:
        print(component)
        print(component.settings)


if __name__ == "__main__":
    main()
