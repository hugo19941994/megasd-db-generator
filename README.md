# MegaSD Cover Scripts

Python 3 scripts to create a DB for [Terraonion's GameDB Manager](https://github.com/Terraonion-dev/GameDBManagerMD) for the MegaSD.

Downloads info from [GiantBomb's API](https://www.giantbomb.com/api/)

## How to run

Download covers from the [libretro](http://thumbnailpacks.libretro.com/) website and place them inside `./libretro-imgs`. Place any No-Intro ROMs in the `No-Intro` folder and all Redump bin+cue files in the `Redump` folder.

```bash
# Convert images to tiles
./convert.sh

# Install dependencies
pipenv install

# Set the GB API Key
export GB_API_KEY=9a286a31-6da4-4fc3-a356-dcc62d1eb289

# Download info from GB and generate the JSON DB (they will be downloaded in the dbs folder)
python downloader.py

# Build the MegaSD's XML DB with info + covers
python xml_builder.py
```

Place the generated `db.xml` file and the output folder in the same folder as the `GameDBManagerMD` executable file, press convert images and finally scan your SD card.

