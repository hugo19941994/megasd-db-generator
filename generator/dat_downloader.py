import logging
import os
import re
import zipfile
from io import BytesIO

import requests


class InvalidNumberOfDatsError(Exception):
    def __init__(self):
        super().__init__("Expected 5 DATs in ./dats folder")


def download_no_intro():
    logging.info("Downloading No-Intro DATs")

    r = requests.get(
        "https://github.com/hugo19941994/auto-datfile-generator/releases/latest/download/no-intro.zip", timeout=60
    )
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


def download_redump():
    logging.info("Downloading Redump Sega CD DAT")

    # Download redump Sega-CD datfile
    r = requests.get("http://redump.org/datfile/mcd/", timeout=60)
    r.raise_for_status()

    # Load zip file into memory
    zipdata = BytesIO()
    zipdata.write(r.content)
    archive = zipfile.ZipFile(zipdata)

    # Extract Sega CD datfile
    archive.extractall("./dats/")

    d = r.headers["content-disposition"]
    fname = re.findall("filename=(.+)", d)[0]
    return fname[1:-5] + ".dat"


def download_smokemonster_cd():
    logging.info("Downloading Sega CD SmokeMonster DB")
    r = requests.get(
        "https://raw.githubusercontent.com/SmokeMonsterPacks/EverDrive-Packs-Lists-Database/master/EverDrive%20Pack%20SMDBs/MegaSD%20SMDB.txt",
        timeout=60,
    )
    r.raise_for_status()

    with open("./dats/MegaSD SMDB.txt", "w") as f:
        f.write(r.text)


def check_dats():
    if len(os.listdir("./dats")) != 5:
        raise InvalidNumberOfDatsError()


def download_dats():
    download_no_intro()
    # Redump CRCs don't correspond to the MegaSD's expected CRC values
    # use --update-custom-dat to generate the expected CRC values
    # downloadRedump()
    # checkDATs()

    logging.info("Successfully downloaded DATs\n")
