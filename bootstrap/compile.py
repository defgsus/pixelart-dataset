import json
import math
import os
import sys
import argparse
import hashlib
from io import BytesIO
from pathlib import Path
from typing import Generator, Tuple, Optional, List

from PyQt5.QtCore import *
from PyQt5.QtGui import *

from tqdm import tqdm

from bootstrap.app.sourcemodel import SourceModel
from bootstrap.app.util import Tiling
from bootstrap import config


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-s", "--size", type=int, nargs="?", default=16,
        help="Size of patches (width and height)",
    )
    parser.add_argument(
        "-d", "--duplicates", type=bool, nargs="?", default=False, const=True,
        help="Write the bootstrap/data/duplicates.json files",
    )
    parser.add_argument(
        "-o", "--output", type=str, nargs="?", default=None,
        help="Directory to store the dataset",
    )
    parser.add_argument(
        "-ms", "--min-size", type=int, nargs="?", default=0,
        help="Minimum size of a source patch to consider",
    )
    parser.add_argument(
        "-mp", "--max-patches", type=int, nargs="?", default=0,
        help="Maximum number of patches to compile",
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
            image = QImage(image_data["filename"])
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


def write_dataset(directory: str, patches: List[QImage], statistics: dict):
    directory = Path(directory)

    size = patches[0].width()
    width = int(math.floor(math.sqrt(len(patches))))

    pixmap = QPixmap(QSize(width * size, width * size))
    print(f"creating {pixmap.width()}x{pixmap.height()} image")

    painter = QPainter(pixmap)
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

    os.makedirs(directory, exist_ok=True)
    pixmap.save(str(directory / "tiles.png"))

    (directory / "info.json").write_text(json.dumps({
        "count": len(patches),
        "shape": (3, size, size),
        "statistics": statistics,
    }, indent=2))


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


def main(
        size: int,
        duplicates: bool,
        output: Optional[str],
        min_size: int,
        max_patches: int,
):
    app = QGuiApplication(sys.argv)

    patches = []
    num_duplicates = 0
    duplicates_map = {}
    num_skipped = 0
    sim_filter = SimilarityFilter()
    label_stats = {}
    source_stats = {}

    for patch_data in tqdm(iter_patches(size=size)):
        source = patch_data["source"]
        image_data = patch_data["image_data"]
        tiling_index = patch_data["tiling_index"]
        tile_pos = patch_data["tile_pos"]
        tiling = patch_data["tiling"]
        patch = patch_data["patch"]

        if sim_filter.is_similar(patch):
            num_duplicates += 1

            # store in global duplicate map
            if source["url"] not in duplicates_map:
                duplicates_map[source["url"]] = {}
            filename = str(Path(image_data["filename"]).relative_to(config.BOOTSTRAP_WEBCACHE_PATH))
            if filename not in duplicates_map[source["url"]]:
                duplicates_map[source["url"]][filename] = {}
            if str(tiling_index) not in duplicates_map[source["url"]][filename]:
                duplicates_map[source["url"]][filename][str(tiling_index)] = []
            duplicates_map[source["url"]][filename][str(tiling_index)].append(tile_pos)
            continue

        # -- filter by min-size --
        source_size = patch_data["rect"]
        if any(s < min_size for s in (source_size.width(), source_size.height())):
            num_skipped += 1
            continue

        patches.append(patch)

        # -- statistics --
        labels = tiling.get_labels_at(*tile_pos)
        label = "/".join(sorted(labels)) or "undefined"
        label_stats[label] = label_stats.get(label, 0) + 1

        source_stats[source["url"]] = source_stats.get(source["url"], 0) + 1

        if max_patches and len(patches) >= max_patches:
            break

    def _sort_stats(stats):
        return {
            key: stats[key]
            for key in sorted(stats, key=lambda k: stats[k], reverse=True)
        }

    label_stats = _sort_stats(label_stats)
    source_stats = _sort_stats(source_stats)

    print(f"duplicates: {num_duplicates:,}")
    if duplicates:
        (config.BOOTSTRAP_DATA_PATH / "duplicates.json").write_text(json.dumps(duplicates_map))
    print(f"skipped:    {num_skipped:,}")
    print(f"patches:    {len(patches):,}")

    if output:
        write_dataset(
            directory=output,
            patches=patches,
            statistics={
                "label_distribution": label_stats,
                "source_distribution": source_stats,
            }
        )


if __name__ == "__main__":
    main(**parse_args())
