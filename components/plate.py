import Rhino
import Rhino.Geometry as rg
from helpers.geometry import ClosedPolyline
import scriptcontext as sc
import math
import helpers.keys as keys
import logging
import helpers.serde as serde
import helpers.algorithms as algorithms
from components.component import Component
from System import Guid


class Plate(Component):
    # region fields

    _LABEL_HEIGHT = 0.1
    _LAYER_NAME = "Plate"
    outlines = {keys.TOP_OUTLINE_KEY: None, keys.BOTTOM_OUTLINE_KEY: None}
    outline_ids = {key: Guid.Empty for key in outlines}
    volume_geometry = None
    volume_id = Guid.Empty
    detailed_edges = None
    detailed_edge_ids = None
    detailed_volume_geometry = None
    detailed_volume_id = Guid.Empty

    # endregion

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

        # create volume geometry
        self.volume_geometry = self.create_volume_geometry(
            self.outlines[keys.TOP_OUTLINE_KEY], self.outlines[keys.BOTTOM_OUTLINE_KEY]
        )

        self.reset_detailed_edges()

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

    def create_and_set_detail_geometry(self):
        def join_outline(edge_dict):
            joined = rg.Curve.JoinCurves(edge_dict.values())
            if joined.Count != 1:
                logging.error("Failed to join detail outline")
                return
            return joined[0]

        top_detail_crv = join_outline(self.detailed_edges.get(keys.TOP_OUTLINE_KEY))
        bottom_detail_crv = join_outline(
            self.detailed_edges.get(keys.BOTTOM_OUTLINE_KEY)
        )

        self.detailed_volume_geometry = algorithms.loft_curves(
            top_detail_crv, bottom_detail_crv
        )

    def reset_detailed_edges(self):
        top_outline = self.outlines.get(keys.TOP_OUTLINE_KEY)
        bottom_outline = self.outlines.get(keys.BOTTOM_OUTLINE_KEY)
        self.detailed_edges = {
            keys.TOP_OUTLINE_KEY: {
                key: rg.LineCurve(top_outline.get_edge(key))
                for key in keys.edge_keys(top_outline.corner_count)
            },
            keys.BOTTOM_OUTLINE_KEY: {
                key: rg.LineCurve(bottom_outline.get_edge(key))
                for key in keys.edge_keys(top_outline.corner_count)
            },
        }

        self.detailed_edge_ids = {
            keys.TOP_OUTLINE_KEY: {
                key: Guid.Empty for key in self.detailed_edges[keys.TOP_OUTLINE_KEY]
            },
            keys.BOTTOM_OUTLINE_KEY: {
                key: Guid.Empty for key in self.detailed_edges[keys.BOTTOM_OUTLINE_KEY]
            },
        }

    def create_detailed_edge(
        self, edge_key, depth, width, safety, tooth_count, flip_direction
    ):
        """
        Adds sawtooths to the top and bottom outlines, using guides.

        Args:
            depth (float): The depth of the sawtooths
            width (float): The width of the sawtooths
            top_guide (Line): The linear guide at the top
            bottom_guide (Line): The linear guide at the bottom
        """

        def divide_guide(guide, safety, width, tooth_count):
            width /= 2
            length = guide.Length
            total_tooth_width = (tooth_count) * width
            start_length = (length - total_tooth_width) / 2
            end_length = length - start_length

            helper_guide = rg.Line(
                guide.PointAtLength(start_length), guide.PointAtLength(end_length)
            )
            divisions = tooth_count * 2
            division_params = [float(i) / divisions for i in range(divisions + 1)]
            division_points = [helper_guide.PointAt(t) for t in division_params]

            return division_points

        def transform_edge_divisions(edge, divisions, depth, flip_direction):
            trans_dir = edge.Direction
            trans_dir.Unitize()
            trans_dir.Rotate(math.pi / 2.0, self.plane.ZAxis)

            inner_trans = rg.Transform.Translation(trans_dir * depth)
            outer_trans = rg.Transform.Translation(trans_dir * -depth)

            if flip_direction:
                (inner_trans, outer_trans) = (outer_trans, inner_trans)
            inner = True

            for i in range(0, len(divisions), 1):
                if i % 2 == 1:
                    if inner:
                        trans = inner_trans
                        inner = False
                    else:
                        trans = outer_trans
                        inner = True

                    divisions[i].Transform(trans)

        def add_details_to_edge(
            edge, depth, width, safety, tooth_count, flip_direction, toolhead_radius
        ):
            divisions = divide_guide(edge, safety, width, tooth_count)
            transform_edge_divisions(edge, divisions, depth, flip_direction)

            edge_crv = rg.Polyline([edge.From, edge.To])
            edge_crv.InsertRange(1, divisions)
            edge_crv = edge_crv.ToPolylineCurve()

            start_t = edge_crv.ClosestPoint(divisions[0])[1]
            end_t = edge_crv.ClosestPoint(divisions[-1])[1]
            split = edge_crv.Split([start_t, end_t])
            if split.Count != 3:
                logging.error("Failed to split sawtooth outline")
                return
            split = sorted(split, key=lambda x: x.GetLength())
            fillet = rg.Curve.CreateFilletCornersCurve(
                split[-1], toolhead_radius, 0.001, 0.0
            )
            if fillet is None:
                logging.error("Failed to fillet sawtooth outline")
                return
            joined = rg.Curve.JoinCurves([fillet, split[0], split[1]])
            if joined.Count != 1:
                logging.error(
                    "Failed to join filleted und unfilleted sawtooth outlines"
                )
                return
            return joined[0]

        top_edge = self.outlines[keys.TOP_OUTLINE_KEY].get_edge(edge_key)
        bottom_edge = self.outlines[keys.BOTTOM_OUTLINE_KEY].get_edge(edge_key)

        top_edge_crv = add_details_to_edge(
            top_edge,
            depth,
            width,
            safety,
            tooth_count,
            flip_direction,
            # self.settings["toolhead_radius"],
            4,
        )
        bottom_edge_crv = add_details_to_edge(
            bottom_edge,
            depth,
            width,
            safety,
            tooth_count,
            flip_direction,
            # self.settings["toolhead_radius"],
            4,
        )

        self.detailed_edges[keys.TOP_OUTLINE_KEY][edge_key] = top_edge_crv
        self.detailed_edges[keys.BOTTOM_OUTLINE_KEY][edge_key] = bottom_edge_crv

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

        # deserialize label and settings
        self = super(Plate, cls).deserialize(group_index, doc)

        # get the outlines
        outlines = [
            member
            for member in members
            if member.ObjectType == Rhino.DocObjects.ObjectType.Curve
            and (
                member.Name == keys.TOP_OUTLINE_KEY
                or member.Name == keys.BOTTOM_OUTLINE_KEY
            )
        ]

        self.outlines = {
            outline.Name: ClosedPolyline(outline.Geometry.ToPolyline())
            for outline in outlines
        }
        self.outline_ids = {outline.Name: outline.Id for outline in outlines}

        detailed_edges = [
            member
            for member in members
            if member.ObjectType == Rhino.DocObjects.ObjectType.Curve
            and (
                member.Name != keys.BOTTOM_OUTLINE_KEY
                and member.Name != keys.TOP_OUTLINE_KEY
            )
        ]
        if detailed_edges:
            self.detailed_edges = {
                keys.TOP_OUTLINE_KEY: {},
                keys.BOTTOM_OUTLINE_KEY: {},
            }
            self.detailed_edge_ids = {key: {} for key in self.detailed_edges}
            for edge in detailed_edges:
                level_key, edge_key = edge.Name.split("|")
                self.detailed_edges[level_key][edge_key] = edge.Geometry
                self.detailed_edge_ids[level_key][edge_key] = edge.Id

        volume_obj = serde.find_named_obj(members, "volume_geometry")
        if volume_obj is not None:
            self.volume_geometry = volume_obj.Geometry
            self.volume_id = volume_obj.Id

        detailed_volume_obj = serde.find_named_obj(members, "detailed_volume_geometry")
        if detailed_volume_obj is not None:
            self.detailed_volume_geometry = detailed_volume_obj.Geometry
            self.volume_id = detailed_volume_obj.Id

        return self

    def serialize(self, doc=None):
        if doc is None:
            doc = sc.doc

        # get or create main layer
        parent = self._main_layer(doc)

        # create an empty list for guids off all child objects
        assembly_ids = []

        # serialize label and settings
        assembly_ids.append(super(Plate, self).serialize(doc))

        # get or create a child layer for the outlines
        outline_layer_index = serde.add_or_find_layer(
            self._child_layer_name("outlines"),
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

        detailed_edges_layer_index = serde.add_or_find_layer(
            self._child_layer_name("detailed_edges"), doc, serde.DETAIL_COLOR, parent
        )

        for level_key in self.detailed_edges:
            edges = self.detailed_edges.get(level_key)
            if not edges:
                continue
            for edge_key in edges:
                if edges[edge_key] is None:
                    continue
                id = serde.serialize_geometry(
                    edges[edge_key],
                    detailed_edges_layer_index,
                    doc,
                    "{}|{}".format(level_key, edge_key),
                    self.detailed_edge_ids[level_key][edge_key],
                )
                assembly_ids.append(id)

        # get or create a child layer for the volume geo
        volume_layer_index = serde.add_or_find_layer(
            self._child_layer_name("volume"), doc, serde.VOLUME_COLOR, parent
        )

        # serialize volume geo
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
            self._child_layer_name("detailed_volume"), doc, serde.VOLUME_COLOR, parent
        )
        if self.detailed_volume_geometry:
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

    def extract_geometry(self):
        geo = []

        if self.volume_geometry:
            geo.append(self.volume_geometry)

        if self.detailed_volume_geometry:
            geo.append(self.detailed_volume_geometry)

        if self.outlines:
            for outline in self.outlines.values():
                geo.append(outline)

        return

    def transform(self, xform):

        # call transform on parent class
        super(Plate, self).transform(xform)

        # TODO: Transform everythign else
        for geo in self.extract_geometry():
            geo.Transform(xform)


if __name__ == "__main__":

    identifier = "Test_Plate_Serde"
    plane = rg.Plane.WorldXY
    top_outline = ClosedPolyline(rg.Rectangle3d(plane, 1000, 1500).ToPolyline())
    angles = {key: 0.0 for key in keys.edge_keys(4)}
    thickness = 50

    plate = Plate(identifier, plane, top_outline, angles, thickness)
    idx = plate.serialize()

    plate.settings["test"] = 12
    plate.serialize()

    test = Plate.deserialize(idx)
    print(test.settings)
