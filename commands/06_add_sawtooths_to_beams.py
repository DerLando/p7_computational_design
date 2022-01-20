import components.repository as repo
import rhinoscriptsyntax as rs


<<<<<<< HEAD
=======
def add_sawtooths_to_beams(joints):

    for joint in joints:
        joint.add_joint_geometry_to_children()

    repo.commit_changes()


>>>>>>> 9232948ef733a6cb85614d7e1deb78da31ca675d
def main():

    picked_label_ids = rs.GetObjects(
        "Select joints to generate sawtooths from", filter=512
    )
    if picked_label_ids is None:
        return

    joints = [repo.get_component_by_part_id(id) for id in picked_label_ids]

<<<<<<< HEAD
    for joint in joints:
        joint.add_joint_geometry_to_children()

    repo.commit_changes()
=======
    add_sawtooths_to_beams(joints)
>>>>>>> 9232948ef733a6cb85614d7e1deb78da31ca675d


if __name__ == "__main__":
    main()
