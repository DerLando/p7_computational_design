import components.repository as repo
import rhinoscriptsyntax as rs
<<<<<<< HEAD
from 01_create_panels import create_panels
from 02_create_beams import create_beams
=======

create_panels = __import__("01_create_panels")
create_beams = __import__("02_create_beams")
create_plates = __import__("03_create_plates")
create_dowels = __import__("04_create_plate_dowels")
create_joints = __import__("05_create_joints")
add_sawtooths_to_beams = __import__("06_add_sawtooths_to_beams")
add_sawtooths_to_plates = __import__("07_add_sawtooths_to_plates")

import components.repository as repo

>>>>>>> 9232948ef733a6cb85614d7e1deb78da31ca675d

def main():

    # create panels
<<<<<<< HEAD
    panels = create_panels()

    # create beams from panels
    beams = create_beams(panels)
=======
    panel_ids = create_panels.create_panels()

    # create beams from panels
    beams = create_beams.create_beams([repo.read_component(id) for id in panel_ids])

    # create plates from panels
    plates = create_plates.create_plates([repo.read_component(id) for id in panel_ids])

    # create dowels from panels
    dowels = create_dowels.create_dowels([repo.read_component(id) for id in panel_ids])

    # create joints between panels
    joint_ids = create_joints.create_joints(
        [repo.read_component(id) for id in panel_ids]
    )

    joints = [repo.read_component(id) for id in joint_ids]
    for joint in joints:
        print(joint.label_id)

    # add sawtooths to beams
    add_sawtooths_to_beams.add_sawtooths_to_beams(
        [repo.read_component(id) for id in joint_ids]
    )

    # add sawtooths to plates
    add_sawtooths_to_plates.add_sawtooths_to_plates(
        [repo.read_component(id) for id in joint_ids]
    )

>>>>>>> 9232948ef733a6cb85614d7e1deb78da31ca675d

if __name__ == "__main__":
    main()
