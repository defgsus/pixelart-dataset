import json
from functools import partial
from typing import List
from pathlib import Path
from copy import deepcopy
import urllib.parse

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from bootstrap.config import SOURCE_URLS, BOOTSTRAP_WEBCACHE_PATH, BOOTSTRAP_DATA_PATH
from bootstrap.app.util import DEFAULT_TILING


class LabelModel(QAbstractItemModel):

    def __init__(self, parent):
        super().__init__(parent)
        self.data_path = BOOTSTRAP_DATA_PATH

        self._labels = []
        self.load_preset()

    def rowCount(self, parent = ...):
        return len(self._labels)

    def columnCount(self, parent = ...):
        return 1

    def parent(self, child):
        return QModelIndex()

    def index(self, row, column, parent = ...):
        if row < 0 or row >= len(self._labels):
            return QModelIndex()
        if column != 0:
            return QModelIndex()

        return self.createIndex(row, column)

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = ...):
        if not index.isValid():
            return None

        label = self._labels[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return label["name"]

        elif role == Qt.ItemDataRole.BackgroundRole:
            return QColor(*label["color"])

        elif role == Qt.ItemDataRole.UserRole:
            return label

    def load_preset(self):
        if (self.data_path / "labels.json").exists():
            self._labels = json.loads((self.data_path / "labels.json").read_text())
        else:
            self._labels = []

    def save_preset(self):
        self._labels.sort(key=lambda l: l["name"])
        (self.data_path / "labels.json").write_text(json.dumps(self._labels, indent=2))

    def add_label(self, label: dict) -> int:
        self.load_preset()
        for i, l in enumerate(self._labels):
            if l["name"] == label["name"]:
                self._labels[i] = label
                self.save_preset()
                return i

        self._labels.append(label)
        self.save_preset()
        for i, l in enumerate(self._labels):
            if l["name"] == label["name"]:
                return i
