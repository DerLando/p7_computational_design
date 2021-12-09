import Rhino
import Rhino.Geometry as rg
from geometry import ClosedPolyline
import scriptcontext as sc
import math
import keys
import logging
import serde
import algorithms
from component import Component

OUTLINES_LAYER_NAME = "{}{}Outlines".format(serde.PLATE_LAYER_NAME, serde.SEPERATOR)
VOLUME_LAYER_NAME = "{}{}Volume".format(serde.PLATE_LAYER_NAME, serde.SEPERATOR)
LABEL_LAYER_NAME = "{}{}Label".format(serde.PLATE_LAYER_NAME, serde.SEPERATOR)


class Plate(Component):
    def __init__(self, identifier, plane, top_outline, angles, thickness):

        self._LABEL_HEIGHT = 0.1

        # call super constructor
        super(Plate, self).__init__(identifier, plane)

        # create outlines dict
        self.outlines = {
            keys.TOP_OUTLINE_KEY: top_outline,
            keys.BOTTOM_OUTLINE_KEY: self.create_bottom_outline(
                plane, top_outline, thickness, angles
            ),
        }
        self.outline_ids = {key: None for key in self.outlines}

        # create volume geometry
        self.volume_geometry = self.create_volume_geometry(
            self.outlines[keys.TOP_OUTLINE_KEY], self.outlines[keys.BOTTOM_OUTLINE_KEY]
        )
        self.volume_id = None

    @staticmethod
    def create_bottom_outline(plane, top_outline, thickness, angles):
        get_offset = lambda angle, t: math.tan(math.pi - angle / 2.0) * t
        offset_amounts = {key: get_offset(angles[key], thickness) for key in angles}
        inner = top_outline.as_moved_edges(plane, offset_amounts).duplicate_inner()
        inner.Transform(rg.Transform.Translation(plane.ZAxis * -thickness))
        return ClosedPolyline(inner)

    @staticmethod
    def create_volume_geometry(top_outline, bottom_outline):
        return algorithms.loft_outlines(top_outline, bottom_outline)

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

        # get the outlines
        outlines = [
            member
            for member in members
            if member.ObjectType == Rhino.DocObjects.ObjectType.Curve
        ]
        self.outlines = {
            outline.Name: ClosedPolyline(outline.Geometry.ToPolyline())
            for outline in outlines
        }
        self.outline_ids = {outline.Name: outline.Id for outline in outlines}

        # get the volume
        volume_obj = [
            member
            for member in members
            if member.ObjectType == Rhino.DocObjects.ObjectType.Brep
        ][0]
        self.volume_geometry = volume_obj.Geometry
        self.volume_id = volume_obj.Id

        return self

    def serialize(self, doc=None):
        if doc is None:
            doc = sc.doc

        # get or create main layer
        main_layer_index = serde.add_or_find_layer(serde.PLATE_LAYER_NAME, doc)
        parent = doc.Layers.FindIndex(main_layer_index)

        # create an empty list for guids off all child objects
        assembly_ids = []

        # get or create a child layer for the outlines
        outline_layer_index = serde.add_or_find_layer(
            OUTLINES_LAYER_NAME,
            doc,
            serde.CURVE_COLOR,
            parent,
        )

        # serialize outlines
        for key in self.outlines:
            id = serde.serialize_geometry(
                self.outlines[key].as_curve(),
                outline_layer_index,
                doc,
                key,
                self.outline_ids[key],
            )
            assembly_ids.append(id)

        # get or create a child layer for the volume geo
        volume_layer_index = serde.add_or_find_layer(
            VOLUME_LAYER_NAME, doc, serde.VOLUME_COLOR, parent
        )

        # serialize volume geo
        id = serde.serialize_geometry(
            self.volume_geometry, volume_layer_index, doc, old_id=self.volume_id
        )
        assembly_ids.append(id)

        # get or create a child layer for label
        label_layer_index = serde.add_or_find_layer(
            "{}{}Label".format(serde.PLATE_LAYER_NAME, serde.SEPERATOR),
            doc,
            serde.LABEL_COLOR,
            parent,
        )

        # serialize label
        id = self._serialize_label(label_layer_index, doc)
        assembly_ids.append(id)

        # add serialized geo as a group
        group = sc.doc.Groups.FindName(self.identifier)
        if group is None:
            # group with our identifier does not exist yet, add to table
            return sc.doc.Groups.Add(self.identifier, assembly_ids)

        else:
            # members_ids = [member.Id for member in doc.Groups.GroupMembers(group.Index)]
            # assembly_ids = [id for id in assembly_ids if id not in members_ids]
            sc.doc.Groups.AddToGroup(group.Index, assembly_ids)
            return group.Index


if __name__ == "__main__":

    identifier = "Test_Plate_Serde"
    plane = rg.Plane.WorldXY
    top_outline = ClosedPolyline(rg.Rectangle3d(plane, 1.0, 1.5).ToPolyline())
    angles = {key: 0.0 for key in keys.edge_keys(4)}
    thickness = 0.05

    group = sc.doc.Groups.FindIndex(0)
    if group is None:
        plate = Plate(identifier, plane, top_outline, angles, thickness)
    else:
        plate = Plate.deserialize(0)

    idx = plate.serialize()

    print(idx, plate.label_id)
