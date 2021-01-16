import glob
from pathlib import Path
from PIL import Image
import os
import json
from subprocess import call
import requests
import re
from bs4 import BeautifulSoup
import string

for i in os.listdir('/Users/hfs/Downloads/real-last'):
    i = os.path.splitext(Path(i).name)[0]
    if os.path.isfile(f'/Users/hfs/Downloads/new/{i}.png'):
        continue
    print(i)
    call(f'convert "/Users/hfs/Downloads/real-last/{i}.png" -filter lanczos -resize 64x40! -normalize -unsharp 0 -enhance +dither "/Users/hfs/Downloads/new/{i}.bmp3"', shell=True)
    os.rename(f'/Users/hfs/Downloads/new/{i}.bmp3', f'/Users/hfs/Downloads/new/{i}.bmp')
    call(f'python3 Quantomatic.py "/Users/hfs/Downloads/new/{i}" -p 13', shell=True)
    call(f'convert "/Users/hfs/Downloads/new/{i}CrushedPals.bmp" "/Users/hfs/Downloads/new/{i}.png"', shell=True)

