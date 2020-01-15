import requests
import zipfile

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8,it;q=0.7",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded",
    "DNT": "1",
    "Host": "datomatic.no-intro.org",
    "Origin": "https://datomatic.no-intro.org",
    "Pragma": "no-cache",
    "Referer": "https://datomatic.no-intro.org/index.php?page=download&fun=daily",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36",
}

# Prepare no-intro zip
s = requests.Session()  # session to maintain cookies
r = s.post('https://datomatic.no-intro.org/index.php?page=download&fun=daily',
           data={"dat_type": 'standard', "prepare_2": 'Prepare'}, headers=headers, allow_redirects=False)


download_id = r.headers['Location'].rsplit('=', 1)[-1]

# Download latest no-intro packs
r = s.post('https://datomatic.no-intro.org/index.php?page=manager&download='+download_id,
           data={"download": 'Download'}, headers=headers, allow_redirects=True)

open('no-intro.zip', 'wb').write(r.content)

archive = zipfile.ZipFile('no-intro.zip')

# Extract all no-intro datfiles
dats = ['32X', 'Master System - Mark III', 'Mega Drive - Genesis', 'SG-1000']
for f in archive.namelist():
    if any(platform in f for platform in dats):
        archive.extract(f, './dats/')

# Download redump Sega-CD datfile
r = requests.get('http://redump.org/datfile/mcd/')
filename = r.headers['Content-Disposition'].rsplit('filename="', 1)[-1][:-1]

open(filename, 'wb').write(r.content)

# Extract Sega CD datfile
archive = zipfile.ZipFile(filename)
archive.extractall('./dats/')
