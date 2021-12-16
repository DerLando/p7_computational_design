import logging
import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import helpers.algorithms as algorithms
from helpers.geometry import ClosedPolyline
from components.component import Component
import math
from helpers import serde, keys
from System import Guid

THICKNESS_KEY = "thickness"
NEIGHBOR_ANGLES_KEY = "neighbor_angles"
TOOTH_COUNT_KEY = "tooth_count"
TOOLHEAD_RADIUS_KEY = "toolhead_radius"


class Beam(Component):

    # region fields
    _LAYER_NAME = "Beam"
    _LABEL_HEIGHT = 25
    """The text height of the identifier label"""
    thickness = 0.0
    """The material thickness of the beam"""
    neighbor_angles = {key: 0.0 for key in keys.edge_keys(4)}
    """A dictionary of the angles towards neighbors at every beam edge"""
    outlines = {keys.TOP_OUTLINE_KEY: None, keys.BOTTOM_OUTLINE_KEY: None}
    """A dictionary of the top and bottom simple outlines"""
    outline_ids = {key: Guid.Empty for key in outlines}
    """A dictionary of the simple outline ids in the rhino doc"""
    volume_geometry = None
    """The geometry of the simple beam volume"""
    volume_id = Guid.Empty
    """The id of the simple geometry"""
    detailed_volume_geometry = None
    """The detailed geometry with all cutouts added"""
    detailed_volume_id = Guid.Empty
    """The id of the detailed geometry in the rhino doc"""
    tooth_count = -1

    # endregion

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

        super(Beam, self).__init__(identifier, plane)

        # initialize fields from input
        self.settings[THICKNESS_KEY] = thickness
        self.neighbor_angles = neighbor_angles

        self.outlines = {
            keys.TOP_OUTLINE_KEY: top_outline,
            keys.BOTTOM_OUTLINE_KEY: self.create_bottom_outline(
                plane, top_outline, self.neighbor_angles, thickness
            ),
        }

        # create volume geometry from top and bottom outline
        self.volume_geometry = self.create_volume_geometry(
            self.outlines[keys.TOP_OUTLINE_KEY], self.outlines[keys.BOTTOM_OUTLINE_KEY]
        )

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

    def add_sawtooths(
        self,
        depth,
        width,
        top_guide,
        bottom_guide,
        safety=0.1,
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
            top_guide.Direction.IsParallelTo(
                self.outlines[keys.TOP_OUTLINE_KEY].get_segment(0).Direction
            )
            != 1
        ):
            top_guide = rg.Line(top_guide.To, top_guide.From)
            bottom_guide = rg.Line(bottom_guide.To, bottom_guide.From)

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

        def create_detailed_outline(outline, divisions, toolhead_radius):
            outline_crv = (
                outline.as_inserted_range(1, divisions)
                .duplicate_inner()
                .ToPolylineCurve()
            )
            start_t = outline_crv.ClosestPoint(divisions[0])[1]
            end_t = outline_crv.ClosestPoint(divisions[-1])[1]
            split = outline_crv.Split([start_t, end_t])
            if split.Count != 2:
                logging.error("Failed to split sawtooth outline")
                return
            split = sorted(split, key=lambda x: x.GetLength())
            fillet = rg.Curve.CreateFilletCornersCurve(
                split[0], toolhead_radius, 0.001, 0.0
            )
            if fillet is None:
                logging.error("Failed to fillet sawtooth outline")
                return
            joined = rg.Curve.JoinCurves([fillet, split[1]])
            if joined.Count != 1:
                logging.error(
                    "Failed to join filleted und unfilleted sawtooth outlines"
                )
                return
            return joined[0]

        top_crv = create_detailed_outline(
            self.outlines[keys.TOP_OUTLINE_KEY],
            top_divisions,
            self.settings[TOOLHEAD_RADIUS_KEY],
        )
        bottom_crv = create_detailed_outline(
            self.outlines[keys.BOTTOM_OUTLINE_KEY],
            bottom_divisions,
            self.settings[TOOLHEAD_RADIUS_KEY],
        )

        volume = algorithms.loft_curves(top_crv, bottom_crv)

        self.detailed_volume_geometry = volume
        # sc.doc.Objects.AddBrep(self.detailed_volume)
        return tooth_count

    @staticmethod
    def create_volume_geometry(top_outline, bottom_outline):
        return algorithms.loft_outlines(top_outline, bottom_outline)

    @staticmethod
    def create_detailed_geometry(top_crv, bottom_crv):
        return algorithms.loft_curves(top_crv, bottom_crv)

    # region Read/Write

    @classmethod
    def deserialize(cls, group_index, doc=None):
        if doc is None:
            doc = sc.doc

        self = super(Beam, cls).deserialize(group_index, doc)

        # find out what identifier we are working with
        identifier = doc.Groups.GroupName(group_index)
        if identifier is None:
            return

        # get group members for given index
        members = doc.Groups.GroupMembers(group_index)

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

        # get the volumes
        volume_obj = serde.find_named_obj(members, "volume_geometry")
        if volume_obj is not None:
            self.volume_geometry = volume_obj.Geometry
            self.volume_id = volume_obj.Id

        detailed_volume_obj = serde.find_named_obj(members, "detailed_volume_geometry")
        if detailed_volume_obj is not None:
            self.detailed_volume_geometry = detailed_volume_obj.Geometry
            self.detailed_volume_id = detailed_volume_obj.Id

        return self

    def serialize(self, doc=None):
        if doc is None:
            doc = sc.doc

        # get or create main layer
        parent = self._main_layer(doc)

        # create an empty list for guids off all child objects
        assembly_ids = []

        # serialize label and settings
        id = super(Beam, self).serialize(doc)
        assembly_ids.append(id)

        # get or create a child layer for the outlines
        outline_layer_index = serde.add_or_find_layer(
            self._child_layer_name("outlines"),
            doc,
            serde.CURVE_COLOR,
            parent,
        )

        # serialize outlines
        for key in self.outlines:
            if self.outlines[key] is None:
                continue
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
            self._child_layer_name("volume"), doc, serde.VOLUME_COLOR, parent
        )

        # serialize volume geo
        if not self.volume_geometry is None:
            id = serde.serialize_geometry(
                self.volume_geometry,
                volume_layer_index,
                doc,
                name="volume_geometry",
                old_id=self.volume_id,
            )
            assembly_ids.append(id)

        # serialize detailed volume geo
        detailed_volume_layer_index = serde.add_or_find_layer(
            self._child_layer_name("detailed_volume"), doc, serde.DETAIL_COLOR, parent
        )
        if not self.detailed_volume_geometry is None:
            id = serde.serialize_geometry(
                self.detailed_volume_geometry,
                detailed_volume_layer_index,
                doc,
                "detailed_volume_geometry",
                self.detailed_volume_id,
            )
            assembly_ids.append(id)

        # add serialized geo as a group
        return serde.add_named_group(doc, assembly_ids, self.identifier)

    # endregion


if __name__ == "__main__":

    identifier = "Test_BEAM_Serde"
    plane = rg.Plane.WorldXY
    top_outline = ClosedPolyline(rg.Rectangle3d(plane, 200, 1000).ToPolyline())
    angles = {key: 0.1 for key in keys.edge_keys(4)}
    thickness = 50

    group = sc.doc.Groups.FindIndex(0)
    if group is None:
        beam = Beam(identifier, plane, thickness, top_outline, angles)
    else:
        beam = Beam.deserialize(0)

    beam.serialize()

    print(beam.thickness, beam.plane)
