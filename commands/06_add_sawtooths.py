from components.repository import Repository
import rhinoscriptsyntax as rs


def main():

    picked_label_ids = rs.GetObjects(
        "Select joints to generate sawtooths from", filter=512
    )
    if picked_label_ids is None:
        return

    repo = Repository()

    joints = [repo.get_component_by_part_id(id) for id in picked_label_ids]

    for joint in joints:
        joint.add_joint_geometry_to_children()


if __name__ == "__main__":
    main()
