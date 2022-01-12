
try:
    import scriptcontext as sc
except:
    import inside_doc as sc
import logging
import components


TYPE_KEY = "type"

# TODO: How can we expose this to component instances?
# Pythons wonderful circular import block makes this rather hard..

__GID_COMPONENT_MAPPER = {}


def __init__(self, doc=None):
    if doc is None:
        doc = sc.doc

    self.__doc = doc


def get_component_by_identifier(identifier, doc=None):
    if not doc:
        doc = sc.doc

    group = doc.Groups.FindName(identifier)
    if group is None:
        logging.error(
            "Tried to find component {}, but it doesn't exist".format(identifier)
        )
        return

    return read_component(group.Index, doc)


def get_component_by_part_id(part_id, doc=None):
    if doc is None:
        doc = sc.doc

    part_obj = doc.Objects.FindId(part_id)
    if part_obj is None:
        logging.error("Tried to find component for invalid part id")
        return

    if part_obj.GroupCount != 1:
        logging.error("Part {} is in multiple groups".format(part_obj.Name))
        return
    return read_component(part_obj.GetGroupList()[0])


def create_component(component, doc=None):
    if doc is None:
        doc = sc.doc

    group_index = component.serialize(doc)
    group = doc.Groups.FindIndex(group_index)
    group.SetUserString(TYPE_KEY, components.extract_classname(type(component)))

    __GID_COMPONENT_MAPPER[group_index] = component

    return group_index


def read_component(group_index, doc=None):
    component = __GID_COMPONENT_MAPPER.get(group_index)
    if component:
        return component

    if doc is None:
        doc = sc.doc

    group = doc.Groups.FindIndex(group_index)
    if group is None:
        logging.error("No group defined at index {}".format(group_index))
        return

    type_str = group.GetUserString(TYPE_KEY)
    component_type = components.COMPONENT_TYPES.get(type_str)
    if component_type is None:
        logging.error("Unknown component type")
        return

    __GID_COMPONENT_MAPPER[group_index] = component_type.deserialize(group_index)

    return __GID_COMPONENT_MAPPER[group_index]


def commit_changes():
    for component in __GID_COMPONENT_MAPPER.values():
        component.serialize()


def __update_component(self, component):
    group_index = component.serialize(self.__doc)
    group = self.__doc.Groups.FindIndex(group_index)
    group.SetUserString(TYPE_KEY, components.extract_classname(type(component)))


if __name__ == "__main__":
    a = read_component(0)
    b = read_component(0)

    print(a, b)
    print(a == b)

    a = get_component_by_identifier("P_0")
    b = get_component_by_identifier("P_0")

    print(a == b)

    a.settings["test"] = "test"
    print(b.settings["test"])
