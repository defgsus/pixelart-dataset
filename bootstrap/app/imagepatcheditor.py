from copy import deepcopy
from functools import partial
from typing import List, Optional, Any
from pathlib import Path

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .imagepatchwidget import ImagePatchWidget
from .sourcemodel import DEFAULT_TILING


class ImagePatchEditor(QWidget):

    signal_save_settings = pyqtSignal(dict, int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._source: Optional[dict] = None
        self._index: Optional[int] = None
        self._image_data: Optional[dict] = None

        self._create_widgets()

    def _create_widgets(self):
        l = QVBoxLayout(self)

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
        self.controls.set_tilings(self._image_data["tilings"])
        self.patch_widget.set_image(self._image_data)

    def _slot_tilings_changed(self, tilings: List[dict]):
        if self._image_data is not None:
            self._image_data["tilings"] = deepcopy(tilings)
            self.patch_widget.set_image(self._image_data)


class ImagePatchEditorControls(QWidget):

    signal_zoom_changed = pyqtSignal(int)
    signal_tilings_changed = pyqtSignal(list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._tilings = []
        self._do_listen_value_change = True

        self._create_widgets()

    def _create_widgets(self):
        l = QVBoxLayout(self)

        self.zoom_widget = QSlider(Qt.Horizontal)
        l.addWidget(self.zoom_widget)
        self.zoom_widget.setMinimum(1)
        self.zoom_widget.setMaximum(10)
        self.zoom_widget.valueChanged.connect(self.signal_zoom_changed)

        self.tiling_tab = QTabBar(self)
        l.addWidget(self.tiling_tab)
        self.tiling_tab.tabBarClicked.connect(self._tab_clicked)

        self._widgets = {}
        for name in ("offset", "patch_size", "spacing"):
            lh = QHBoxLayout()
            l.addLayout(lh)
            lh.addWidget(QLabel(name, self))
            spin_x = QSpinBox(self)
            spin_x.setMinimum(0)
            lh.addWidget(spin_x)
            spin_y = QSpinBox(self)
            spin_y.setMinimum(0)
            lh.addWidget(spin_y)

            self._widgets[f"{name}_x"] = spin_x
            self._widgets[f"{name}_y"] = spin_y

            spin_x.valueChanged.connect(partial(self._slot_value_changed, f"{name}_x"))
            spin_y.valueChanged.connect(partial(self._slot_value_changed, f"{name}_y"))
            # spin_y.valueChanged.connect(lambda x: self._slot_value_changed(f"{name}_y", x))

    def set_tilings(self, tilings: List[dict]):
        while self.tiling_tab.count():
            self.tiling_tab.removeTab(0)

        while self.tiling_tab.count() < len(tilings):
            self.tiling_tab.addTab(f"Tiling #{self.tiling_tab.count() + 1}")

        self.tiling_tab.addTab("+")

        self.tiling_tab.setCurrentIndex(0)
        self._tilings = deepcopy(tilings)
        self._tab_clicked(0)

    def _tab_clicked(self, index: int):
        if index == self.tiling_tab.count() - 1:
            self.set_tilings(self._tilings + [deepcopy(DEFAULT_TILING)])
            return

        if index >= len(self._tilings):
            data = DEFAULT_TILING
        else:
            data = self._tilings[index]

        try:
            self._do_listen_value_change = False
            self._widgets["offset_x"].setValue(data["offset"][0])
            self._widgets["offset_y"].setValue(data["offset"][1])
            self._widgets["patch_size_x"].setValue(data["patch_size"][0])
            self._widgets["patch_size_y"].setValue(data["patch_size"][1])
            self._widgets["spacing_x"].setValue(data["spacing"][0])
            self._widgets["spacing_y"].setValue(data["spacing"][1])
        finally:
            self._do_listen_value_change = True

    def _slot_value_changed(self, name: str, value: int):
        if not self._do_listen_value_change:
            return

        index = self.tiling_tab.currentIndex()
        if index >= len(self._tilings):
            return

        if name.endswith("_x") or name.endswith("_y"):
            index = 0 if name.endswith("_x") else 1
            self._tilings[index][name[:-2]][index] = value
        else:
            self._tilings[index][name] = value

        self.signal_tilings_changed.emit(self._tilings)
