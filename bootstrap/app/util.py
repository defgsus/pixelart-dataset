from copy import deepcopy
from typing import List

from PyQt5.QtCore import *
from PyQt5.QtGui import *


DEFAULT_TILING = {
    "offset_x": 0,
    "offset_y": 0,
    "patch_size_x": 16,
    "patch_size_y": 16,
    "spacing_x": 0,
    "spacing_y": 0,
}


def get_default_tiling(image_size: QSize):
    tiling = deepcopy(DEFAULT_TILING)

    min_size = min(image_size.width(), image_size.height())
    max_size = max(image_size.width(), image_size.height())

    if max_size <= 64 and max_size == min_size:
        tiling["patch_size_x"] = tiling["patch_size_y"] = max_size

    return tiling


def get_patch_rects(
        image_size: QSize,
        tiling: dict,
        zoom: int = 1,
) -> List[QRect]:
    stride_x = tiling["patch_size_x"] + tiling["spacing_x"]
    stride_y = tiling["patch_size_y"] + tiling["spacing_y"]

    rects = []
    for y in range(tiling["offset_y"], image_size.height(), stride_y):
        if y + tiling["patch_size_y"] <= image_size.height():
            for x in range(tiling["offset_x"], image_size.width(), stride_x):
                if x + tiling["patch_size_x"] <= image_size.width():
                    rects.append(QRect(
                        zoom * x,
                        zoom * y,
                        zoom * tiling["patch_size_x"],
                        zoom * tiling["patch_size_y"],
                    ))

    return rects
