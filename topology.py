import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc


class MeshFace(object):
    """
    A single face of arbitrary vertex count.
    """

    def __init__(self, index, plane, outline):
        """
        Initialize a new MeshFace instance

        Args:
            index (int): The index of the face in the facebuffer it is extracted from
            plane (Plane): The plane of the face, centered at the face center, with normal in face-normal direction
            outline (Polyline): The face edges as a closed polyline
        """
        self.__index = index
        self.__plane = plane
        self.__outline = outline

    @property
    def index(self):
        """
        The index of the face in the facebuffer it is extracted from

        Returns:
            int: The index
        """
        return self.__index

    @property
    def plane(self):
        return self.__plane

    @property
    def outline(self):
        return self.__outline


class MeshTopology(object):
    """
    A topology helper class extracted from a Rhino.Geometry.Mesh instance,
    that allows for convenient neigbor queries, as well as generalizes
    over faces and ngons present in the base mesh.
    """

    def __init__(self, mesh):
        self.mesh = mesh

        # TODO: Extract topology

    def face(self, index):
        """
        Get the face at the given index from the internal face buffer

        Args:
            index (int): The index of the face

        Returns:
            MeshFace: The face
        """
        raise NotImplementedError()

    def faces(self):
        """
        Return all faces in the internal face buffer

        Returns:
            List[MeshFace]: The faces
        """
        raise NotImplementedError()

    def face_neighbors(self, face):
        """
        Get the faces that share an edge with the given face

        Args:
            face (MeshFace): The face to get the neighbors off

        Returns:
            List[MeshFace]: The neighboring faces
        """
        raise NotImplementedError()
