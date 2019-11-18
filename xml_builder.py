from collections import defaultdict
import json
import zlib
import glob
import os
from xml.dom import minidom
from lxml import etree
from io import StringIO, BytesIO
from stop_words import get_stop_words

STOP_WORDS = get_stop_words('en')
STOP_WORDS = [word.replace('\'', '') for word in STOP_WORDS]

# Unique counter per game
COUNTER = 0
# Some geneis sgames have same CRC as Master system games?
hashes = []

def main():
    # load xsd for xml validation
    xmlschema_doc = etree.parse('game.xsd')
    xmlschema = etree.XMLSchema(xmlschema_doc)
    a = etree.Element('{http://tempuri.org/GameDB.xsd}GameDB')

    do_roms('No-Intro', '*.md', 'output/Sega - Mega Drive - Genesis/Named_Titles', 'dbs/md.json', a)
    do_roms('No-Intro', '*.sms', 'output/Sega - Master System - Mark III/Named_Titles', 'dbs/master.json', a)
    do_roms('No-Intro', '*.32x', 'output/Sega - 32X/Named_Titles', 'dbs/32x.json', a)
    do_roms('No-Intro', '*.sg', 'output/Sega - SG-1000/Named_Titles', 'dbs/sg.json', a)
    do_roms('Redump', '*.cue', 'output/Sega - Mega-CD - Sega CD/Named_Titles', 'dbs/scd.json', a)

    # Insert genres at the end of the XML
    l1 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k1 = etree.SubElement(l1, '{http://tempuri.org/GameDB.xsd}Genre')
    k1.text = str(1)
    k2 = etree.SubElement(l1, '{http://tempuri.org/GameDB.xsd}Name')
    k2.text = 'Shooter'

    l2 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k3 = etree.SubElement(l2, '{http://tempuri.org/GameDB.xsd}Genre')
    k3.text = str(2)
    k4 = etree.SubElement(l2, '{http://tempuri.org/GameDB.xsd}Name')
    k4.text = 'Action'

    l3 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k5 = etree.SubElement(l3, '{http://tempuri.org/GameDB.xsd}Genre')
    k5.text = str(3)
    k6 = etree.SubElement(l3, '{http://tempuri.org/GameDB.xsd}Name')
    k6.text = 'Sports'

    l4 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k7 = etree.SubElement(l4, '{http://tempuri.org/GameDB.xsd}Genre')
    k7.text = str(4)
    k8 = etree.SubElement(l4, '{http://tempuri.org/GameDB.xsd}Name')
    k8.text = 'Misc'

    l5 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k9 = etree.SubElement(l5, '{http://tempuri.org/GameDB.xsd}Genre')
    k9.text = str(5)
    k10 = etree.SubElement(l5, '{http://tempuri.org/GameDB.xsd}Name')
    k10.text = 'Casino'

    l6 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k11 = etree.SubElement(l6, '{http://tempuri.org/GameDB.xsd}Genre')
    k11.text = str(6)
    k12 = etree.SubElement(l6, '{http://tempuri.org/GameDB.xsd}Name')
    k12.text = 'Driving'

    l7 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k11 = etree.SubElement(l7, '{http://tempuri.org/GameDB.xsd}Genre')
    k11.text = str(7)
    k12 = etree.SubElement(l7, '{http://tempuri.org/GameDB.xsd}Name')
    k12.text = 'Platform'

    l8 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k13 = etree.SubElement(l8, '{http://tempuri.org/GameDB.xsd}Genre')
    k13.text = str(8)
    k14 = etree.SubElement(l8, '{http://tempuri.org/GameDB.xsd}Name')
    k14.text = 'Puzzle'

    l9 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k15 = etree.SubElement(l9, '{http://tempuri.org/GameDB.xsd}Genre')
    k15.text = str(9)
    k16 = etree.SubElement(l9, '{http://tempuri.org/GameDB.xsd}Name')
    k16.text = 'Boxing'

    l10 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k17 = etree.SubElement(l10, '{http://tempuri.org/GameDB.xsd}Genre')
    k17.text = str(10)
    k18 = etree.SubElement(l10, '{http://tempuri.org/GameDB.xsd}Name')
    k18.text = 'Wrestling'

    l11 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k19 = etree.SubElement(l11, '{http://tempuri.org/GameDB.xsd}Genre')
    k19.text = str(11)
    k20 = etree.SubElement(l11, '{http://tempuri.org/GameDB.xsd}Name')
    k20.text = 'Strategy'

    l12 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k21 = etree.SubElement(l12, '{http://tempuri.org/GameDB.xsd}Genre')
    k21.text = str(12)
    k22 = etree.SubElement(l12, '{http://tempuri.org/GameDB.xsd}Name')
    k22.text = 'Soccer'

    l13 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k23 = etree.SubElement(l13, '{http://tempuri.org/GameDB.xsd}Genre')
    k23.text = str(13)
    k24 = etree.SubElement(l13, '{http://tempuri.org/GameDB.xsd}Name')
    k24.text = 'Golf'

    l14 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k25 = etree.SubElement(l14, '{http://tempuri.org/GameDB.xsd}Genre')
    k25.text = str(14)
    k26 = etree.SubElement(l14, '{http://tempuri.org/GameDB.xsd}Name')
    k26.text = 'Beat\'Em-Up'

    l15 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k27 = etree.SubElement(l15, '{http://tempuri.org/GameDB.xsd}Genre')
    k27.text = str(15)
    k28 = etree.SubElement(l15, '{http://tempuri.org/GameDB.xsd}Name')
    k28.text = 'Baseball'

    l16 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k29 = etree.SubElement(l16, '{http://tempuri.org/GameDB.xsd}Genre')
    k29.text = str(16)
    k30 = etree.SubElement(l16, '{http://tempuri.org/GameDB.xsd}Name')
    k30.text = 'Mahjong'

    l17 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k31 = etree.SubElement(l17, '{http://tempuri.org/GameDB.xsd}Genre')
    k31.text = str(17)
    k32 = etree.SubElement(l17, '{http://tempuri.org/GameDB.xsd}Name')
    k32.text = 'Board'

    l18 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k33 = etree.SubElement(l18, '{http://tempuri.org/GameDB.xsd}Genre')
    k33.text = str(18)
    k34 = etree.SubElement(l18, '{http://tempuri.org/GameDB.xsd}Name')
    k34.text = 'Tennis'

    l19 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k35 = etree.SubElement(l19, '{http://tempuri.org/GameDB.xsd}Genre')
    k35.text = str(19)
    k36 = etree.SubElement(l19, '{http://tempuri.org/GameDB.xsd}Name')
    k36.text = 'Fighter'

    l20 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k37 = etree.SubElement(l20, '{http://tempuri.org/GameDB.xsd}Genre')
    k37.text = str(20)
    k38 = etree.SubElement(l20, '{http://tempuri.org/GameDB.xsd}Name')
    k38.text = 'Horse Racing'

    l21 = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Genre')
    k39 = etree.SubElement(l21, '{http://tempuri.org/GameDB.xsd}Genre')
    k39.text = str(21)
    k40 = etree.SubElement(l21, '{http://tempuri.org/GameDB.xsd}Name')
    k40.text = 'Other'

    # Validate schema - Exception thrown if not valid
    try:
        valid = xmlschema.assertValid(etree.ElementTree(a))
    except Exception as e:
        print(e)
        pass

    # Save XML with indentation
    xmlstr = minidom.parseString(etree.tostring(a)).toprettyxml(indent="    ")
    with open('db.xml', 'w') as f:
        f.write(xmlstr)

