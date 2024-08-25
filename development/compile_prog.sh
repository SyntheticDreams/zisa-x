#! /bin/bash

# Note: -DZISA_PROG ensures the correct RST is called to dispatch system calls in user mode (modules can extend/override)

# Update for your environment
ZCCCFG=/home/megaboz/apps/z88dk/lib/config PATH=$PATH:/home/megaboz/apps/z88dk/bin zcc +z80 -DZISA_PROG -clib=classic -create-app -mz80 -m $@
