import os
import tempfile
import zipfile
from pathlib import Path
from typing import List, Union

import requests
import bs4

from bootstrap import config


def download_all(
        urls: List[str] = config.SOURCE_URLS,
        storage_path: Union[str, Path] = config.BOOTSTRAP_WEBCACHE_PATH,
):
    storage_path = Path(storage_path).expanduser()

    print(f"Downloading all pixelart to: {storage_path}")

    for url in urls:
        name = url.split("/")[-1]

        folder = storage_path / name
        os.makedirs(folder, exist_ok=True)

        index_file = folder / "index.html"
        if not index_file.exists():
            print(f"downloading {url}")
            response = requests.get(url)
            index_file.write_text(response.text)

        markup = index_file.read_text()
        soup = bs4.BeautifulSoup(markup, features="html.parser")

        print(f"\n-- {url} --")
        div = soup.find("div", {"class": "field-name-field-art-files"})
        for a in div.find_all("a"):
            url = a.attrs["href"]
            filename = folder / "oga" / url.split("/")[-1]

            if filename.suffix[1:].lower() not in ("png", "gif", "zip"):
                continue

            if not filename.exists():
                print(f"downloading {url}")
                response = requests.get(url)
                filename.write_bytes(response.content)

            if filename.suffix.lower() == ".zip":
                with zipfile.ZipFile(filename) as zipf:
                    for file in zipf.filelist:
                        if not file.is_dir():
                            fp = zipf.open(file.filename)
                            sub_filename = Path(str(filename)[:-4]) / file.filename
                            if not sub_filename.exists():
                                print(f"extracting {file.filename}")
                                os.makedirs(sub_filename.parent, exist_ok=True)
                                sub_filename.write_bytes(fp.read())


if __name__ == "__main__":
    download_all()
