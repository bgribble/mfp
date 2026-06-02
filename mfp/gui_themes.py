"""
definitions of default color themes.

New themes can be added to your ~/.mfprc.py using this pattern
"""

dusk_purp = (0x49, 0x35, 0x48, 0xff)
dusk_blue = (0x4e, 0x4b, 0x6d, 0xff)
dusk_grue = (0x6a, 0x8d, 0x92, 0xff)
dusk_teal = (0x80, 0xb1, 0x92, 0xff)
dusk_green = (0xa1, 0xe8, 0x87, 0xff)
dusk_gold = (0xf1, 0xd3, 0x02, 0xff)
dusk_red = (0xc1, 0x29, 0x2e, 0xff)

dusk_gray_1 = (0xd3, 0xd2, 0xcf, 0xff)
dusk_gray_2 = (0xbc, 0xb9, 0xb5, 0xff)
dusk_gray_3 = (0x43, 0x41, 0x3d, 0xff)
dusk_gray_4 = (0x21, 0x20, 0x1e, 0xff)

def trn(color, transparency):
    return (*color[:3], transparency)

def brt(color, scale):
    return (*(c * scale for c in color[:3]), color[3])

theme_dusk = {
    "imgui_theme": "light",
    "colors": {
        'default-canvas-color-selected': brt(dusk_gray_1, 1.1),
        'default-canvas-color': brt(dusk_gray_1, 1.0),
        'default-grid-color': trn(dusk_grue, 0x60),
        'default-operate-grid-color': trn(dusk_grue, 0x10),
        'default-stroke-color': dusk_gray_4,
        'default-stroke-color-selected': dusk_teal,
        'default-stroke-color-hover': trn(dusk_teal, 0x90),
        'default-stroke-color-debug': (0x3f, 0xbf, 0x7f, 0xff),
        'default-selbox-stroke-color': dusk_blue,
        'default-selbox-fill-color': trn(dusk_teal, 0x50),
        'default-link-color': dusk_gray_3,
        'default-link-color-dashed': trn(dusk_grue, 0xf0),
        'default-link-color-selected': brt(dusk_grue, 0.9),
        'default-link-color-snoop': dusk_green,
        'default-fill-color': brt(dusk_gray_3, 1.5),
        'default-fill-color-selected': brt(dusk_gray_3, 1.9),
        'default-fill-color-debug': (0x2f, 0x4f, 0x2f, 0xff),
        'default-alt-fill-color': dusk_grue,
        'default-text-color': brt(dusk_gray_1, 1.2),
        'default-text-color-selected': brt(dusk_gray_1, 1.2),
        'default-text-cursor-color': trn(dusk_grue, 0x70),
        'default-alt-text-color': dusk_gray_2,
        'default-reverse-text-color': dusk_gray_3,
        'default-text-element-text-color': dusk_gray_3,
        'default-text-element-text-color-selected': brt(dusk_gray_3, 1.5),
        'default-match-text-color': (0xaa, 0xff, 0xaa, 0xff),
        'default-emph-text-color': dusk_gold,
        'default-edit-badge-color': (0x74, 0x4b, 0x94, 0xff),
        'default-learn-badge-color': (0x19, 0xff, 0x90, 0xff),
        'default-error-badge-color': (0xb7, 0x21, 0x21, 0xff),
        'default-play-badge-color': dusk_grue,
        'default-record-badge-color': dusk_red,
        'default-data-color-0': (0x88, 0x52, 0x7f, 0xff),
        'default-data-color-1': (0x4c, 0x60, 0x85, 0xff),
        'default-data-color-2': (0x39, 0xa0, 0xed, 0xff),
        'default-data-color-3': (0x36, 0xf1, 0xcd, 0xff),
        'default-data-color-4': (0x13, 0xc4, 0xa3, 0xff),
        'default-data-color-5': (0xd3, 0x61, 0x35, 0xff),
        'default-cursor-color': trn(dusk_gray_1, 0x30),
        'transparent': (0x00, 0x00, 0x00, 0x00),
        'meter-color-rms': dusk_teal,
        'meter-color-peak': dusk_gold,
        'default-button-color': dusk_gray_1,
        'default-button-color-highlight': brt(dusk_gray_1, 1.2),
        'default-button-color-clicked': brt(dusk_gray_1, 0.9),
        'play-button-color': dusk_teal,
        'play-button-color-highlight': brt(dusk_teal, 1.2),
        'play-button-color-clicked': brt(dusk_teal, 0.9),
        'rec-button-color': dusk_red,
        'rec-button-color-highlight': brt(dusk_red, 1.2),
        'rec-button-color-clicked': brt(dusk_red, 0.9),
        'zone-drag-color': dusk_gray_2,
    }
}

