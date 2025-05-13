"""
info_panel.py: render helper for inspector/navigator panel

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from datetime import datetime
from imgui_bundle import imgui, imgui_color_text_edit as ed
from mfp import log
from mfp.gui_main import MFPGUI
from mfp.gui.colordb import RGBAColor
from mfp.gui.base_element import BaseElement, PROPERTY_ATTRS
from mfp.gui.param_info import (
    ParamInfo,
    ListOfInt,
    ListOfPairs,
    DictOfRGBAColor,
    DictOfProperty,
    PyLiteral,
    CodeBlock,
)

single_params = [
    'obj_type',
    'obj_args',
    'display_type',
    'obj_name',
    'scope',
    'layer',
    'min_width',
    'min_height',
    'panel_enable',
]


any_params = [
    'position_x',
    'position_y',
    'position_z',
]

TAB_PADDING_X = 12
TAB_PADDING_Y = 4


def render_code_editor(app_window, param_name, param_type, param_value, target):
    def _ensure_editor():
        editor = target.imgui_code_editor
        if not editor:
            editor = ed.TextEditor()
            target.imgui_code_editor = editor
            init_text = ""
            if param_value:
                init_text = param_value.get("body", "")
            editor.set_text(init_text)
            editor.set_language_definition(ed.TextEditor.LanguageDefinition.python())

        return editor

    if target.name:
        label = f"{target.obj_type} {target.name}"
    else:
        label = f"{target.obj_type} {id(target)}"

    editor = _ensure_editor()
    imgui.set_next_window_size(
        (app_window.info_panel_width - 24, 350)
    )
    editor.render(label)

    if imgui.button("Save"):
        new_val = {**target.code} if target.code else {}
        new_val["body"] = editor.get_text()
        new_val["lang"] = "python"
        new_val["errorinfo"] = None
        MFPGUI().async_task(target.dispatch_setter(param_name, new_val))
    imgui.same_line()

    if imgui.button("Revert"):
        prev_code = target.code or {}
        editor.set_text(prev_code.get("body", ""))


# info panel is the layer/patch list and the object inspector
def render(app_window):
    imgui.begin(
        "info_panel",
        flags=(
            imgui.WindowFlags_.no_collapse
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_title_bar
            | imgui.WindowFlags_.no_bring_to_front_on_focus
        ),
    )
    if imgui.is_window_hovered(imgui.FocusedFlags_.child_windows):
        app_window.selected_window = "info"

    if imgui.begin_tab_bar("inspector_tab_bar", imgui.TabBarFlags_.none):
        if imgui.begin_tab_item("Patch")[0]:
            render_patch_tab(app_window)
            imgui.end_tab_item()

        # always show info about selection
        if imgui.begin_tab_item("Object")[0]:
            render_object_tab(app_window)
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


def render_param(
    app_window, param_name, param_type, param_value, target=None, readonly=False, override=None
):
    item_spacing = 12

    imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, 4.0))

    # parameter name, except for property lists which each have their own name
    if param_type.param_type != DictOfProperty:
        imgui.text(param_type.label)

    newval = param_value if override is None else override
    changed = False

    imgui.push_id(param_name)

    try:
        if readonly or param_type.editable is False:
            imgui.begin_disabled()

        if callable(param_type.choices) and target:
            choices = {
                c[0]: c[1]
                for c in param_type.choices(target)
            }
            current_choice = next((c for c in choices.items() if c[1] == param_value), None)
            if not current_choice:
                current_choice = (choices[0], choices[choices[0]])
            if imgui.button(current_choice[0]):
                imgui.open_popup("##param_choices_popup")
            imgui.push_style_var(imgui.StyleVar_.window_padding, (8, 8))
            imgui.push_style_var(imgui.StyleVar_.item_spacing, (3, 3))
            if imgui.begin_popup("##param_choices_popup"):
                mouse_pos = imgui.get_mouse_pos_on_opening_current_popup()
                cursor_pos = (mouse_pos[0] + 8, mouse_pos[1] + 8)
                imgui.set_cursor_screen_pos(cursor_pos)
                for choice_label, choice_value in choices.items():
                    item_selected, _ = imgui.menu_item(
                        choice_label, '', False, True
                    )
                    if item_selected and choice_label != current_choice[0]:
                        changed = True
                        newval = choice_value
                imgui.dummy([1, 4])
                imgui.end_popup()
            imgui.pop_style_var(2)

        elif param_type.param_type is PyLiteral:
            import ast
            imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, item_spacing))
            changed, newval = imgui.input_text(
                f"##{param_name}",
                repr(param_value),
                imgui.InputTextFlags_.enter_returns_true
            )
            if changed:
                try:
                    newval = ast.literal_eval(newval)
                except Exception:
                    log.warning(f"Unable to parse value for parameter {param_type.label}")
            imgui.pop_style_var()

        elif param_type.param_type is str:
            imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, item_spacing))
            changed, newval = imgui.input_text(
                f"##{param_name}",
                str(param_value),
                imgui.InputTextFlags_.enter_returns_true
            )
            imgui.pop_style_var()

        elif param_type.param_type is ListOfInt:
            imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, item_spacing))
            changed, newval = imgui.input_text(
                f"##{param_name}",
                str(param_value),
                imgui.InputTextFlags_.enter_returns_true
            )
            imgui.pop_style_var()

        elif param_type.param_type is bool:
            imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, item_spacing))
            changed, newval = imgui.checkbox(f"##{param_name}", bool(param_value))
            imgui.pop_style_var()

        elif param_type.param_type is int:
            show_input = True
            show_input_changed = False
            imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, item_spacing))
            imgui.begin_group()
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
                )
                if changed:
                    delta = abs(newval - param_value)
                    if delta > 10:
                        changed = changed and imgui.is_item_deactivated_after_edit()

                changed = changed or show_input_changed
            else:
                changed = show_input_changed
                newval = None
            imgui.end_group()
            imgui.pop_style_var()

        elif param_type.param_type is float:
            show_input = True
            show_input_changed = False
            imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, item_spacing))
            imgui.begin_group()
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
                imgui.push_style_var(imgui.StyleVar_.item_spacing, (0.0, 6.0))
                changed, newval = imgui.input_double(
                    f"##{param_name}",
                    float(param_value or 0),
                    step=1,
                    step_fast=10,
                    format="%.2f",
                )
                if changed:
                    delta = abs(newval - (param_value or 0))
                    if delta > 10:
                        changed = changed and imgui.is_item_deactivated_after_edit()

                changed = changed or show_input_changed
                imgui.pop_style_var()
            else:
                changed = show_input_changed
                newval = None
            imgui.end_group()
            imgui.pop_style_var()

        elif param_type.param_type is RGBAColor:
            components = [
                param_value.red / 255.0,
                param_value.green / 255.0,
                param_value.blue / 255.0,
                param_value.alpha / 255.0
            ]
            imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, item_spacing))
            imgui.begin_group()
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
            imgui.end_group()
            imgui.pop_style_var()
            if txt_changed:
                changed = True
                txt_newval = txt_newval.replace("#", "")
                parts = [
                    txt_newval[2*i:2*i+1]
                    for i in range(len(txt_newval) // 2)
                ]
                red, green, blue, alpha = parts
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

            imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, item_spacing))
            imgui.begin_group()
            imgui.push_id(param_name)

            if param_value and len(param_value) > 0:
                flags = 0
                imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, 4.0))
                imgui.push_id(param_name)
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
                imgui.pop_style_var()
            if imgui.button("Add"):
                newval.append(("", ""))
                changed = True
            imgui.pop_id()
            imgui.end_group()
            imgui.pop_style_var()

        elif param_type.param_type is DictOfRGBAColor:
            newval = {}
            changed = False

            imgui.push_id(param_name)
            imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, item_spacing))
            if param_value and len(param_value) > 0:
                flags = 0
                if imgui.begin_table("##table", 2, flags):
                    for row_num, row_key in enumerate(param_value):
                        row_value = param_value.get(row_key)
                        imgui.table_next_row()

                        imgui.table_set_column_index(0)
                        imgui.push_id(row_num)
                        imgui.text("  " + str(row_key))

                        imgui.table_set_column_index(1)

                        components = [
                            row_value.red / 255.0,
                            row_value.green / 255.0,
                            row_value.blue / 255.0,
                            row_value.alpha / 255.0
                        ]
                        imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, item_spacing))
                        imgui.begin_group()
                        txt_changed, txt_newval = imgui.input_text(
                            "##color_txt",
                            str(row_value),
                            imgui.InputTextFlags_.enter_returns_true
                        )
                        imgui.same_line()
                        pick_changed, pick_newval = imgui.color_edit4(
                            "##color_pick",
                            components,
                            imgui.ColorEditFlags_.no_inputs | imgui.ColorEditFlags_.no_label
                        )
                        if txt_changed:
                            changed = True
                            red, green, blue, alpha = txt_newval
                            newval[row_key] = RGBAColor(
                                red=red*255.0, green=green*255.0, blue=blue*255.0, alpha=alpha*255.0
                            )
                        elif pick_changed:
                            changed = True
                            red, green, blue, alpha = pick_newval
                            newval[row_key] = RGBAColor(
                                red=red*255.0, green=green*255.0, blue=blue*255.0, alpha=alpha*255.0
                            )
                        else:
                            newval[row_key] = row_value
                        imgui.end_group()
                        imgui.pop_style_var()
                        imgui.pop_id()
                    imgui.end_table()
            imgui.pop_style_var()
            imgui.pop_id()

        elif param_type.param_type is CodeBlock:
            show_input = True
            show_input_changed = False

            imgui.push_id(param_name)
            imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, item_spacing))
            imgui.begin_group()

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
                render_code_editor(app_window, param_name, param_type, param_value, target)
            imgui.end_group()
            imgui.pop_style_var()
            imgui.pop_id()

        elif param_type.param_type is DictOfProperty:
            newval = {}
            changed = False
            imgui.push_id(param_name)
            if param_value and len(param_value) > 0:
                for prop_name, prop_value in param_value.items():
                    pinfo = PROPERTY_ATTRS.get(prop_name)
                    new_pval = prop_value
                    if pinfo:
                        new_pval = render_param(
                            app_window, prop_name, pinfo, prop_value,
                            target
                        )
                        if new_pval != prop_value:
                            changed = True
                    newval[prop_name] = new_pval

            imgui.pop_id()

        elif param_type.param_type is dict:
            newval = {}
            changed = False

            imgui.push_id(param_name)
            imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, item_spacing))
            if param_value and len(param_value) > 0:
                flags = 0
                if imgui.begin_table(f"##{param_name}_table", 2, flags):
                    for row_num, row_key in enumerate(param_value):
                        row_value = param_value.get(row_key)
                        imgui.table_next_row()

                        imgui.table_set_column_index(0)
                        imgui.push_id(row_num)
                        imgui.text("  " + str(row_key))

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
            imgui.pop_style_var()
            imgui.pop_id()

        if readonly or param_type.editable is False:
            imgui.end_disabled()

        if override is not None:
            imgui.push_style_var(imgui.StyleVar_.item_spacing, (4.0, item_spacing))
            imgui.same_line()
            param_value = override
            changed, newval = imgui.checkbox(f"##{param_name}_override", override)
            imgui.same_line()
            imgui.text("Change")
            imgui.pop_style_var()

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

    imgui.pop_id()
    imgui.pop_style_var()
    if changed:
        return newval
    return param_value


def render_patch_tab(app_window):
    patch = app_window.selected_patch
    layer = app_window.selected_layer

    if not patch or not layer or not patch.display_info:
        return

    ######################
    # a little padding
    imgui.dummy([1, TAB_PADDING_Y])
    imgui.dummy([TAB_PADDING_X, 1])
    imgui.same_line()

    imgui.begin_group()

    ######################
    # patch params
    imgui.separator_text(" Patch ")

    oldval = patch.obj_name
    newval = render_param(
        app_window, 'patch_name', ParamInfo(label="Name", param_type=str), oldval
    )
    if newval != oldval:
        patch.obj_name = newval
        MFPGUI().async_task(MFPGUI().mfp.rename_obj(patch.obj_id, newval))
        patch.send_params()

    render_param(
        app_window, 'patch_context',
        ParamInfo(label="DSP context", param_type=str, editable=False),
        patch.context_name
    )

    ######################
    # viewport params
    imgui.separator_text(" Viewport ")
    di = patch.display_info
    view_x = render_param(
        app_window, 'viewport_x', ParamInfo(label="X origin", param_type=float), di.view_x
    )
    view_y = render_param(
        app_window, 'viewport_y', ParamInfo(label="Y origin", param_type=float), di.view_y
    )
    view_zoom = render_param(
        app_window, 'viewport_zoom', ParamInfo(label="Zoom", param_type=float), di.view_zoom
    )
    render_param(
        app_window, 'viewport_pos_x',
        ParamInfo(label="Tile X position", param_type=float, editable=False),
        di.origin_x
    )
    render_param(
        app_window, 'viewport_pos_y',
        ParamInfo(label="Tile Y position", param_type=float, editable=False),
        di.origin_y
    )
    render_param(
        app_window, 'viewport_width',
        ParamInfo(label="Tile width", param_type=float, editable=False),
        di.width
    )
    render_param(
        app_window, 'viewport_height',
        ParamInfo(label="Tile height", param_type=float, editable=False),
        di.height
    )

    if view_x != di.view_x or view_y != di.view_y:
        di.view_x = view_x
        di.view_y = view_y
        app_window.viewport_pos_set = True

    if view_zoom != di.view_zoom:
        di.view_zoom = view_zoom
        app_window.viewport_zoom_set = True

    ######################
    # layer params
    imgui.separator_text(" Layer ")

    oldval = layer.name
    newval = render_param(
        app_window, 'layer_name', ParamInfo(label="Name", param_type=str), oldval
    )
    if newval != oldval:
        layer.name = newval
        patch.send_params()
        for lobj in layer.objects:
            lobj.send_params()

    imgui.end_group()


def render_object_tab(app_window):
    ######################
    # a little padding
    imgui.dummy([1, TAB_PADDING_Y])
    imgui.dummy([TAB_PADDING_X, 1])
    imgui.same_line()

    imgui.begin_group()

    if len(app_window.selected) == 1:
        for param in single_params:
            ptype = BaseElement.store_attrs.get(param)
            sel = app_window.selected[0]
            pvalue = getattr(sel, param)
            newval = render_param(app_window, param, ptype, pvalue, sel)
            if newval != pvalue:
                MFPGUI().async_task(sel.dispatch_setter(param, newval))
    for param in any_params:
        ptype = BaseElement.store_attrs.get(param)
        if len(app_window.selected) == 1:
            sel = app_window.selected[0]
            pvalue = getattr(sel, param)
            newval = render_param(app_window, param, ptype, pvalue, sel)
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
    imgui.end_group()


def render_params_tab(app_window, param_list):
    if len(app_window.selected) != 1 or len(param_list) == 0:
        return

    ######################
    # a little padding
    imgui.dummy([1, TAB_PADDING_Y])
    imgui.dummy([TAB_PADDING_X, 1])
    imgui.same_line()

    imgui.begin_group()

    for param in param_list:
        sel = app_window.selected[0]
        ptype = sel.store_attrs.get(param)
        pvalue = getattr(sel, param)
        newval = render_param(app_window, param, ptype, pvalue, sel)
        if newval != pvalue:
            MFPGUI().async_task(sel.dispatch_setter(param, newval))

    imgui.end_group()


def render_style_tab(app_window):
    if imgui.begin_tab_bar("styles_tab_bar", imgui.TabBarFlags_.none):
        style = None
        style_changed = False

        override_params = []

        # always show info about selection
        if len(app_window.selected) == 1:
            sel = app_window.selected[0]
            style = {**sel.style}
            style_changed = False

            override_params = list(style.keys())

            # the Element tab is the only on where params can be edited
            if imgui.begin_tab_item("Element")[0]:
                imgui.dummy([1, TAB_PADDING_Y])
                imgui.dummy([TAB_PADDING_X, 1])
                imgui.same_line()

                imgui.begin_group()
                for propname, value in sel.style.items():
                    pp = MFPGUI().style_vars[propname]
                    newval = render_param(app_window, propname, pp, value, sel)
                    if newval != value:
                        style[propname] = newval
                        style_changed = True
                imgui.end_group()
                imgui.end_tab_item()

            # defaults for this type of element
            if imgui.begin_tab_item("Type")[0]:
                imgui.dummy([1, TAB_PADDING_Y])
                imgui.dummy([TAB_PADDING_X, 1])
                imgui.same_line()

                imgui.begin_group()
                for propname, value in type(sel).style_defaults.items():
                    pp = MFPGUI().style_vars[propname]
                    override = propname in override_params
                    newval = render_param(
                        app_window, propname, pp, value, sel,
                        readonly=True, override=override
                    )
                    if newval != override:
                        if newval:
                            style[propname] = value
                        elif propname in style:
                            del style[propname]
                        style_changed = True
                imgui.end_group()
                imgui.end_tab_item()

            # style shared by all element types
            if imgui.begin_tab_item("Base")[0]:
                imgui.dummy([1, TAB_PADDING_Y])
                imgui.dummy([TAB_PADDING_X, 1])
                imgui.same_line()

                imgui.begin_group()
                for propname, value in BaseElement.style_defaults.items():
                    pp = MFPGUI().style_vars[propname]
                    override = propname in override_params
                    newval = render_param(
                        app_window, propname, pp, value, sel,
                        readonly=True, override=override
                    )
                    if newval != override:
                        if newval:
                            style[propname] = value
                        elif propname in style:
                            del style[propname]

                        style_changed = True
                imgui.end_group()
                imgui.end_tab_item()

        if imgui.begin_tab_item("Global")[0]:
            imgui.dummy([1, TAB_PADDING_Y])
            imgui.dummy([TAB_PADDING_X, 1])
            imgui.same_line()

            imgui.begin_group()
            for propname, value in MFPGUI().style_defaults.items():
                pp = MFPGUI().style_vars[propname]
                override = propname in override_params
                newval = render_param(
                    app_window, propname, pp, value, readonly=True, override=override
                )
                if newval != override:
                    if newval:
                        style[propname] = value
                    else:
                        if propname in style:
                            del style[propname]
                    style_changed = True
            imgui.end_group()
            imgui.end_tab_item()

        if len(app_window.selected) == 1:
            if imgui.begin_tab_item("Computed")[0]:
                imgui.dummy([1, TAB_PADDING_Y])
                imgui.dummy([TAB_PADDING_X, 1])
                imgui.same_line()

                imgui.begin_group()

                # these should be readonly
                for propname, value in sel._all_styles.items():
                    pp = MFPGUI().style_vars[propname]
                    render_param(app_window, propname, pp, value, readonly=True)
                imgui.end_group()
                imgui.end_tab_item()

        if style is not None and style_changed:
            MFPGUI().async_task(sel.dispatch_setter('style', style))

        imgui.end_tab_bar()


def render_bindings_tab(app_window):
    sel = app_window.selected[0]
    if not sel.tooltip_info:
        return

    ######################
    # a little padding
    imgui.dummy([1, TAB_PADDING_Y])
    imgui.dummy([TAB_PADDING_X, 1])
    imgui.same_line()

    imgui.begin_group()
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
        (
            imgui.TableFlags_.row_bg
            | imgui.TableFlags_.borders
            | imgui.TableFlags_.borders_h
            | imgui.TableFlags_.borders_v
        )
    ):
        # headers
        imgui.table_setup_column("Chan")
        imgui.table_setup_column("Note/CC")
        imgui.table_setup_column("Type")
        imgui.table_headers_row()

        for binding in sel.tooltip_info.get("midi_handlers", []):
            imgui.table_next_row()
            imgui.table_set_column_index(0)
            imgui.text(str(binding["channel"]))
            imgui.table_set_column_index(1)
            imgui.text(str(binding.get("note") or binding.get("number")))
            imgui.table_set_column_index(2)
            imgui.text(str(binding.get("type")))
        imgui.end_table()
    imgui.pop_style_var()
    imgui.end_group()


def render_activity_tab(app_window):

    sel = app_window.selected[0]
    if not sel.tooltip_info:
        return
    info = sel.tooltip_info

    ######################
    # a little padding
    imgui.dummy([1, TAB_PADDING_Y])
    imgui.dummy([TAB_PADDING_X, 1])
    imgui.same_line()

    imgui.begin_group()
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
            imgui.push_text_wrap_pos(350)
            imgui.text(message)
            imgui.pop_text_wrap_pos()
        imgui.end_table()

    imgui.pop_style_var()
    imgui.end_group()
