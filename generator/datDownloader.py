from io import BytesIO
from selenium import webdriver
from time import sleep
import hashlib
import logging
import os
import re
import requests
import zipfile


def downloadNoIntro():
    logging.info("Downloading No-Intro DATs")

    # Dowload no-intro pack using selenium
    dir_path = os.path.dirname(os.path.realpath(__file__))
    fx_profile = webdriver.FirefoxProfile();
    fx_profile.set_preference("browser.download.folderList", 2);
    fx_profile.set_preference("browser.download.manager.showWhenStarting", False);
    fx_profile.set_preference("browser.download.dir", dir_path);
    fx_profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/zip");

    options = webdriver.FirefoxOptions()
    options.headless = True

    driver = webdriver.Firefox(firefox_profile=fx_profile, options=options);
    driver.implicitly_wait(10)

    driver.get("https://datomatic.no-intro.org")

    # select downloads
    driver.find_element_by_xpath('/html/body/div/header/nav/ul/li[3]/a').click()

    # select daily downloads
    driver.find_element_by_xpath('/html/body/div/section/article/table[1]/tbody/tr/td/a[6]').click()

    sleep(5)

    # click the prepare button
    driver.find_element_by_xpath(f'/html/body/div/section/article/div/form/input[1]').click()

    captcha = False

    try:
        captcha_image = driver.find_element_by_xpath('/html/body/div/section/article/div/form/img').get_attribute(
            'src')
        captcha = True
    except NoSuchElementException:
        pass

    if not captcha:
        driver.find_element_by_name('dwnl').click()
    else:
        # download the captcha image
        image = requests.get(captcha_image, stream=True).raw

        # hash the image
        hasher = hashlib.md5()
        buf = image.read()
        hasher.update(buf)
        hash = hasher.hexdigest()

        hash_map = {
            '402240d761cb146915b25a01c771c6a9': 'dwnl_blue',
            '3fe379d46842ffed389aa9bbeb42bb93': 'dwnl_red',
            '1e3ad98f1290f8ba0d3fc21f313f5396': 'dwnl_yellow'
        }

        # click the correct captcha color coded download button
        driver.find_element_by_name(hash_map[hash]).click()

    # wait until file is found
    found = False
    name = None
    time_slept = 0
    while not found:
        if time_slept > 360:
            raise Exception('No-Intro zip file not found')

        for f in os.listdir(dir_path):
            if 'No-Intro Love Pack' in f:
                name = f
                found = True
                break

        # wait 5 seconds
        sleep(5)
        time_slept += 5

    # Load zip file into memory
    archive = zipfile.ZipFile(f'{dir_path}/{name}')

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
