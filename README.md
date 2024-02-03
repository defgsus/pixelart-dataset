# pixel-art image dataset


## bootstrapping

- search for interesting pages on [opengameart.org](https://opengameart.org/)
- add them to [bootstrap/data/urls.txt](bootstrap/data/urls.txt)
- run `python bootstrap/download.py` to cache the graphic files.
- run `python bootstrap/app/` to setup tile sizes and spacing for specific images.
- run `python bootstrap/compile.py --duplicates` to detect duplicates and update [bootstrap/data/duplicates.json](bootstrap/data/duplicates.json)
- run `python bootstrap/app/` again to assign labels to the tiles.
- ...
