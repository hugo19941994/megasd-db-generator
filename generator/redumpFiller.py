import zipfile
from xml.dom import minidom
import zlib
import os
import time
import httpx
import asyncio
from io import BytesIO
from urllib.parse import quote
from lxml import objectify, etree
from datDownloader import downloadRedump


def _dat_to_dict(xml_path):
    xml_dict = {}
    tree_redump = objectify.parse(xml_path)
    for t in tree_redump.iter('rom'):
        if '.cue' in t.attrib.get('name'):
            xml_dict[t.attrib.get('name')] = t.attrib.get('crc')
    return xml_dict


def checkMissing(game_source):
    # Game source is either a URL or local folder

    # First download the newset Redump DAT and load it
    redump_dat_name = downloadRedump()
    redump_dict = _dat_to_dict(f"./dats/{redump_dat_name}")

    # The load the custom MegaSD DAT file and the Extras DAT file
    megasd_dict = _dat_to_dict(f"./dats/Sega - Mega CD & Sega CD - Datfile (MegaSD).dat")
    extras_dict = _dat_to_dict(f"./dats/Sega - Mega CD & Sega CD - Datfile (EXTRAS).dat")

    # The extras DAT file contains CRCs for games not present in the Redump set
    # Remove it temporarily to update the MegaSD set with the newer Redump set
    megasd_dict = dict(megasd_dict.items() - extras_dict.items())

    # Remove any removed or renamed game of the Redump set from the MegaSD set
    for name in list(megasd_dict.keys()):
        if name not in redump_dict.keys():
            print(f'Deleting game: {name}')
            del megasd_dict[name]

    # Add any new game from the Redump set in the MegaSD set
    for name in redump_dict.keys():
        if name not in megasd_dict.keys():
            # the CRC from the dict is not valid for the MegaSD, so get the ROM from somewhere and generate the new CRC
            print(f'Adding: {name[:-4]}')
            # Attempt to download game OR open from a folder
            if game_source.startswith('http'):
                crc = asyncio.run(downloadRom(name[:-4], game_source))
            else:
                crc = crc_from_folder(name[:-4], game_source)
            if crc is None:
                print(f'{name[:-4]} NOT found')
                continue
            print(f'{name[:-4]} has CRC {crc}')
            megasd_dict[name] = crc

    # Re-add the games from the EXTRA DAT
    for name, crc in extras_dict.items():
        megasd_dict[name] = crc

    # Generate new DAT file and overwrite the old one
    # This can be used by the CI pipeline to create a PR with the new data
    # Games are sorted alphabteically for easier diffs in the PR
    a = etree.Element('datafile')
    for name, crc in sorted(megasd_dict.items()):
        b = etree.SubElement(a, "game")
        b.attrib["name"] = name[:-4]
        c = etree.SubElement(b, "rom")
        c.attrib["name"] = name
        c.attrib["crc"] = crc

    dat = minidom.parseString(etree.tostring(a)).toprettyxml(indent="    ")
    with open('./dats/Sega - Mega CD & Sega CD - Datfile (MegaSD).dat', 'w') as f:
        f.write(dat)


async def download_chunk(url, start_byte, end_byte, zipdata, client):
    """
    Asynchronosuly download a single chunk
    Thi ZIP chunk itself will be streamed in 4096 byte chunks
    """
    start_time = time.time()

    # Write to in-memory IO from start_byte to end_byte
    # sart writing at start_byte
    zipdata.seek(start_byte, 0)

    # Keep track of current byte
    current = start_byte
    headers = {
        'Range': f'bytes={start_byte}-{end_byte}',
        'Cache-Control': 'no-cache',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }

    # Stream ZIP chunk in 4096 byte chunks
    async with client.stream('GET', url, headers=headers, timeout=60.0) as resp:
        resp.raise_for_status()
        async for data in resp.aiter_bytes():
            if data:
                # write in the corrent place
                zipdata.seek(current, 0)
                zipdata.write(data)
                # keep track of current byte
                current += len(data)

    end_time = time.time()
    print(f'{start_byte}-{end_byte} took {str(end_time-start_time)}')


async def downloadRom(name, base_url):
    # Download game from a URL to generate the MegaSD hash
    # url from arguments
    url = f'{base_url}/{quote(name)}.zip'

    client = httpx.AsyncClient()

    # HEAD request to check the content-length
    r = await client.head(url)

    # Game not found - abort
    if r.status_code != 200:
        return None

    length = int(r.headers['Content-Length'])

    # Divide game in X chunks and download concurrently
    CONCURRENT = 40
    chunk_size = (length / CONCURRENT) + (length % CONCURRENT)  #  TODO: last chunk will be smaller
    print(f'Content length: {length}')

    # Store all the needed requests to execute concurrently
    urls = []
    for i in range(CONCURRENT):
        urls.append((url, int(chunk_size * i), int(chunk_size * (i + 1))))

    # Save ZIP data in memory
    zipdata = BytesIO()

    # Download all chunks concurrently
    await asyncio.gather(*[download_chunk(d[0], d[1], d[2], zipdata, client) for d in urls])

    # calculate MegaSD CRC from the ZIP file
    crc = cal_crc(zipdata)
    print(f'CRC: {crc}')
    return crc


def crc_from_folder(name, source):
    print(f'Attempting to open {source}/{name}.zip')
    try:
        with open(f'{source}/{name}.zip', 'rb') as f:
            crc = cal_crc(f)
            print(f'CRC: {crc}')
            return crc
    except FileNotFoundError:
        print(f'{source}/{name}.zip not found')
        pass


def cal_crc(file_io):
    """Calculate MegaSD CRC value from an in-memory zip file"""
    archive = zipfile.ZipFile(file_io)

    for a in archive.namelist():
        file_without_ext, ext = os.path.splitext(a)
        if ext == '.cue':
            cueFile = archive.open(a)
            # Get first bin file from first or second cue sheet line
            for i, line in enumerate(cueFile):
                line = line.decode('unicode_escape')
                if 'CATALOG' in line:
                    continue
                else:
                    bin_file = line[6:-10]
                    break

            # Read first 2KB of first bin file of CUE sheet
            binFile = archive.open(bin_file)
            prev = 0
            binFile.read(16)
            b = binFile.read(2048)
            prev = zlib.crc32(b, prev)
            return "%X" % (prev & 0xFFFFFFFF)
