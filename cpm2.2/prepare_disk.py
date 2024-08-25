#! /usr/bin/env python3

import subprocess
import math

DISK_SIZE = 2 * 40 * 32 * 128

with open("cpm22.bin", "rb") as handle:
    cpm_data = handle.read()

size_byte = chr(int(math.ceil(len(cpm_data) / 256))).encode("ascii")

# Boot sector format: ZB<256 blocks to copy><Destination Address><Jump Address>
disk_data = b"ZB" + size_byte + b"\x00\xC0\x00\xC0\x01" + b"\x00" * 120
disk_data += cpm_data
disk_data += (b"\xE5" * (DISK_SIZE - len(disk_data)))

with open("../images/cpm22.img", "wb") as handle:
    handle.write(disk_data)

subprocess.run("cpmcp -f zisa-x ../images/cpm22.img ../images/progs/cpm/* 0:", shell=True)
