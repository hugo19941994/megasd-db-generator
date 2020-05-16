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


def checkMissing(base_url):
    # First download the newset Redump DAT
    redump_dict = {}
    redump_dat_name = downloadRedump()
    tree_redump = objectify.parse(f"./dats/{redump_dat_name}")
    for t in tree_redump.iter('rom'):
        if '.cue' in t.attrib.get('name'):
            redump_dict[t.attrib.get('name')] = t.attrib.get('crc')

    # Load current
    megasd_dict = {}
    tree_megasd = objectify.parse(f"./dats/Sega - Mega CD & Sega CD - Datfile (MegaSD).dat")
    for t in tree_megasd.iter('rom'):
        megasd_dict[t.attrib.get('name')] = t.attrib.get('crc')

    extras_dict = {}
    tree_extras = objectify.parse(f"./dats/Sega - Mega CD & Sega CD - Datfile (EXTRAS).dat")
    for t in tree_extras.iter('rom'):
        extras_dict[t.attrib.get('name')] = t.attrib.get('crc')

    print(len(megasd_dict))

    # megasd_dict now doesn't contain the extra roms not present in redump TODO: Get from smokemonster packs
    megasd_dict = dict(megasd_dict.items() - extras_dict.items())

    # remove from megasd_dict any roms that has a name which is not in the redump set (possible renames)
    for name in list(megasd_dict.keys()):
        if name not in redump_dict.keys():
            print('deleting', name)
            del megasd_dict[name]

    # now add any new rom not present in the megasd dataset from the redump set
    for name in redump_dict.keys():
        if name not in megasd_dict.keys():
            # the CRC from the dict is not valid for the MegaSD, so get the ROM from somewhere and generate the new CRC
            print('adding', name)
            # TODO: make compatible with offline, downloaded roms too
            crc = asyncio.run(downloadRom(name[:-4], base_url))
            if crc is None:
                print('could not add', name)
                continue
            print('added', name)
            megasd_dict[name] = crc

    # Now re-add the extras
    for name, crc in extras_dict.items():
        megasd_dict[name] = crc

    print(len(redump_dict))
    print(len(extras_dict))

    print(len(megasd_dict))

    # Generate new DAT file and overwrite the old one
    # This can be used by the CI pipeline to create a PR with the new data
    # TODO: check if there is a difference regardless of order
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
    start_time = time.time()
    zipdata.seek(start_byte, 0)
    current = start_byte
    headers = {
        'Range': f'bytes={start_byte}-{end_byte}',
        'Cache-Control': 'no-cache',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    async with client.stream('GET', url, headers=headers, timeout=60.0) as resp:
        resp.raise_for_status()
        async for data in resp.aiter_bytes():
            if data:
                zipdata.seek(current, 0)
                zipdata.write(data)
                current += len(data)
    end_time = time.time()
    print(f'{start_byte}-{end_byte} took {str(end_time-start_time)}')


async def downloadRom(name, base_url):
    url = f'{base_url}/{quote(name)}.zip'

    client = httpx.AsyncClient()
    r = await client.head(url)
    if r.status_code != 200:
        return None

    length = int(r.headers['Content-Length'])
    CONCURRENT = 40
    chunk_size = length / CONCURRENT
    chunk_remainder = length % CONCURRENT
    chunk_size += chunk_remainder
    print(length)

    urls = []
    for i in range(CONCURRENT):
        urls.append((url, int(chunk_size * i), int(chunk_size * (i + 1))))

    zipdata = BytesIO()
    await asyncio.gather(*[download_chunk(d[0], d[1], d[2], zipdata, client) for d in urls])
    crc = cal_crc(zipdata)

    print(crc)
    return crc


def cal_crc(file_io):
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
