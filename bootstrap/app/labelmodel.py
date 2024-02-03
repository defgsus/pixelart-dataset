import json
from functools import partial
from pathlib import Path
from copy import deepcopy
from typing import List, Optional, Union

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

    def index_for_label(self, label: Union[str, dict]) -> QModelIndex:
        if isinstance(label, dict):
            label = label["name"]
        for i, l in enumerate(self._labels):
            if l["name"] == label:
                return self.index(i, 0)
        return QModelIndex()

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
        self.modelReset.emit()

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

        # self.dataChanged.emit(self.index(0, 0), self.index(len(self._labels) - 1, 0))
        self.modelReset.emit()

    def labels(self) -> List[str]:
        return [l["name"] for l in self._labels]

    def get_label(self, name: str) -> Optional[dict]:
        for label in self._labels:
            if label["name"] == name:
                return label

    def autocomplete(self, text: str) -> List[str]:
        if not text:
            return []

        candidates = {}
        for label in self._labels:
            i = 0
            for i, (t, l) in enumerate(zip(text, label["name"])):
                if t != l:
                    break
            if i:
                candidates[label["name"]] = i

        return sorted(sorted(candidates), key=lambda c: candidates[c], reverse=True)
