import json
from functools import partial
from typing import List
from pathlib import Path
import urllib.parse

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from bootstrap.config import SOURCE_URLS, BOOTSTRAP_STORAGE_PATH


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

        filename = self._source["images"][index.row()]["filename"]

        if role == Qt.ItemDataRole.DisplayRole:
            return str(Path(filename).relative_to(self._source["folder"]))

        elif role == Qt.ItemDataRole.DecorationRole:
            return QPixmap(filename).scaledToWidth(100)
