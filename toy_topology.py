import Rhino
import Rhino.Geometry as rg
from geometry import ClosedPolyline
import scriptcontext as sc
import clr

clr.AddReference("MeshTableLibrary.dll")
clr.AddReference("RhinoMeshTablesIO.dll")

import MeshTableLibrary as mtl
import RhinoMeshTablesIO as rmio
from MeshTableLibrary.Core.Indices import FaceIndex, VertexIndex, EdgeIndex, IndexPair


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

    def __str__(self):
        return "MeshFace: index={}".format(str(self.index))


class MeshTopology(object):
    """
    A topology helper class extracted from a Rhino.Geometry.Mesh instance,
    that allows for convenient neigbor queries, as well as generalizes
    over faces and ngons present in the base mesh.
    """

    def __init__(self, mesh):
        self.mesh = mesh

        extractor = rmio.RhinoMeshExtractor(mesh)
        self.__connectivity = mtl.Core.MeshElements.MeshConnectivity[rg.Mesh](extractor)
        self.__faces = [
            self.__create_face_from_index(self.__connectivity, index)
            for index in range(self.__connectivity.FaceCount)
        ]

        """
        'EdgeCount', 'Equals', 'FaceCount', 'GetAllVertexIndices', 'GetEdge', 'GetEdgeDirection', 'GetEdgeIndices',
        'GetEdgeMid', 'GetEdges', 'GetFace', 'GetFaceCentroid', 'GetFaceIndices', 'GetFaceNeighborIndices',
        'GetFacePair', 'GetFacePairs', 'GetFaces', 'GetHashCode', 'GetNormal', 'GetSharedEdgeIndex',
        'GetVertex', 'GetVertexIndices', 'GetVertexNeighborIndices', 'GetVertices', 'VertexCount'
        """

    @staticmethod
    def __create_face_from_index(connectivity, index):
        fi = FaceIndex(index)
        face = connectivity.GetFace(fi)
        verts = [connectivity.GetVertex(vi).Position for vi in face.VertexIndices]
        verts = [rg.Point3d(v.X, v.Y, v.Z) for v in verts]
        verts.append(verts[0])
        outline = rg.Polyline(verts)

        normal = connectivity.GetNormal(fi)
        normal = rg.Vector3d(normal.X, normal.Y, normal.Z)
        plane = rg.Plane(outline.CenterPoint(), normal)
        return MeshFace(index, plane, outline)

    def face(self, index):
        """
        Get the face at the given index from the internal face buffer

        Args:
            index (int): The index of the face

        Returns:
            MeshFace: The face
        """

        return self.__faces[index]

    def faces(self):
        """
        Return all faces in the internal face buffer

        Returns:
            List[MeshFace]: The faces
        """
        return self.__faces[::]

    def face_neighbors(self, index):
        """
        Get the faces that share an edge with the given face

        Args:
            face (MeshFace): The face to get the neighbors off

        Returns:
            List[MeshFace]: The neighboring faces
        """
        nis = self.__connectivity.GetFaceNeighborIndices(FaceIndex(index))
        return [self.__faces[index.Value] for index in nis]
