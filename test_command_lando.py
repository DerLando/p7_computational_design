import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import rhinoscriptsyntax as rs
import logging
import math
from beam import Beam
from dowel import Dowel
from plate import Plate
from cassette import Cassette
from building import Building, GeometrySettings
from bake import Baker
from algorithms import offset_pline_wards, point_polar, ensure_winding_order
from toy_topology import MeshTopology
from geometry import ClosedPolyline
from topology import PanelTopology


def test_topology():
    size = rg.Interval(-10.0, 10.0)
    mesh = rg.Mesh.CreateFromBox(rg.Box(rg.Plane.WorldXY, size, size, size), 10, 10, 10)

    topo = MeshTopology(mesh)

    face = topo.face(0)

    neighbors = topo.face_neighbors(face)

    print(neighbors)


def create_one_cassette():
    result, objRef = Rhino.Input.RhinoGet.GetOneObject(
        "Select Cassette outline", False, Rhino.DocObjects.ObjectType.Curve
    )
    if result != Rhino.Commands.Result.Success:
        return result

    crv = objRef.Curve().ToPolyline()
    ensure_winding_order(crv, rg.Plane.WorldXY)

    settings = GeometrySettings(0.06, 0.02, 0.02, 0.005, 0.015, 0.04)
    cassette = Cassette("cassette", 0, rg.Plane.WorldXY, crv, [], settings)
    cassette.create_geometry()

    baker = Baker()

    baker.bake_cassette(cassette)

    for beam in cassette.all_beams:
        baker.bake_beam(beam, detailed=True)


def create_multiple_cassettes():
    result, objRef = Rhino.Input.RhinoGet.GetOneObject(
        "Select Cassettes Mesh", False, Rhino.DocObjects.ObjectType.Mesh
    )
    if result != Rhino.Commands.Result.Success:
        return result

    mesh = objRef.Mesh()

    settings = GeometrySettings(0.06, 0.02, 0.02, 0.005, 0.015, 0.04)
    building = Building(mesh, settings, create_geoemtry=True)

    baker = Baker()

    for cassette in building.cassettes.values():

        baker.bake_cassette(cassette)

        # for beam in cassette.all_beams:
        #     baker.bake_beam(beam)

        for layer in cassette.layers:
            for beam in layer.beams.values():
                baker.bake_beam(beam, detailed=True)

    # for cassette in building.cassettes.values():
    #     text = "{} \n".format(cassette.identifier)
    #     for neighbor in cassette.existing_neighbors:
    #         text += "{}, ".format(neighbor.identifier)
    #     sc.doc.Objects.AddTextDot(text, cassette.plane.Origin)


def find_neighbors():

    # list of breps
    cassettes = []

    grouped = {0: extract_edges([cassettes[0]])}

    for key in grouped:
        neighbors = {}
        main_edges = grouped[key]
        for other_key in grouped:
            if key == other_key:
                continue

            other_edges = grouped[other_key]

            for index, edge in enumerate(main_edges):
                for other_edge in other_edges:
                    if not rg.GeometryBase.GeometryEquals(edge, other_edge):
                        continue

                    neighbors[index] = other_key


def cc_edges():

    for key, edge in ClosedPolyline(
        rg.Rectangle3d(rg.Plane.WorldXY, 10.0, 5.0).ToPolyline()
    ).get_edges():
        print(key)


def cassettes_from_panels():
    obj_ids = rs.GetObjects("Select panels with associated data", filter=8)
    if obj_ids is None:
        return

    settings = GeometrySettings(0.06, 0.02, 0.02, 0.005, 0.015, 0.04)
    building = Building(obj_ids, settings, create_geoemtry=True)

    baker = Baker()

    for cassette in building.cassettes.values():

        baker.bake_cassette(cassette)

        # for beam in cassette.all_beams:
        #     baker.bake_beam(beam)

        for layer in cassette.layers:
            for beam in layer.beams.values():
                baker.bake_beam(beam, detailed=True)

        baker.bake_plate(cassette.plate)

    return


if __name__ == "__main__":
    logging.basicConfig(
        filename="test_command_lando.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%d/%m/%Y %I:%M:%S",
    )

    # create_one_cassette()
    # test_topology()
    # cc_edges()
    # create_multiple_cassettes()
    cassettes_from_panels()
