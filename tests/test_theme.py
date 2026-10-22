from __future__ import annotations

from src.ui.theme import BASE_PALETTE, get_palette


def test_light_palette_uses_coordinated_light_surfaces() -> None:
    palette = get_palette(dark=False)

    assert palette["bg_1"] == "#FFFFFF"
    assert palette["accent_dim"] != BASE_PALETTE["accent_dim"]
    assert palette["btn_primary"] != BASE_PALETTE["btn_primary"]
    assert palette["btn_secondary"] == palette["bg_2"]
    assert palette["btn_text"] == "#FFFFFF"


def test_light_palette_defines_every_base_token() -> None:
    palette = get_palette(dark=False)

    assert palette.keys() == BASE_PALETTE.keys()
