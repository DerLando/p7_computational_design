from beam import Beam
from joint import Joint
from dowel import Dowel
from panel import Panel
from plate import Plate


def extract_classname(type):
    return str(type).split(".")[-1]


COMPONENT_TYPES = {
    extract_classname(Beam): Beam,
    extract_classname(Dowel): Dowel,
    extract_classname(Panel): Panel,
    extract_classname(Plate): Plate,
    extract_classname(Joint): Joint,
}
