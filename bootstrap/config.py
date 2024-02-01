from pathlib import Path
import tempfile

import decouple


BOOTSTRAP_STORAGE_PATH = Path(
    decouple.config(
        "BOOTSTRAP_STORAGE_PATH",
        default=str(Path(tempfile.gettempdir()) / "pixelart-dataset"),
        cast=str,
    )
).expanduser()


with open(Path(__file__).resolve().parent / "urls.txt") as fp:
    SOURCE_URLS = list(
        line.strip()
        for line in fp.readlines()
        if line.startswith("http")
    )
