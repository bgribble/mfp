"""
menu_bar.py -- main menu
"""

import re
from imgui_bundle import imgui
from mfp.gui.input_mode import InputMode

# items with checkmarks maintain their state here
toggle_items_state = {}


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
    # items with no separator. "value" could be either a binding
    # or a dict of bindings for a separator section or a submenu.
    for itemname, value in itemdict.items():
        if itemname.startswith("|"):
            continue
        if isinstance(value, dict):
            if imgui.begin_menu(itemname):
                add_menu_items(app_window, value)
                imgui.end_menu()
        else:
            keysym = value.keysym
            menu_path = value.menupath

            # items with [] or [x] preceding name (ie File > []Pause/unpause")
            # will have a checkmark when selected. Default is no check.
            toggle_state = None
            if itemname.startswith("["):
                default_toggle = False
                if itemname[1] == "x":
                    default_toggle = True
                    itemname = itemname[3:]
                else:
                    itemname = itemname[2:]
                toggle_state = toggle_items_state.setdefault(menu_path, default_toggle)

            # make the actual menu item
            item_selected, item_toggled = imgui.menu_item(
                itemname, keysym, toggle_state, value.enabled
            )

            # send synthesized keypress(es) if selected
            if item_selected:
                if toggle_state is not None:
                    toggle_items_state[menu_path] = item_toggled
                keys = [keysym]
                if ' ' in keysym and '- ' not in keysym:
                    keys = keysym.split(' ')
                for key in keys:
                    app_window.input_mgr.handle_keysym(key)

    # iterate over separators
    for separators in range(1, 10):
        sep_items = itemdict.get(separators * '|')
        if not sep_items:
            continue
        imgui.separator()
        add_menu_items(app_window, sep_items)


def load_menupaths(app_window, only_enabled=False):
    by_menu = {}

    # get all the input mode items
    for name, mode in InputMode._registry.items():
        for keysym, binding in mode._bindings.items():
            if binding.menupath:
                menupath = binding.menupath.split(" > ")
                submenu = by_menu
                keysym = binding.keysym
                always_on = False
                if mode._mode_prefix:
                    keysym = f"{mode._mode_prefix} {keysym}"
                    always_on = True
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

                if enabled or always_on:
                    submenu[item] = binding.copy(
                        keysym=keysym,
                        menupath=binding.menupath,
                        enabled=True
                    )
                elif item not in submenu and not only_enabled:
                    submenu[item] = binding.copy(
                        keysym=keysym,
                        menupath=binding.menupath,
                        enabled=False
                    )
    return by_menu


def render(app_window):
    quit_selected = False

    by_menu = load_menupaths(app_window)
    menu_open = False

    if imgui.begin_menu("File"):
        menu_open = True
        add_menu_items(app_window, by_menu.get("File", {}))
        imgui.end_menu()

    if imgui.begin_menu("Edit"):
        menu_open = True
        add_menu_items(app_window, by_menu.get("Edit", {}))
        imgui.end_menu()

    if imgui.begin_menu("Layer"):
        menu_open = True
        add_menu_items(app_window, by_menu.get("Layer", {}))
        if app_window.selected_patch and len(app_window.selected_patch.layers) > 0:
            imgui.separator()
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

    if imgui.begin_menu("Window"):
        menu_open = True
        add_menu_items(app_window, by_menu.get("Window", {}))
        imgui.end_menu()

    app_window.main_menu_open = menu_open

    return quit_selected
