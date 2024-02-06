import json
import math
import os
import sys
import argparse
import hashlib
from io import BytesIO
import csv
from pathlib import Path
from typing import Generator, Tuple, Optional, List

from PyQt5.QtCore import *
from PyQt5.QtGui import *

from tqdm import tqdm

from bootstrap.app.sourcemodel import SourceModel
from bootstrap.app.util import Tiling, get_qimage_from_source
from bootstrap import config


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-s", "--size", type=int, default=16,
        help="Size of patches (width and height)",
    )
    parser.add_argument(
        "-d", "--duplicates", type=bool, nargs="?", default=False, const=True,
        help="Write the bootstrap/data/duplicates.json file",
    )
    parser.add_argument(
        "-o", "--output", type=str, nargs="?", default=None,
        help="Directory to store the dataset",
    )
    parser.add_argument(
        "-ms", "--min-size", type=int, default=0,
        help="Minimum size of a source patch to consider",
    )
    parser.add_argument(
        "-mp", "--max-patches", type=int, default=0,
        help="Maximum number of patches to compile",
    )
    parser.add_argument(
        "-rl", "--require-label", type=bool, nargs="?", default=False, const=True,
        help="Only consider labeled patches",
    )

    return vars(parser.parse_args())


def iter_patches(
        size: int,
        # in order to determine all duplicates we need to include them here
        include_duplicates: bool = True,
) -> Generator[dict, None, None]:

    patch_size = QSize(size, size)
    model = SourceModel(None)

    for i in range(model.rowCount()):
        source = model.data(model.index(i, 0), Qt.ItemDataRole.UserRole)
        for image_index, image_data in enumerate(source["images"]):
            image = get_qimage_from_source(image_data)
            for tiling_index, tiling in enumerate(image_data["tilings"]):
                tiling = Tiling(image.size(), tiling)

                if include_duplicates:
                    tiling.duplicate_tiles.clear()

                for rect, tile_pos in tiling.iter_rects(yield_pos=True):
                    patch = image.copy(rect).scaled(patch_size)
                    yield {
                        "source": source,
                        "image_index": image_index,
                        "tiling_index": tiling_index,
                        "tile_pos": tile_pos,
                        "rect": rect,
                        "image": image,
                        "image_data": image_data,
                        "tiling": tiling,
                        "patch": patch,
                    }


class SimilarityFilter:

    def __init__(self, type: str = "exact"):
        self.type = type
        self.hash_set = set()

    def is_similar(self, patch: QImage) -> bool:
        if self.type == "exact":
            data = patch.bits().asarray(size=patch.byteCount())
            hash = hashlib.md5(data).hexdigest()
            similar = hash in self.hash_set
            if not similar:
                self.hash_set.add(hash)
            return similar

        else:
            raise ValueError(f"Invalid type `{self.type}`")


