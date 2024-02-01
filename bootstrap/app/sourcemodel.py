import json
from functools import partial
from typing import List
from pathlib import Path
from copy import deepcopy
import urllib.parse

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from bootstrap.config import SOURCE_URLS, BOOTSTRAP_STORAGE_PATH


DEFAULT_TILING = {
    "offset": [0, 0],
    "patch_size": [16, 16],
    "spacing": [0, 0],
}


class SourceModel(QAbstractItemModel):

    def __init__(self, parent):
        super().__init__(parent)
        self.urls = SOURCE_URLS
        self.storage_path = BOOTSTRAP_STORAGE_PATH

        self._sources = []
        self._scan_sources()

    def rowCount(self, parent = ...):
        return len(self._sources)

    def columnCount(self, parent = ...):
        return 1

    def parent(self, child):
        return QModelIndex()

    def index(self, row, column, parent = ...):
        if row < 0 or row >= len(self._sources):
            return QModelIndex()
        if column != 0:
            return QModelIndex()

        return self.createIndex(row, column)

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = ...):
        if not index.isValid():
            return None

        source = self._sources[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            return source["name"]

        elif role == Qt.ItemDataRole.UserRole:
            return source

    def _scan_sources(self):
        source_image_map = {}

        for url in sorted(self.urls):

            name = url.split("/")[-1]
            folder = self.storage_path / name

            for file in sorted(folder.rglob("**/*")):
                if file.suffix.lower() in (".png", ".gif") and not file.name.startswith("."):

                    if url not in source_image_map:
                        source_image_map[url] = {
                            "url": url,
                            "name": urllib.parse.unquote(name),
                            "folder": str(folder),
                            "images": [],
                        }

                    source_image_map[url]["images"].append({
                        "filename": str(file),
                        "tilings": [
                            deepcopy(DEFAULT_TILING),
                        ],
                    })

        self._sources.clear()
        for key in sorted(source_image_map):
            self._sources.append(source_image_map[key])
