import string

__EDGE_KEYS = [c for c in string.ascii_lowercase]
__CORNER_KEYS = [c for c in string.ascii_uppercase]

TOP_OUTLINE_KEY = "top_outline"
"""
Key for an outline that is at the top of the assembly
"""
BOTTOM_OUTLINE_KEY = "bottom_outline"
"""
Key for an outline that is at the bottom of the assembly
"""

BEAM_WIDTH_KEY = "beam_width"
BEAM_THICKNESS_KEY = "beam_thickness"


def create_settings(
    beam_max_width=0.06,
    beam_thickness=0.02,
    plate_thickness=0.025,
    dowel_radius=0.005,
    sawtooth_depth=0.015,
    sawtooth_width=0.04,
):
    return {}


def corner_keys(count):
    """
    Gets the first n corner keys

    Args:
        count (int): The number of corner_keys to return

    Returns:
        list[str]: The keys
    """

    return __CORNER_KEYS[:count]


def edge_keys(count):
    """
    Gets the first n edge keys

    Args:
        count (int): The number of edge keys to return

    Returns:
        list[str]: The keys
    """

    return __EDGE_KEYS[:count]


def corner_key_from_index(index):
    """
    Gets the corner key from the given index

    Args:
        index (int): The index of the corner,
        if the corner points are considered as an ordered list around their polygon

    Returns:
        [string]: The corner key
    """

    return __CORNER_KEYS[index]


def edge_key_from_index(index):
    """
    Gets the edge key from the given index

    Args:
        index (int): The index of the edge,
        if the edges are considered as an ordered list around their polygon

    Returns:
        [string]: The edge key
    """

    return __EDGE_KEYS[index]


def inflection_key(corner_key, direction):
    """
    Gets the inflection key for the given corner_key and the given direction

    Args:
        corner_key (string): The key of the corner
        direction (int): An index representing direction,
        0 for left, 1 for inner and 2 for right

    Returns
        string: The generated key
    """

    if direction < 0 or direction > 2:
        return None

    if direction == 0:
        dir_key = "left"
    if direction == 1:
        dir_key = "inner"
    if direction == 2:
        dir_key = "right"

    return "{}_{}".format(corner_key, dir_key)


def __offset_key(buffer, key, offset, wrapping_length):
    index = buffer.index(key)
    return buffer[(index + offset) % wrapping_length]


def offset_edge_key(key, offset, wrapping_length):
    """
    Gets the key with a specified offset from the given key

    Args:
        key (char): The key of the edge
        offset (int): The number of keys to skip (can be negative),
        wrapping_length (int): The index where to wrap around

    Returns:
        char: The key with the specified offset
    """

    return __offset_key(__EDGE_KEYS, key, offset, wrapping_length)


def corner_keys_from_edge_key(edge_key, wrapping_length):
    corner_indices = [
        __EDGE_KEYS.index(key)
        for key in [edge_key, offset_edge_key(edge_key, 1, wrapping_length)]
    ]

    return [__CORNER_KEYS[index] for index in corner_indices]


def panel_beam_identifier(panel_identifier, level, edge_key):
    return "{}_B{}{}".format(panel_identifier, level, edge_key)
