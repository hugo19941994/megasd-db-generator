import sys

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
