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
        id = serde.serialize_geometry(
            self.label, label_layer_index, doc, self.identifier, self.label_id
        )
        assembly_ids.append(id)

        # add serialized geo as a group
        group = sc.doc.Groups.FindName(self.identifier)
        if group is None:
            # group with our identifier does not exist yet, add to table
            return sc.doc.Groups.Add(self.identifier, assembly_ids)

        else:
            sc.doc.Groups.AddToGroup(group.Index, assembly_ids)
            return group.Index


if __name__ == "__main__":

    identifier = "Test_Plate_Serde"
    plane = rg.Plane.WorldXY
    top_outline = ClosedPolyline(rg.Rectangle3d(plane, 1.0, 1.5).ToPolyline())
    angles = {key: 0.0 for key in keys.edge_keys(4)}
    thickness = 0.05

    plate = Plate(identifier, plane, top_outline, angles, thickness)

    plate.serialize()
