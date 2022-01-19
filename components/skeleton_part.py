import math
from components.component import Component
import logging
from components.joint import JointFactory
from helpers import algorithms, serde, keys
from helpers.geometry import ClosedPolyline
import Rhino.Geometry as rg
import Rhino
import scriptcontext as sc
from System import Guid
import rhinoscriptsyntax as rs
import repository as repo
from System.Collections.Generic import List

SURFACE_LAYER_NAME = "{}{}Surface".format(serde.PANEL_LAYER_NAME, serde.SEPERATOR)
SIZE = 100


class SkeletonFactory(object):
    @staticmethod
    def create_skeletonpart(skeleton, panel):

        # calculate cutting planes
        planes = []
        for neighbor_id in panel.get_existing_neighbor_ids():
            neighbor = repo.get_component_by_part_id(neighbor_id)

            key = JointFactory.get_shared_edge_key(panel, neighbor)

            plane = JointFactory.calculate_shared_plane(panel, neighbor, key)

            plane.Rotate(math.pi / 2.0, plane.XAxis)

            planes.append(plane)

        # convert planes to breps
        cutters = List[rg.Brep]()
        for plane in planes:
            size = rg.Interval(-SIZE, SIZE)
            rect = rg.Rectangle3d(plane, size, size)
            cutters.Add(rg.Brep.CreateTrimmedPlane(plane, rect.ToNurbsCurve()))

        # split skeleton with cutters
        parts = skeleton.Split(cutters, 0.001)
        if parts.Count != 2:
            logging.error("Failed to split skeleton in parts!")
            for cutter in cutters:
                sc.doc.Objects.AddBrep(cutter)
            return

        # find the smaller part by comparing their bboxes
        part = sorted(parts, key=lambda x: x.GetBoundingBox(False).Area)[0]

        # make sure part is a solid
        part = part.CapPlanarHoles(0.001)

        return SkeletonPart(
            keys.panel_skeleton_identifier(panel.identifier), panel.plane, part
        )


class SkeletonPart(Component):

    # region fields

    _LABEL_HEIGHT = 75
    skeleton_id = Guid.Empty
    skeleton_geo = None

    # endregion

    def __init__(self, identifier, plane, skeleton_part):

        super(SkeletonPart, self).__init__(identifier, plane)

        self.skeleton_geo = skeleton_part

    # region Read/Write

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

        # get the skeleton geo
        skeleton_obj = [
            member
            for member in members
            if member.ObjectType == Rhino.DocObjects.ObjectType.Brep
        ][0]
        self.skeleton_geo = skeleton_obj.Geometry
        self.skeleton_id = skeleton_obj.Id

        return self

    def serialize(self, doc=None):
        if doc is None:
            doc = sc.doc

        # get or create main layer
        main_layer_index = serde.add_or_find_layer(serde.SKELTON_LAYER_NAME, doc)
        parent = doc.Layers.FindIndex(main_layer_index)

        # create an empty list for guids off all child objects
        assembly_ids = []

        # serialize label and settings
        id = super(SkeletonPart, self).serialize(doc)
        assembly_ids.append(id)

        # get or create a child layer for the geometry
        geo_layer_index = serde.add_or_find_layer(
            SURFACE_LAYER_NAME,
            doc,
            serde.VOLUME_COLOR,
            parent,
        )

        # serialize geometry
        id = serde.serialize_geometry(
            self.skeleton_geo,
            geo_layer_index,
            doc,
            old_id=self.skeleton_id,
        )
        assembly_ids.append(id)

        # add serialized geo as a group
        return serde.add_named_group(doc, assembly_ids, self.identifier)

    # endregion
