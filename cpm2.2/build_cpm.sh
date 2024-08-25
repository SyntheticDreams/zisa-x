#! /bin/bash

z80asm -i cpm22.z80 -l &> cpm22.lst
z80asm -i cpm22.z80 -o cpm22.bin
