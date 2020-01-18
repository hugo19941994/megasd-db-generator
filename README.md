# MegaSD DB Generator

Python 3 scripts to create a DB for [Terraonion's GameDB Manager](https://github.com/Terraonion-dev/GameDBManagerMD) for the MegaSD.

Downloads info from [IGDB](https://www.igdb.com/discover)

## Thumbnails

Most original thumbnails come from the [libretro-thumbnails](https://github.com/libretro-thumbnails/libretro-thumbnails) project. They can also be downloaded from the [libretro website](http://thumbnailpacks.libretro.com/). They have been resized and their color palette reduced to work with the MegaSD menu.

## How to run

```bash
# Install dependencies
pipenv install

# Download info from GB or IGDB using Postman

# Set the GB API Key
export IGDB_API_KEY=9a286a31-6da4-4fc3-a356-dcc62d1eb289

# Download info from GB and generate the JSON DB (they will be downloaded in the dbs folder)
./generator/main.py --download-dats --download-db --generate-xml
```

This will generate a `.zip` file with the thumbnails, the XML database, and a list of fuzzy matched ROMs.

