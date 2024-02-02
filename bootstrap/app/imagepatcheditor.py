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
        self.patch_widget.signal_image_changed.connect(self._update_image_from_patch_widget)

        self.controls.signal_zoom_changed.connect(self.patch_widget.set_zoom)
        self.controls.signal_tilings_changed.connect(self._slot_tilings_changed)
        self.controls.signal_tiling_selected.connect(self.patch_widget.set_tiling_index)

    def set_image(self, source: dict, index: int):
        self._source = source
        self._index = index
        self._image_data = deepcopy(self._source["images"][index])
        self._image_size = QPixmap(self._image_data["filename"]).size()
        self.controls.set_tilings(self._image_data["tilings"], self._image_size)
        self.patch_widget.set_image(self._image_data)
        self.setEnabled(True)

    def _update_image_from_patch_widget(self, image_data: dict):
        self._image_data = deepcopy(image_data)
        self.controls.set_tilings(self._image_data["tilings"], self._image_size)

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

    XY_PARAMS = ("offset", "patch_size", "spacing", "size")

    signal_zoom_changed = pyqtSignal(int)
    signal_tilings_changed = pyqtSignal(list)
    signal_tiling_selected = pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._tilings = []
        self._image_size: Optional[QSize] = None
        self._do_listen_value_change = True
        self._do_listen_tab_click = True

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
        self.tiling_tab.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tiling_tab.customContextMenuRequested.connect(self._tab_context_menu)

        self._widgets = {}
        for name in self.XY_PARAMS:
            lh = QHBoxLayout()
            l.addLayout(lh)
            lh.addWidget(QLabel(name, self))

            min_value = 1 if name in ("patch_size",) else 0
            spin_x = QSpinBox(self)
            spin_x.setRange(min_value, 2**24)
            lh.addWidget(spin_x)
            spin_y = QSpinBox(self)
            spin_y.setRange(min_value, 2**24)
            spin_y.setDisabled(True)
            lh.addWidget(spin_y)

            self._widgets[f"{name}_x"] = spin_x
            self._widgets[f"{name}_y"] = spin_y

            spin_x.valueChanged.connect(partial(self._slot_value_changed, f"{name}_x"))
            spin_y.valueChanged.connect(partial(self._slot_value_changed, f"{name}_y"))

    def set_tilings(self, tilings: List[dict], image_size: QSize):
        old_index = self.tiling_tab.currentIndex()

        while self.tiling_tab.count():
            self.tiling_tab.removeTab(0)

        while self.tiling_tab.count() < len(tilings):
            self.tiling_tab.addTab(f"Tiling #{self.tiling_tab.count() + 1}")

        self.tiling_tab.addTab("➕ new tiling")

        self._tilings = deepcopy(tilings)
        self._image_size = image_size

        self.tiling_tab.setCurrentIndex(max(0, min(old_index, self.tiling_tab.count() - 2)))

        if not self._tilings:
            for w in self._widgets.values():
                w.setDisabled(True)
        else:
            self._update_xy_widgets(self._tilings[self.tiling_tab.currentIndex()])

    def _tab_clicked(self, index: int):
        if not self._do_listen_tab_click:
            return

        if index < 0:
            for w in self._widgets.values():
                w.setDisabled(True)
            return

        if self._tilings and self.tiling_tab.currentIndex() < len(self._tilings):
            default_tiling = deepcopy(self._tilings[self.tiling_tab.currentIndex()])
            default_tiling.pop("ignore", None)
        else:
            default_tiling = get_default_tiling(self._image_size)

        if index == self.tiling_tab.count() - 1:
            try:
                self._do_listen_tab_click = False
                self.set_tilings(self._tilings + [default_tiling], self._image_size)
            finally:
                self._do_listen_tab_click = True

            self.signal_tilings_changed.emit(self._tilings)
            self.signal_tiling_selected.emit(len(self._tilings) - 1)
            return

        if index >= len(self._tilings):
            data = default_tiling
        else:
            data = self._tilings[index]
            for w in self._widgets.values():
                w.setEnabled(True)

        self._update_xy_widgets(data)

        self.signal_tiling_selected.emit(index)

    def _tab_context_menu(self, pos: QPoint):
        idx = self.tiling_tab.currentIndex()
        menu = QMenu()
        menu.addAction(f"Remove #{idx + 1}", partial(self._remove_tiling, idx))
        menu.exec(self.tiling_tab.mapToGlobal(pos))

    def _remove_tiling(self, index: int):
        if index < len(self._tilings):
            tilings = self._tilings.copy()
            tilings.pop(index)
            self.set_tilings(tilings, self._image_size)
            self.signal_tilings_changed.emit(self._tilings)

    def _update_xy_widgets(self, data):
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
