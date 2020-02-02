import glob
from PIL import Image
import os
import json
from subprocess import call
import requests
import re
from bs4 import BeautifulSoup
import string

db = []


def convert_genre(genre):
    genre_conversion = {
        "HERE": "Platform",
        "MAHJONG": "Mahjong",
        "VERTICAL SHOOT 'EM UP": "Shooter",
        "BEAT 'EM UP": "Beat\'Em-Up",
        "QUIZ GAME": "Other",
        "HORIZONTAL SHOOT 'EM UP": "Shooter",
        "PLATFORM": "Platform",
        "PACHINKO": "Puzzle",
        "POKER": "Casino",
        "ACTION": "Fighter",
        "DRAWING APPLICATION": "Other",
        "SHOOT 'EM UP": "Shooter",
        "GAMBLING": "Casino",
        "DIGITAL COMIC": "Other",
        "SPORT": "Sports",
        "ADULT": "Other",
        "FLIGHT COMBAT SIMULATION": "Strategy",
        "ROLE-PLAYING": "Strategy",
        "GAMBLING SIMULATION": "Casino",
        "QUIZ": "Strategy",
        "SIMULATION": "Other",
        "RACING": "Driving",
        "INTO-THE-SCREEN SHOOT 'EM UP": "Shooter",
        "PINBALL": "Other",
        "INTO-THE-SCREEN SHOOTER": "Shooter",
        "DRIVING": "Driving",
        "SUPER CD-ROM": "Shooter",
        "HORIZONZAL SHOOT 'EM UP": "Shooter",
        "KARAOKE": "Other",
        "DUNGEON CRAWLER": "Strategy",
        "PLATFORMER": "Platform",
        "ROLE PLAYING": "Strategy",
        "SCROLLING BEAT 'EM UP": "Beat\'Em-Up",
        "OTHER": "Other",
        "ONE-ON-ONE BEAT 'EM UP": "Beat\'Em-Up",
        "STRATEGY": "Strategy",
        "SPORTS": "Sports",
        "LIFE SIMULATION": "Strategy",
        "STRATEGY MANAGEMENT": "Strategy",
        "ACTION ROLE-PLAYING": "Strategy",
        "RPG": "Strategy",
        "WRESTLING": "Sports",
        "RACING SIMULATION": "Driving",
        "BOXING": "Sports",
        "ADVENTURE": "Action",
        "CARD GAME": "Strategy",
        "PUZZLE": "Puzzle",
        "CARD GAMES": "Board",
        "BOARD GAME": "Board"
    }
    return genre_conversion[genre]


def optimize_image(path):
    img = Image.open(path)
    colors = 64
    t = count_palette(img)
    while t > 13 and colors > 0:
        colors = colors - 1
        call(
            f'convert "{path}" -colors {colors} "{path}"', shell=True)
        img = Image.open(path)
        t = count_palette(img)


def reduce_tiles(tiles):
    tilesC = tiles[:]
    for m in tilesC:
        for n in tilesC:
            if m.issubset(n) and m != n:
                tiles.remove(m)
                break
    return tiles


def count_palette(img):
    tiles = []
    for r in range(0, 64, 8):
        for c in range(0, 64, 8):
            tile = set()
            for x in range(8):
                for y in range(8):
                    tile.add(img.getpixel((r+x, c+y)))
            tiles.append(tile)

    tiles = reduce_tiles(tiles)

    # if less tahn 16 colors per tile try to reduce further
    all_colors = set()
    for m in tiles:
        for n in m:
            all_colors.add(n)

    tilesC = tiles[:]
    for idx, m in enumerate(tilesC):
        for c in all_colors:
            if len(m) < 16:
                m.add(c)
                tilesC[idx] = m
            else:
                break

    tiles = reduce_tiles(tilesC)
    for t in tiles:
        if len(t) > 16:
            return 1000
    return len(tiles)


