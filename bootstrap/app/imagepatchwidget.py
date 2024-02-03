import json
from functools import partial
from typing import List, Optional
from pathlib import Path

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .util import Tiling
from .labelmodel import LabelModel


class ImagePatchWidget(QWidget):

    signal_image_changed = pyqtSignal(dict)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._image_data: Optional[dict] = None
        self._image: Optional[QPixmap] = None
        self._zoom = 3
        self._tiling_index = 0
        self._tiling: Optional[Tiling] = None
        self._is_drawing = False
        self._draw_state = None
        self._mode = "tiles"
        self._current_label: Optional[dict] = None
        model = LabelModel(self)
        if model.rowCount():
            self._current_label = model.data(model.index(0, 0), role=Qt.ItemDataRole.UserRole)

    def set_image(self, image_data: Optional[dict] = None):
        if image_data is None:
            self._image_data = image_data
            self._image = None
            self._tiling_index = 0
            self._tiling = None
            self.setGeometry(QRect(0, 0, 10, 10))
        else:
            if not self._image_data or self._image_data["filename"] != image_data["filename"]:
                self._image = QPixmap(image_data["filename"])
                r = self._image.rect()
                r = QRect(QPoint(0, 0), QPoint(r.width() * self._zoom, r.height() * self._zoom))
                if self.geometry() != r:
                    self.setGeometry(r)

            self._image_data = image_data
            self._tiling_index = max(0, min(self._tiling_index, len(self._image_data["tilings"]) - 1))
            self._tiling = None
            if self._image_data["tilings"]:
                self._tiling = Tiling(self._image.size(), self._image_data["tilings"][self._tiling_index], zoom=self._zoom)

        self.update()

    def set_zoom(self, zoom: int):
        self._zoom = zoom
        if self._image is not None:
            r = self._image.rect()
            r = QRect(QPoint(0, 0), QPoint(r.width() * self._zoom, r.height() * self._zoom))
            if self.geometry() != r:
                self.setGeometry(r)

            if self._image_data["tilings"]:
                self._tiling = Tiling(self._image.size(), self._image_data["tilings"][self._tiling_index], zoom=self._zoom)

        self.update()

    def set_mode(self, mode: str):
        assert mode in ("tiles", "labels"), f"Got: {mode}"
        self._mode = mode
        self.update()

    def set_tiling_index(self, index: int):
        self._tiling_index = index
        self._tiling = None
        if self._image_data:
            self._tiling_index = min(self._tiling_index, len(self._image_data["tilings"]))
            if self._image_data["tilings"]:
                self._tiling = Tiling(self._image.size(), self._image_data["tilings"][self._tiling_index], zoom=self._zoom)
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawRect(event.rect())

        if self._image_data is None:
            return

        painter.drawPixmap(self.rect(), self._image)

        if self._tiling:
            if self._mode == "tiles":
                painter.setPen(QPen(QColor(255, 255, 255, 196)))
                painter.setBrush(QBrush(QColor(255, 255, 255, 50)))
                painter.drawRects(self._tiling.rects(size_minus=1))

                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(255, 128, 128, 196)))
                painter.drawRects(self._tiling.rects(ignored=True))

                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(64, 0, 0, 196)))
                painter.drawRects(self._tiling.rects(duplicates=True))

            elif self._mode == "labels":
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(0, 0, 0, 128)))
                #painter.drawRects(self._tiling.rects(all_the_rest=True))

                if self._current_label:

                    for label, pos_set in self._tiling.labels.items():

                        if self._current_label and self._current_label["name"] == label:
                            color = self._current_label["color"]
                            painter.setPen(QPen(QColor(*color).lighter()))
                            painter.setBrush(QBrush(QColor(*color, 128)))
                        else:
                            painter.setPen(Qt.NoPen)
                            painter.setBrush(QBrush(QColor(0, 0, 0, 196)))

                        rects = []
                        for rect, pos in self._tiling.iter_rects(size_minus=1, yield_pos=True):
                            if pos in pos_set:
                                rects.append(rect)
                        if rects:
                            painter.drawRects(rects)

    def mousePressEvent(self, event: QMouseEvent):
        if self._tiling:
            pos = self._tiling.to_tile_pos(event.y(), event.x())
            if self._mode == "tiles":
                self._draw_state = self.swap_ignore_tile(*pos)
                if self._draw_state is not None:
                    self._is_drawing = True
                    self.update()
                    self.signal_image_changed.emit(self._image_data)

            elif self._mode == "labels":
                if self._current_label:
                    self._draw_state = pos not in self._tiling.labels.get(self._current_label["name"], tuple())
                    self.set_label_tile(*pos, label=self._current_label["name"], remove=not self._draw_state)
                    self._is_drawing = True
                    self.update()
                    self.signal_image_changed.emit(self._image_data)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._tiling and self._is_drawing:
            pos = self._tiling.to_tile_pos(event.y(), event.x())

            if self._mode == "tiles":
                if self.set_ignor_tile(*pos, state=self._draw_state):
                    self.update()
                    self.signal_image_changed.emit(self._image_data)

            elif self._mode == "labels" and self._current_label:
                if self.set_label_tile(*pos, label=self._current_label["name"], remove=not self._draw_state):
                    self.update()
                    self.signal_image_changed.emit(self._image_data)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._is_drawing = False

    def swap_ignore_tile(self, *pos: int) -> Optional[bool]:
        next_state = pos not in self._tiling.ignore_tiles
        if next_state is not None:
            self.set_ignor_tile(*pos, state=next_state)
        return next_state

    def set_ignor_tile(self, *pos: int, state: bool) -> Optional[bool]:
        if pos in self._tiling.duplicate_tiles:
            return None

        ret = False

        if not state:
            if pos in self._tiling.ignore_tiles:
                self._tiling.ignore_tiles.remove(pos)
                ret = True
        else:
            if pos not in self._tiling.ignore_tiles:
                self._tiling.ignore_tiles.add(pos)
                ret = True

        if self._tiling.ignore_tiles:
            self._image_data["tilings"][self._tiling_index]["ignore"] = list(self._tiling.ignore_tiles)
        else:
            self._image_data["tilings"][self._tiling_index].pop("ignore", None)

        return ret

    def set_label(self, label: dict):
        self._current_label = label
        self.update()

    def set_label_tile(self, *pos: int, label: Optional[str], remove: bool = False) -> bool:
        is_changed = False

        pos_set = self._tiling.labels.get(label, tuple())
        if remove:
            if pos in pos_set:
                pos_set.remove(pos)
                is_changed = True
            if not pos_set:
                self._tiling.labels.pop(label)
        else:
            if label not in self._tiling.labels:
                self._tiling.labels[label] = set()
            if pos not in self._tiling.labels[label]:
                self._tiling.labels[label].add(pos)
                is_changed = True

        if self._tiling.labels:
            self._image_data["tilings"][self._tiling_index]["labels"] = {
                l: list(p)
                for l, p in self._tiling.labels.items()
            }
        else:
            self._image_data["tilings"][self._tiling_index].pop("labels", None)

        return is_changed
