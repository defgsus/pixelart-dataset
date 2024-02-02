import json
from functools import partial
from typing import List
from pathlib import Path
import urllib.parse

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from bootstrap.config import SOURCE_URLS, BOOTSTRAP_WEBCACHE_PATH


class SourceImageModel(QAbstractItemModel):

    def __init__(self, parent, source: dict):
        super().__init__(parent)

        self._source = source

    def rowCount(self, parent = ...):
        return len(self._source["images"])

    def columnCount(self, parent = ...):
        return 1

    def parent(self, child):
        return QModelIndex()

    def index(self, row, column, parent = ...):
        if row < 0 or row >= len(self._source["images"]):
            return QModelIndex()
        if column != 0:
            return QModelIndex()

        return self.createIndex(row, column)

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = ...):
        if not index.isValid():
            return None

        source_image =  self._source["images"][index.row()]
        filename = source_image["filename"]

        if role == Qt.ItemDataRole.DisplayRole:
            return str(Path(filename).relative_to(self._source["web_folder"]))

        elif role == Qt.ItemDataRole.DecorationRole:
            return QPixmap(filename).scaledToWidth(100)

        elif role == Qt.ItemDataRole.BackgroundRole:
            if source_image["tilings"]:
                return QColor(24, 48, 24)
        elif role == Qt.ItemDataRole.FontRole:
            if source_image["tilings"]:
                font = QFont()
                font.setBold(True)
                return font
