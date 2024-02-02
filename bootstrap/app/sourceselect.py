import json
from functools import partial
from typing import List
from pathlib import Path

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from bootstrap.config import SOURCE_URLS, BOOTSTRAP_WEBCACHE_PATH
from .sourcemodel import SourceModel


class SourceSelect(QWidget):

    signal_source_selected = pyqtSignal(dict)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.urls = SOURCE_URLS
        self.storage_path = BOOTSTRAP_WEBCACHE_PATH

        self._create_widgets()

    def _create_widgets(self):
        l = QVBoxLayout(self)

        self.view = QListView(self)
        l.addWidget(self.view)
        # self.view.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))
        self.model = SourceModel(self)
        self.view.setModel(self.model)
        self.view.activated.connect(self._slot_select)

    def _slot_select(self, index: QModelIndex):
        data = self.model.data(index, role=Qt.ItemDataRole.UserRole)
        self.signal_source_selected.emit(data)

    def update_source(self, source: dict):
        self.model.update_source(source)
        self.update()
