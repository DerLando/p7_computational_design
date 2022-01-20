import components.repository as repo
import rhinoscriptsyntax as rs


<<<<<<< HEAD
def main():

    picked_label_ids = rs.GetObjects(
        "Select joints to generate sawtooths from", filter=512
    )
    if picked_label_ids is None:
        return

    joints = [repo.get_component_by_part_id(id) for id in picked_label_ids]
=======
def add_sawtooths_to_plates(joints):
>>>>>>> 9232948ef733a6cb85614d7e1deb78da31ca675d
    plate_ids = set()

    for joint in joints:
        plate_ids.add(joint.add_joint_geometry_to_plates())

    for plates in plate_ids:
        for plate in plates:
            plate = repo.get_component_by_part_id(plate)
            plate.create_and_set_detail_geometry()

    repo.commit_changes()


<<<<<<< HEAD
=======
def main():

    picked_label_ids = rs.GetObjects(
        "Select joints to generate sawtooths from", filter=512
    )
    if picked_label_ids is None:
        return

    joints = [repo.get_component_by_part_id(id) for id in picked_label_ids]

    add_sawtooths_to_plates(joints)


>>>>>>> 9232948ef733a6cb85614d7e1deb78da31ca675d
if __name__ == "__main__":
    main()
