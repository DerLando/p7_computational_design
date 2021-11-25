import Rhino
import Rhino.Geometry as rg
from algorithms import close_polyline


class ClosedPolyline:
    POINT_NAMES = ["A", "B", "C", "D", "E", "F", "G", "H"]

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
        if self.__corner_dict is None:
            self.__corner_dict = {
                self.POINT_NAMES[index]: self.corners[index]
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
        for i in range(len(corners)):
            prev_vert = corners[(i - 1) % len(corners)]
            cur_vert = corners[i]
            next_vert = corners[(i + 1) % len(corners)]

            incoming = prev_vert - cur_vert
            outgoing = next_vert - cur_vert

            angles.append(rg.Vector3d.VectorAngle(incoming, outgoing, plane.ZAxis))

        return angles

    def get_segment(self, index):
        return rg.Line(
            self.corners[index], self.corners[(index + 1) % self.corner_count]
        )

    def center_point(self):
        return self.__inner.CenterPoint()

    def duplicate_inner(self):
        return self.__inner.Duplicate()

    def as_curve(self):
        return self.__inner.ToPolylineCurve()

    def as_inserted_range(self, index, points):
        new = self.duplicate_inner()
        new.InsertRange(index, points)
        return ClosedPolyline(new)
