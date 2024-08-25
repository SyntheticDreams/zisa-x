#! /bin/bash

ZCCCFG=/home/megaboz/apps/z88dk/lib/config PATH=$PATH:/home/megaboz/apps/z88dk/bin z88dk-dis -o 0x0200 -x a.map a.rom
