import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
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


def test_topology():
    size = rg.Interval(-10.0, 10.0)
    mesh = rg.Mesh.CreateFromBox(rg.Box(rg.Plane.WorldXY, size, size, size), 10, 10, 10)

    topo = MeshTopology(mesh)

    topo.face(0)


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


if __name__ == "__main__":
    logging.basicConfig(
        filename="test_command_lando.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%d/%m/%Y %I:%M:%S",
    )

    create_one_cassette()
    # test_topology()
