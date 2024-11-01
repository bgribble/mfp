"""
menu_bar.py -- main menu
"""

import re
from imgui_bundle import imgui
from mfp import log
from mfp.gui.input_mode import InputMode


def splitsep(itemname):
    m = re.search(r"^(\|+)", itemname)
    if not m:
        return '', itemname

    separators = m.group(0)
    return separators, itemname[len(separators):]

def add_menu_items(app_window, itemdict):
    """
    Add items, separators, and submenus to the current menu
    """
    # first: items with no separator
    for itemname, value in itemdict.items():
        if itemname.startswith("|"):
            continue
        if isinstance(value, dict):
            if imgui.begin_menu(itemname):
                add_menu_items(app_window, value)
                imgui.end_menu()
        else:
            item_selected, _ = imgui.menu_item(itemname, value[4], False, value[6])
            if item_selected:
                app_window.input_mgr.handle_keysym(value[4])

    # then iterate over separators
    for separators in range(1, 10):
        sep_items = itemdict.get(separators * '|')
        if not sep_items:
            continue
        imgui.separator()
        add_menu_items(app_window, sep_items)

def render(app_window):
    quit_selected = False

    by_menu = {}

    # get all the input mode items
    for name, mode in InputMode._registry.items():
        for keysym, binding in mode._bindings.items():
            if binding[5]:
                menupath = binding[5].split(" > ")
                submenu = by_menu
                for menu in menupath[:-1]:
                    sep, item = splitsep(menu)
                    if not sep:
                        submenu = submenu.setdefault(item, {})
                    else:
                        sep_items = submenu.setdefault(sep, {})
                        submenu = sep_items.setdefault(item, {})

                sep, item = splitsep(menupath[-1])
                if sep:
                    submenu = submenu.setdefault(sep, {})

                # if there are multiple items with the same text,
                # one that's enabled wins
                enabled = app_window.input_mgr.mode_enabled(mode)
                if enabled:
                    submenu[item] = (*binding, True)
                elif item not in submenu:
                    submenu[item] = (*binding, False)

    if imgui.begin_menu("File"):
        add_menu_items(app_window, by_menu.get("File", {}))

        # Quit
        imgui.separator()
        quit_selected, _ = imgui.menu_item("Quit", "Ctrl+Q", False)
        imgui.end_menu()

    if imgui.begin_menu("Edit"):
        add_menu_items(app_window, by_menu.get("Edit", {}))
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
