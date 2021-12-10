import scriptcontext as sc
import logging
from component import Component
from beam import Beam
from dowel import Dowel
from panel import Panel
from plate import Plate
from joint import Joint


def extract_classname(type):
    return str(type).split(".")[-1]


TYPE_KEY = "type"
COMPONENT_TYPES = {
    extract_classname(Beam): Beam,
    extract_classname(Dowel): Dowel,
    extract_classname(Panel): Panel,
    extract_classname(Plate): Plate,
    extract_classname(Joint): Joint,
}


class Repository(object):
    def __init__(self, doc=None):
        if doc is None:
            doc = sc.doc

        self.__doc = doc

    def get_component_by_identifier(self, identifier):
        group = self.__doc.Groups.FindName(identifier)
        if group is None:
            logging.error(
                "Tried to find component {}, but it doesn't exist".format(identifier)
            )
            return

        return self.read_component(group.index)

    def get_component_by_part_id(self, part_id):
        part_obj = self.__doc.FindId(part_id)
        if part_obj is None:
            logging.error("Tried to find component for invalid part id")
            return

        if part_obj.GroupCount != 1:
            logging.error("Part {} is in multiple groups".format(part_obj.Name))
            return

        return self.read_component(part_obj.GetGroupList()[0])

    def read_component(self, group_index):
        group = self.__doc.Groups.FindIndex(group_index)
        if group is None:
            logging.error("No group defined at index {}".format(group_index))
            return

        type_str = group.GetUserString(TYPE_KEY)
        component_type = COMPONENT_TYPES.get(type_str)
        if component_type is None:
            logging.error("Unknown component type")
            return

        return component_type.deserialize(group_index)

    def update_component(self, component):
        group_index = component.serialize(self.__doc)
        group = self.__doc.Groups.FindIndex(group_index)
        group.SetUserString(TYPE_KEY, extract_classname(type(component)))


if __name__ == "__main__":
    repo = Repository()
    print(repo.read_component(0))
