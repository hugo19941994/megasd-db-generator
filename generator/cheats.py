from pygit2 import clone_repository
import os
import re
import shutil
from pathlib import Path

def convert_code(code):
    genesis_chars = "ABCDEFGHJKLMNPRSTVWXYZ0123456789"

    code = code[0:4] + code[5:9]

    data = []
    for idx, c in enumerate(code):
        data.append(genesis_chars.find(c))

    code = data

    address = 0
    value = 0

    address |= (code[3] & 0x0f) << 20
    address |= (code[3] & 0x0f) << 20;
    address |= (code[4] & 0x1e) << 15;
    address |= (code[1] & 0x03) << 14;
    address |= (code[2] & 0x1f) << 9;
    address |= (code[3] & 0x10) << 4;
    address |= (code[6] & 0x07) << 5;
    address |= (code[7] & 0x1f);

    value |= (code[5] & 0x01) << 15;
    value |= (code[6] & 0x18) << 10;
    value |= (code[4] & 0x01) << 12;
    value |= (code[5] & 0x1e) << 7;
    value |= (code[0] & 0x1f) << 3;
    value |= (code[1] & 0x1C) >> 2;

    #print('{:08x}'.format(address))
    #print('{:04x}'.format(value))
    #print("aligned", (address & 0x1) == 0)

    return(('{:08x}'.format(address), '{:04x}'.format(value)))


db = Path('./libretro-database')
shutil.rmtree(db, ignore_errors=True)

clone_repository("git://github.com/libretro/libretro-database.git", "./libretro-database",
    bare=False, repository=None, remote=None, checkout_branch=None, callbacks=None)

# create cheat path
shutil.rmtree('./cheats', ignore_errors=True)
os.mkdir('./cheats')

# Genesis cheats
regex_cheat = r"cheat[0-9]+_code = \"([A-F0-9]{6}:[A-F0-9]{4})\""
regex_cheat2 = r"cheat[0-9]+_code = \"([A-Z0-9]{4}-[A-Z0-9]{4})\""
regex_name = r"cheat[0-9]+_desc = \"([a-zA-Z0-9 ]+)\""

for cheat_path in Path('./libretro-database/cht/Sega - Mega Drive - Genesis/').glob('*.cht'):
    try:
        with open(cheat_path) as cheat:
            print(cheat_path.name)
            name = cheat_path.name[:-4]
            pat_file = open(f'./cheats/{name}.PAR', 'wb')
            pat_file.write(b'\x00' * 6 * 16)
            pat_file.seek(0)
            print(name)
            num_cheats = 0
            for line in cheat.readlines():
                #if num_cheats >= 16:
                    #continue
                res_name = re.findall(regex_name, line)
                res_cheat = re.findall(regex_cheat, line)
                res_cheat2 = re.findall(regex_cheat2, line)
                if res_name:
                    print(res_name[0])
                if res_cheat:
                    first_part = res_cheat[0].split(':')[0].zfill(8)
                    print(first_part)
                    pat_file.write(bytes.fromhex(first_part))
                    second_part = res_cheat[0].split(':')[1].zfill(4).replace("x", "0").replace("X", "0")
                    print(second_part)
                    pat_file.write(bytes.fromhex(second_part))
                    num_cheats += 1
                    print(res_cheat[0])
                if res_cheat2:
                    address, value = convert_code(res_cheat2[0])
                    pat_file.write(bytes.fromhex(address))
                    pat_file.write(bytes.fromhex(value))
                    num_cheats += 1
                    print(f'{address}:{value}')
            pat_file.close()
    except Exception as e:
        print(cheat)
        print(e)



