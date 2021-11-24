import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc


class Baker:
    BEAM_LAYER_NAME = "BEAMS"
    SEPERATOR = "_"

    def __init__(self, doc=None):
        if doc is None:
            doc = sc.doc.ActiveDoc

        self.__doc = doc

    def add_or_find_layer(self, name, color=None):
        layer = self.__doc.Layers.FindName(name)

        if layer is not None:
            return layer.Index

        layer = Rhino.DocObjects.Layer()
        layer.Name = name

        if color:
            layer.Color = color

        return self.__doc.Layers.Add(layer)

    def bake_beam(self, beam, detailed=False):
        """
        Bakes a beam to the rhino document.

        Args:
            beam (Beam): The beam to bake
            detailed (bool | optional): Bake additional debug information, Defaults to False

        Returns:
            int: The group id of the assembly in the rhino doc
        """

        beam_layer_id = self.add_or_find_layer(self.BEAM_LAYER_NAME)
        attrs = Rhino.DocObjects.ObjectAttributes()
        attrs.LayerIndex = beam_layer_id
        attrs.Name = beam.identifier

        assembly_ids = []
        assembly_ids.append(self.__doc.Objects.AddBrep(beam.volume_geometry, attrs))

        return self.__doc.Groups.Add(assembly_ids)