def inspect_game(name, alt_names):
    game = {}
    r = requests.get(f'http://www.pcengine.co.uk/HTML_Games/{name}.htm')
    soup = BeautifulSoup(r.text)
    title = soup.find('span', attrs={'class': 'title'}).text
    names = [str.strip(x) for x in title.split('\n')]
    game['name'] = " ".join(names)

    alternative_names = []

    if len(names) > 1:
        for n in names:
            alternative_names.append(n)

    try:
        alternative_names_cand = []
        for span in soup.findChildren('span', attrs={'class': 'details'}):
            span = span.text.split('\n')
            alternative_names_cand = alternative_names_cand + [str.strip(x) for x in span]
            alternative_names_cand = list(filter(lambda x: x != "", alternative_names_cand))

        for d in alternative_names_cand+alt_names:
            if "RELEASE DATE:" in d:
                release_date = re.search(r"(\d{4})", d).group(1)
                if release_date is not None:
                    game['release_dates'] = [{'y': release_date}]
            elif "STYLE:" in d:
                genre = d[7:]
                if genre != "":
                    game['genres'] = genre.split('/')
                    game['genres'] = [str.strip(x) for x in game['genres']]
                    game['genres'] = [convert_genre(x) for x in game['genres']]
            elif "MAKER:" in d:
                pass
            elif "STYLE:" in d:
                pass
            elif "FORMAT:" in d:
                pass
            elif "RATING:" in d:
                pass
            else:
                d = d.replace('AKA:', '')
                d = d.replace('US-', '')
                d = d.replace('(US)', '')
                extra = re.search(r"\[(.*?)\]", d)
                if extra is not None:
                    extra = extra.group(1)
                    d = d.replace(f"[{extra}]", "")
                    d = str.strip(extra)

                    alternative_names.append(d)
                    for dd in extra.split(', '):
                        if dd.lower() != 'the' and dd not in alternative_names:
                            alternative_names.append(dd)

                d = str.strip(d)
                alternative_names.append(d)
                for dd in d.split(', '):
                    if dd.lower() != 'the' and dd not in alternative_names:
                        alternative_names.append(dd)

        alternative_names = list(filter(lambda x: x != "", alternative_names))
        if len(alternative_names) > 0:
            game['alternative_names'] = alternative_names

    except Exception as e:
        print(e)
        pass

    try:
        details = soup.find('p', attrs={'class': 'details'}).text.split("\n")
        details = [str.strip(x) for x in details]
        for d in details:
            if "RELEASE DATE" in d:
                release_date = re.search(r"(\d{4})", d).group(1)
                if release_date is not None:
                    game['release_dates'] = [{'y': release_date}]
            if "STYLE" in d:
                genre = d[7:]
                if genre != "":
                    game['genres'] = genre.split('/')
                    game['genres'] = [str.strip(x) for x in game['genres']]
                    game['genres'] = [convert_genre(x) for x in game['genres']]
    except Exception:
        pass


    # Download game cover
    if "YAMAMURA MISA SUSPENSE" in game["name"]:
        game["name"] = game["name"].replace(":", "")
    table = soup.find('table', id="Info and Cover")
    imgs = table.findChildren('img')
    for img in imgs:
        if "Images-Coverthumbs" in img['src']:
            if not os.path.isfile(f'output/pce/{game["name"].replace("/", " ")}.jpg'):
                r = requests.get(f"http://www.pcengine.co.uk/{img['src'][3:]}")
                with open(f'output/pce/{game["name"].replace("/", " ")}.jpg', 'wb') as f:
                    f.write(r.content)
                call(f'convert "output/pce/{game["name"].replace("/", " ")}.jpg" -filter lanczos -resize 64x64! -normalize -unsharp 0 -enhance +dither "output/pce/{game["name"].replace("/", " ")}.bmp3"', shell=True)
                os.rename(f'output/pce/{game["name"].replace("/", " ")}.bmp3', f'output/pce/{game["name"].replace("/", " ")}.bmp')
                call(f'python3 Quantomatic.py "output/pce/{game["name"].replace("/", " ")}" -p 13', shell=True)
                call(f'convert "output/pce/{game["name"].replace("/", " ")}CrushedPals.bmp" "output/pce/{game["name"].replace("/", " ")}.png"', shell=True)
                os.remove(f'output/pce/{game["name"].replace("/", " ")}.bmp')
                os.remove(f'output/pce/{game["name"].replace("/", " ")}CrushedPals.bmp')
            #optimize_image(f'output/pce/{game["name"].replace("/", " ")}.png')

            game['image'] = f'output/pce/{game["name"].replace("/", " ")}.png'
            return (True, game["name"].replace("/", " "), game)
    return (False, game["name"].replace("/", " "), game)


for c in string.ascii_uppercase:
    r = requests.get(f'http://www.pcengine.co.uk/HTML_A-Z_Pages/{c}.htm')
    soup = BeautifulSoup(r.text)
    table = soup.find('table', id='Music')
    for row in table.findChildren('tr'):
        links = row.findChildren('a')
        if len(links) == 2:
            link = links[1]
        else:
            link = links[0]
        alt_names = link.text.split('\n')
        name = link['href'].split('/')[2][:-4]
        cover_downloaded = inspect_game(name, alt_names)
        game = cover_downloaded[2]

        # If no cover was present in the game page download from game list
        if not cover_downloaded[0]:
            print("DOWNLOADING")
            imgs = row.findChildren('img')
            for img in imgs:
                if "Images-Minicovers" in img['src']:
                    r = requests.get(f"http://www.pcengine.co.uk/{img['src'][3:]}")
                    if not os.path.isfile(f'output/pce/{cover_downloaded[1]}.jpg'):
                        with open(f'output/pce/{cover_downloaded[1]}.jpg', 'wb') as f:
                            f.write(r.content)
                        call(
                            f'convert "output/pce/{cover_downloaded[1]}.jpg" -filter lanczos -resize 64x64! -normalize -unsharp 0 -enhance +dither "output/pce/{cover_downloaded[1]}.bmp3"', shell=True)
                        os.rename(f'output/pce/{cover_downloaded[1]}.bmp3', f'output/pce/{cover_downloaded[1]}.bmp')
                        call(f'python3 Quantomatic.py "output/pce/{cover_downloaded[1]}" -p 13', shell=True)
                        call(f'convert "output/pce/{cover_downloaded[1]}CrushedPals.bmp" "output/pce/{cover_downloaded[1]}.png"', shell=True)
                        os.remove(f'output/pce/{cover_downloaded[1]}.bmp')
                        os.remove(f'output/pce/{cover_downloaded[1]}CrushedPals.bmp')
                    game['image'] = f'output/pce/{cover_downloaded[1]}.png'
                    #optimize_image(f"output/pce/{cover_downloaded[1]}.png")
        db.append(game)
        print(name)

with open('db.json', 'w') as f:
    json.dump(db, f, indent=2)

# clean jpg images
for y in glob.glob('output/pce/*.jpg'):
    os.remove(y)
