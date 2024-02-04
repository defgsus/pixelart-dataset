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


class SourceModel(QAbstractItemModel):

    def __init__(self, parent):
        super().__init__(parent)
        self.urls = SOURCE_URLS
        self.webcache_path = BOOTSTRAP_WEBCACHE_PATH

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

        elif role == Qt.ItemDataRole.BackgroundRole:
            if any(img["tilings"] for img in source["images"]):
                return QColor(24, 48, 24)
        elif role == Qt.ItemDataRole.FontRole:
            if any(img["tilings"] for img in source["images"]):
                font = QFont()
                font.setBold(True)
                return font

    def _scan_sources(self):
        source_image_map = {}
        duplicates_map = {}

        duplicates_name = BOOTSTRAP_DATA_PATH / "duplicates.json"
        if duplicates_name.exists():
            duplicates_map = json.loads(duplicates_name.read_text())

        for url in sorted(self.urls):

            name = url.split("/")[-1]
            folder = self.webcache_path / "oga" / name

            for file in sorted(folder.rglob("**/*")):
                if file.suffix.lower() in (".png", ".gif") and not file.name.startswith("."):

                    if url not in source_image_map:
                        source_image_map[url] = {
                            "url": url,
                            "name": f"oga/{urllib.parse.unquote(name)}",
                            "web_folder": str(folder),
                            "data_filename": str(BOOTSTRAP_DATA_PATH / f"oga/{name}.json"),
                            "images": [],
                        }
                        if Path(source_image_map[url]["data_filename"]).exists():
                            source_image_map[url].update(
                                json.loads(Path(source_image_map[url]["data_filename"]).read_text())
                            )
                        # temporarily convert images to dict for quicker lookup
                        source_image_map[url]["images_map"] = {
                            str((Path(source_image_map[url]["web_folder"]) / img["filename"]).relative_to(BOOTSTRAP_WEBCACHE_PATH)): {
                                **img,
                                "filename": str(Path(source_image_map[url]["web_folder"]) / img["filename"])
                            }
                            for img in source_image_map[url]["images"]
                        }

                    relative_filename = str(file.relative_to(BOOTSTRAP_WEBCACHE_PATH))
                    if relative_filename not in source_image_map[url]["images_map"]:
                        source_image_map[url]["images_map"][relative_filename] = {
                            "filename": str(file),
                            "tilings": [],
                        }

        self._sources.clear()
        for url in sorted(source_image_map):
            source_image_map[url]["images"] = list(source_image_map[url].pop("images_map").values())
            for image in source_image_map[url]["images"]:
                for tiling_index, tiling in enumerate(image["tilings"]):
                    for k, v in DEFAULT_TILING.items():
                        tiling.setdefault(k, v)
                    
                    if url in duplicates_map:
                        filename = str(Path(image["filename"]).relative_to(BOOTSTRAP_WEBCACHE_PATH))
                        if filename in duplicates_map[url]:
                            if str(tiling_index) in duplicates_map[url][filename]:
                                tiling["duplicates"] = duplicates_map[url][filename][str(tiling_index)]
            self._sources.append(source_image_map[url])

    def update_source(self, source: dict):
        for i, src in enumerate(self._sources):
            if src["name"] == source["name"]:
                self._sources[i] = source
