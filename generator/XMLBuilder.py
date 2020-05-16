from collections import defaultdict
from csv import DictWriter
from datetime import date
from fuzzywuzzy import process
from io import StringIO
from lxml import etree, objectify
from stop_words import get_stop_words
from xml.dom import minidom
from zipfile import ZipFile
import glob
import json
import logging
import os
import re
import unicodedata
import zlib


class XMLGenerator():
    def __init__(self):
        logging.info("Generating DB XML")
        self.cfm = StringIO()
        self.cfmw = DictWriter(self.cfm, fieldnames=["ROM", "Cover", "Score"])
        self.cfmw.writeheader()

        self.ifm = StringIO()
        self.ifmw = DictWriter(self.ifm, fieldnames=["ROM", "DB Entry", "Score"])
        self.ifmw.writeheader()

        # Store some info to later put in the GitHub release as markdown
        self.release_md = "| System | Info | Covers |%0A| --- | --- | --- |%0A"

        self.STOP_WORDS = get_stop_words('en')
        self.STOP_WORDS = [word.replace('\'', '') for word in self.STOP_WORDS]
        self.STOP_WORDS.remove('same')

        # Add some mor stopwords manually
        self.STOP_WORDS.append('les')
        self.STOP_WORDS.append('la')

        # Unique counter per game
        self.COUNTER = 0

        # Some geneis sgames have same CRC as Master system games?
        self.hashes = []

        try:
            # Generate XML
            XMLStr = self.run()

            # Generate release ZIP file
            self.generate_zip(XMLStr)

            # Release text for Github
            if os.environ.get("GITHUB_ACTIONS"):
                print(f"::set-output name=GITHUB_RELEASE_MD::{self.release_md}")

        finally:
            # Close files
            self.cfm.close()
            self.ifm.close()

    def generate_zip(self, XMLStr):
        # create a ZipFile object
        zipObj = ZipFile(f'DB_{date.today()}.zip', 'w')

        # Add multiple files to the zip
        zipObj.writestr("db.xml", XMLStr)
        zipObj.writestr("cover_fuzzy_matches.csv", self.cfm.getvalue())
        zipObj.writestr("info_fuzzy_matches.csv", self.ifm.getvalue())

        # Insert images
        for root, dirs, files in os.walk('output'):
            for f in files:
                zipObj.write(os.path.join(root, f))

        # close the Zip File
        zipObj.close()

    def normalize(self, name):
        nfkd_form = unicodedata.normalize('NFKD', name)
        name = u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

        norm = os.path.splitext(name)[0]

        norm = norm.lower()
        substitutions = [(' ii', ' 2'), (' iii', ' 3'), (' iv', '4'), ('!', ''), ('-', ' '), (':', ''), ('\'', ''),
                         ('~', ' '), (',', ''), ('&', ''), ('+', ''), ('_', ' '), ('/', ''), ('.', ''), ('*', ' ')]
        for sub in substitutions:
            norm = norm.replace(sub[0], sub[1])

        if '(' in norm:
            norm = norm.split('(')[0]

        # Remove any duplicated spaces
        norm = re.sub(r' {2,}', ' ', norm)

        return ''.join([word for word in norm.split() if word not in self.STOP_WORDS])

    def run(self):
        # load xsd for xml validation
        xmlschema_doc = etree.parse(
            f"{os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))}/game.xsd")
        xmlschema = etree.XMLSchema(xmlschema_doc)
        a = etree.Element('{http://tempuri.org/GameDB.xsd}GameDB')

        self.do_roms('Mega Drive - Genesis', '*.md',
                     'output/Sega - Mega Drive - Genesis/Named_Titles', 'dbs/genesis.json', a)
        self.do_roms('Master System - Mark III', '*.sms',
                     'output/Sega - Master System - Mark III/Named_Titles', 'dbs/ms.json', a)
        self.do_roms('32X', '*.32x', 'output/Sega - 32X/Named_Titles', 'dbs/32x.json', a)
        self.do_roms('SG-1000', '*.sg', 'output/Sega - SG-1000/Named_Titles', 'dbs/sg1000.json', a)
        self.do_roms('Sega - Mega CD & Sega CD - Datfile (MegaSD).dat', '*.cue', 'output/Sega - Mega CD & Sega CD/Named_Titles', 'dbs/cd.json', a)

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
            xmlschema.assertValid(etree.ElementTree(a))
        except Exception as e:
            print(e)
            pass

        # Save XML with indentation
        # Return DB in XML as string
        return minidom.parseString(etree.tostring(a)).toprettyxml(indent="    ")

    def do_roms(self, datfile_name, rom_ext, cover_path, db_path, a):
        # Load all roms with full path
        roms = []
        roms_hash = {}  # store rom name with corresponding hash
        filename = [x for x in os.listdir('./dats') if datfile_name in x][0]
        tree = objectify.parse(f"./dats/{filename}")
        for t in tree.iter('rom'):
            roms.append(t.attrib.get('name'))
            roms_hash[t.attrib.get('name')] = t.attrib.get('crc')

        # Load game covers
        game_covers_l = []
        for x in os.walk(f'{cover_path}'):
            for y in glob.glob(os.path.join(x[0], '*.png')):
                game_covers_l.append(y)
        game_covers = {}
        # Normalize cover name (some will be overwritten by the normalization)
        for d in game_covers_l:
            game_covers[self.normalize(os.path.basename(d))] = d

        # Load IGDB games lists
        # Use downloader.py
        games_list = []
        with open(db_path) as f:
            games_list = json.load(f)

        # Normalize game names
        new_games_list = {}
        for game in games_list:
            new_games_list[self.normalize(game['name'])] = game
            # Add alternate names to list too (copies the whole object)
            if 'alternative_names' in game:
                for alt_name in game['alternative_names']:
                    new_games_list[self.normalize(alt_name)] = game
        games_list = new_games_list

        # Build dict of normalized game title -> rom paths
        res = defaultdict(list)
        for f in roms:
            title = os.path.basename(f)
            filename = self.normalize(title)
            res[filename].append(f)

        # Search for coincidences and build xml
        found_db = 0
        found_covers = 0

        for filename, paths in res.items():
            # Skip any BIOS files
            if '[bios]' in filename:
                continue

            self.COUNTER += 1

            b = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}Game')

            c = etree.SubElement(b, '{http://tempuri.org/GameDB.xsd}ID')
            c.text = str(self.COUNTER)

            d = etree.SubElement(b, '{http://tempuri.org/GameDB.xsd}Name')
            d.text = os.path.basename(paths[0].split('(')[0]) + f'({rom_ext[2:]})'

            # Fuzzy match
            match = process.extractOne(filename, games_list.keys())
            score = 90
            if match[0][-1].isdigit() or filename[-1].isdigit():
                score = 100
            if (len(filename) < 6) or (len(match[0]) < 6):
                score = 100

            if match[1] >= score:
                game = games_list[match[0]]

                found_db += 1

                if match[1] != 100:
                    self.ifmw.writerow({'ROM': paths[0], 'DB Entry': games_list[match[0]]["name"], "Score": match[1]})

                # Year must be inserted before the genre
                if 'release_dates' in game and 'y' in game['release_dates'][0]:
                    e2 = etree.SubElement(b, '{http://tempuri.org/GameDB.xsd}Year')
                    e2.text = str(game['release_dates'][0]['y'])

                if 'genres' in game and len(game['genres']) != 0:
                    e = etree.SubElement(b, '{http://tempuri.org/GameDB.xsd}Genre')
                    g = game['genres'][0]
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
                    else:  # Wrong genre
                        print(f'ABORTING - WRONG GENRE {g}')
                        exit()

            # Fuzzy match
            match = process.extractOne(filename, game_covers.keys())
            if match[1] >= score:

                if match[1] != 100:
                    self.cfmw.writerow({"ROM": paths[0], "Cover": game_covers[match[0]], "Score": match[1]})

                game_cover = game_covers[match[0]]
                f = etree.SubElement(b, '{http://tempuri.org/GameDB.xsd}Screenshot')
                f.text = game_cover.replace('/mnt/c', 'c:\\').replace('/', '\\\\')
                found_covers += 1

            # Calulcate hash for all rom variations
            for p in paths:
                crc_hash = roms_hash[p]
                if crc_hash not in self.hashes:
                    self.hashes.append(crc_hash)
                    g = etree.SubElement(a, '{http://tempuri.org/GameDB.xsd}GameCk')

                    h = etree.SubElement(g, '{http://tempuri.org/GameDB.xsd}Checksum')
                    h.text = crc_hash.zfill(8)

                    i = etree.SubElement(g, '{http://tempuri.org/GameDB.xsd}GameID')
                    i.text = str(self.COUNTER)

                title = os.path.basename(p)
                if filename in game_covers.keys():
                    cover = game_covers[filename]
                else:
                    cover = None

        # Print stats
        logging.info(f"ROM type: {rom_ext}")
        logging.info(f"Total ROMs: {len(res.keys())}")
        logging.info(f"IGDB Matches: {found_db}/{len(games_list.keys())}")
        logging.info(f"Cover matches: {found_covers}/{len(game_covers.keys())}\n")

        self.release_md += f"| {datfile_name} | {found_db} | {found_covers} |%0A"

    @staticmethod
    def crc(fileName):
        """
        Calculate CRC for ROMs and cue+bin
        """
        file_without_ext, ext = os.path.splitext(fileName)

        # cue + bin
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
            return "%X" % (prev & 0xFFFFFFFF)

        # ROMs
        else:
            prev = 0
            for eachLine in open(fileName, "rb"):
                prev = zlib.crc32(eachLine, prev)
            return "%X" % (prev & 0xFFFFFFFF)
