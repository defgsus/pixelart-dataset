from copy import deepcopy
from typing import List, Generator, Tuple, Optional

from PyQt5.QtCore import *
from PyQt5.QtGui import *


DEFAULT_TILING = {
    "offset_x": 0,
    "offset_y": 0,
    "patch_size_x": 16,
    "patch_size_y": 16,
    "spacing_x": 0,
    "spacing_y": 0,
    "size_x": 0,
    "size_y": 0,
}


def get_default_tiling(image_size: Optional[QSize] = None):
    tiling = deepcopy(DEFAULT_TILING)

    if image_size is None:
        return tiling

    min_size = min(image_size.width(), image_size.height())
    max_size = max(image_size.width(), image_size.height())

    if max_size <= 64 and max_size == min_size:
        tiling["patch_size_x"] = tiling["patch_size_y"] = max_size

    return tiling


class Tiling:
    
    def __init__(self, image_size: QSize, tiling: dict, zoom: int = 1):
        self.image_size = image_size
        self._tiling = tiling
        self.zoom = zoom

        self.offset_x = tiling["offset_x"]
        self.offset_y = tiling["offset_y"]
        self.patch_size_x = tiling["patch_size_x"]
        self.patch_size_y = tiling["patch_size_y"]
        self.stride_x = tiling["patch_size_x"] + tiling["spacing_x"]
        self.stride_y = tiling["patch_size_y"] + tiling["spacing_y"]
        #self.limit_x = tiling.get("limit_x") or image_size.width()
        #self.limit_y = tiling.get("limit_y") or image_size.height()
        self.size_x = tiling.get("size_x") or 0
        self.size_y = tiling.get("size_y") or 0
        if tiling.get("ignore"):
            self.ignore_tiles = set(tuple(t) for t in tiling["ignore"])
        else:
            self.ignore_tiles = set()

    def rects(self, ignored: bool = False) -> List[QRect]:
        return list(self.iter_rects(ignored=ignored))

    def iter_rects(self, ignored: bool = False) -> Generator[QRect, None, None]:
        for y in range(self.offset_y, self.image_size.height(), self.stride_y):
            if y + self.patch_size_y <= self.image_size.height():
                for x in range(self.offset_x, self.image_size.width(), self.stride_x):
                    if x + self.patch_size_x <= self.image_size.width():

                        tile_pos = self.to_tile_pos(self.zoom * y, self.zoom * x)
                        if ignored == (tile_pos in self.ignore_tiles):

                            if not self.size_y or tile_pos[0] < self.size_y:
                                if not self.size_x or tile_pos[1] < self.size_x:

                                    yield QRect(
                                        self.zoom * x,
                                        self.zoom * y,
                                        self.zoom * self.patch_size_x,
                                        self.zoom * self.patch_size_y,
                                    )

    def to_tile_pos(self, y: int, x: int) -> Tuple[int, int]:
        return (
            (y // self.zoom - self.offset_y) // self.stride_y,
            (x // self.zoom - self.offset_x) // self.stride_x,
        )
