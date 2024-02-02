from copy import deepcopy
from functools import partial
from typing import List, Optional, Any
from pathlib import Path

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .imagepatchwidget import ImagePatchWidget
from .util import get_default_tiling


class ImagePatchEditor(QWidget):

    signal_save_source = pyqtSignal(dict)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._source: Optional[dict] = None
        self._index: Optional[int] = None
        self._image_data: Optional[dict] = None
        self._image_size: Optional[QSize] = None

        self._create_widgets()
        self.setDisabled(True)

    def _create_widgets(self):
        l = QVBoxLayout(self)

        lh = QHBoxLayout()
        l.addLayout(lh)
        self.save_butt = QPushButton("Save", self)
        lh.addWidget(self.save_butt)
        self.save_butt.clicked.connect(self._save_source_image)

        self.controls = ImagePatchEditorControls(self)
        l.addWidget(self.controls)

        self.view = QScrollArea(self)
        l.addWidget(self.view)
        self.patch_widget = ImagePatchWidget(self)
        self.view.setWidget(self.patch_widget)

        self.controls.signal_zoom_changed.connect(self.patch_widget.set_zoom)
        self.controls.signal_tilings_changed.connect(self._slot_tilings_changed)


    def set_image(self, source: dict, index: int):
        self._source = source
        self._index = index
        self._image_data = deepcopy(self._source["images"][index])
        self._image_size = QPixmap(self._image_data["filename"]).size()
        self.controls.set_tilings(self._image_data["tilings"], self._image_size)
        self.patch_widget.set_image(self._image_data)
        self.setEnabled(True)

    def _slot_tilings_changed(self, tilings: List[dict]):
        if self._image_data is not None:
            self._image_data["tilings"] = deepcopy(tilings)
            self.patch_widget.set_image(self._image_data)

            #self.signal_save_source_image

    def _save_source_image(self):
        source = deepcopy(self._source)
        source["images"][self._index] = self._image_data
        self.signal_save_source.emit(source)


class ImagePatchEditorControls(QWidget):

    XY_PARAMS = ("offset", "patch_size", "spacing")

    signal_zoom_changed = pyqtSignal(int)
    signal_tilings_changed = pyqtSignal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._tilings = []
        self._image_size: Optional[QSize] = None
        self._do_listen_value_change = True

        self._create_widgets()

    def _create_widgets(self):
        l = QVBoxLayout(self)

        self.zoom_slider = QSlider(Qt.Horizontal)
        l.addWidget(self.zoom_slider)
        self.zoom_slider.setRange(1, 10)
        self.zoom_slider.setValue(3)
        self.zoom_slider.valueChanged.connect(self.signal_zoom_changed)

        self.tiling_tab = QTabBar(self)
        l.addWidget(self.tiling_tab)
        self.tiling_tab.tabBarClicked.connect(self._tab_clicked)

        self._widgets = {}
        for name in self.XY_PARAMS:
            lh = QHBoxLayout()
            l.addLayout(lh)
            lh.addWidget(QLabel(name, self))
            spin_x = QSpinBox(self)
            spin_x.setRange(0, 2**24)
            lh.addWidget(spin_x)
            spin_y = QSpinBox(self)
            spin_y.setRange(0, 2**24)
            lh.addWidget(spin_y)

            self._widgets[f"{name}_x"] = spin_x
            self._widgets[f"{name}_y"] = spin_y

            spin_x.valueChanged.connect(partial(self._slot_value_changed, f"{name}_x"))
            spin_y.valueChanged.connect(partial(self._slot_value_changed, f"{name}_y"))

    def set_tilings(self, tilings: List[dict], image_size: QSize):
        while self.tiling_tab.count():
            self.tiling_tab.removeTab(0)

        while self.tiling_tab.count() < len(tilings):
            self.tiling_tab.addTab(f"Tiling #{self.tiling_tab.count() + 1}")

        self.tiling_tab.addTab("➕ new tiling")

        self.tiling_tab.setCurrentIndex(0)
        self._tilings = deepcopy(tilings)
        self._image_size = image_size

        if self._tilings:
            self._tab_clicked(0)
        else:
            for w in self._widgets.values():
                w.setDisabled(True)

    def _tab_clicked(self, index: int):
        default_tiling = get_default_tiling(self._image_size)

        if index == self.tiling_tab.count() - 1:
            self.set_tilings(self._tilings + [default_tiling], self._image_size)
            self.signal_tilings_changed.emit(self._tilings)
            return

        if index >= len(self._tilings):
            data = default_tiling
        else:
            data = self._tilings[index]
            for w in self._widgets.values():
                w.setEnabled(True)

        try:
            self._do_listen_value_change = False

            for key in self.XY_PARAMS:
                for sub_key in ("x", "y"):
                    self._widgets[f"{key}_{sub_key}"].setValue(data[f"{key}_{sub_key}"])

        finally:
            self._do_listen_value_change = True

    def _slot_value_changed(self, name: str, value: int):
        if not self._do_listen_value_change:
            return

        index = self.tiling_tab.currentIndex()
        if index >= len(self._tilings):
            return

        self._tilings[index][name] = value

        self.signal_tilings_changed.emit(self._tilings)
