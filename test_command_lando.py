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
from algorithms import offset_pline_wards, point_polar


def main():
    result, objRef = Rhino.Input.RhinoGet.GetOneObject(
        "Select Cassette outline", False, Rhino.DocObjects.ObjectType.Curve
    )
    if result != Rhino.Commands.Result.Success:
        return result

    crv = objRef.Curve().ToPolyline()

    sc.doc.Objects.AddPoint(point_polar(rg.Plane.WorldXY, 1, math.pi / 1))

    settings = GeometrySettings(0.06, 0.02, 0.02, 0.005)
    cassette = Cassette("cassette", 0, rg.Plane.WorldXY, crv, [], settings)
    cassette.create_geometry()

    print(cassette.beam_corner_points.keys())

    for key in cassette.beam_corner_points["TopUpper"]:
        sc.doc.Objects.AddTextDot(key, cassette.beam_corner_points["TopUpper"][key])

    for key in cassette.beam_corner_points["MiddleUpper"]:
        sc.doc.Objects.AddTextDot(key, cassette.beam_corner_points["MiddleUpper"][key])

    for beam in cassette.beams:
        sc.doc.Objects.AddBrep(beam.volume_geometry)


if __name__ == "__main__":
    logging.basicConfig(
        filename="test_command_lando.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%d/%m/%Y %I:%M:%S",
    )

    main()
