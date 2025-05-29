"""
image_utils.py -- load and convert images
"""

import os
import numpy as np
from mfp import log
from mfp.gui_main import MFPGUI
from mfp.utils import find_file_in_path

image_cache = {}
texture_cache = {}


def image_to_texture(pil_image):
    from OpenGL import GL
    np_image = np.array(pil_image)
    if not(np_image.dtype == np.uint8 and np_image.ndim == 3 and np_image.shape[2] == 4):
        return None, 0, 0

    height, width = np_image.shape[:2]

    # Generate a texture ID
    texture_id = GL.glGenTextures(1)
    GL.glBindTexture(GL.GL_TEXTURE_2D, texture_id)

    # Set texture parameters (you may want to adjust this)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)

    # Upload the image
    GL.glTexImage2D(
        GL.GL_TEXTURE_2D,
        0,                  # level
        GL.GL_RGBA,            # internal format
        width,
        height,
        0,                  # border
        GL.GL_RGBA,            # input format
        GL.GL_UNSIGNED_BYTE,   # input type
        np_image
    )

    GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
    return texture_id, width, height


def load_texture_from_file(filename):
    if filename in texture_cache:
        return texture_cache[filename]

    pil_image = load_image_from_file(filename)
    texture_id, width, height = image_to_texture(pil_image)
    texture_cache[filename] = (texture_id, width, height)
    return texture_id, width, height


def load_image_from_file(filename):
    from PIL import Image
    if filename in image_cache:
        return image_cache[filename]

    loadpath = os.path.dirname(filename)
    loadfile = os.path.basename(filename)

    searchpath = MFPGUI().searchpath + ((':' + loadpath) if loadpath else "")

    path = find_file_in_path(loadfile, searchpath)
    if not path:
        return None

    pil_image = Image.open(path).convert("RGBA")
    image_cache[filename] = pil_image
    return pil_image