theme_dark = {
    "imgui_theme": "classic",
    "colors": {
        'default-canvas-color': (0x5b, 0x5b, 0x5b, 0xff),
        'default-grid-color': (0x75, 0x75, 0x75, 0xff),
        'default-operate-grid-color': (0x75, 0x75, 0x75, 0x60),
        'default-stroke-color': (0xaa, 0xaa, 0xaa, 0xff),
        'default-stroke-color-selected': (0xdd, 0xdd, 0xdd, 0xff),
        'default-selbox-stroke-color': (0x33, 0xcc, 0xff, 0xff),
        'default-selbox-fill-color': (0x33, 0xcc, 0xff, 0x20),
        'default-link-color': (0xaa, 0xaa, 0xaa, 0xff),
        'default-link-color-selected': (0xdd, 0xdd, 0xdd, 0xff),
        'default-link-color-snoop': (0xaa, 0xff, 0xaa, 0xff),
        'default-stroke-color-hover': (0x99, 0x99, 0x99, 0x0d),
        'default-stroke-color-debug': (0x3f, 0xbf, 0x7f, 0xff),
        'default-fill-color': (0x1f, 0x1f, 0x1f, 0xff),
        'default-fill-color-selected': (0x2f, 0x2f, 0x2f, 0xff),
        'default-fill-color-debug': (0x2f, 0x4f, 0x2f, 0xff),
        'default-alt-fill-color': (0x7d, 0x7d, 0x7d, 0xff),
        'default-text-color': (0xde, 0xde, 0xde, 0xff),
        'default-alt-text-color': (0x1f, 0x1f, 0x1f, 0xff),
        'default-light-text-color': (0xf7, 0xf9, 0xf9, 0xff),
        'default-match-text-color': (0xaa, 0xff, 0xaa, 0xff),
        'default-text-color-selected': (0xde, 0xde, 0xde, 0xff),
        'default-edit-badge-color': (0x74, 0x4b, 0x94, 0xff),
        'default-learn-badge-color': (0x19, 0xff, 0x90, 0xff),
        'default-error-badge-color': (0xb7, 0x21, 0x21, 0xff),
        'default-text-cursor-color': (0xff, 0xff, 0xff, 0x40),
        'default-data-color-0': (0x88, 0x52, 0x7f, 0xff),
        'default-data-color-1': (0x4c, 0x60, 0x85, 0xff),
        'default-data-color-2': (0x39, 0xa0, 0xed, 0xff),
        'default-data-color-3': (0x36, 0xf1, 0xcd, 0xff),
        'default-data-color-4': (0x13, 0xc4, 0xa3, 0xff),
        'default-data-color-5': (0xd3, 0x61, 0x35, 0xff),
        'default-cursor-color': (0xff, 0xff, 0xff, 0x70),
        'transparent': (0x00, 0x00, 0x00, 0x00),
    }
}

theme_light = {
    "imgui_theme": "light",
    "colors": {
        'default-canvas-color': (0xf7, 0xf9, 0xf9, 0),
        'default-cursor-color': (0xff, 0xff, 0xff, 0x70),
        'default-grid-color': (0xd0, 0xd0, 0xd0, 0xff),
        'default-stroke-color': (0x1f, 0x30, 0x2e, 0xff),
        'default-stroke-color-selected': (0x00, 0x7f, 0xff, 0xff),
        'default-stroke-color-hover': (0x00, 0x20, 0x40, 0x0d),
        'default-stroke-color-debug': (0x3f, 0xbf, 0x7f, 0xff),
        'default-link-color': (0x1f, 0x30, 0x2e, 0xff),
        'default-link-color-selected': (0x00, 0x7f, 0xff, 0xff),
        'default-fill-color': (0xd4, 0xdc, 0xff, 0xff),
        'default-fill-color-selected': (0xe4, 0xec, 0xff, 0xff),
        'default-fill-color-debug': (0xcd, 0xf8, 0xec, 0xff),
        'default-alt-fill-color': (0x7d, 0x83, 0xff, 0xff),
        'default-text-color': (0x1f, 0x30, 0x2e, 0xff),
        'default-light-text-color': (0xf7, 0xf9, 0xf9, 0xff),
        'default-text-color-selected': (0x00, 0x7f, 0xff, 0xff),
        'default-edit-badge-color': (0x74, 0x4b, 0x94, 0xff),
        'default-learn-badge-color': (0x19, 0xff, 0x90, 0xff),
        'default-error-badge-color': (0xb7, 0x21, 0x21, 0xff),
        'default-text-cursor-color': (0x0, 0x0, 0x0, 0x40),
        'default-data-color-0': (0x88, 0x52, 0x7f, 0xff),
        'default-data-color-1': (0x4c, 0x60, 0x85, 0xff),
        'default-data-color-2': (0x39, 0xa0, 0xed, 0xff),
        'default-data-color-3': (0x36, 0xf1, 0xcd, 0xff),
        'default-data-color-4': (0x13, 0xc4, 0xa3, 0xff),
        'default-data-color-5': (0xd3, 0x61, 0x35, 0xff),
        'transparent': (0x00, 0x00, 0x00, 0x00),
    }
}
