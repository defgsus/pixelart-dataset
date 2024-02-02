from pathlib import Path
import tempfile

import decouple


BOOTSTRAP_BASE_PATH = Path(__file__).resolve().parent

BOOTSTRAP_WEBCACHE_PATH = Path(
    decouple.config("BOOTSTRAP_WEBCACHE_PATH", default=str(BOOTSTRAP_BASE_PATH / "web-cache"))
).expanduser()

BOOTSTRAP_DATA_PATH = Path(
    decouple.config("BOOTSTRAP_DATA_PATH", default=str(BOOTSTRAP_BASE_PATH / "data"))
).expanduser()


with open(BOOTSTRAP_DATA_PATH / "urls.txt") as fp:
    SOURCE_URLS = list(
        line.strip()
        for line in fp.readlines()
        if line.startswith("http")
    )