class DatasetCompiler:

    def __init__(
            self,
            size: int,
            duplicates: bool,
            output: Optional[str],
            min_size: int,
            max_patches: int,
            require_label: bool,
    ):
        self.size = size
        self.do_write_duplicates = duplicates
        self.directory = None if output is None else Path(output)
        self.filter_min_size = min_size
        self.max_patches = max_patches
        self.filter_label = require_label

        self.patches: List[dict] = []
        self.num_duplicates = 0
        self.duplicates_map = {}
        self.num_skipped = 0
        self.sim_filter = SimilarityFilter()
        self.label_stats = {}
        self.source_stats = {}

    def compile(self):
        self._get_patches()

        print(f"duplicates: {self.num_duplicates:,}")
        print(f"skipped:    {self.num_skipped:,}")
        print(f"patches:    {len(self.patches):,}")

        if self.do_write_duplicates:
            filename = config.BOOTSTRAP_DATA_PATH / "duplicates.json"
            print(f"writing duplicates: {filename}")
            filename.write_text(json.dumps(self.duplicates_map))

        if self.directory:
            os.makedirs(self.directory, exist_ok=True)

            self._write_patches("tiles.png", [p["patch"] for p in self.patches])

            rows, statistics = self._get_rows_and_statistics(self.patches)

            filename = (self.directory / "tiles.json")
            print(f"writing info: {filename}")
            filename.write_text(json.dumps({
                "count": len(self.patches),
                "channels": 3,
                "shape": (self.size, self.size),
                "min_source_shape": (self.filter_min_size, self.filter_min_size),
                "info": statistics,
            }, indent=2))

            filename = self.directory / "tiles.csv"
            print(f"writing table: {filename}")
            with filename.open("wt") as fp:
                writer = csv.DictWriter(fp, list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)

    def _get_patches(self):
        for patch_data in tqdm(iter_patches(size=self.size)):
            source = patch_data["source"]
            image_data = patch_data["image_data"]
            tiling_index = patch_data["tiling_index"]
            tile_pos = patch_data["tile_pos"]
            tiling = patch_data["tiling"]
            patch = patch_data["patch"]

            if self.sim_filter.is_similar(patch):
                self.num_duplicates += 1

                # store in global duplicate map
                if source["url"] not in self.duplicates_map:
                    self.duplicates_map[source["url"]] = {}
                filename = str(Path(image_data["filename"]).relative_to(config.BOOTSTRAP_WEBCACHE_PATH))
                if filename not in self.duplicates_map[source["url"]]:
                    self.duplicates_map[source["url"]][filename] = {}
                if str(tiling_index) not in self.duplicates_map[source["url"]][filename]:
                    self.duplicates_map[source["url"]][filename][str(tiling_index)] = []
                self.duplicates_map[source["url"]][filename][str(tiling_index)].append(tile_pos)
                continue

            # -- filter by min-size --
            source_size = patch_data["rect"]
            if any(s < self.filter_min_size for s in (source_size.width(), source_size.height())):
                self.num_skipped += 1
                continue

            # -- filter by label --
            label = patch_data["label"] = self._get_single_label(tiling.get_labels_at(*tile_pos))

            if self.filter_label and label == "undefined":
                self.num_skipped += 1
                continue

            self.patches.append(patch_data)

            if self.max_patches and len(self.patches) >= self.max_patches:
                break

    def _get_single_label(self, labels: List[str]):
        return "/".join(sorted(labels)) or "undefined"

    def _get_rows_and_statistics(self, patches: List[dict]):

        rows = []
        label_stats = dict()
        source_stats = dict()
        source_ids = dict()

        for idx, patch in enumerate(patches):
            source = patch["source"]
            url = source["url"]
            label = patch["label"]

            if url not in source_ids:
                source_ids[url] = len(source_ids) + 1

            label_stats[label] = label_stats.get(label, 0) + 1
            source_stats[url] = source_stats.get(url, 0) + 1

            rows.append({
                "index": idx,
                "source_id": source_ids[url],
                "label": patch["label"],
            })

        def _sort_stats(stats):
            return {
                key: stats[key]
                for key in sorted(stats, key=lambda k: stats[k], reverse=True)
            }

        statistics = {
            "distribution": {
                "label": _sort_stats(label_stats),
                "source": _sort_stats(source_stats),
            },
            "source_id_mapping": {
                str(source_ids[key]): key
                for key in sorted(source_ids, key=lambda k: source_ids[k])
            },
        }
        return rows, statistics

    def _write_patches(self, name: str, patches: List[QImage]):
        size = patches[0].width()
        width = int(math.ceil(math.sqrt(len(patches))))

        pixmap = QPixmap(QSize(width * size, width * size))
        print(f"creating {pixmap.width()}x{pixmap.height()} image")

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(0, 0, 0)))
        painter.drawRect(pixmap.rect())

        x, y = 0, 0
        for patch in patches:
            painter.drawImage(QPoint(x * size, y * size), patch)
            x += 1
            if x >= width:
                x = 0
                y += 1
        painter.end()

        filename = self.directory / name
        print(f"writing tiles: {filename}")
        pixmap.save(str(filename))


def main():
    app = QGuiApplication(sys.argv)
    compiler = DatasetCompiler(**parse_args())
    compiler.compile()


if __name__ == "__main__":
    main()
