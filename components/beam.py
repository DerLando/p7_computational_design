import logging
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import helpers.algorithms as algorithms
from helpers.geometry import ClosedPolyline
from components.component import Component
import math
from helpers import serde, keys

THICKNESS_KEY = "thickness"
NEIGHBOR_ANGLES_KEY = "neighbor_angles"
OUTLINES_LAYER_NAME = "{}{}Outlines".format(serde.BEAM_LAYER_NAME, serde.SEPERATOR)
VOLUME_LAYER_NAME = "{}{}Volume".format(serde.BEAM_LAYER_NAME, serde.SEPERATOR)
PROPERTIES_KEY = "PROPERTIES"


class Beam(Component):
    def __init__(self, identifier, plane, thickness, top_outline, neighbor_angles):
        """
        Initializes a new instance of the beam class

        Args:
            identifier (str): The identifier of the beam
            plane (Plane): The plane of the beam
            thickness (float): The material thickness of the beam
            top_outline (ClosedPolyline): The outline of the beam geometry, at it's top face. Needs to be closed and aligned in such a way, that the first segment of the outline is outwards facing.
            neighbor_angles (dict[str: float]): The angles of the beam planes to the beam sides at it's edges.
        """

        self._LABEL_HEIGHT = 0.025
        super(Beam, self).__init__(identifier, plane)

        # initialize fields from input
        self.thickness = thickness
        self.neighbor_angles = neighbor_angles

        self.outlines = {
            keys.TOP_OUTLINE_KEY: top_outline,
            keys.BOTTOM_OUTLINE_KEY: self.create_bottom_outline(
                plane, top_outline, self.neighbor_angles, thickness
            ),
        }
        self.outline_ids = {key: None for key in self.outlines}

        # create volume geometry from top and bottom outline
        self.volume_geometry = self.create_volume_geometry(
            self.outlines[keys.TOP_OUTLINE_KEY], self.outlines[keys.BOTTOM_OUTLINE_KEY]
        )
        self.volume_id = None

    @staticmethod
    def create_bottom_outline(plane, top_outline, angles, thickness):
        get_offset = (
            lambda angle, t: math.tan(math.pi - angle / 2.0) * t
            if (angle is not None)
            else 0.0
        )
        offset_amounts = {key: get_offset(angles[key], thickness) for key in angles}
        inner = top_outline.as_moved_edges(plane, offset_amounts).duplicate_inner()
        inner.Transform(rg.Transform.Translation(plane.ZAxis * -thickness))
        return ClosedPolyline(inner)

    def add_sawtooths_to_outlines(
        self,
        depth,
        width,
        top_guide,
        bottom_guide,
        tooth_count=None,
        flip_direction=False,
    ):
        """
        Adds sawtooths to the top and bottom outlines, using guides.

        Args:
            depth (float): The depth of the sawtooths
            width (float): The width of the sawtooths
            top_guide (Line): The linear guide at the top
            bottom_guide (Line): The linear guide at the bottom
        """

        # TODO: Check guide direction parallel to first segment
        if (
            top_guide.Direction.IsParallelTo(self.top_outline.get_segment(0).Direction)
            != 1
        ):
            top_guide.Flip()
            bottom_guide.Flip()

        # safety hardcoded for now
        safety = 0.1

        def divide_guide(guide, safety, width, tooth_count=None):
            width /= 2
            length = guide.Length
            if not tooth_count:
                tooth_count = (
                    int(math.floor((length - 2 * safety) / (2 * width))) * 2 + 1
                )
            total_tooth_width = (tooth_count) * width
            start_length = (length - total_tooth_width) / 2
            end_length = length - start_length

            # print(length, tooth_count, total_tooth_width, start_length, end_length)

            helper_guide = rg.Line(
                guide.PointAtLength(start_length), guide.PointAtLength(end_length)
            )
            divisions = tooth_count * 2
            division_params = [float(i) / divisions for i in range(divisions + 1)]
            division_points = [helper_guide.PointAt(t) for t in division_params]

            return (division_points, tooth_count)

        top_divisions, tooth_count = divide_guide(top_guide, safety, width, tooth_count)
        bottom_divisions, _ = divide_guide(bottom_guide, safety, width, tooth_count)

        trans_dir = top_guide.Direction
        trans_dir.Unitize()
        trans_dir.Rotate(math.pi / 2.0, self.plane.ZAxis)

        inner_trans = rg.Transform.Translation(trans_dir * depth)
        outer_trans = rg.Transform.Translation(trans_dir * -depth)

        if flip_direction:
            (inner_trans, outer_trans) = (outer_trans, inner_trans)
        inner = True

        for i in range(0, len(top_divisions), 1):
            if i % 2 == 1:
                if inner:
                    trans = inner_trans
                    inner = False
                else:
                    trans = outer_trans
                    inner = True

                top_divisions[i].Transform(trans)
                bottom_divisions[i].Transform(trans)

        # TODO: Fix this mess
        top_corners = self.top_outline.corner_dict
        bottom_corners = self.bottom_outline.corner_dict
        self.top_outline = self.top_outline.as_inserted_range(1, top_divisions)
        self.bottom_outline = self.bottom_outline.as_inserted_range(1, bottom_divisions)
        self.top_outline.corner_dict = top_corners
        self.bottom_outline.corner_dict = bottom_corners

        return tooth_count

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

        # extract properties from label object
        prop_dict = cls._deserialize_properties(label_obj, doc)
        for key, value in prop_dict.items():
            self.__setattr__(key, value)

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
        main_layer_index = serde.add_or_find_layer(serde.BEAM_LAYER_NAME, doc)
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

        # create a dict of all properties to serialize
        prop_dict = {
            THICKNESS_KEY: self.thickness,
            NEIGHBOR_ANGLES_KEY: self.neighbor_angles,
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


if __name__ == "__main__":

    identifier = "Test_BEAM_Serde"
    plane = rg.Plane.WorldXY
    top_outline = ClosedPolyline(rg.Rectangle3d(plane, 0.2, 1.0).ToPolyline())
    angles = {key: 0.1 for key in keys.edge_keys(4)}
    thickness = 0.05

    group = sc.doc.Groups.FindIndex(0)
    if group is None:
        beam = Beam(identifier, plane, thickness, top_outline, angles)
    else:
        beam = Beam.deserialize(0)

    beam.serialize()

    print(beam.thickness, beam.plane)
