# MegaSD DB Generator

Python 3 scripts to create a DB for [Terraonion's GameDB Manager](https://github.com/Terraonion-dev/GameDBManagerMD) for the MegaSD.

Downloads info from [GiantBomb's API](https://www.giantbomb.com/api/) or from the [IGDB](https://www.igdb.com/discover)

## Thumbnails

Most original thumbnails come from the [libretro-thumbnails](https://github.com/libretro-thumbnails/libretro-thumbnails) project. They can also be downloaded from the [libretro website](http://thumbnailpacks.libretro.com/). They have been resized and their color palette reduced to work with the MegaSD menu.

## How to run

Place any No-Intro ROMs in the `No-Intro` folder and all Redump bin+cue files in the `Redump` folder.

```bash
# Convert images to tiles
./convert.sh

# Install dependencies
pipenv install

# Download info from GB or IGDB using Postman

# Set the GB API Key
export GB_API_KEY=9a286a31-6da4-4fc3-a356-dcc62d1eb289

# Download info from GB and generate the JSON DB (they will be downloaded in the dbs folder)
python downloader.py

# Build the MegaSD's XML DB with info + covers
python xml_builder.py
```

Place the generated `db.xml` file and the output folder in the same folder as the `GameDBManagerMD` executable file, press convert images and finally scan your SD card.

**The current version of the database has been compiled using the IGDB as the data source instead of GiantBomb. Adjustments might need to be made for the latest xml_builder.py to work with data from GB**

All fuzzy matches will be stored in a CSV file (`cover_fuzzy_matches.csv` and `info_fuzzy_matches.csv`) to easily check if the match is correct or not
