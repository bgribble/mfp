"""
canvas_pane -- render the 'imgui node editor' canvas pane

Copyright (c) Bill Gribble <grib@billgribble.com>
"""
import math

from imgui_bundle import imgui, imgui_node_editor as nedit
from mfp.gui_main import MFPGUI
from mfp.gui.colordb import ColorDB
from mfp.gui.connection_element import ConnectionElement
from mfp.gui.modes.patch_edit import PatchEditMode
from mfp.gui.modes.global_mode import GlobalMode
from . import menu_bar


def render_selection_box(app_window, pane_origin, canvas_origin, tile):
    draw_list = imgui.get_foreground_draw_list()
    outline_color = app_window.get_color('selbox-stroke-color')
    fill_color = app_window.get_color('selbox-fill-color')

    # in canvas coordinates
    x0, y0, x1, y1 = app_window.selection_box_bounds

    pmin = (
        pane_origin[0]
        + canvas_origin[0]
        + tile.origin_x
        - tile.view_x * tile.view_zoom
        + x0 * tile.view_zoom,
        pane_origin[1]
        + canvas_origin[1]
        + tile.origin_y
        - tile.view_y * tile.view_zoom
        + y0 * tile.view_zoom
    )

    pmax = (
        pane_origin[0]
        + canvas_origin[0]
        + tile.origin_x
        - tile.view_x * tile.view_zoom
        + x1 * tile.view_zoom,
        pane_origin[1]
        + canvas_origin[1]
        + tile.origin_y
        - tile.view_y * tile.view_zoom
        + y1 * tile.view_zoom
    )

    draw_list.push_clip_rect(
        (pane_origin[0] + canvas_origin[0] + tile.origin_x,
         pane_origin[1] + canvas_origin[1] + tile.origin_y),
        (pane_origin[0] + canvas_origin[0] + tile.origin_x + tile.width,
         pane_origin[1] + canvas_origin[1] + tile.origin_y + tile.height),
    )

    draw_list.add_rect_filled(
        pmin, pmax,
        ColorDB().backend.im_col32(fill_color),
        0, 0
    )
    draw_list.add_rect(
        pmin, pmax,
        ColorDB().backend.im_col32(outline_color),
        0, 0, 1.0
    )
    draw_list.pop_clip_rect()


