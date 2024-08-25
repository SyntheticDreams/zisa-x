#! /bin/bash

# Note: -DZISA_MODULE ensures the correct RST is called to dispatch system calls in kernel mode (no further module processing)

# Update for your environment
ZCCCFG=/home/megaboz/apps/z88dk/lib/config PATH=$PATH:/home/megaboz/apps/z88dk/bin zcc +z80 -DZISA_MODULE -clib=classic -create-app -mz80 -m $@
