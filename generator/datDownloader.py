from io import BytesIO
import re
import logging
import os
import requests
import zipfile


def downloadNoIntro():
    logging.info("Downloading No-Intro DATs")

    headers = {
        "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,"
                   "application/signed-exchange;v=b3;q=0.9"),
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8,it;q=0.7",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded",
        "DNT": "1",
        "Host": "datomatic.no-intro.org",
        "Origin": "https://datomatic.no-intro.org",
        "Pragma": "no-cache",
        "Referer": "https://datomatic.no-intro.org/index.php?page=download&op=daily",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/79.0.3945.117 Safari/537.36")
    }

    # Request daily DAT pack
    s = requests.Session()  # session to maintain cookies
    r = s.post("https://datomatic.no-intro.org/index.php?page=download&op=daily",
               data={"dat_type": "standard", "prepare_4": "Prepare", "recaptcha_response": ""}, headers=headers, allow_redirects=False)
    r.raise_for_status()

    # Extract download ID from the 302 response Location header
    download_id = r.headers["Location"].rsplit("=", 1)[-1]

    # Download the DAT pack
    r = s.post(f"https://datomatic.no-intro.org/index.php?page=manager&download={download_id}",
               params={"page": "manager", "download": download_id}, data={"wtwtwtf": "Download"}, headers=headers, allow_redirects=True)
    r.raise_for_status()

    # Load zip file into memory
    zipdata = BytesIO()
    zipdata.write(r.content)
    archive = zipfile.ZipFile(zipdata)

    # Extract relevent DAT files
    dats = ["32X", "Master System - Mark III", "Mega Drive - Genesis", "SG-1000"]
    for f in archive.namelist():
        if any(platform in f for platform in dats):
            archive.extract(f, "./dats/")


def downloadRedump():
    logging.info("Downloading Redump Sega CD DAT")

    # Download redump Sega-CD datfile
    r = requests.get("http://redump.org/datfile/mcd/")
    r.raise_for_status()

    # Load zip file into memory
    zipdata = BytesIO()
    zipdata.write(r.content)
    archive = zipfile.ZipFile(zipdata)

    # Extract Sega CD datfile
    archive.extractall("./dats/")

    d = r.headers['content-disposition']
    fname = re.findall("filename=(.+)", d)[0]
    return fname[1:-5] + ".dat"


def downloadSmokemonsterCD():
    logging.info("Downloading Sega CD SmokeMonster DB")
    r = requests.get(
        "https://raw.githubusercontent.com/SmokeMonsterPacks/EverDrive-Packs-Lists-Database/master/EverDrive%20Pack%20SMDBs/MegaSD%20SMDB.txt")
    r.raise_for_status()

    with open('./dats/MegaSD SMDB.txt', 'w') as f:
        f.write(r.text)


def checkDATs():
    if len(os.listdir("./dats")) != 5:
        raise Exception("Expected 5 DATs in ./dats folder")


def downloadDATs():
    downloadNoIntro()
    # Redump CRCs don't correspond to the MegaSD's expected CRC values
    # use --update-custom-dat to generate the expected CRC values
    # downloadRedump()
    # checkDATs()

    logging.info("Successfully downloaded DATs\n")
