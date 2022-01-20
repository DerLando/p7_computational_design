from component import Component
import logging
import Rhino.Geometry as rg
import repository as repo
from helpers import keys
from helpers.keys import TOP_OUTLINE_KEY
import scriptcontext as sc
from helpers import serde, algorithms
import Rhino
from helpers.geometry import ClosedPolyline
from System import Guid
import math
import rhinoscriptsyntax as rs
import copy

MALE_KEY = "male_id"
FEMALE_KEY = "female_id"
GUIDES_LAYER_NAME = "{}{}Guides".format(serde.JOINT_LAYER_NAME, serde.SEPERATOR)


def level_key(level):
    return "Level_{}".format(level)


class JointFactory(object):
    @staticmethod
    def get_shared_edge_key(panel_a, panel_b):
        shared_edge_key = None
        for key, value in panel_a.neighbor_ids.items():
            if value != panel_b.panel_id:
                continue
            shared_edge_key = key
            break

        if shared_edge_key is None:
            logging.error(
                "Failed to find shared edge key between {} and {}".format(
                    panel_a, panel_b
                )
            )
            return

        return shared_edge_key

    @staticmethod
    def calculate_shared_plane(panel_a, panel_b, shared_edge_key):
        edge = panel_a.outline.get_edge(shared_edge_key)
        origin = edge.PointAt(0.5)
        x_axis = panel_a.plane.ZAxis + panel_b.plane.ZAxis
        y_axis = rg.Vector3d.CrossProduct(x_axis, edge.Direction)
        plane = rg.Plane(origin, x_axis, y_axis)

        return plane

    @staticmethod
    def create_joint(panel_a, panel_b):
        identifier = "{} x {}".format(panel_a.identifier, panel_b.identifier)
        shared_edge_key = JointFactory.get_shared_edge_key(panel_a, panel_b)

        plane = JointFactory.calculate_shared_plane(panel_a, panel_b, shared_edge_key)

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

        return Joint(identifier, plane, (panel_a.panel_id, panel_b.panel_id), guides)


