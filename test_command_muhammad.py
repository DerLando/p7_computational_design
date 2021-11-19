import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import logging
from beam import Beam
from dowel import Dowel
from plate import Plate
from cassette import Cassette
from building import Building
from algorithms import offset_pline_wards


def main():
    result, objRef = Rhino.Input.RhinoGet.GetOneObject(
        "Select Beam outline", False, Rhino.DocObjects.ObjectType.Curve
    )
    if result != Rhino.Commands.Result.Success:
        return result

    crv = objRef.Curve().ToPolyline()

    result = offset_pline_wards(crv, rg.Plane.WorldXY, 0.02, inwards=False)

    sc.doc.Objects.AddPolyline(result)


if __name__ == "__main__":
    logging.basicConfig(
        filename="test_command_muhammad.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%d/%m/%Y %I:%M:%S",
    )

    main()