def render_tile(app_window, patch):
    """
    render a patch tile
    """
    # for some reason this still leaves a gap under the menu bar
    canvas_pane_origin = (1, app_window.menu_height + 1)

    tile = patch.display_info

    imgui.set_next_window_size((tile.width, tile.height))
    imgui.set_next_window_pos((
        canvas_pane_origin[0] + tile.origin_x,
        canvas_pane_origin[1] + tile.origin_y
    ))

    if not hasattr(patch, 'nedit_editor'):
        patch.nedit_editor = nedit.create_editor(app_window.nedit_config)
    nedit.set_current_editor(patch.nedit_editor)

    imgui.begin(
        f"{patch.obj_name} ({tile.page_id}.{tile.tile_id})",
        flags=(
            imgui.WindowFlags_.no_collapse
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_resize
        ),
    )

    if imgui.is_window_hovered(imgui.FocusedFlags_.child_windows):
        app_window.selected_window = "canvas"
        if not isinstance(app_window.input_mgr.global_mode, GlobalMode):
            app_window.input_mgr.global_mode = GlobalMode(app_window)
            app_window.input_mgr.major_mode.enable()
        if app_window.imgui_tile_selected:
            app_window.layer_select(patch.selected_layer)
            app_window.imgui_tile_selected = False

    if app_window.viewport_selection_set:
        if app_window.selected_patch == patch:
            imgui.set_window_focus()
            app_window.viewport_selection_set = False
    elif imgui.is_window_focused(imgui.FocusedFlags_.child_windows):
        app_window.selected_patch = patch
        app_window.selected_layer = patch.selected_layer

    # get_cursor_pos appears to be relative to the origin of the current window
    cursor_pos = imgui.get_cursor_pos()

    # canvas_origin is the screen offset of the upper-left of the canvas
    # relative to the tile (accounting for the tile title bar)
    canvas_origin = (cursor_pos[0], cursor_pos[1])
    tile.frame_offset_x = cursor_pos[0]
    tile.frame_offset_y = cursor_pos[1]

    ###################
    # set up for imgui-node-editor

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

    if (
        isinstance(app_window.input_mgr.major_mode, PatchEditMode)
        and app_window.selected_patch == patch
    ):
        nedit.push_style_color(
            nedit.StyleColor.grid,
            app_window.get_color('grid-color:edit').to_rgbaf()
        )
    else:
        nedit.push_style_color(
            nedit.StyleColor.grid,
            app_window.get_color('grid-color:operate').to_rgbaf()
        )

    nedit.begin("canvas_editor", (0.0, 0.0))

    conf = nedit.get_config()

    # disable NodeEditor dragging and selecting
    conf.drag_button_index = 3
    conf.select_button_index = 3

    # reselect nodes if needed (part of the hack to resize the viewport)
    if app_window.imgui_needs_reselect:
        nedit.clear_selection()
        for obj in app_window.imgui_needs_reselect:
            if isinstance(obj, ConnectionElement):
                nedit.select_link(obj.node_id, True)
            else:
                nedit.select_node(obj.node_id, True)
        app_window.imgui_needs_reselect = []

    if patch.selected_layer:
        # first pass: non-links
        all_pins = {}
        for obj in sorted(patch.selected_layer.objects, key=lambda o: o.position_z):
            if not isinstance(obj, ConnectionElement):
                obj.render()
                for port_id, pin_id in obj.port_elements.items():
                    all_pins[pin_id.id()] = (obj, port_id)

        # second pass: links
        for obj in sorted(app_window.objects, key=lambda o: o.position_z):
            if obj.layer == patch.selected_layer and isinstance(obj, ConnectionElement):
                obj.render()

    # draw the autoplace target
    if app_window.selected_patch == patch and app_window.autoplace_x is not None:
        color = ColorDB().backend.im_col32(app_window.get_color('stroke-color:selected'))

        autoplace_window_pos = [
            app_window.autoplace_x,
            app_window.autoplace_y
        ]
        draw_list = imgui.get_window_draw_list()
        mark_radius = 6
        draw_list.add_circle(autoplace_window_pos, mark_radius, color, 21, 1.0)
        draw_list.path_arc_to(
            autoplace_window_pos,
            mark_radius,
            0, math.pi/2, 13
        )
        draw_list.path_line_to(autoplace_window_pos)
        draw_list.path_fill_convex(color)

        draw_list.path_arc_to(
            autoplace_window_pos,
            mark_radius,
            math.pi, 1.5*math.pi, 13
        )
        draw_list.path_line_to(autoplace_window_pos)
        draw_list.path_fill_convex(color)

    # draw the selection rectangle if needed
    if app_window.selected_patch == patch and app_window.selection_box_bounds is not None:
        render_selection_box(
            app_window,
            canvas_pane_origin,
            canvas_origin,
            tile
        )

    #############################
    # viewport management
    # this is janky. We create an invisible upper-left and lower-right
    # node that we will use wth zoom_to_selection()

    # create nodes if needed
    if not hasattr(patch, 'viewport_box_nodes'):
        min_node_id = nedit.NodeId.create()
        max_node_id = nedit.NodeId.create()
        patch.viewport_box_nodes = (min_node_id, max_node_id)

    current_zoom = 1.0 / nedit.get_current_zoom()

    # nedit.screen_to_canvas wants true screen coordinates?
    viewport_x, viewport_y = nedit.screen_to_canvas((
        canvas_pane_origin[0] + tile.origin_x + canvas_origin[0],
        canvas_pane_origin[1] + tile.origin_y + canvas_origin[1]
    ))

    need_navigate = False
    need_zoom = False

    if current_zoom != tile.view_zoom:
        if app_window.viewport_zoom_set:
            need_navigate = True
            need_zoom = True
        else:
            tile.view_zoom = current_zoom

    if tile.view_x != viewport_x or tile.view_y != viewport_y:
        if app_window.viewport_pos_set:
            need_navigate = True
        elif not app_window.viewport_drag_active:
            tile.view_x = viewport_x
            tile.view_y = viewport_y

    if need_navigate:
        window_size = (tile.width - canvas_origin[0], tile.height - canvas_origin[1])

        # navigate_to_selection expands the selection box by 10%
        EXP = 1.10
        dw = 0.5 * (1.0 - 1.0/EXP) * window_size[0]
        dh = 0.5 * (1.0 - 1.0/EXP) * window_size[1]

        upper_left = (
            tile.view_x + dw,
            tile.view_y + dh
        )
        canvas_dimensions = (
            (1.0 / tile.view_zoom) * window_size[0],
            (1.0 / tile.view_zoom) * window_size[1]
        )
        lower_right = (
            tile.view_x + canvas_dimensions[0] - 2*dw,
            tile.view_y + canvas_dimensions[1] - 2*dh
        )
        nedit.push_style_var(nedit.StyleVar.node_rounding, 0)
        nedit.push_style_var(nedit.StyleVar.node_padding, (0, 0, 0, 0))
        nedit.push_style_var(nedit.StyleVar.node_border_width, 0)

        nedit.set_node_position(patch.viewport_box_nodes[0], upper_left)
        nedit.begin_node(patch.viewport_box_nodes[0])
        nedit.end_node()

        nedit.set_node_position(patch.viewport_box_nodes[1], lower_right)
        nedit.begin_node(patch.viewport_box_nodes[1])
        nedit.end_node()

        nedit.pop_style_var(3)

        # save the current selection, then clear it
        selection = [
            obj for obj in app_window.objects if obj.selected
        ]
        for obj in selection:
            if isinstance(obj, ConnectionElement):
                nedit.deselect_link(obj.node_id)
            else:
                nedit.deselect_node(obj.node_id)

        # select the upper-left and lower-right nodes
        for obj_id in patch.viewport_box_nodes:
            nedit.select_node(obj_id, True)

        # navigate to them
        nedit.navigate_to_selection(need_zoom, 0)
        app_window.imgui_prevent_idle = 10
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
                    app_window.render_make_connection(
                        start_obj, start_port_id[1], end_obj, end_port_id[1]
                    )
                )
        nedit.end_create()

    #################
    # context menu
    nedit.suspend()
    imgui.push_style_var(imgui.StyleVar_.window_padding, (8, 8))
    imgui.push_style_var(imgui.StyleVar_.item_spacing, (3, 3))
    node_id = nedit.NodeId.create()
    if nedit.show_node_context_menu(node_id):
        imgui.open_popup("##context menu popup")

    if imgui.begin_popup("##context menu popup"):
        mouse_pos = imgui.get_mouse_pos_on_opening_current_popup()
        cursor_pos = (mouse_pos[0] + 8, mouse_pos[1] + 8)
        imgui.set_cursor_screen_pos(cursor_pos)
        app_window.context_menu_open = True
        menu_items = menu_bar.load_menupaths(app_window, only_enabled=True)
        context_items = menu_items.get("Context", {})
        menu_bar.add_menu_items(app_window, context_items)
        imgui.end_popup()
    else:
        app_window.context_menu_open = False
    imgui.pop_style_var(2)
    nedit.resume()
    # context menu
    #################

    nedit.end()  # node_editor
    nedit.pop_style_color(5)

    imgui.end()


def render(app_window):
    imgui.begin(
        "canvas",
        flags=(
            imgui.WindowFlags_.no_collapse
            | imgui.WindowFlags_.no_move
            | imgui.WindowFlags_.no_title_bar
            | imgui.WindowFlags_.no_bring_to_front_on_focus
        ),
    )

    if imgui.is_window_hovered(imgui.FocusedFlags_.child_windows):
        app_window.selected_window = "canvas"
        if not isinstance(app_window.input_mgr.global_mode, GlobalMode):
            app_window.input_mgr.global_mode = GlobalMode(app_window)
            app_window.input_mgr.major_mode.enable()

    displayed_patches = [
        p for p in app_window.patches
        if p.display_info.page_id == app_window.canvas_tile_page
    ]

    for tile_num, patch in enumerate(displayed_patches):
        imgui.push_id(tile_num)
        render_tile(app_window, patch)
        imgui.pop_id()

    app_window.viewport_zoom_set = False
    app_window.viewport_pos_set = False

    imgui.end()

    app_window.imgui_selection_started = False

    # nothing in here can make us exit
    return True
