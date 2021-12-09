import logging
import Rhino
import Rhino.Geometry as rg
import math
from algorithms import close_polyline, offset_side, move_polyline_segment
from collections import deque
import keys


class ClosedPolyline:
    def __init__(self, pline):

        if not pline.IsClosed:
            pline = close_polyline(pline)

        self.__inner = pline
        self.corners = list(self.__inner.GetEnumerator())[:-1]

        self.__corner_dict = None

    @property
    def corner_count(self):
        return self.__inner.Count - 1

    @property
    def corner_dict(self):
        """
        A dictionary of all the corner points of the closed polyline,
        accessed like so:
        ```python
        pta = pline.corner_dict["A"]
        ```
        TODO: Re-write this with immutability in mind
        Returns:
            dict: A dictionary providing named access to the pline corners
        """

        # check of the corner dict isn't defined yet
        if self.__corner_dict is None:
            # define the corner doct from corner keys and set to private field
            self.__corner_dict = {
                keys.corner_key_from_index(index): self.corners[index]
                for index in range(self.corner_count)
            }

        return self.__corner_dict

    @corner_dict.setter
    def corner_dict(self, dict):
        self.__corner_dict = dict

    def get_angles(self, plane):
        """
        TODO: Fix me
        """
        corners = self.corners
        angles = []
        for i in range(self.corner_count):
            prev_vert = corners[(i - 1) % self.corner_count]
            cur_vert = corners[i]
            next_vert = corners[(i + 1) % self.corner_count]

            incoming = prev_vert - cur_vert
            outgoing = next_vert - cur_vert

            angles.append(rg.Vector3d.VectorAngle(incoming, outgoing, plane.ZAxis))

        return angles

    def as_moved_edge(self, plane, key, offset_amount):
        """
        TODO: Untested yet!
        """
        index = keys.edge_keys(self.corner_count).index(key)
        moved = move_polyline_segment(
            self.duplicate_inner(), plane, index, offset_amount
        )

        return ClosedPolyline(moved)

    def as_moved_edges(self, plane, offset_amounts):
        """
        Offsets each edge by the given amount

        Args:
            plane (Plane): The plane to offset in
            offset_amounts (dict): A dictionary of edge keys and offset values
        """
        # sort the offsets by their edge keys
        offsets = sorted(offset_amounts.items(), key=lambda x: x[0])

        # extract offset value from key/offset tuple
        offsets = [offset[1] for offset in offsets]

        # actually call into as_moved_segments with aligned offset list
        return self.as_moved_segments(plane, offsets)

    def as_moved_segments(self, plane, offset_amounts):
        """
        Create a copy of this `ClosedPolyline`, with all it's segments moved
        by the specified offset amounts. Notably, the moved segments get re-intersected
        which ensures the inner angles of the `ClosedPolyline` stay the same.

        Args:
            plane (Plane): The plane to offset in
            offset_amounts (list[int]): The offset amounts. Length must be the same as segments in the `ClosedPolyline`

        Returns:
            ClosedPolyline: A new `ClosedPolyline`, with all segments moved by the appropriate amount.
        """

        # Check if the offset amounts are in sync with the edges
        if len(offset_amounts) != self.corner_count:
            logging.error(
                "ClosedPolyline.as_moved_segments: Called with {} offset values, but only {} corners".format(
                    len(offset_amounts), self.corner_count
                )
            )
            return

        # offset all segments by the given amounts
        offset_segments = [
            offset_side(segment, plane, amount)
            for segment, amount in zip(self.get_segments(), offset_amounts)
        ]

        # create a buffer for the new corners
        new_corners = []

        # iterate over corners
        for index, _ in enumerate(self.corners):

            # extract incoming and outgoing segment for the current corner
            incoming = offset_segments[(index - 1) % self.corner_count]
            outgoing = offset_segments[index]

            # try to intersect incoming and outgoing
            success, ta, _ = rg.Intersect.Intersection.LineLine(
                incoming, outgoing, 0.01, False
            )

            # check if the intersection succeeded, log the error if it didn't
            if not success:
                logging.error(
                    "as_moved_segments: Failed to intersect segments {} and {}".format(
                        index - 1, index
                    )
                )

            # fill the buffer with the new corner
            new_corners.append(incoming.PointAt(ta))

        return ClosedPolyline(rg.Polyline(new_corners))

    def get_edge(self, edge_key):
        """
        Get the edge for the given edge key

        Args:
            edge_key (str): The key for the edge

        Returns:
            Line: The edge as a line
        """

        # get the corner keys for the given edge key
        corner_keys = keys.corner_keys_from_edge_key(edge_key, self.corner_count)

        # create and return a line from the corner keys
        return rg.Line(
            self.corner_dict[corner_keys[0]], self.corner_dict[corner_keys[1]]
        )

    def get_edges(self):
        """
        Get all edges in this `ClosedPolyline` grouped with their edge key

        Returns:
            generator[(str, Line)]: A generator over the edge key and the edge as a tuple
        """
        return (
            (keys.edge_key_from_index(index), self.get_segment(index))
            for index in xrange(self.corner_count)
        )

    def get_segment(self, index):
        """
        Get the segment at the given index

        Args:
            index (int): The index of the segment

        Returns:
            Line: The segment
        """
        return rg.Line(
            self.corners[index], self.corners[(index + 1) % self.corner_count]
        )

    def get_segments(self):
        """
        Get all polyline segments

        Returns:
            list[Line]: The segments as lines
        """
        return [self.get_segment(index) for index in range(self.corner_count)]

    def center_point(self):
        """
        Calculate the center point of the polyline

        Returns:
            Point3d: The center point
        """
        return self.__inner.CenterPoint()

    def duplicate_inner(self):
        """
        Give access to a duplicate of the inner polyline

        Returns:
            Polyline: The duplicated polyline
        """
        return self.__inner.Duplicate()

    def as_curve(self):
        """
        Creates a Rhino.Geometry.Curve from the inner polyline

        Returns:
            Rhino.Geometry.Curve: The created curve
        """
        return self.__inner.ToPolylineCurve()

    def as_inserted_range(self, index, points):
        """
        Creates a copy of the ClosedPolyline, with the points inserted from the given index

        Args:
            index (int): The index at which to insert the points
            points (list[Point3d]): The points to insert
        """
        new = self.duplicate_inner()
        new.InsertRange(index, points)
        return ClosedPolyline(new)
