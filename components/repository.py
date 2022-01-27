try:
    import scriptcontext as sc
except:
    import inside_doc as sc
import logging
import components
from helpers import keys, serde
import fnmatch

TYPE_KEY = "type"

# TODO: How can we expose this to component instances?
# Pythons wonderful circular import block makes this rather hard..

__GID_COMPONENT_MAPPER = {}


def __get_gid_by_identifier(identifier, doc=None):
    if not doc:
        doc = sc.doc

    group = doc.Groups.FindName(identifier)
    if group is None:
        logging.error(
            "Tried to find component {}, but it doesn't exist".format(identifier)
        )
        return

    return group.Index


def get_component_by_identifier(identifier, doc=None):
    return read_component(__get_gid_by_identifier(identifier), doc)


def get_component_by_part_id(part_id, doc=None):
    if doc is None:
        doc = sc.doc

    part_obj = doc.Objects.FindId(part_id)
    if part_obj is None:
        logging.error("Tried to find component for invalid part id: {}".format(part_id))
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
    if group_index is None:
        return

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


def update_component(component, doc=None):
    gid = __get_gid_by_identifier(component.identifier)
    if not gid:
        logging.error(
            "Tried to update non existing component {}".format(component.identifier)
        )
        return

    component.serialize()

    __GID_COMPONENT_MAPPER[gid] = component


def __get_layer_group_ids(layer_name, doc=None):
    if not doc:
        doc = sc.doc

    layer = doc.Layers.FindName(layer_name)
    if layer is None:
        logging.error("Failed to find layer {}".format(layer_name))
        return

    objects = doc.Objects.FindByLayer(layer)

    gids = set()

    for object in objects:
        if object.GroupCount != 1:
            continue
        gids.add(object.GetGroupList()[0])

    return gids


def search_components(search, doc=None):
    """
    Searches for components by identifier search.
    Supports wildcards.
    """

    if doc is None:
        doc = sc.doc

    found = []
    for group in sc.doc.Groups:
        matches = fnmatch.filter([group.Name], search)
        if not matches:
            continue

        found.append(group.Index)

    return found


def select_component(gid, doc=None):
    if doc is None:
        doc = sc.doc

    rhobjs = doc.Groups.GroupMembers(gid)
    if rhobjs is None:
        logging.error("Failed to read objects for group {}".format(gid))

    for rhobj in rhobjs:
        rhobj.Select(True)


def get_all_components(component_type, doc=None):
    if doc is None:
        doc = sc.doc

    main_layer = doc.Layers.FindName(component_type._LAYER_NAME)
    if not main_layer:
        logging.error(
            "Failed to find component layer for type {}!".format(component_type)
        )
        return

    children = main_layer.GetChildren()
    if children.Count == 0:
        logging.error("Failed to find child layers for type {}!".format(component_type))
        return

    # for gids in children, union to set
    gids = set()

    # get comps for gids set
    for layer in children:
        gids = gids.union(__get_layer_group_ids(layer.Name, doc))

    # return coms
    return [read_component(gid, doc) for gid in gids]


def get_cassette_from_panel(panel):
    """
    Gets all components that 'belongs' to a logic cassette.
    This won't get non-components like screws and dowels, you
    will need to find them by calling `get_all_components()`.
    """

    components = []

    # get panel plate
    plate_ident = keys.panel_plate_identifier(panel.identifier)
    plate = get_component_by_identifier(plate_ident)
    if not plate:
        logging.warn("Could not find a plate for panel {}".format(panel.identifier))
    else:
        components.append(plate)

    # get panel skeleton
    skeleton_ident = keys.panel_skeleton_identifier(panel.identifier)
    skeleton = get_component_by_identifier(skeleton_ident)
    if not skeleton:
        logging.warn("Could not find skeleton for panel {}".format(panel.identifier))
    else:
        components.append(skeleton)

    # get panel beams
    edge_keys = keys.edge_keys(panel.outline.corner_count)
    for level in range(3):
        for key in edge_keys:
            beam_ident = keys.panel_beam_identifier(panel.identifier, level, key)
            beam = get_component_by_identifier(beam_ident)
            if not beam:
                logging.warn(
                    "Could not find beam {}{}{}".format(panel.identifier, level, key)
                )
            else:
                components.append(beam)

    return components


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
