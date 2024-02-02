import json
from functools import partial
from typing import List, Optional
from pathlib import Path

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .util import get_patch_rects


class ImagePatchWidget(QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._image_data: Optional[dict] = None
        self._image: Optional[QPixmap] = None
        self._zoom = 3

    def set_image(self, image_data: Optional[dict] = None):
        if image_data is None:
            self._image_data = image_data
            self._image = None
            self.setGeometry(QRect(0, 0, 10, 10))
        else:
            if not self._image_data or self._image_data["filename"] != image_data["filename"]:
                self._image = QPixmap(image_data["filename"])
                r = self._image.rect()
                r = QRect(QPoint(0, 0), QPoint(r.width() * self._zoom, r.height() * self._zoom))
                if self.geometry() != r:
                    self.setGeometry(r)
            self._image_data = image_data

        self.update()

    def set_zoom(self, zoom: int):
        self._zoom = zoom
        if self._image is not None:
            r = self._image.rect()
            r = QRect(QPoint(0, 0), QPoint(r.width() * self._zoom, r.height() * self._zoom))
            if self.geometry() != r:
                self.setGeometry(r)
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawRect(event.rect())

        if self._image_data is None:
            return

        painter.drawPixmap(self.rect(), self._image)

        painter.setBrush(Qt.NoBrush)
        for tiling in self._image_data["tilings"]:
            painter.setPen(QPen(QColor(255, 255, 255)))
            rects = get_patch_rects(self._image.size(), tiling, zoom=self._zoom)
            painter.drawRects(rects)
