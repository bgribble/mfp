"""
info_panel.py: render helper for inspector/navigator panel

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from datetime import datetime
from imgui_bundle import imgui
from mfp import log
from mfp.gui_main import MFPGUI
from mfp.gui.colordb import RGBAColor
from mfp.gui.base_element import BaseElement
from mfp.gui.param_info import ListOfInt, ListOfPairs

single_params = [
    'obj_type',
    'obj_args',
    'display_type',
    'obj_name',
    'scope',
    'layername',
    'min_width',
    'min_height',
]


any_params = [
    'position_x',
    'position_y',
    'position_z',
]


# info panel is the layer/patch list and the object inspector
def render(app_window):
    imgui.begin(
        "info_panel",
        flags=(
            imgui.WindowFlags_.no_collapse
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_title_bar
        ),
    )
    if imgui.is_window_hovered(imgui.FocusedFlags_.child_windows):
        app_window.selected_window = "info"

    if imgui.begin_tab_bar("inspector_tab_bar", imgui.TabBarFlags_.none):
        # always show info about selection
        if imgui.begin_tab_item("Basics")[0]:
            render_basics_tab(app_window)
            imgui.end_tab_item()

        # specific info about this type of object
        if len(app_window.selected) == 1:
            param_list = [
                pname
                for pname, pval in app_window.selected[0].store_attrs.items()
                if pname not in single_params and pname not in any_params and pval.show
            ]

            if len(param_list) > 0 and imgui.begin_tab_item("Params")[0]:
                render_params_tab(app_window, param_list)
                imgui.end_tab_item()

        # show style for global (no selection) or single selection
        if len(app_window.selected) <= 1:
            if imgui.begin_tab_item("Style")[0]:
                render_style_tab(app_window)
                imgui.end_tab_item()

        # show bindings and activity for exactly one selection
        if len(app_window.selected) == 1:
            sel = app_window.selected[0]

            # this update will apply in a few render cycles
            if (
                not sel.tooltip_timestamp
                or (datetime.now() - sel.tooltip_timestamp).total_seconds() > 0.5
            ):
                MFPGUI().async_task(sel.tooltip_update())

            if imgui.begin_tab_item("Bindings")[0]:
                render_bindings_tab(app_window)
                imgui.end_tab_item()
            if imgui.begin_tab_item("Activity")[0]:
                render_activity_tab(app_window)
                imgui.end_tab_item()
        imgui.end_tab_bar()
    imgui.end()


# I want to log a message when there's an error rendering a param,
# but only once -- not on every render()
logged_errors = set()


def render_param(app_window, param_name, param_type, param_value):
    if param_type.editable is False:
        imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, 8.0))
    else:
        imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 4.0))

    imgui.text(param_type.label)

    newval = param_value
    changed = False
    try:
        if param_type.editable is False:
            imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, 8.0))
            imgui.text(
                " " + str(param_value),
            )
            imgui.pop_style_var()

        elif param_type.param_type is str:
            changed, newval = imgui.input_text(
                f"##{param_name}",
                str(param_value),
                imgui.InputTextFlags_.enter_returns_true
            )

        elif param_type.param_type is ListOfInt:
            changed, newval = imgui.input_text(
                f"##{param_name}",
                str(param_value),
                imgui.InputTextFlags_.enter_returns_true
            )

        elif param_type.param_type is bool:
            imgui.push_style_var(imgui.StyleVar_.item_spacing, (6, 0))
            imgui.same_line()
            changed, newval = imgui.checkbox(
                f"##{param_name}",
                bool(param_value),
            )
            imgui.pop_style_var()

        elif param_type.param_type is int:
            show_input = True
            show_input_changed = False
            if param_type.null:
                imgui.push_style_var(imgui.StyleVar_.item_spacing, (6, 0))
                imgui.same_line()
                show_input_changed, none_val = imgui.checkbox(
                    f"##{param_name}_none",
                    param_value is None
                )
                imgui.same_line()
                imgui.text(" None")
                imgui.pop_style_var()
                if none_val:
                    show_input = False
            if show_input:
                changed, newval = imgui.input_int(
                    f"##{param_name}",
                    int(param_value),
                    step=1,
                    step_fast=10,
                    flags=imgui.InputTextFlags_.enter_returns_true
                )
                changed = changed or show_input_changed
            else:
                changed = show_input_changed
                newval = None

        elif param_type.param_type is float:
            show_input = True
            show_input_changed = False
            if param_type.null:
                imgui.push_style_var(imgui.StyleVar_.item_spacing, (6, 0))
                imgui.same_line()
                show_input_changed, none_val = imgui.checkbox(
                    f"##{param_name}_none",
                    param_value is None
                )
                imgui.same_line()
                imgui.text(" None")
                imgui.pop_style_var()
                if none_val:
                    show_input = False
            if show_input:
                changed, newval = imgui.input_double(
                    f"##{param_name}",
                    float(param_value or 0),
                    step=1,
                    step_fast=10,
                    format="%.2f",
                    flags=imgui.InputTextFlags_.enter_returns_true
                )
                changed = changed or show_input_changed
            else:
                changed = show_input_changed
                newval = None

        elif param_type.param_type is RGBAColor:
            components = [
                param_value.red / 255.0,
                param_value.green / 255.0,
                param_value.blue / 255.0,
                param_value.alpha / 255.0
            ]
            txt_changed, txt_newval = imgui.input_text(
                f"##{param_name}_txt",
                str(param_value),
                imgui.InputTextFlags_.enter_returns_true
            )
            imgui.same_line()
            pick_changed, pick_newval = imgui.color_edit4(
                f"##{param_name}_pick",
                components,
                imgui.ColorEditFlags_.no_inputs | imgui.ColorEditFlags_.no_label
            )
            if txt_changed:
                changed = True
                red, green, blue, alpha = txt_newval
                newval = RGBAColor(
                    red=red*255.0, green=green*255.0, blue=blue*255.0, alpha=alpha*255.0
                )
            elif pick_changed:
                changed = True
                red, green, blue, alpha = pick_newval
                newval = RGBAColor(
                    red=red*255.0, green=green*255.0, blue=blue*255.0, alpha=alpha*255.0
                )

        elif param_type.param_type is ListOfPairs:
            newval = []
            changed = False

            if param_value and len(param_value) > 0:
                flags = 0
                if imgui.begin_table(f"##{param_name}_table", 3, flags):
                    imgui.table_setup_column("Display")
                    imgui.table_setup_column("Value")
                    imgui.table_setup_column("Del")
                    imgui.table_headers_row()

                    for row_num, row_item in enumerate(param_value):
                        display, value = row_item
                        imgui.table_next_row()
                        imgui.table_set_column_index(0)
                        imgui.push_id(row_num)
                        display_changed, display_newval = imgui.input_text(
                            f"##{param_name}_display",
                            display
                        )
                        imgui.table_set_column_index(1)
                        val_changed, val_newval = imgui.input_text(
                            f"##{param_name}_value",
                            value
                        )
                        imgui.table_set_column_index(2)
                        del_clicked = imgui.button("x")
                        imgui.pop_id()

                        if del_clicked:
                            changed = True
                            continue

                        new_item = (
                            display_newval if display_changed else display,
                            val_newval if val_changed else value
                        )

                        changed = changed or val_changed or display_changed
                        newval.append(new_item)
                    imgui.end_table()
            if imgui.button("Add"):
                newval.append(("", ""))
                changed = True

        elif param_type.param_type is dict:
            newval = {}
            changed = False

            if param_value and len(param_value) > 0:
                flags = 0
                if imgui.begin_table(f"##{param_name}_table", 2, flags):
                    for row_num, row_key in enumerate(param_value):
                        row_value = param_value.get(row_key)
                        imgui.table_next_row()

                        imgui.table_set_column_index(0)
                        imgui.push_id(row_num)
                        imgui.text("  " + row_key)

                        imgui.table_set_column_index(1)
                        val_changed, val_newval = imgui.input_text(
                            f"##{param_name}_value",
                            str(row_value)
                        )
                        imgui.pop_id()
                        if val_changed:
                            try:
                                val_type = type(row_value)
                                newval[row_key] = val_type(val_newval)
                                changed = True
                            except Exception:
                                newval[row_key] = row_value

                        else:
                            newval[row_key] = row_value
                    imgui.end_table()

        if param_name in logged_errors:
            logged_errors.remove(param_name)
    except Exception as e:
        imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, 8.0))
        imgui.text(
            " <error>"
        )
        imgui.pop_style_var()
        if param_name not in logged_errors:
            log.warning(f"[render] Error in param {param_name}: {type(e)} {e}")
            logged_errors.add(param_name)

    imgui.pop_style_var()
    if changed:
        return newval
    return param_value


def render_basics_tab(app_window):
    if len(app_window.selected) == 1:
        for param in single_params:
            ptype = BaseElement.store_attrs.get(param)
            sel = app_window.selected[0]
            pvalue = getattr(sel, param)
            newval = render_param(app_window, param, ptype, pvalue)
            if newval != pvalue:
                MFPGUI().async_task(sel.dispatch_setter(param, newval))

    for param in any_params:
        ptype = BaseElement.store_attrs.get(param)
        if len(app_window.selected) == 1:
            sel = app_window.selected[0]
            pvalue = getattr(sel, param)
            newval = render_param(app_window, param, ptype, pvalue)
            if newval != pvalue:
                MFPGUI().async_task(sel.dispatch_setter(param, newval))
        elif len(app_window.selected) > 1:
            min_val = min(
                getattr(elem, param) for elem in app_window.selected
            )
            new_val = render_param(app_window, param, ptype, min_val)
            if min_val != new_val:
                delta = new_val - min_val
                for elem in app_window.selected:
                    old_val = getattr(elem, param)
                    MFPGUI().async_task(
                        elem.dispatch_setter(param, old_val + delta)
                    )


def render_params_tab(app_window, param_list):
    if len(app_window.selected) != 1 or len(param_list) == 0:
        return

    for param in param_list:
        sel = app_window.selected[0]
        ptype = sel.store_attrs.get(param)
        pvalue = getattr(sel, param)
        newval = render_param(app_window, param, ptype, pvalue)
        if newval != pvalue:
            MFPGUI().async_task(sel.dispatch_setter(param, newval))


def render_style_tab(app_window):
    if imgui.begin_tab_bar("styles_tab_bar", imgui.TabBarFlags_.none):
        style = None
        style_changed = False

        # always show info about selection
        if len(app_window.selected) == 1:
            sel = app_window.selected[0]
            style = {**sel.style}
            style_changed = False

            if imgui.begin_tab_item("Element")[0]:
                for propname, value in sel.style.items():
                    pp = MFPGUI().style_vars[propname]
                    newval = render_param(app_window, propname, pp, value)
                    if newval != value:
                        style[propname] = newval
                        style_changed = True
                imgui.end_tab_item()
            if imgui.begin_tab_item("Type")[0]:
                for propname, value in type(sel).style_defaults.items():
                    pp = MFPGUI().style_vars[propname]
                    newval = render_param(app_window, propname, pp, value)
                    if newval != value:
                        style[propname] = newval
                        style_changed = True
                imgui.end_tab_item()
            if imgui.begin_tab_item("Base")[0]:
                for propname, value in BaseElement.style_defaults.items():
                    pp = MFPGUI().style_vars[propname]
                    newval = render_param(app_window, propname, pp, value)
                    if newval != value:
                        style[propname] = newval
                        style_changed = True
                imgui.end_tab_item()

        if imgui.begin_tab_item("Global")[0]:
            for propname, value in MFPGUI().style_defaults.items():
                pp = MFPGUI().style_vars[propname]
                newval = render_param(app_window, propname, pp, value)
                if style and newval != value:
                    style[propname] = newval
                    style_changed = True
            imgui.end_tab_item()

        if len(app_window.selected) == 1:
            if imgui.begin_tab_item("Computed")[0]:
                # these should be readonly
                for propname, value in sel._all_styles.items():
                    pp = MFPGUI().style_vars[propname]
                    render_param(app_window, propname, pp, value)
                imgui.end_tab_item()

        if style and style_changed:
            MFPGUI().async_task(sel.dispatch_setter('style', style))

        imgui.end_tab_bar()


def render_bindings_tab(app_window):
    sel = app_window.selected[0]
    if not sel.tooltip_info:
        return

    imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, 8.0))
    imgui.text("OSC bindings")
    if imgui.begin_table(
        "##osc_bindings",
        2,
        (
            imgui.TableFlags_.row_bg
            | imgui.TableFlags_.borders
            | imgui.TableFlags_.borders_h
            | imgui.TableFlags_.borders_v
            | imgui.TableFlags_.borders_v
            | imgui.TableFlags_.sizing_fixed_fit
        )
    ):
        # headers
        imgui.table_setup_column("Route")
        imgui.table_setup_column("Types", 0, 60)
        imgui.table_headers_row()

        for route, handler in sel.tooltip_info.get("osc_handlers", {}).items():
            imgui.table_next_row()
            imgui.table_set_column_index(0)
            imgui.text(route)
            imgui.table_set_column_index(1)
            imgui.text(str(handler))
        imgui.end_table()
    imgui.text("MIDI bindings")

    if imgui.begin_table(
        "##midi_bindings",
        3,
        imgui.TableFlags_.row_bg | imgui.TableFlags_.borders | imgui.TableFlags_.borders_h | imgui.TableFlags_.borders_v
    ):
        # headers
        imgui.table_setup_column("Chan")
        imgui.table_setup_column("Note")
        imgui.table_setup_column("Type")
        imgui.table_headers_row()

        for binding in sel.tooltip_info.get("midi_handlers", []):
            imgui.table_next_row()
            imgui.table_set_column_index(0)
            imgui.text(binding["channel"])
            imgui.table_set_column_index(1)
            imgui.text(binding["note"])
            imgui.table_set_column_index(2)
            imgui.text(binding["type"])
        imgui.end_table()
    imgui.pop_style_var()


def render_activity_tab(app_window):

    sel = app_window.selected[0]
    if not sel.tooltip_info:
        return
    info = sel.tooltip_info

    imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, 8.0))

    imgui.text(f"Messages in: {info.get('messages_in')}")
    imgui.text(f"Messages out: {info.get('messages_out')}")
    imgui.text(f"Times triggered: {info.get('trigger_count')}")
    imgui.text('')
    imgui.text(f"Error count: {info.get('error_count')}")

    imgui.text("Error messages:")
    if imgui.begin_table(
        "##error_messages",
        2,
        (
            imgui.TableFlags_.row_bg
            | imgui.TableFlags_.borders
            | imgui.TableFlags_.borders_h
            | imgui.TableFlags_.borders_v
            | imgui.TableFlags_.sizing_fixed_fit
        )
    ):
        # headers
        imgui.table_setup_column("Count", 0, 50)
        imgui.table_setup_column("Message")
        imgui.table_headers_row()

        for message, count in info.get('error_messages', []):
            imgui.table_next_row()
            imgui.table_set_column_index(0)
            imgui.text(str(count))
            imgui.table_set_column_index(1)
            imgui.text(message)
        imgui.end_table()

    imgui.pop_style_var()