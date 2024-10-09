"""
menu_bar.py -- main menu
"""

from imgui_bundle import imgui


def render(app_window):
    quit_selected = False
    if imgui.begin_menu("File"):
        # Quit
        quit_selected, _ = imgui.menu_item("Quit", "Ctrl+Q", False)
        imgui.end_menu()

    if app_window.selected_patch and len(app_window.selected_patch.layers) > 0:
        if imgui.begin_menu("Layers"):
            for layer_num, layer in enumerate(app_window.selected_patch.layers):
                imgui.push_id(layer_num)
                layer_selected, _ = imgui.menu_item(
                    layer.name,
                    None,
                    app_window.selected_layer == layer
                )
                if layer_selected and app_window.selected_layer != layer:
                    app_window.layer_select(layer)
                imgui.pop_id()
            imgui.end_menu()

    return quit_selected
