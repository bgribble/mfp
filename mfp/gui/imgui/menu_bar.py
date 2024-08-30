
from imgui_bundle import imgui

def render(app_window):
    clicked = False
    if imgui.begin_menu("File"):
        # Quit
        clicked, _ = imgui.menu_item("Quit", "Ctrl+Q", False)
        if clicked:
            keep_going = False
        imgui.end_menu()

    return clicked
