import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import math
import logging
import string

"""
Module that exposes general-purpose geometric algorithms,
missing in Rhinocommon and rhinoscriptsyntax
"""


def char_range(count, lower_case=True):
    """
    Returns the first n characters of the alphabet, either in upper or lowercase

    Args:
        count (int): The number of characters to generate
        lower_case (bool, optional): Letter should be lowercase, defaults to True

    Returns:
        generator[char]: A generator over the generated chars
    """
    if lower_case:
        return (string.ascii_lowercase[i] for i in xrange(count))
    else:
        return (string.ascii_uppercase[i] for i in xrange(count))


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

    # TODO: Replace with angle calculated points, more numerically stable
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


def offset_pline_wards(pline, plane, amount, inwards=True):
    """
    Offset the given closed polyline either inwards or outwards

    Args:
        pline (Polyline): The polyline to offset
        plane (Plane); The plane to offset on
        amount (float): The distance by which to offset
        inwards (bool, optional): True if onwards, False if outwards. Defaults to inwards

    Returns:
        Polyline: The offset polyline
    """

    # set a tolerance of 1 millimeter
    tolerance = 0.001

    # offset pline twice
    a = pline.ToPolylineCurve().Offset(
        plane, amount, tolerance, rg.CurveOffsetCornerStyle.Sharp
    )
    b = pline.ToPolylineCurve().Offset(
        plane, -amount, tolerance, rg.CurveOffsetCornerStyle.Sharp
    )

    a = a[0]
    b = b[0]

    # check which pline is offset to the wanted side
    if inwards and a.GetLength() > b.GetLength():
        return b.ToPolyline()

    if not inwards and a.GetLength() > b.GetLength():
        return a.ToPolyline()


def offset_side(line, plane, amount, left=True):
    """
    Offsets the given line to the given side

    Args:
        line (Line): The line to offset
        plane (Plane): The reference plane to determine the side
        amount (float): The amount by which to offset by
        left (bool, optional): Should we offset to the left?
    """

    # create a direction vector to offset to from line direction and plane normal
    dir_vec = rg.Vector3d.CrossProduct(line.Direction, plane.Normal)
    dir_vec.Unitize()
    dir_vec *= amount

    # if right side is wanted, invert the direction vector
    if not left:
        dir_vec *= -1

    # duplicate the line and transform it by the direction vector
    result = rg.Line(line.From, line.To)
    result.Transform(rg.Transform.Translation(dir_vec))

    return result


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

    # get curve orientation
    orientation = pline.ToPolylineCurve().ClosedCurveOrientation(plane)

    # compare to target orientation
    if orientation == rg.CurveOrientation.Clockwise and not clockwise:
        pline.Reverse()

    if orientation == rg.CurveOrientation.CounterClockwise and clockwise:
        pline.Reverse()


def point_polar(plane, radius, angle):
    """
    Evaluate a point in polar coordinates on the given plane

    Args:
        plane (Plane): The base plane to evaluate on
        radius (float): The distance from the plane origin
        angle (float): The rotation angle around plane origin in radians

    Returns:
        Point3d: The evaluated point, in carthesian coordinates
    """

    # evaluate a polar point on world.XY
    point = rg.Point3d(math.cos(angle) * radius, math.sin(angle) * radius, 0.0)

    # transform point to given plane
    transform = rg.Transform.PlaneToPlane(rg.Plane.WorldXY, plane)
    point.Transform(transform)

    return point


def are_lines_equal(a, b):
    """
    Tets if two lines span an equal space.
    If one line is the same as the other, but flipped,
    this will also return True

    Args:
        a (Line): The first line
        b (Line): The second line

    Returns:
        bool: True if equal, False if not
    """
    # set a tolerance of 1cm
    tol = 0.01

    # check if the lines match point-wise
    if a.From.EpsilonEquals(b.From, tol) and a.To.EpsilonEquals(b.To, tol):
        return True

    # flip line one and test again
    if a.To.EpsilonEquals(b.From, tol) and a.From.EpsilonEquals(b.To, tol):
        return True

    # if both checks failed, we can return False here
    return False


def loft_curves(top_crv, bottom_crv):
    # loft between top and bottom
    results = rg.Brep.CreateFromLoft(
        [top_crv, bottom_crv],
        rg.Point3d.Unset,
        rg.Point3d.Unset,
        rg.LoftType.Straight,
        False,
    )

    # check if loft succeeded
    if results is None:
        logging.error("algorithms.loft_outlines: Loft result is None!")
        return

    # test if we got a valid result, meaning only one brep in the returned buffer
    if results.Count != 1:
        logging.error("algorithms.loft_outlines: Loft result is multiple breps!")
        return

    # cap result
    capped = results[0].CapPlanarHoles(sc.doc.ModelAbsoluteTolerance)
    if capped is None:
        logging.error("algorithms.loft_outlines: Failed to cap loft!")
        return

    return capped


def loft_outlines(top_outline, bottom_outline):
    return loft_curves(top_outline.as_curve(), bottom_outline.as_curve())


def draft_angle_offset(outline, plane, angles, distance):
    """
    Create an offset `ClosedPolyline`, that is offset
    by the draft angles given together with the distance

    Args:
        outline (ClosedPolyline): The outline to offset
        plane (Plane): The plane in which to perform the offset in.
        angles (dict[str: float]): The angles for the outline edges
        distance (float): The distance by which to move the outline in negative plane Z direction

    Returns:
        Polyline: The resulting offset
    """

    # create a lambda function to calculate offset values from angle and thickness
    get_offset = lambda angle, t: math.tan(math.pi - angle / 2.0) * t

    # calculate the individual offset amounts and store in an edge dict
    offset_amounts = {key: get_offset(angles[key], distance) for key in angles}

    # move the segments of the outline by the offset amounts
    inner = outline.as_moved_edges(plane, offset_amounts).duplicate_inner()

    # transform the result in negative plane z direction
    inner.Transform(rg.Transform.Translation(plane.ZAxis * -distance))

    return inner
