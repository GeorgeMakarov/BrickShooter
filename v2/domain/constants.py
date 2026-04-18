"""Board geometry and palette constants.

Kept as plain module-level values so they can be imported without constructing
anything. Values match v1 one-to-one so rules port without coordinate changes.
"""

FIELD_SIZE: int = 16                                    #!< field is FIELD_SIZE x FIELD_SIZE
LAUNCH_ZONE_DEPTH: int = 3                              #!< launcher rows/cols on each side
PLAY_AREA_START: int = LAUNCH_ZONE_DEPTH                #!< inclusive lower bound of play area
PLAY_AREA_END: int = FIELD_SIZE - LAUNCH_ZONE_DEPTH     #!< exclusive upper bound of play area

COLOR_NAMES: tuple[str, ...] = (
    "red", "blue", "purple", "green", "yellow",
    "brown", "cyan", "orange", "grey", "magenta",
)
