from component import Component
import logging
import Rhino.Geometry as rg
from helpers.keys import TOP_OUTLINE_KEY
import scriptcontext as sc
from helpers import serde, algorithms
import Rhino
from helpers.geometry import ClosedPolyline
from System import Guid
from plate import Plate

MALE_KEY = "male"
FEMALE_KEY = "female"
GUIDES_LAYER_NAME = "{}{}Guides".format(serde.JOINT_LAYER_NAME, serde.SEPERATOR)


def level_key(level):
    return "Level_{}".format(level)


class JointFactory(object):
    @staticmethod
    def create_joint(panel_a, panel_b):
        identifier = "{} x {}".format(panel_a.identifier, panel_b.identifier)
        shared_edge_key = None
        for key, value in panel_a.neighbor_ids.items():
            if value != panel_b.panel_id:
                continue
            shared_edge_key = key
            break

        if shared_edge_key is None:
            logging.error("Failed to create joint {}".format(identifier))
            return

        # TODO calc. plane aces
        edge = panel_a.outline.get_edge(shared_edge_key)
        origin = edge.PointAt(0.5)
        x_axis = panel_a.plane.ZAxis + panel_b.plane.ZAxis
        y_axis = rg.Vector3d.CrossProduct(x_axis, edge.Direction)
        plane = rg.Plane(origin, x_axis, y_axis)

        # create guides
        outlines = [panel_a.outline]
        for _ in range(3):
            outlines.append(
                ClosedPolyline(
                    algorithms.draft_angle_offset(
                        outlines[-1],
                        panel_a.plane,
                        panel_a.neighbor_angles,
                        panel_a.settings["beam_thickness"],
                    )
                )
            )

        guides = [outline.get_edge(shared_edge_key) for outline in outlines]

        return Joint(identifier, plane, (panel_a, panel_b), guides)


class Joint(Component):
    def __init__(self, identifier, plane, panels, guides):

        self._LABEL_HEIGHT = 0.025

        super(Joint, self).__init__(identifier, plane)

        self.male_id = panels[0]
        self.female_id = panels[1]
        self.guides = {
            key: guide for key, guide in zip([level_key(i) for i in range(4)], guides)
        }
        self.guide_ids = {key: Guid.Empty for key in self.guides}

    def add_joint_geometry_to_children(self):

        pass

    @classmethod
    def deserialize(cls, group_index, doc=None):
        if doc is None:
            doc = sc.doc

        # create a new, empty instance of self
        self = cls.__new__(cls)

        # find out what identifier we are working with
        identifier = doc.Groups.GroupName(group_index)
        if identifier is None:
            return

        # get group members for given index
        members = doc.Groups.GroupMembers(group_index)

        # get the label object
        label_obj = [member for member in members if member.Name == identifier][0]
        self.label = label_obj.Geometry
        self.label_id = label_obj.Id

        # extract properties from label object
        prop_dict = cls._deserialize_properties(label_obj, doc)
        for key, value in prop_dict.items():
            self.__setattr__(key, value)

        # get the guides
        guide_objs = [
            member
            for member in members
            if member.ObjectType == Rhino.DocObjects.ObjectType.Curve
        ]
        self.guides = {}
        self.guide_ids = {}
        for guide_obj in guide_objs:
            self.guides[guide_obj.Name] = guide_obj.Geometry.Line
            self.guide_ids[guide_obj.Name] = guide_obj.Id

        return self

    def serialize(self, doc=None):
        if doc is None:
            doc = sc.doc

        # get or create main layer
        main_layer_index = serde.add_or_find_layer(serde.JOINT_LAYER_NAME, doc)
        parent = doc.Layers.FindIndex(main_layer_index)

        # create an empty list for guids off all child objects
        assembly_ids = []

        # get or create a child layer for the outlines
        guide_layer_index = serde.add_or_find_layer(
            GUIDES_LAYER_NAME,
            doc,
            serde.CURVE_COLOR,
            parent,
        )

        # serialize outlines
        for key in self.guides:
            id = serde.serialize_geometry(
                self.guides[key].ToNurbsCurve(),
                guide_layer_index,
                doc,
                name=key,
                old_id=self.guide_ids[key],
            )
            assembly_ids.append(id)

        # get or create a child layer for label
        label_layer_index = serde.add_or_find_layer(
            "{}{}Label".format(serde.JOINT_LAYER_NAME, serde.SEPERATOR),
            doc,
            serde.LABEL_COLOR,
            parent,
        )

        # create a dict of all properties to serialize
        prop_dict = {
            MALE_KEY: self.male_id,
            FEMALE_KEY: self.female_id,
        }

        # serialize label
        id = self._serialize_label(label_layer_index, doc, prop_dict)
        assembly_ids.append(id)

        # add serialized geo as a group
        group = sc.doc.Groups.FindName(self.identifier)
        if group is None:
            # group with our identifier does not exist yet, add to table
            return sc.doc.Groups.Add(self.identifier, assembly_ids)

        else:
            sc.doc.Groups.AddToGroup(group.Index, assembly_ids)
            return group.Index
