import Rhino
import scriptcontext as sc
import logging
from beam import Beam
from dowel import Dowel
from plate import Plate
from cassette import Cassette
from building import Building


def main():
    result, objRef = Rhino.Input.RhinoGet.GetOneObject(
        "Select Beam outline", False, Rhino.DocObjects.ObjectType.Curve
    )
    if result != Rhino.Commands.Result.Success:
        return result

    crv = objRef.Curve().ToPolyline()

    for i in range(3):

        beam = Beam(
            "beam",
            Rhino.Geometry.Plane.WorldXY,
            0.04,
            crv,
            Rhino.RhinoMath.ToRadians(15),
        )
        crv = beam.bottom_outline

        for key in beam.corners["top"]:
            sc.doc.Objects.AddTextDot(key, beam.corners["top"][key])

        for key in beam.corners["bottom"]:
            sc.doc.Objects.AddTextDot(key, beam.corners["bottom"][key])

        sc.doc.Objects.AddBrep(beam.volume_geometry)


if __name__ == "__main__":
    logging.basicConfig(
        filename="command_logs/test_command.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%d/%m/%Y %I:%M:%S",
    )

    main()
