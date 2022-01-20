from components.component import Component
import logging
from helpers import algorithms, serde, keys
from helpers.geometry import ClosedPolyline
import Rhino.Geometry as rg
import Rhino
import scriptcontext as sc
from System import Guid
import rhinoscriptsyntax as rs

OUTLINE_LAYER_NAME = "{}{}Outline".format(serde.PANEL_LAYER_NAME, serde.SEPERATOR)
SURFACE_LAYER_NAME = "{}{}Surface".format(serde.PANEL_LAYER_NAME, serde.SEPERATOR)
NEIGHBOR_IDS_KEY = "neighbor_ids"
NEIGHBOR_ANGLES_KEY = "neighbor_angles"
INDEX_KEY = "panel_index"


class Panel(Component):

    # region fields

    _LABEL_HEIGHT = 150
    panel_id = Guid.Empty
    panel_index = -1
    outline = None
    outline_id = Guid.Empty
    neighbor_ids = {}
    neighbor_angles = {}

    # endregion

    def __init__(self, identifier, plane, panel_id, panel_index, outline):

        super(Panel, self).__init__(identifier, plane)

        self.panel_id = panel_id
        self.panel_index = panel_index
        self.outline = outline

        self.neighbor_ids = {
            key: Guid.Empty for key in keys.edge_keys(outline.corner_count)
        }
        self.neighbor_angles = {key: 0.0 for key in self.neighbor_ids}

    # region neighbors

    def add_neighbor(self, panel):
        """
        Adds a neighbor at the correct index in the neighbor buffer.
        Basically alinged at the same index, the connecting edge has

        Args:
            neighbor (Panel): The neighbor to add

        Returns:
            str: The edge key the neighbor connects to this cassette at
        """

        # find the connecting edge
        neighbor_key = None
        for key, edge in self.outline.get_edges():
            for neighbor_segment in panel.outline.get_segments():
                if not algorithms.are_lines_equal(edge, neighbor_segment):
                    continue
                neighbor_key = key

        if neighbor_key is None:
            logging.error(
                "Cassette.add_neighbor: Tried to add neighbor {} to cassette {}, but they do not share an edge!".format(
                    panel.identifier, self.identifier
                )
            )
            return None

        if self.neighbor_ids.get(neighbor_key) == Guid.Empty:
            logging.warn(
                "Cassette.add_neighbor: found key {} which was already occupied!".format(
                    neighbor_key
                )
            )

        # calculate angle to neighboring panel
        angle = rg.Vector3d.VectorAngle(
            self.plane.Normal,
            panel.plane.Normal,
            self.outline.get_edge(neighbor_key).Direction,
        )

        # store neighbor panel_id and neighbor angle in inner dicts
        self.neighbor_ids[neighbor_key] = panel.panel_id
        self.neighbor_angles[neighbor_key] = angle

        # return edge key of new neighbor
        return neighbor_key

    def get_existing_neighbor_ids(self):
        """
        Gets the id of all neighbors of this panel.
        Since the neighbors dict contains Guid.Empty values, those are skipped.
        """
        return (
            neighbor_id
            for neighbor_id in self.neighbor_ids.values()
            if neighbor_id != Guid.Empty
        )

    # endregion

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

        # get the outline
        outline_obj = [
            member
            for member in members
            if member.ObjectType == Rhino.DocObjects.ObjectType.Curve
        ][0]
        self.outline = ClosedPolyline(outline_obj.Geometry.ToPolyline())
        self.outline_id = outline_obj.Id

        # get the volume
        surface_obj = [
            member
            for member in members
            if member.ObjectType == Rhino.DocObjects.ObjectType.Brep
        ][0]
        self.panel_id = surface_obj.Id

        return self

    def serialize(self, doc=None):
        if doc is None:
            doc = sc.doc

        # get or create main layer
        main_layer_index = serde.add_or_find_layer(serde.PANEL_LAYER_NAME, doc)
        parent = doc.Layers.FindIndex(main_layer_index)

        # create an empty list for guids off all child objects
        assembly_ids = []

        # get or create a child layer for the outlines
        outline_layer_index = serde.add_or_find_layer(
            OUTLINE_LAYER_NAME,
            doc,
            serde.CURVE_COLOR,
            parent,
        )

        # serialize outline
        id = serde.serialize_geometry(
            self.outline.as_curve(),
            outline_layer_index,
            doc,
            old_id=self.outline_id,
        )
        assembly_ids.append(id)

        # get or create a child layer for the outlines
        surface_layer_index = serde.add_or_find_layer(
            SURFACE_LAYER_NAME,
            doc,
            serde.VOLUME_COLOR,
            parent,
        )

        # serialize surface
        id = serde.serialize_geometry(
            rs.coercebrep(self.panel_id),
            surface_layer_index,
            doc,
            old_id=self.panel_id,
        )
        assembly_ids.append(id)

        # get or create a child layer for label
        label_layer_index = serde.add_or_find_layer(
            "{}{}Label".format(serde.PANEL_LAYER_NAME, serde.SEPERATOR),
            doc,
            serde.LABEL_COLOR,
            parent,
        )

        # create a dict of all properties to serialize
        prop_dict = {
            NEIGHBOR_IDS_KEY: self.neighbor_ids,
            NEIGHBOR_ANGLES_KEY: self.neighbor_angles,
            INDEX_KEY: self.panel_index,
            "settings": self.settings,
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

    # endregion

    def transform(self, xform):

        # call transform on parent class
        super(Panel, self).transform(xform)

        # TODO: Transform everythign else
        self.outline.Transform(xform)
        rs.TransformObject(self.panel_id, xform)
