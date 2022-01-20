class GeometrySettings(object):
    """
    Full set of geometry settings, like width, heigh, radius of different building elements,
    used for geometry generation.
    """

    def __init__(
        self,
        beam_max_width,
        beam_thickness,
        plate_thickness,
        dowel_radius,
        sawtooth_depth,
        sawtooth_width,
    ):
        self.beam_max_width = beam_max_width
        self.beam_thickness = beam_thickness
        self.plate_thickness = plate_thickness
        self.dowel_radius = dowel_radius
        self.sawtooth_depth = sawtooth_depth
        self.sawtooth_width = sawtooth_width
