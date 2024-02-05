# pixel-art image dataset


## bootstrapping

1. search for interesting pages on [opengameart.org](https://opengameart.org/)
2. add them to [bootstrap/data/urls.txt](bootstrap/data/urls.txt)
3. run `python bootstrap/download.py` to cache the graphic files. 
4. run `python bootstrap/app/` to setup tile sizes and spacing for specific images. 
5. run `python bootstrap/compile.py --duplicates` to detect duplicates and update [bootstrap/data/duplicates.json](bootstrap/data/duplicates.json)
6. run `python bootstrap/app/` again to assign labels to the tiles.
7. run `python bootstrap/compile.py --output dataset-path` to compile the dataset and meta-information

Notes:
- Duplicates are only detected by the `compile.py` program. It's best to
  repeat steps 4. and 5. often to avoid spending too much work on duplicate tiles.
  Basically, if you setup the tiling for a big image file that looks somehow
  similar to stuff you mapped already then, after setting up the tiling
  (without assigning the ignored tiles), run `compile.py --duplicates` and
  restart the `app`. If there are duplicates, they will be marked deeply red.
