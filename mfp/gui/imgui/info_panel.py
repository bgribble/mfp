"""
info_panel.py: render helper for inspector/navigator panel

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from imgui_bundle import imgui
from mfp.gui.base_element import BaseElement


# info panel is the layer/patch list and the object inspector
def render(app_window):
    if imgui.begin_tab_bar("inspector_tab_bar", imgui.TabBarFlags_.none):
        # always show info about selection
        if imgui.begin_tab_item("Basics")[0]:
            render_basics_tab(app_window)
            imgui.end_tab_item()

        # show style for global (no selection) or single selection
        if len(app_window.selected) <= 1:
            if imgui.begin_tab_item("Style")[0]:
                imgui.end_tab_item()

        # show bindings and activity for exactly one selection
        if len(app_window.selected) == 1:
            if imgui.begin_tab_item("Bindings")[0]:
                imgui.end_tab_item()
            if imgui.begin_tab_item("Activity")[0]:
                imgui.end_tab_item()
        imgui.end_tab_bar()


def render_param(app_window, param_name, param_type, param_value):
    label_width = max(
        app_window.info_panel_width * 0.3,
        40
    )
    if param_type.param_type:
        imgui.push_item_width(label_width)
        imgui.text(param_type.label)
        imgui.pop_item_width()
        newval = imgui.input_text(f"##{param_name}", str(param_value))

    return newval


def render_basics_tab(app_window):
    single_params = [
        'obj_type',
        'obj_args',
        'display_type',
        'obj_name',
        'scope',
        'layername'
    ]

    any_params = [
        'position_x',
        'position_y',
        'position_z',
    ]

    if len(app_window.selected) == 1:
        for param in single_params:
            ptype = BaseElement.store_attrs.get(param)
            sel = app_window.selected[0]
            pvalue = getattr(sel, param)
            newval = render_param(app_window, param, ptype, pvalue)

    for param in any_params:
        ptype = BaseElement.store_attrs.get(param)
        if len(app_window.selected) == 1:
            sel = app_window.selected[0]
            pvalue = getattr(sel, param)
            newval = render_param(app_window, param, ptype, pvalue)

