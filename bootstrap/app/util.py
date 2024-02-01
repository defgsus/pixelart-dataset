from typing import List

from PyQt5.QtCore import *
from PyQt5.QtGui import *


def get_patch_rects(image_size: QSize, tiling: dict, zoom: int = 1) -> List[QRect]:
    stride_x = tiling["patch_size"][0] + tiling["spacing"][0]
    stride_y = tiling["patch_size"][1] + tiling["spacing"][1]

    rects = []
    for y in range(tiling["offset"][1], image_size.height(), stride_y):
        for x in range(tiling["offset"][0], image_size.width(), stride_x):
            rects.append(QRect(
                zoom * x,
                zoom * y,
                zoom * tiling["patch_size"][0],
                zoom * tiling["patch_size"][1],
            ))

    return rects
