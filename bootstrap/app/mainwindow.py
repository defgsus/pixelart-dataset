import json
import os
from pathlib import Path
from functools import partial
from copy import deepcopy
from typing import List

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from .sourceselect import SourceSelect
from .imageselect import ImageSelect
from .imagepatcheditor import ImagePatchEditor
from .. import config


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

        lv = QVBoxLayout()
        lh.addLayout(lv, stretch=3)
        self.source_select = SourceSelect(self)
        lv.addWidget(self.source_select)
        self.source_select.signal_source_selected.connect(self._slot_source_selected)

        self.image_select = ImageSelect(self)
        lv.addWidget(self.image_select)
        self.image_select.signal_image_selected.connect(self._slot_image_selected)

        lv = QVBoxLayout()
        lh.addLayout(lv, stretch=6)
        self.image_editor = ImagePatchEditor(self)
        lv.addWidget(self.image_editor)
        self.image_editor.signal_save_source.connect(self.slot_save_source)

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

    def slot_save_source(self, source: dict):
        self.image_select.set_source(source)
        self.source_select.update_source(source)

        filename = Path(source["data_filename"])
        os.makedirs(filename.parent, exist_ok=True)

        source2 = deepcopy(source)
        source2["images"] = []
        for image in source["images"]:
            if image["tilings"]:
                image = deepcopy(image)
                image["filename"] = str(Path(image["filename"]).relative_to(source["web_folder"]))
                source2["images"].append(image)

        for key in ("name", "web_folder", "data_filename"):
            source2.pop(key, None)

        filename.write_text(json.dumps(source2, indent=2))