class Joint(Component):

    # region fields
    _LAYER_NAME = "Joint"
    _LABEL_HEIGHT = 25
    male_id = Guid.Empty  # Do not transform
    female_id = Guid.Empty  # Do not transform
    guides = {key: None for key in [level_key(i) for i in range(4)]}
    guide_ids = {key: Guid.Empty for key in guides}

    # endregion

    def __init__(self, identifier, plane, panels, guides):

        super(Joint, self).__init__(identifier, plane)

        self.settings[MALE_KEY] = panels[0]
        self.settings[FEMALE_KEY] = panels[1]
        self.guides = {
            key: guide for key, guide in zip([level_key(i) for i in range(4)], guides)
        }
        self.guide_ids = {key: Guid.Empty for key in self.guides}

    @property
    def male_id(self):
        return self.settings.get(MALE_KEY)

    @male_id.setter
    def male_id(self, id):
        self.settings[MALE_KEY] = id

    @property
    def female_id(self):
        return self.settings.get(FEMALE_KEY)

    @female_id.setter
    def female_id(self, id):
        self.settings[FEMALE_KEY] = id

    @staticmethod
    def __get_safety_length(panel, edge_key):
        calc_safety = lambda angle, t: t / math.sin(math.pi - angle)
        return (
            max(
                [
                    calc_safety(angle, panel.settings["beam_max_width"])
                    for angle in panel.outline.get_edge_angles(panel.plane, edge_key)
                ]
            )
            + 10  # hard coded safety offset
        )

    def add_joint_geometry_to_children(self):
        # get the two connected panels
        # male_panel = repo.get_component_by_part_id(self.male_id)
        # female_panel = repo.get_component_by_part_id(self.female_id)
        male_panel = repo.get_component_by_identifier(self.identifier.split(" ")[0])
        female_panel = repo.get_component_by_identifier(self.identifier.split(" ")[-1])

        # get the connecting edge keys
        def get_shared_edge_key(panel_a, panel_b):
            for key, value in panel_a.neighbor_ids.items():
                if value != panel_b.panel_id:
                    continue
                return key

        shared_key_male = get_shared_edge_key(male_panel, female_panel)
        shared_key_female = get_shared_edge_key(female_panel, male_panel)

        # get beams
        get_beams = lambda repo, panel, edge_key: [
            repo.get_component_by_identifier(ident)
            for ident in [
                keys.panel_beam_identifier(panel.identifier, i, edge_key)
                for i in range(3)
            ]
        ]
        male_beams = get_beams(repo, male_panel, shared_key_male)
        female_beams = get_beams(repo, female_panel, shared_key_female)

        # calc safety length
        safety = max(
            [
                self.__get_safety_length(male_panel, shared_key_male),
                self.__get_safety_length(female_panel, shared_key_female),
            ]
        )

        # get sawtooth settings
        sawtooth_count = None
        sawtooth_depth = male_panel.settings["sawtooth_depth"]
        sawtooth_width = male_panel.settings["sawtooth_width"]

        # iterate over beams and add sawtooths
        # TODO: sawtooth code inside of beams is not too hot
        for i, (male_beam, female_beam) in enumerate(zip(male_beams, female_beams)):

            # make sure toolhead_radius is set
            male_beam.settings["toolhead_radius"] = male_panel.settings[
                "toolhead_radius"
            ]
            female_beam.settings["toolhead_radius"] = female_panel.settings[
                "toolhead_radius"
            ]

            sawtooth_count = male_beam.add_sawtooths(
                sawtooth_depth,
                sawtooth_width,
                self.guides[level_key(i)],
                self.guides[level_key(i + 1)],
                safety,
                sawtooth_count,
            )
            sawtooth_count = female_beam.add_sawtooths(
                sawtooth_depth,
                sawtooth_width,
                self.guides[level_key(i)],
                self.guides[level_key(i + 1)],
                safety,
                sawtooth_count,
                flip_direction=True,
            )

        # repo.commit_changes()

        self.settings["sawtooth_count"] = sawtooth_count

    def add_joint_geometry_to_plates(self):

        # get the two connected panels
        male_panel = repo.get_component_by_identifier(self.identifier.split(" ")[0])
        female_panel = repo.get_component_by_identifier(self.identifier.split(" ")[-1])

        # get the connecting edge keys
        def get_shared_edge_key(panel_a, panel_b):
            for key, value in panel_a.neighbor_ids.items():
                if value != panel_b.panel_id:
                    continue
                return key

        shared_key_male = get_shared_edge_key(male_panel, female_panel)
        shared_key_female = get_shared_edge_key(female_panel, male_panel)

        # get plates
        male_plate = repo.get_component_by_identifier(
            keys.panel_plate_identifier(male_panel.identifier)
        )
        female_plate = repo.get_component_by_identifier(
            keys.panel_plate_identifier(female_panel.identifier)
        )

        # calc safety length
        safety = max(
            [
                self.__get_safety_length(male_panel, shared_key_male),
                self.__get_safety_length(female_panel, shared_key_female),
            ]
        )

        # get sawtooth settings
        # sawtooth_count = self.settings["sawtooth_count"]
        sawtooth_count = self.tooth_count
        sawtooth_depth = male_panel.settings["sawtooth_depth"]
        sawtooth_width = male_panel.settings["sawtooth_width"]

        # add detailed outlines to plates
        # self, edge_key, depth, width, safety, tooth_count, flip_direction
        male_plate.create_detailed_edge(
            shared_key_male,
            sawtooth_depth,
            sawtooth_width,
            safety,
            sawtooth_count,
            False,
        )
        female_plate.create_detailed_edge(
            shared_key_female,
            sawtooth_depth,
            sawtooth_width,
            safety,
            sawtooth_count,
            True,
        )

        # update male and female plate in document
        repo.commit_changes()

        return frozenset([male_plate.label_id, female_plate.label_id])

    # region Read/Write

    @classmethod
    def deserialize(cls, group_index, doc=None):
        if doc is None:
            doc = sc.doc

        # find out what identifier we are working with
        identifier = doc.Groups.GroupName(group_index)
        if identifier is None:
            return

        # get group members for given index
        members = doc.Groups.GroupMembers(group_index)

        # deserialize label and props
        self = super(Joint, cls).deserialize(group_index, doc)
        self.settings = copy.deepcopy(self.settings)
        tooth_count = rs.GetUserText(self.label_id, "sawtooth_count")
        if tooth_count:
            self.tooth_count = int(tooth_count)

        # get the guides
        guide_objs = [
            member
            for member in members
            if member.ObjectType == Rhino.DocObjects.ObjectType.Curve
        ]
        self.guides = {}
        self.guide_ids = {}
        for guide_obj in guide_objs:
            geo = guide_obj.Geometry
            self.guides[guide_obj.Name] = rg.Line(geo.PointAtStart, geo.PointAtEnd)
            self.guide_ids[guide_obj.Name] = guide_obj.Id

        return self

    def serialize(self, doc=None):
        if doc is None:
            doc = sc.doc

        # get or create main layer
        parent = self._main_layer(doc)

        # create an empty list for guids off all child objects
        assembly_ids = []

        # serialize label and settings
        assembly_ids.append(super(Joint, self).serialize(doc))
        tooth_count = self.settings.get("sawtooth_count")
        if tooth_count:
            print(self.label_id)
            rs.SetUserText(self.label_id, "sawtooth_count", tooth_count)

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

        # add serialized geo as a group
        return serde.add_named_group(doc, assembly_ids, self.identifier)

    # endregion


# TODO: Tets updates to settings...
