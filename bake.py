import Rhino
import Rhino.Geometry as rg
import scriptcontext as sc
import System.Drawing as draw


class Baker(object):
    BEAM_LAYER_NAME = "BEAMS"
    CASSETTE_LAYER_NAME = "CASSETTES"
    DOWEL_LAYER_NAME = "DOWELS"
    SEPERATOR = "_"
    CURVE_COLOR = draw.Color.FromArgb(230, 79, 225)
    DOT_COLOR = draw.Color.FromArgb(55, 230, 206)
    VOLUME_COLOR = draw.Color.FromArgb(230, 203, 101)

    def __init__(self, doc=None):
        if doc is None:
            doc = sc.doc.ActiveDoc

        self.__doc = doc

    def add_or_find_layer(self, name, color=None, parent=None):
        layer = self.__doc.Layers.FindName(name)

        if layer is not None:
            return layer.Index

        layer = Rhino.DocObjects.Layer()
        layer.Name = name

        if color:
            layer.Color = color

        if parent:
            layer.ParentLayerId = parent.Id

        return self.__doc.Layers.Add(layer)

    def bake_cassette(self, cassette, detailed=True):
        """
        Bakes a cassete to the rhino document.

        Args:
            cassette (Cassette): The cassette to bake
            detailed (bool | optional): Bake additional debug information, Defaults to False

        Returns:
            int: The group id of the assembly in the rhino doc
        """

        # get the beam layer and create attributes from it
        main_layer_id = self.add_or_find_layer(self.CASSETTE_LAYER_NAME)
        parent = self.__doc.Layers.FindIndex(main_layer_id)
        volume_layer_id = self.add_or_find_layer(
            "{}{}volume".format(self.CASSETTE_LAYER_NAME, self.SEPERATOR),
            self.VOLUME_COLOR,
            parent,
        )

        attrs = Rhino.DocObjects.ObjectAttributes()
        attrs.Name = cassette.identifier
        attrs.LayerIndex = volume_layer_id

        assembly_ids = []

        # create a layer for text dots
        dot_layer_name = "{}{}dot".format(self.CASSETTE_LAYER_NAME, self.SEPERATOR)
        dot_layer_id = self.add_or_find_layer(dot_layer_name, self.DOT_COLOR, parent)
        attrs.LayerIndex = dot_layer_id

        for key in cassette.beam_corner_points["TopUpper"]:
            assembly_ids.append(
                self.__doc.Objects.AddTextDot(
                    key, cassette.beam_corner_points["TopUpper"][key], attrs
                )
            )

        # TODO: should be inside of cassette group...
        for dowel in cassette.dowels:
            self.bake_dowel(dowel)

        return self.__doc.Groups.Add(assembly_ids)

    def bake_beam(self, beam, detailed=False):
        """
        Bakes a beam to the rhino document.

        Args:
            beam (Beam): The beam to bake
            detailed (bool | optional): Bake additional debug information, Defaults to False

        Returns:
            int: The group id of the assembly in the rhino doc
        """

        # get the beam layer and create attributes from it
        beam_layer_id = self.add_or_find_layer(self.BEAM_LAYER_NAME)
        parent = self.__doc.Layers.FindIndex(beam_layer_id)
        beam_volume_layer_id = self.add_or_find_layer(
            "{}{}volume".format(self.BEAM_LAYER_NAME, self.SEPERATOR),
            self.VOLUME_COLOR,
            parent,
        )
        attrs = Rhino.DocObjects.ObjectAttributes()
        attrs.Name = beam.identifier
        attrs.LayerIndex = beam_volume_layer_id

        # bake volume and add to assembly ids
        assembly_ids = []
        assembly_ids.append(self.__doc.Objects.AddBrep(beam.volume_geometry, attrs))

        # if we don't want detailed output, we can return early here
        if not detailed:
            return self.__doc.Groups.Add(assembly_ids)

        # create a layer for beam outlines
        outline_layer_name = "{}{}outline".format(self.BEAM_LAYER_NAME, self.SEPERATOR)
        beam_outline_layer_id = self.add_or_find_layer(
            outline_layer_name, self.CURVE_COLOR, parent
        )
        attrs.LayerIndex = beam_outline_layer_id

        # bake all outlines
        assembly_ids.append(
            self.__doc.Objects.AddCurve(beam.top_outline.as_curve(), attrs)
        )
        assembly_ids.append(
            self.__doc.Objects.AddCurve(beam.bottom_outline.as_curve(), attrs)
        )

        # create a layer for text dots
        dot_layer_name = "{}{}dot".format(self.BEAM_LAYER_NAME, self.SEPERATOR)
        beam_dot_layer_id = self.add_or_find_layer(
            dot_layer_name, self.DOT_COLOR, parent
        )
        attrs.LayerIndex = beam_dot_layer_id

        # bake all dots
        for key in beam.corners["bottom"]:
            assembly_ids.append(
                self.__doc.Objects.AddTextDot(key, beam.corners["bottom"][key], attrs)
            )
        for key in beam.corners["top"]:
            assembly_ids.append(
                self.__doc.Objects.AddTextDot(key, beam.corners["top"][key], attrs)
            )

        return self.__doc.Groups.Add(assembly_ids)

    def bake_dowel(self, dowel):
        # get the beam layer and create attributes from it
        main_layer_id = self.add_or_find_layer(self.DOWEL_LAYER_NAME)
        parent = self.__doc.Layers.FindIndex(main_layer_id)
        volume_layer_id = self.add_or_find_layer(
            "{}{}volume".format(self.DOWEL_LAYER_NAME, self.SEPERATOR),
            self.VOLUME_COLOR,
            parent,
        )

        attrs = Rhino.DocObjects.ObjectAttributes()
        attrs.Name = str(dowel)
        attrs.LayerIndex = volume_layer_id

        assembly_ids = [
            self.__doc.Objects.AddBrep(dowel.volume_geometry.ToBrep(True, True), attrs)
        ]

        # create a layer for beam outlines
        outline_layer_name = "{}{}outline".format(self.DOWEL_LAYER_NAME, self.SEPERATOR)
        outline_layer_id = self.add_or_find_layer(
            outline_layer_name, self.CURVE_COLOR, parent
        )
        attrs.LayerIndex = outline_layer_id

        assembly_ids.append(self.__doc.Objects.AddCircle(dowel.top_circle, attrs))
        assembly_ids.append(self.__doc.Objects.AddCircle(dowel.bottom_circle, attrs))

        return self.__doc.Groups.Add(assembly_ids)
