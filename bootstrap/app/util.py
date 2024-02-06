from io import BytesIO
from copy import deepcopy
from typing import List, Generator, Tuple, Optional

from PyQt5.QtCore import *
from PyQt5.QtGui import *

import PIL.Image
import numpy as np


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
        if tiling.get("duplicates"):
            self.duplicate_tiles = set(tuple(t) for t in tiling["duplicates"])
        else:
            self.duplicate_tiles = set()
        if tiling.get("labels"):
            self.labels = {
                label: set(tuple(p) for p in positions)
                for label, positions in tiling["labels"].items()
            }
        else:
            self.labels = {}

    def rects(
            self,
            ignored: bool = False,
            duplicates: bool = False,
            yield_pos: bool = False,
            size_minus: int = 0,
    ) -> List[QRect]:
        return list(self.iter_rects(
            ignored=ignored, duplicates=duplicates, yield_pos=yield_pos, size_minus=size_minus
        ))

    def iter_rects(
            self,
            ignored: bool = False,
            duplicates: bool = False,
            yield_pos: bool = False,
            size_minus: int = 0,
            full_stride: bool = False,
    ) -> Generator[QRect, None, None]:

        patch_size_y = self.patch_size_y
        patch_size_x = self.patch_size_x
        if full_stride:
            patch_size_y = self.stride_y
            patch_size_x = self.stride_x

        for y in range(self.offset_y, self.image_size.height(), self.stride_y):
            if y + self.patch_size_y <= self.image_size.height():
                for x in range(self.offset_x, self.image_size.width(), self.stride_x):
                    if x + self.patch_size_x <= self.image_size.width():

                        tile_pos = self.to_tile_pos(self.zoom * y, self.zoom * x)
                        if ignored == (tile_pos in self.ignore_tiles) or duplicates:
                            if duplicates == (tile_pos in self.duplicate_tiles):

                                if not self.size_y or tile_pos[0] < self.size_y:
                                    if not self.size_x or tile_pos[1] < self.size_x:

                                        rect = QRect(
                                            self.zoom * x,
                                            self.zoom * y,
                                            self.zoom * patch_size_x - size_minus,
                                            self.zoom * patch_size_y - size_minus,
                                        )
                                        if yield_pos:
                                            yield rect, tile_pos
                                        else:
                                            yield rect

    def outside_polygon(self, display_rect: Optional[QRect] = None):
        if display_rect is None:
            display_rect = QRect(QPoint(0, 0), self.image_size * self.zoom)
        polygon = QPolygon(display_rect)
        for r in self.iter_rects(full_stride=True):
            if r.intersects(display_rect):
                polygon = polygon.subtracted(QPolygon(r))
        return polygon

    def to_tile_pos(self, y: int, x: int) -> Tuple[int, int]:
        return (
            (y // self.zoom - self.offset_y) // self.stride_y,
            (x // self.zoom - self.offset_x) // self.stride_x,
        )

    def is_ignored(self, *pos: int) -> bool:
        return pos in self.ignore_tiles

    def is_duplicate(self, *pos: int) -> bool:
        return pos in self.duplicate_tiles

    def get_labels_at(self, *pos: int) -> List[str]:
        labels = []
        for key, pos_set in self.labels.items():
            if pos in pos_set:
                labels.append(key)
        return labels


def qimage_to_pil(image: QImage) -> PIL.Image.Image:
    image = image.convertToFormat(QImage.Format_ARGB32)
    buffer = QBuffer()
    buffer.open(QBuffer.ReadWrite)
    image.save(buffer, "PNG")
    pil_im = PIL.Image.open(BytesIO(buffer.data()))
    return pil_im


def pil_to_qimage(image: PIL.Image.Image) -> QImage:
    buffer = BytesIO()
    image.save(buffer, "PNG")
    buffer.seek(0)
    image = QImage()
    image.loadFromData(buffer.read(), "PNG")
    return image


def qimage_to_numpy(image: QImage) -> np.ndarray:
    """
    Convert QImage to numpy array

    The image is converted to ARGB32 format before conversion.

    Result is in torch-style shape: [C, H, W], where C in (red, green, blue, alpha)

    """
    image = image.convertToFormat(QImage.Format_ARGB32)
    data = image.bits().asarray(image.byteCount())
    data = np.array(data, dtype=np.uint8).reshape(image.height(), image.width(), 4)
    data = data.transpose(2, 0, 1)
    return np.concatenate([data[2:3, :, :], data[1:2, :, :], data[0:1, :, :], data[3:4, :, :]], axis=0)


def numpy_to_qimage(data: np.ndarray) -> QImage:
    return pil_to_qimage(numpy_to_pil(data))


def numpy_to_pil(data: np.ndarray) -> PIL.Image.Image:
    data = data.transpose(1, 2, 0)
    data = data.reshape(data.shape[-1], data.shape[0], data.shape[1])
    image = PIL.Image.frombytes("RGBA", (data.shape[-1], data.shape[-2]), data.tobytes())
    return image


def get_qimage_from_source(image_data: dict) -> QImage:
    image = QImage(image_data["filename"])

    if image.hasAlphaChannel() or image_data.get("alpha"):
        image = image.convertToFormat(QImage.Format_ARGB32)
    else:
        image = image.convertToFormat(QImage.Format_RGB32)

    if image_data.get("alpha"):
        image_np = qimage_to_numpy(image)

        for color in image_data["alpha"]:
            mask = (image_np[0] == color[0]) & (image_np[1] == color[1]) & (image_np[2] == color[2])
            mask = ~mask

            image_np[3] = image_np[3] * mask

        image = numpy_to_qimage(image_np.astype(np.uint8))

    return image

