"""Board geometry constants. Locked to v1 values so rules port one-to-one."""

from domain import constants as C


def test_field_is_16x16():
    assert C.FIELD_SIZE == 16


def test_launch_zone_depth_is_three():
    assert C.LAUNCH_ZONE_DEPTH == 3


def test_play_area_derived_from_launch_zone_depth():
    assert C.PLAY_AREA_START == C.LAUNCH_ZONE_DEPTH
    assert C.PLAY_AREA_END == C.FIELD_SIZE - C.LAUNCH_ZONE_DEPTH


def test_play_area_is_10_cells_wide():
    assert C.PLAY_AREA_END - C.PLAY_AREA_START == 10


def test_color_names_has_ten_entries():
    assert len(C.COLOR_NAMES) == 10
