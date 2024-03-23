"""
Helper to create raw GLFW window
"""
import OpenGL.GL as gl
from PIL import Image

from mfp import log as mfplog
from imgui_bundle import imgui, ImVec2
from sdl2 import *
import os


def update_sdl2_keymap(renderer):
    renderer.key_map[SDL_SCANCODE_0] = imgui.Key(536)

    for index, key in enumerate("123456789"):
        renderer.key_map[SDL_SCANCODE_1 + index] = imgui.Key(index + 537)

    for index, key in enumerate("abcdefghijklmnopqrstuvwxyz"):
        renderer.key_map[SDL_SCANCODE_A + index] = imgui.Key(index + 546)

    renderer.key_map[SDL_SCANCODE_APOSTROPHE] = imgui.Key(596)
    renderer.key_map[SDL_SCANCODE_COMMA] = imgui.Key(597)
    renderer.key_map[SDL_SCANCODE_MINUS] = imgui.Key(598)
    renderer.key_map[SDL_SCANCODE_PERIOD] = imgui.Key(599)
    renderer.key_map[SDL_SCANCODE_SLASH] = imgui.Key(600)
    renderer.key_map[SDL_SCANCODE_SEMICOLON] = imgui.Key(601)
    renderer.key_map[SDL_SCANCODE_EQUALS] = imgui.Key(602)
    renderer.key_map[SDL_SCANCODE_LEFTBRACKET] = imgui.Key(603)
    renderer.key_map[SDL_SCANCODE_BACKSLASH] = imgui.Key(604)
    renderer.key_map[SDL_SCANCODE_RIGHTBRACKET] = imgui.Key(605)
    renderer.key_map[SDL_SCANCODE_GRAVE] = imgui.Key(606)

    # Fn keys
    for index in range(12):
        renderer.key_map[SDL_SCANCODE_F1 + index] = imgui.Key(572 + index)



def create_sdl2_window(name, width, height, icon_path):
    os.environ['SDL_VIDEO_X11_WMCLASS'] = "mfp"

    if SDL_Init(SDL_INIT_EVERYTHING) < 0:
        mfplog.error(
            "[sdl2] Error: SDL could not initialize! SDL Error: "
            + SDL_GetError().decode("utf-8")
        )
        return None, None

    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1)
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 24)
    SDL_GL_SetAttribute(SDL_GL_STENCIL_SIZE, 8)
    SDL_GL_SetAttribute(SDL_GL_ACCELERATED_VISUAL, 1)
    SDL_GL_SetAttribute(SDL_GL_MULTISAMPLEBUFFERS, 1)
    SDL_GL_SetAttribute(SDL_GL_MULTISAMPLESAMPLES, 8)
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_FLAGS, SDL_GL_CONTEXT_FORWARD_COMPATIBLE_FLAG)
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 4)
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1)
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK, SDL_GL_CONTEXT_PROFILE_CORE)

    SDL_SetHint(SDL_HINT_MAC_CTRL_CLICK_EMULATE_RIGHT_CLICK, b"1")
    SDL_SetHint(SDL_HINT_VIDEO_HIGHDPI_DISABLED, b"1")
    SDL_SetHint(SDL_HINT_VIDEODRIVER, b"wayland,x11")
    SDL_SetHint(SDL_HINT_VIDEO_X11_FORCE_EGL, b"1")
    SDL_SetHint(SDL_HINT_APP_NAME, name.encode('utf-8'))

    window = SDL_CreateWindow(
        name.encode("utf-8"),
        SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED,
        width,
        height,
        SDL_WINDOW_OPENGL | SDL_WINDOW_RESIZABLE,
    )

    if window is None:
        mfplog.error(
            "[sdl2] Error: Window could not be created! SDL Error: "
            + SDL_GetError().decode("utf-8")
        )
        return None, None

    gl_context = SDL_GL_CreateContext(window)
    if gl_context is None:
        mfplog.error(
            "[sdl2] Error: Cannot create OpenGL Context! SDL Error: "
            + SDL_GetError().decode("utf-8")
        )
        return None, None

    SDL_GL_MakeCurrent(window, gl_context)
    if SDL_GL_SetSwapInterval(1) < 0:
        mfplog.error(
            "[sdl2] Error: Unable to set VSync! SDL Error: " + SDL_GetError().decode("utf-8")
        )
        return None, None
    mfplog.debug(f"[sdl2] Created window={window} context={gl_context}")
    return window, gl_context


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
