"""
Helper to create raw GLFW window
"""
import os
import OpenGL.GL as gl
from PIL import Image

from imgui_bundle import imgui, ImVec2


def create_glfw_window(name, width, height, icon_path):
    import glfw
    if not glfw.init():
        print("Could not initialize OpenGL context")
        return None

    # OS X supports only forward-compatible core profiles from 3.2
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)

    # only available in glfw 3.4 and later
    glfw.window_hint_string(glfw.WAYLAND_APP_ID, name)

    # probably useless in Wayland backend
    glfw.window_hint_string(glfw.X11_CLASS_NAME, name)

    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, gl.GL_TRUE)


    # Create a windowed mode window and its OpenGL context
    window = glfw.create_window(
        int(width),
        int(height),
        name,
        None,
        None
    )

    glfw.make_context_current(window)
    glfw.set_window_focus_callback(window, lambda *args: mfplog.debug(f"focus: {args}"))
    glfw.set_key_callback(window, lambda *args: mfplog.debug(f"key: {args}"))

    glfw.show_window(window)
    icon_image = Image.open(icon_path)
    try:
        glfw.set_window_icon(
            window, 1, [icon_image]
        )
    except Exception:
        pass

    if not window:
        glfw.terminate()
        return None

    return window
