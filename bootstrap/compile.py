import json
import math
import sys
import argparse
import hashlib
from io import BytesIO
from pathlib import Path
from typing import Generator, Tuple

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

    return vars(parser.parse_args())


def iter_patches(
        size: int,
) -> Generator[Tuple[dict, int, int, Tuple[int, int], QImage], None, None]:

    patch_size = QSize(size, size)
    model = SourceModel(None)

    for i in range(model.rowCount()):
        source = model.data(model.index(i, 0), Qt.ItemDataRole.UserRole)
        for image_index, image_data in enumerate(source["images"]):
            image = QImage(image_data["filename"])
            for tiling_index, tiling in enumerate(image_data["tilings"]):
                tiling = Tiling(image.size(), tiling)

                for rect, tile_pos in tiling.iter_rects(yield_pos=True):
                    patch = image.copy(rect).scaled(patch_size)
                    yield source, image_index, tiling_index, tile_pos, patch


def main(
        size: int,
        duplicates: bool,
):
    app = QGuiApplication(sys.argv)

    num_duplicates = 0
    hash_set = set()

    duplicates_map = {}
    patches = []

    for source, image_index, tiling_index, tile_pos, patch in tqdm(iter_patches(size=size)):
        data = patch.bits().asarray(size=patch.byteCount())
        hash = hashlib.md5(data).hexdigest()

        if hash in hash_set:
            num_duplicates += 1
            if source["url"] not in duplicates_map:
                duplicates_map[source["url"]] = {}
            image_data = source["images"][image_index]
            filename = str(Path(image_data["filename"]).relative_to(config.BOOTSTRAP_WEBCACHE_PATH))
            if filename not in duplicates_map[source["url"]]:
                duplicates_map[source["url"]][filename] = {}
            if str(tiling_index) not in duplicates_map[source["url"]][filename]:
                duplicates_map[source["url"]][filename][str(tiling_index)] = []
            duplicates_map[source["url"]][filename][str(tiling_index)].append(tile_pos)
            continue

        hash_set.add(hash)
        patches.append(patch)
        #if len(patches) >= 1000:
        #    break

    print(f"duplicates: {num_duplicates}")
    if duplicates:
        (config.BOOTSTRAP_DATA_PATH / "duplicates.json").write_text(json.dumps(duplicates_map))
    print(f"patches: {len(patches)}")

    width = int(math.floor(math.sqrt(len(patches))))
    pixmap = QPixmap(QSize(width * size, width * size))
    print(f"creating {pixmap.size()} png")

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
    pixmap.save("pixmap.png")


if __name__ == "__main__":
    main(**parse_args())
