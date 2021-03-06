import components.repository as repo
import rhinoscriptsyntax as rs


def add_sawtooths_to_beams(joints):

    for joint in joints:
        joint.add_joint_geometry_to_children()

        print(
            "Added sawtooths to panels beams connected to joint {}".format(
                joint.identifier
            )
        )

    # repo.commit_changes()


def main():

    picked_label_ids = rs.GetObjects(
        "Select joints to generate sawtooths from", filter=512
    )
    if picked_label_ids is None:
        return

    joints = [repo.get_component_by_part_id(id) for id in picked_label_ids]

    add_sawtooths_to_beams(joints)


if __name__ == "__main__":
    main()
