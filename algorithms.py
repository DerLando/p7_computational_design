import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import math
import logging

"""
Module that exposes general-purpose geometric algorithms,
missing in Rhinocommon and rhinoscriptsyntax
"""


def close_polyline(pline):
    """
    Closes the given polyline.
    If the polyline is already closed, this does nothing.

    Args:
        pline (Polyline): The polyline to close

    Returns:
        Polyline: The closed polyline
    """

    # if the polyline is already closed, there is nothing we can do
    if pline.IsClosed:
        return pline

    # add the first point of the polyline again as the last point, this way thino considers this polyline closed
    pline.Add(pline[0])

    return pline


def move_polyline_segment(pline, plane, segment_index, amount):
    """
    Moves a segment of a polyline inwards, by the given amount.
    This will re-intersect with the adjacent segments, so no angles of the polyline will change.

    Args:
        pline (Polyline): The Polyline to move the Segment of.
        plane (Plane): The plane to move on, important to find the inside direction.
        segment_index (int): The index of the segment to move.
        amount (float): The amount to move by.

    Returns:
        Polyline: A new polyline with the moved segment.
    """

    # Duplicate all segments of the polyline
    segments = [crv.Line for crv in pline.ToPolylineCurve().DuplicateSegments()]

    # Get the segment that should move
    moved = segments[segment_index]

    # Calculate the translation vector
    translation = moved.Direction
    if (
        pline.ToPolylineCurve().ClosedCurveOrientation(plane)
        != rg.CurveOrientation.Clockwise
    ):
        translation.Rotate(math.pi / 2.0, plane.ZAxis)
    else:
        translation.Rotate(-math.pi / 2.0, plane.ZAxis)
    translation.Unitize()
    translation *= amount

    # move the segment
    moved.Transform(rg.Transform.Translation(translation))

    # get the segment neighbors
    prev = segments[(segment_index - 1) % segments.Count]
    next = segments[(segment_index + 1) % segments.Count]

    # intersect moved segment with prev and next segments
    first_success, t_prev, _ = rg.Intersect.Intersection.LineLine(
        prev, moved, sc.doc.ModelAbsoluteTolerance, False
    )
    second_success, t_next, _ = rg.Intersect.Intersection.LineLine(
        next, moved, sc.doc.ModelAbsoluteTolerance, False
    )

    # check for valid intersection results
    if not (first_success and second_success):
        logging.error("move_polyline_segment: Failed to intersect!")
        return

    # build a new polyline from the segments
    pline = rg.Polyline()
    for i in range(len(segments)):
        if i == segment_index:
            pline.Add(prev.PointAt(t_prev))
        elif i == segment_index + 1:
            pline.Add(next.PointAt(t_next))
        else:
            pline.Add(segments[i].From)

    return close_polyline(pline)


def polyline_to_point_dict(pline):
    """
    Created a dictionary that allows pline vertex access by names.
    The first vertices are named starting at 'A'.
    If the polyline is closed, the last point will be ignored.

    Args:
        pline (Polyline): The polyline to create the vertex dict for.

    Returns:
        dict: The dictionary of named vertices
    """

    # initial point dict names, we don't expect polylines to have more than 8 corners.
    point_names = ["A", "B", "C", "D", "E", "F", "G", "H"]

    # check to see if we have a valid corner count
    if pline.Count > len(point_names) - 1:
        logging.error("polyline_to_point_dict: more vertices than letters!")
        return

    # extract pline length and normalize for closed / open
    length = pline.Count
    if pline.IsClosed:
        length -= 1

    # populate points dict
    points = {}
    for i in range(length):
        points[point_names[i]] = pline[i]

    return points

    def offset_pline_wards(pline, amount, inwards=True):
        """
        Offset the given closed polyline either inwards or outwards

        Args:
            pline (Polyline): The polyline to offset
            amount (float): The distance by which to offset
            inwards (bool, optional): True if onwards, False if outwards. Defaults to inwards

        Returns:
            Polyline: The offset polyline
        """

        raise NotImplementedError()

    def ensure_winding_order(pline, plane, clockwise=False):
        """
        Ensure the winding order of the given polyline is equal to the given orientation,
        either Clockwise, or counter-clockwise. The given polyline is changed to match the
        required winding order

        Args:
            pline (Polyline): The polyline to ensure the winding order of
            plane (Plane): The plane to compare the winding order to
            clockwise (bool, optional): Either clockwise or counter-clockwise, Defaults to counter-clockwise
        """

        raise NotImplementedError()
