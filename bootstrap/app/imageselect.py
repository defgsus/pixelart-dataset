import json
from functools import partial
from typing import List
from pathlib import Path

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from bootstrap.config import SOURCE_URLS, BOOTSTRAP_WEBCACHE_PATH
from .sourceimagemodel import SourceImageModel


class ImageSelect(QWidget):

    signal_image_selected = pyqtSignal(dict, int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._create_widgets()

    def _create_widgets(self):
        l = QVBoxLayout(self)

        self.view = QListView(self)
        l.addWidget(self.view)
        self.view.activated.connect(self._slot_select)

    def set_source(self, data: dict):
        self.model = SourceImageModel(self, data)
        self.view.setModel(self.model)
        self._slot_select(self.model.createIndex(0, 0))

    def _slot_select(self, index: QModelIndex):
        self.signal_image_selected.emit(self.model._source, index.row())

