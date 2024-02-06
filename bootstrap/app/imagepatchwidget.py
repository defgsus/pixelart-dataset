import json
from functools import partial
from typing import List, Optional
from copy import deepcopy
from pathlib import Path

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .util import Tiling, get_qimage_from_source
from .labelmodel import LabelModel
from .selectlabelbox import SelectLabelBox


class ImagePatchWidget(QWidget):

    signal_info_changed = pyqtSignal(str)
    signal_image_changed = pyqtSignal(dict)
    signal_set_label = pyqtSignal(dict)

    signal_color_selected = pyqtSignal(QColor)

    def __init__(self, *args, **kwargs):
        from .imagepatcheditor import ImagePatchEditorControls

        super().__init__(*args, **kwargs)
        self._image_data: Optional[dict] = None
        self._image: Optional[QImage] = None
        self._zoom = 3
        self._tiling_index = 0
        self._tiling: Optional[Tiling] = None
        self._outside_control_widget: Optional[ImagePatchEditorControls] = None
        self._control_widget: Optional[ImagePatchWidgetControls] = None
        self._background = "cross"
        self._is_color_select = False
        self._is_drawing = False
        self._draw_state = None
        self._mode = "tiles"
        self._current_label: Optional[dict] = None
        self._last_hover_label_pos = None
        self._label_select_box: Optional[SelectLabelBox] = None
        self._outside_polygon: Optional[QPolygon] = None
        self._last_outside_polygon_rect: Optional[QRect] = None
        self.label_model = None

        # quickly load throw-away label model
        #   later self.label_model is assigned to the one that is updated by the new-label action
        model = LabelModel(self)
        if model.rowCount():
            self._current_label = model.data(model.index(0, 0), role=Qt.ItemDataRole.UserRole)

        self.setMouseTracking(True)

    def create_control_widget(self) -> QWidget:
        self._control_widget = ImagePatchWidgetControls(self)
        self._control_widget.signal_background_changed.connect(self.set_background)
        self._control_widget.signal_select_color.connect(self._select_color)
        self._control_widget.signal_image_changed.connect(self._update_image_from_control)
        self.signal_color_selected.connect(self._control_widget.set_selected_color)

        return self._control_widget

    def set_image(self, image_data: Optional[dict] = None):
        if image_data is None:
            self._image_data = image_data
            self._image = None
            self._tiling_index = 0
            self._tiling = None
            self._outside_polygon = None
            self.setGeometry(QRect(0, 0, 10, 10))
        else:
            if (not self._image_data
                    or self._image_data["filename"] != image_data["filename"]
                    or self._image_data.get("alpha") != image_data.get("alpha")
            ):
                self._image = get_qimage_from_source(image_data)
                r = self._image.rect()
                r = QRect(QPoint(0, 0), QPoint(r.width() * self._zoom, r.height() * self._zoom))
                if self.geometry() != r:
                    self.setGeometry(r)

            self._image_data = deepcopy(image_data)
            self._tiling_index = max(0, min(self._tiling_index, len(self._image_data["tilings"]) - 1))
            self._tiling = None
            self._outside_polygon = None
            if self._image_data["tilings"]:
                self._tiling = Tiling(self._image.size(), self._image_data["tilings"][self._tiling_index], zoom=self._zoom)

            if self._control_widget:
                self._control_widget.set_image_data(self._image_data, self._image, self._tiling)

        self._label_select_box = None
        self.update()

    def set_zoom(self, zoom: int):
        self._zoom = zoom
        self._outside_polygon = None
        if self._image is not None:
            r = self._image.rect()
            r = QRect(QPoint(0, 0), QPoint(r.width() * self._zoom, r.height() * self._zoom))
            if self.geometry() != r:
                self.setGeometry(r)

            if self._image_data["tilings"]:
                self._tiling = Tiling(self._image.size(), self._image_data["tilings"][self._tiling_index], zoom=self._zoom)

            if self._control_widget:
                self._control_widget.set_image_data(self._image_data, self._image, self._tiling)

        self.update()

    def set_mode(self, mode: str):
        assert mode in ("tiles", "labels"), f"Got: {mode}"
        self._mode = mode
        self._label_select_box = None
        self._outside_polygon = None
        self.update()

    def set_tiling_index(self, index: int):
        self._label_select_box = None
        self._tiling_index = index
        self._tiling = None
        self._outside_polygon = None
        if self._image_data:
            self._tiling_index = min(self._tiling_index, len(self._image_data["tilings"]))
            if self._image_data["tilings"]:
                self._tiling = Tiling(self._image.size(), self._image_data["tilings"][self._tiling_index], zoom=self._zoom)
                self.update_info_label(0, 0)

            if self._control_widget:
                self._control_widget.set_image_data(self._image_data, self._image, self._tiling)

        self.update()

    def set_background(self, mode: str):
        self._background = mode
        self.update()

    def paintEvent(self, event: QPaintEvent):
        if self._last_outside_polygon_rect != event.rect():
            if self._last_outside_polygon_rect is None or not self._last_outside_polygon_rect.contains(event.rect()):
                self._last_outside_polygon_rect = event.rect()
                self._outside_polygon = None

        painter = QPainter(self)
        if not self._is_color_select:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            painter.setPen(Qt.NoPen)
            brush = QBrush(QColor(0, 0, 0))
            if self._background == "cross":
                brush = QBrush(QColor(128, 128, 128), Qt.BrushStyle.DiagCrossPattern)
            elif self._background == "black":
                pass
            elif self._background == "white":
                brush = QBrush(QColor(255, 255, 255))
            elif self._background == "red":
                brush = QBrush(QColor(255, 0, 0))
            elif self._background == "green":
                brush = QBrush(QColor(0, 255, 0))
            elif self._background == "blue":
                brush = QBrush(QColor(0, 0, 255))

            painter.setBrush(brush)
            painter.drawRect(event.rect())

        if self._image_data is None:
            return

        painter.drawImage(self.rect(), self._image)

        if self._is_color_select:
            return

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
                painter.setBrush(QBrush(QColor(0, 0, 0, 196)))
                if self._outside_polygon is None:
                    # print("calc", event.rect(), self._last_outside_polygon_rect)
                    self._outside_polygon = self._tiling.outside_polygon(event.rect())
                painter.drawPolygon(self._outside_polygon)

                if self._current_label:
                    for label, pos_set in self._tiling.labels.items():

                        if self._current_label and self._current_label["name"] == label:
                            color = self._current_label["color"]
                            painter.setPen(QPen(QColor(*color).lighter()))
                            col = QColor(*color).darker()
                            col.setAlpha(140)
                            painter.setBrush(QBrush(col))
                        else:
                            painter.setPen(Qt.NoPen)
                            painter.setBrush(QBrush(QColor(0, 0, 0, 160)))

                        rects = []
                        for rect, pos in self._tiling.iter_rects(size_minus=1, yield_pos=True):
                            if pos in pos_set:
                                rects.append(rect)
                        if rects:
                            painter.drawRects(rects)

    def mousePressEvent(self, event: QMouseEvent):
        if self._tiling:

            if self._is_color_select:
                self._is_color_select = False
                self.signal_color_selected.emit(self._image.pixelColor(event.x() // self._zoom, event.y() // self._zoom))
                return

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

            self.update_info_label(*pos)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._tiling:
            pos = self._tiling.to_tile_pos(event.y(), event.x())

            if self._is_drawing:

                if self._mode == "tiles":
                    if self.set_ignor_tile(*pos, state=self._draw_state):
                        self.update()
                        self.signal_image_changed.emit(self._image_data)

                elif self._mode == "labels" and self._current_label:
                    if self.set_label_tile(*pos, label=self._current_label["name"], remove=not self._draw_state):
                        self.update()
                        self.signal_image_changed.emit(self._image_data)

            if pos != self._last_hover_label_pos:
                self._last_hover_label_pos = pos
                self.update_info_label(*pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._is_drawing = False

    def update_info_label(self, *pos: int):
        text = [
            f"tiling #{self._tiling_index + 1}, pos x={pos[1]} y={pos[0]}"
        ]

        if self._tiling:
            if self._tiling.is_duplicate(*pos):
                text.append("duplicate")

            if self._tiling.is_ignored(*pos):
                text.append("ignored")

            labels = self._tiling.get_labels_at(*pos)
            if labels:
                labels = ', '.join(f'"{l}"' for l in labels)
                text.append(f"labels: {labels}")

        self.signal_info_changed.emit(", ".join(text))

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
            # clean-up the label dict
            if not pos_set and label in self._tiling.labels:
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

    def enterEvent(self, event):
        if not self._label_select_box:
            self.grabKeyboard()

    def leaveEvent(self, event):
        self.releaseKeyboard()

    def keyPressEvent(self, event: QKeyEvent):
        if self._mode == "labels" and ord("A") <= event.key() <= ord("Z") and not self._label_select_box:
            self.releaseKeyboard()
            self._label_select_box = SelectLabelBox(self, init_text=chr(event.key()).lower())
            self._label_select_box.signal_set_label.connect(self.signal_set_label)
            self._label_select_box.signal_closed.connect(self._select_closed)
            self._label_select_box.setModal(True)
            self._label_select_box.show()

    def _select_closed(self):
        self._label_select_box = None

    def _select_color(self):
        self._is_color_select = True
        self.update()

    def _update_image_from_control(self, image_data: dict):
        # image_data = deepcopy(image_data)
        self.set_image(image_data)
        self.signal_image_changed.emit(image_data)


class ImagePatchWidgetControls(QWidget):

    signal_image_changed = pyqtSignal(dict)
    signal_background_changed = pyqtSignal(str)
    signal_select_color = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._image_data: Optional[dict] = None
        self._image: Optional[QImage] = None
        self._tiling: Optional[Tiling] = None

        self._create_widgets()

    def _create_widgets(self):
        lv = QVBoxLayout(self)

        self.channel_label = QLabel(self)
        lv.addWidget(self.channel_label)
        lv.addSpacing(10)

        lv.addWidget(QLabel("background:"))
        self.background_select = QComboBox(self)
        lv.addWidget(self.background_select)
        for key in ("cross", "black", "white", "red", "green", "blue"):
            self.background_select.addItem(key)
        self.background_select.currentTextChanged.connect(self.signal_background_changed)
        lv.addSpacing(10)

        lv.addWidget(QLabel("alpha channels:"))

        lh = QHBoxLayout()
        lv.addLayout(lh)
        self.add_alpha_butt = QPushButton("add color", self)
        self.add_alpha_butt.setCheckable(True)
        self.add_alpha_butt.clicked.connect(self._add_alpha_click)
        lv.addWidget(self.add_alpha_butt)

        self.alpha_label = QLabel(self)
        lv.addWidget(self.alpha_label)

        self.remove_alpha_butt = QPushButton("remove color", self)
        self.remove_alpha_butt.clicked.connect(self._remove_alpha_click)
        self.remove_alpha_butt.setDisabled(True)
        lv.addWidget(self.remove_alpha_butt)

        lv.addStretch(1)

    def set_image_data(self, image_data: dict, image: QImage, tiling: Tiling):
        self._image_data = deepcopy(image_data)
        self._image = image
        self._tiling = tiling

        format_map = {
            QPixelFormat.ColorModel.RGB: "RGB",
            QPixelFormat.ColorModel.BGR: "BGR",
            QPixelFormat.ColorModel.Indexed: "Indexed",
            QPixelFormat.ColorModel.Grayscale: "Grayscale",
            QPixelFormat.ColorModel.CMYK: "CMYK",
            QPixelFormat.ColorModel.HSL: "HSL",
            QPixelFormat.ColorModel.HSV: "HSV",
            QPixelFormat.ColorModel.YUV: "YUV",
            QPixelFormat.ColorModel.Alpha: "Alpha",
        }

        format_str = format_map.get(self._image.pixelFormat().colorModel(), str(self._image.format()))
        if self._image.hasAlphaChannel():
            format_str += "(A)"
        self.channel_label.setText(f"{self._image.width()}x{self._image.height()}x{format_str}")

        self.alpha_label.setText(
            ", ".join(
                f"{[', '.join(str(c) for c in color)]}"
                for color in (self._image_data.get("alpha") or [])
            )
        )

    def set_selected_color(self, color: QColor):
        color = [color.red(), color.green(), color.blue()]

        if not self._image_data.get("alpha"):
            self._image_data["alpha"] = [color]
        else:
            self._image_data["alpha"].append(color)

        self.add_alpha_butt.setChecked(False)
        self.remove_alpha_butt.setEnabled(True)

        self.signal_image_changed.emit(self._image_data)

    def _add_alpha_click(self):
        self.signal_select_color.emit()

    def _remove_alpha_click(self):
        if self._image_data.get("alpha"):
            self._image_data["alpha"].pop()
            if not self._image_data["alpha"]:
                self._image_data.pop("alpha")
                self.remove_alpha_butt.setDisabled(True)

            self.signal_image_changed.emit(self._image_data)
