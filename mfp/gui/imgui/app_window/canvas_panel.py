"""
canvas_pane -- render the 'imgui node editor' canvas pane

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from imgui_bundle import imgui, imgui_node_editor as nedit
from mfp.gui_main import MFPGUI
from mfp.gui.connection_element import ConnectionElement
from mfp.gui.modes.patch_edit import PatchEditMode
from mfp.gui.modes.global_mode import GlobalMode


def render(app_window):
    imgui.begin(
        "canvas",
        flags=(
            imgui.WindowFlags_.no_collapse
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_title_bar
        ),
    )
    cursor_x, cursor_y = imgui.get_cursor_pos()
    if imgui.is_window_hovered(imgui.FocusedFlags_.child_windows):
        app_window.selected_window = "canvas"
        if not isinstance(app_window.input_mgr.global_mode, GlobalMode):
            app_window.input_mgr.global_mode = GlobalMode(app_window)
            app_window.input_mgr.major_mode.enable()

    nedit.push_style_color(
        nedit.StyleColor.bg,
        app_window.get_color('canvas-color').to_rgbaf()
    )
    nedit.push_style_color(
        nedit.StyleColor.node_border,
        app_window.get_color('stroke-color').to_rgbaf()
    )
    nedit.push_style_color(
        nedit.StyleColor.sel_node_border, (0, 0, 0, 0)
    )
    nedit.push_style_color(
        nedit.StyleColor.sel_link_border, (0, 0, 0, 0)
    )
    nedit.push_style_color(
        nedit.StyleColor.hov_node_border,
        app_window.get_color('stroke-color:hover').to_rgbaf()
    )
    nedit.push_style_color(
        nedit.StyleColor.hov_link_border,
        app_window.get_color('stroke-color:hover').to_rgbaf()
    )

    nedit.begin("canvas_editor", (0.0, 0.0))

    conf = nedit.get_config()

    # disable NodeEditor dragging of nodes when not in edit mode
    if isinstance(app_window.input_mgr.major_mode, PatchEditMode):
        conf.drag_button_index = 0
    else:
        conf.drag_button_index = 3

    # reselect nodes if needed (part of the hack to resize the viewport)
    if app_window.imgui_needs_reselect:
        nedit.clear_selection()
        for obj in app_window.imgui_needs_reselect:
            nedit.select_node(obj.node_id, True)
        app_window.imgui_needs_reselect = []

    # first pass: non-links
    all_pins = {}
    for obj in app_window.objects:
        if not isinstance(obj, ConnectionElement):
            obj.render()
            for port_id, pin_id in obj.port_elements.items():
                all_pins[pin_id.id()] = (obj, port_id)

    # second pass: links
    for obj in app_window.objects:
        if isinstance(obj, ConnectionElement):
            obj.render()

    #############################
    # viewport management
    # this is janky. We create an invisible upper-left and lower-right
    # node that we will use wth zoom_to_selection()

    # create nodes if needed
    if app_window.viewport_box_nodes is None:
        min_node_id = nedit.NodeId.create()
        max_node_id = nedit.NodeId.create()
        app_window.viewport_box_nodes = (min_node_id, max_node_id)

    # for some reason this still leaves a gap under the menu bar
    canvas_origin = (1, app_window.menu_height + 1)

    current_zoom = 1.0 / nedit.get_current_zoom()
    viewport_x, viewport_y = nedit.screen_to_canvas(canvas_origin)

    need_navigate = False
    need_zoom = False

    if current_zoom != app_window.zoom:
        if app_window.viewport_zoom_set:
            need_navigate = True
            need_zoom = True
        else:
            app_window.zoom = current_zoom

    app_window.viewport_zoom_set = False

    if app_window.view_x != viewport_x or app_window.view_y != viewport_y:
        if app_window.viewport_pos_set:
            need_navigate = True
        else:
            app_window.view_x = viewport_x
            app_window.view_y = viewport_y

    app_window.viewport_pos_set = False

    if need_navigate:
        window_size = (app_window.canvas_panel_width, app_window.canvas_panel_height)
        # navigate_to_selection expands the selection box by 10%
        EXP = 1.10
        dw = 0.5 * (1.0 - 1.0/EXP) * window_size[0]
        dh = 0.5 * (1.0 - 1.0/EXP) * window_size[1]
        upper_left = (
            app_window.view_x + dw,
            app_window.view_y + dh
        )
        canvas_dimensions = (
            (1.0 / app_window.zoom) * window_size[0],
            (1.0 / app_window.zoom) * window_size[1]
        )
        lower_right = (
            app_window.view_x + canvas_dimensions[0] - 2*dw,
            app_window.view_y + canvas_dimensions[1] - 2*dh
        )
        nedit.push_style_var(nedit.StyleVar.node_rounding, 0)
        nedit.push_style_var(nedit.StyleVar.node_padding, (0, 0, 0, 0))
        nedit.push_style_var(nedit.StyleVar.node_border_width, 0)

        nedit.set_node_position(app_window.viewport_box_nodes[0], upper_left)
        nedit.begin_node(app_window.viewport_box_nodes[0])
        nedit.end_node()

        nedit.set_node_position(
            app_window.viewport_box_nodes[1], lower_right
        )
        nedit.begin_node(app_window.viewport_box_nodes[1])
        nedit.end_node()
        nedit.pop_style_var(3)

        # save the current selection, then clear it
        selection = [
            obj for obj in app_window.objects if obj.selected
        ]
        for obj in selection:
            nedit.deselect_node(obj.node_id)

        # select the upper-left and lower-right nodes
        for obj_id in app_window.viewport_box_nodes:
            nedit.select_node(obj_id, True)

        # navigate to them
        nedit.navigate_to_selection(need_zoom, 0)
        app_window.imgui_needs_reselect = selection

    #############################
    # creation of links (by click-drag)
    if nedit.begin_create():
        start_pin = nedit.PinId.create()
        end_pin = nedit.PinId.create()
        if nedit.query_new_link(start_pin, end_pin):
            if start_pin and end_pin and nedit.accept_new_item():
                start_obj, start_port_id = all_pins.get(start_pin.id(), (None, None))
                end_obj, end_port_id = all_pins.get(end_pin.id(), (None, None))
                MFPGUI().async_task(
                    app_window.render_make_connection(start_obj, start_port_id[1], end_obj, end_port_id[1])
                )
        nedit.end_create()

    nedit.end()  # node_editor
    nedit.pop_style_color(5)

    imgui.end()

    # nothing in here can make us exit
    return True
