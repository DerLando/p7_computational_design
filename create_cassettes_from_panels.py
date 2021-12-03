import rhinoscriptsyntax as rs
import logging
from building import Building, GeometrySettings
from bake import Baker


def cassettes_from_panels():
    obj_ids = rs.GetObjects("Select panels with associated data", filter=8)
    if obj_ids is None:
        return

    settings = GeometrySettings(0.06, 0.02, 0.02, 0.005, 0.015, 0.04)
    building = Building(obj_ids, settings, create_geoemtry=True)

    baker = Baker()

    for cassette in building.cassettes.values():

        baker.bake_cassette(cassette)

    return


if __name__ == "__main__":
    logging.basicConfig(
        filename="test_command_lando.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%d/%m/%Y %I:%M:%S",
    )

    cassettes_from_panels()