# Calculate CRC for ROMs (not valid for CDs)
def crc(fileName):
    file_without_ext, ext = os.path.splitext(fileName)
    if ext == '.cue':
        with open(fileName) as f:
            # Get first bin file from first or second cue sheet line
            for i, line in enumerate(f):
                if 'CATALOG' in line:
                    continue
                else:
                    bin_file = line[6:-9]
                    break
        # Read first 2KB of first bin file of CUE sheet
        fileName = f'{os.path.dirname(fileName)}/{bin_file}'
        prev = 0
        with open(fileName, 'rb') as f:
            f.read(16)
            b = f.read(2048)
            prev = zlib.crc32(b, prev)
        return "%X"%(prev & 0xFFFFFFFF)
    else:
        prev = 0
        for eachLine in open(fileName,"rb"):
            prev = zlib.crc32(eachLine, prev)
        return "%X"%(prev & 0xFFFFFFFF)

def normalize(name):
    norm = name.lower().replace('-', '').replace(':', '').replace('\'', '').replace('~', '').replace(',', '').replace('&', '').replace('.', '').replace('+', '').replace('_', '').split('(')[0]
    return ''.join([word for word in norm.split() if word not in STOP_WORDS])

def do_roms(rom_path, rom_ext, cover_path, db_path, a):
    global COUNTER
    global hashes
    # Load all roms with full path
    roms = []
    for x in os.walk(rom_path):
        for y in glob.glob(os.path.join(x[0], rom_ext)):
            roms.append(y)

    # Load game covers
    game_covers_l = []
    for x in os.walk(f'/home/hfs/{cover_path}'):
        for y in glob.glob(os.path.join(x[0], '*.png')):
            game_covers_l.append(y[10:])
    game_covers = {}
    # Normalize cover name (some will be overwritten by the normalization)
    for d in game_covers_l:
        game_covers[normalize(os.path.basename(d))] = d

    # Load GB games lists
    # Use downloader.py
    games_list = {}
    with open(db_path) as f:
        games_list = {**games_list, **json.load(f)}

    # Normalize game names
    new_games_list = {}
    for game in games_list.keys():
        new_games_list[normalize(game)] = games_list[game]
    games_list = new_games_list

    # Build dict of normalized game title -> rom paths
    res = defaultdict(list)
    for f in roms:
        title = os.path.basename(f)
        filename = normalize(title)
        res[filename].append(f)

    # Search for coincidences and build xml
    found_db = 0
    found_covers = 0
    #hashes = []
    for filename, paths in res.items():
        COUNTER += 1

        b = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Game')

        c = etree.SubElement(b, '{http://tempuri.org/GameDB.xsd}ID')
        c.text = str(COUNTER)

        d = etree.SubElement(b, '{http://tempuri.org/GameDB.xsd}Name')
        d.text = os.path.basename(paths[0].split('(')[0]) + f'({rom_ext[2:]})'

        if filename in games_list.keys():
            found_db += 1

            # Year must be inserted before the genre
            if games_list[filename]['date'] is not None:
                e2 = etree.SubElement(b, '{http://tempuri.org/GameDB.xsd}Year')
                e2.text = games_list[filename]['date']

            if len(games_list[filename]['genres']) != 0:
                e = etree.SubElement(b, '{http://tempuri.org/GameDB.xsd}Genre')
                g = games_list[filename]['genres'][0]
                if g == 'Shooter':
                    e.text = str(1)
                elif g == 'Action':
                    e.text = str(2)
                elif g == 'Sports':
                    e.text = str(3)
                elif g == 'Misc':
                    e.text = str(4)
                elif g == 'Casino':
                    e.text = str(5)
                elif g == 'Driving':
                    e.text = str(6)
                elif g == 'Platform':
                    e.text = str(7)
                elif g == 'Puzzle':
                    e.text = str(8)
                elif g == 'Boxing':
                    e.text = str(9)
                elif g == 'Wrestling':
                    e.text = str(10)
                elif g == 'Strategy':
                    e.text = str(11)
                elif g == 'Soccer':
                    e.text = str(12)
                elif g == 'Golf':
                    e.text = str(13)
                elif g == 'Beat\'Em-Up':
                    e.text = str(14)
                elif g == 'Baseball':
                    e.text = str(15)
                elif g == 'Mahjong':
                    e.text = str(16)
                elif g == 'Board':
                    e.text = str(17)
                elif g == 'Tennis':
                    e.text = str(18)
                elif g == 'Fighter':
                    e.text = str(19)
                elif g == 'Horse Racing':
                    e.text = str(20)
                elif g == 'Other':
                    e.text = str(21)
                else: # Wrong genre
                    print(f'ABORTING - WRONG GENRE {g}')
                    exit()

        if filename in game_covers.keys():
            f = etree.SubElement(b, '{http://tempuri.org/GameDB.xsd}Screenshot')
            f.text = game_covers[filename].replace('/mnt/c', 'c:\\').replace('/', '\\\\')
            found_covers += 1

        # Calulcate hash for all rom variations
        for p in paths:
            crc_hash = crc(p)
            if crc_hash not in hashes:
                hashes.append(crc_hash)
                g = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}GameCk')

                h = etree.SubElement(g, '{http://tempuri.org/GameDB.xsd}Checksum')
                h.text = crc_hash

                i = etree.SubElement(g, '{http://tempuri.org/GameDB.xsd}GameID')
                i.text = str(COUNTER)

            title = os.path.basename(p)
            if filename in game_covers.keys():
                cover = game_covers[filename]
            else:
                cover = None

    # Print stats
    print('ROM type:' + rom_ext)
    print('Amount of roms:' + str(len(res.keys())))
    print('DB size: ' + str(len(games_list.keys())))
    print('Covers size: ' + str(len(game_covers.keys())))
    print('Matches with DB: ' + str(found_db))
    print('Matches with Covers: ' + str(found_covers))

if __name__ == '__main__':
    main()
