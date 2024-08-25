#! /bin/bash

z80asm -i bios.z80 -o bios.bin
if [ $? -ne 0 ]; then
   echo Compiling BIOS failed
   exit 1
fi

z80asm -i bios.z80 --list=bios.lst
du -b bios.bin
truncate bios.bin -s 33024

../development/compile_prog.sh console.c zisax.c -o console
if [ $? -ne 0 ]; then
   echo Compiling console failed
   exit 1
fi

cat bios.bin console.bin > ../images/rom.bin
