import Rhino
import scriptcontext
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs

surface_planes = []
surface_outline = []
surface_neighbours = []


def getedges(surface):

    # center = rs.SurfaceAreaCentroid((surface))[0]
    # param = rs.SurfaceClosestPoint(surface, center)
    # normal = rs.SurfaceNormal(surface, param)
    # plane = rs.PlaneFromNormal(center, normal)
    outline = rs.DuplicateEdgeCurves(surface)

    return outline


def dictionaries(surfaces):
    Topology_Cassetes = {}
    for d in range(len(surfaces)):

        Topology_Cassetes[d] = getedges(surfaces[d])

    return Topology_Cassetes


def neighbours(surfaces_dict):
    Neighbours = {}
    for surface_key in surfaces_dict:
        surface_neighbours = {}
        for edge_index in range(len(surfaces_dict[surface_key])):
            for other_surface_key in surfaces_dict:
                if surface_key == other_surface_key:
                    continue
                for other_edge_index in range(len(surfaces_dict[other_surface_key])):
                    surface_edge = rs.coercecurve(
                        surfaces_dict[surface_key][edge_index]
                    )
                    other_edge = rs.coercecurve(
                        surfaces_dict[other_surface_key][other_edge_index]
                    )
                    Equality = rg.GeometryBase.GeometryEquals(surface_edge, other_edge)
                    if Equality == True:
                        surface_neighbours[edge_index] = other_surface_key

        Neighbours[surface_key] = surface_neighbours
    # print(Neighbours)
    return Neighbours


def addtext(surfaces_dict, surfaces_list):

    for i in surfaces_dict:
        point = rs.AddPoint(rs.SurfaceAreaCentroid(surfaces_list[i])[0])
        text = rs.AddTextDot(surfaces_dict.keys()[i], point)
    return text


def usertext(neighbours_dict, surfaces_dict, surfaces_list):
    panel_index = "Panel_Index"
    for index in range(len(surfaces_list)):
        rs.SetUserText(surfaces_list[index], panel_index, str(index))

    for surface_index in range(len(surfaces_dict)):
        for neighbour_index in range(len(neighbours_dict[surface_index])):
            print(neighbours_dict[surface_index].keys()[neighbour_index])
            edge_neighbour = (
                "Edge_"
                + str(neighbours_dict[surface_index].keys()[neighbour_index])
                + "_Neighbouring"
            )
            # text = rs.SetUserText(surfaces_dict[surface_index][neighbours_dict[surface_index].keys()[neighbour_index]], edge_neighbour, str(neighbours_dict[surface_index][neighbours_dic[surface_index].keys()[neighbour_index]]))
            text = rs.SetUserText(
                surfaces_list[surface_index],
                edge_neighbour,
                str(
                    neighbours_dict[surface_index][
                        neighbours_dic[surface_index].keys()[neighbour_index]
                    ]
                ),
            )
            print(text)


if __name__ == "__main__":

    surfaces = rs.GetObjects("Please select your cassetes", 0, True, False, True)
    surfaces_dic = dictionaries(surfaces)
    neighbours_dic = neighbours(surfaces_dic)
    # print(surfaces_dic)
    print(neighbours_dic)

    neighbours(surfaces_dic)
    addtext(surfaces_dic, surfaces)
    usertext(neighbours_dic, surfaces_dic, surfaces)
