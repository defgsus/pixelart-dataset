import json
from functools import partial
from typing import List
from pathlib import Path

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .sourceselect import SourceSelect
from .imageselect import ImageSelect
from .imagepatcheditor import ImagePatchEditor


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(self.tr("PixelArt Dataset"))
        # self.setWindowFlag(Qt.WindowMinMaxButtonsHint, True)

        self._create_main_menu()
        self._create_widgets()

    def _create_main_menu(self):
        menu = self.menuBar().addMenu(self.tr("&File"))

        menu.addAction(self.tr("E&xit"), self.slot_exit)

    def _create_widgets(self):
        parent = QWidget(self)
        self.setCentralWidget(parent)
        lh = QHBoxLayout(parent)

        self.source_select = SourceSelect(self)
        lh.addWidget(self.source_select)
        self.source_select.signal_source_selected.connect(self._slot_source_selected)

        self.image_select = ImageSelect(self)
        lh.addWidget(self.image_select)
        self.image_select.signal_image_selected.connect(self._slot_image_selected)

        lv = QVBoxLayout()
        lh.addLayout(lv, stretch=8)
        self.image_editor = ImagePatchEditor(self)
        lv.addWidget(self.image_editor)


    def close(self) -> bool:
        if not super().close():
            return False

        # self.slot_save_sessions()
        # Client.singleton().stop()
        return True

    def slot_exit(self):
        self.close()

    def _slot_source_selected(self, data: dict):
        self.image_select.set_source(data)

    def _slot_image_selected(self, data: dict, index: int):
        self.image_editor.set_image(data, index)


