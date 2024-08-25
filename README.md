# ZISA-X

**ZISA-X is a new computer architecture compatible with the Z80 processor and classic 8-bit ISA bus.**

This allows Z80 compatible software like CP/M-80 to interface with common and readily available PC hardware, including CGA/EGA/VGA cards, floppy controllers, serial controllers, etc.
It features an MMU with robust banking and memory mapping outside of the 64K memory space, allowing resident "kernel modules" to provide hardware driver and extended user functionality without reducing memory available to normal programs (modules can augment and/or override any system call).

The project includes a Python-based emulator, allowing users to experiment and develop software for the system in a modern environment.
It also (partially) features hardware designs for constructing a real version of the computer. Two custom chips (for the MMU and keyboard controller) are designed for the ATF1504 CPLD (CUPL, SI, and JED files are provided).

The emulator includes the following
  1. Emulation of common PC and Z80 hardware, including the CGA/EGA/VGA text buffer, the 82077A floppy controller, CTC compatible interrupt/timer controller, the MMU, and a PS/2 compatible keyboard controller
  2. A disk image for a customized version of CP/M 2.2
  3. A "kernel module" loader that allows users to load hardware drivers and customized functionality
  4. A kernel module for providing ADM-3A terminal emulation
  5. Extensive debugging functionality, including a fully logged trace of all CPU operations, a simple script language for manaully sending I/O commands, the ability to load binary images into memory at location 0x100, etc
  
Status:
  1. DONE: Emulator (and works like a champ!)
  2. DONE: BIOS (includes internal drivers for all emulated hardware. Also includes a robust system call library and kernel module handling)
  3. DONE: Console (saves/loads settings to NVRAM, manual boot selection, etc)
  4. DONE: Kernel module manager/loader
  5. DONE: ADM-3A emulation kernel module
  6. DONE: Development support files done (assembly and C headers/libraries for making system calls, kernel module templates)
  7. DONE: MMU and keyboard controller design (heavily tested in WinCUPL emulator)
  8. TODO: Testing MMU and keyboard controller in physical ATF1504AS
  9. TODO: Design, build, and test ZISA-X PS/2 card
  10. TODO: Design, build, and test ZISA-X CPU card (CPU, ROM, RAM, NVRAM, MMU)
  11. TODO: Full computer build and test
  12. TODO: ISA card compatibility testing

ZISA-X BIOS and Specification Notes

General notes:

* The ZISA-X architecture targets Z80 compatible processors and
  the 8-bit ISA bus. The MMU can address up to 1MB of ROM, 1MB of RAM,
  1MB of NVRAM, and all 20 address lines of the 8-bit ISA I/O bus.
  It addresses these ranges as 64K banks organized in 32K increments 
  in the Z80s 64K address space. In addition to the active
  ROM/RAM/IO/NVRAM bank, the MMU can actively overlay/map the
  RAM 0-page, upper 32K RAM, and 4K of I/O bus in the Z80's
  address space as well. The 4K I/O mapping is configurable for any I/O
  address, but is intended for use with the video frame buffer. The 4K
  mapping sits at $F000, which overlaps the upper 32K if this mapping is
  also active. The I/O mapping take precedence. 

* ZISA-X is designed to be used with CP/M 2.2, but also supports native
  ZISA-X software and custom operating systems through its versatile floppy
  bootloader and large library of system calls (see below).

* The ZISA-X BIOS contains extensive functionality for "kernel modules", 
  which are executables resident in upper memory (bank 2 and above)
  that are forwarded callbacks by the BIOS for all system calls and
  interrupts. Modules may serve many purposes, such as hardware drivers,
  terminal emulation, user utilities, etc.  Modules may implement, 
  augment, or completely replace BIOS functionality, as they can block
  further handling of any system call or interrupt they process. The ZISA-X
  installation includes the CP/M "MODULE.COM" program which allows the user
  to load and configure modules.

* The BIOS supports saving/loading settings from NVRAM, including floppy
  boot order and default screen colors. These configuration values can be 
  viewed and changed from the ROM console accessed by pressing ESC during
  the boot process. The console will also load automatically if no disk
  drives or bootable floppies are found.

* ZISA-X was developing using an emulator implemented in Python. This
  emulator is avilable in the Github repo. It implements the Zilog Z80, the
  custom ZISA-X MMU, Zilog CTC, the Intel 82077AA floppy controller chipset,
  and most functionality of the CGA/EGA/VGA text framebuffer cursor
  registers. See special thanks below for the Z80 functionality.

* The hardware implementation of the ZISA-X architecture is still in
  progress. It will make use of a 14.318MHz clock for ISA cards (like CGA
  adapters) and a divided 7.159MHz CPU clock (requiring a 10MHz or faster
  Z80).

* The BIOS includes system calls for full control of a CGA/EGA/VGA
  text framebuffer, including cursor positioning, fore/back color control,
  scrolling, etc. The BIOS includes basic backspace/CRLF terminal
  emuluation for CP/M, but the ZISA-X installation also includes a module
  that provides full ADM-3A terminal emulation, including Kaypro extensions
  (insert line, delete line, clear to EOL, clear to EOS). A VT-100 module
  will be developed as well.

* The BIOS includes a driver for NEC 765A/Intel 8272A/82077AA based floppy
  controllers. Care was taken to only use features common to all 3 chipsets.

* The BIOS includes a driver for a PS/2 compatible keyboard controller.
  Since PCs typically use an 8042/AIP based controller built into the
  motherboard's chipset and not as a separate card, a CPLD design was
  created to support PS/2 communication (see repo for details). The driver
  fetches and processes PS/2 mode 2 scan codes from the controller. The
  ZISA-X emulator emulates this controller as well.

* Any future drivers (serial, sound, network, etc) or extended functionality
  for existing drivers will be provided as kernel modules.

* The BIOS includes a console stored in ROM bank 1. This may be loaded by
  pressing ESC when prompted during startup. It will also automatically load
  if no valid boot device is found. The console can read/write settings from
  NVRAM, including disk boot order and default screen colors. The console
  can also override the default boot order for the current session.

* Special thanks to osdev.org for lots of floppy/CGA/general info and 
  Ivan Kosarev for a great Z80 emulator with an included Python API. 

* ZISA-X is dedicated to one of my biggest CS heroes, Gary Kildall. Thank
  you for all that you did for computer science and the industry, Gary. You
  deserve much more recognition than you get.

Technical notes:

* After copying itself from ROM to RAM, the BIOS intializes the MMU with the
  following configuration:
     1. The MMU mode is set to RAM
     2. Bank 0 is selected
     3. Page 0 RAM mapping is enabled
     4. Upper 32K RAM mapping is enabled
     5. 4K I/O mapping is enabled
     6. The I/O bank is set to $B800 (CGA/EGA/VGA text framebuffer)

* The BIOS sets up IM 2 interrupt vectors to map interrupts 0-3 to  
  RST1-4 ($08, $10, $18, and $20). RST5 ($28) and RST6 ($30) invoke the
  the system call handler. RST1-5 will forward system calls to all registered
  modules and will process module requests for blocking further callbacks.
  RST6 will not forward system calls to modules and is intended for
  use by modules to prevent recursive callbacks.  All CP/M BIOS functions
  make use of RST5, as should all native ZISA-X software. 

* To make a ZISA-X system call via RST5:
     1. Set E register to the desired function ID (see below)
     2. System call arguments are provided via BC and HL registers
     3. System call return values are provided via A register
     5. Call RST $28 to execute the system call. This call will be forwarded
        to all registered modules for custom handling. If not blocked by
        the module callback handler, the call will also be serviced by the
        the normal BIOS handler. In this way, modules may either augment or
        replace system call and interrupt handling.

* The BIOS intializes the CTC with a 50ms timer on channel 0.  Channels 1-3
  are setup in interrupt mode for use by ISA interrupts.

* The ZISA-X implements a custom floppy boot sector/loader for providing
  support for loading CP/M or any other ZISA-X specific software. The 
  format is as follows: "ZB"|NUM_BLOCKS_COPY|DEST_ADDR|BOOT_ADDR|TYPE
    1. "ZB" are the magic bytes/literal characters
    2. Number of 256 byte blocks to copy from disk to memory (16-bit int)
    3. Destination address in memory to copy to (16-bit address)
    4. Destination address to jump to once copied (16-bit address)
    5. Type (0=Generic, 1=CP/M)

Stack notes:

* Interrupt stack is used by the BIOS during maskable interrupt events for
  internally handled functionality, such as the system timer and floppy
  controller timing. Modules handling interrupt events will maintain their
  own stacks (see below).

* Startup stack is used by the cold boot process, the console, and is also
  available for use by any non-CP/M bootable software if desired.

* Kernel modules should maintain their own stacks within their registered
  RAM bank. This is especially important as modules compiled from C using
  C libs will have especially large stacks. For any modules intercepting 
  system calls, this will overflow the BDOS/CCP stacks and crash CP/M if
  modules do not define their own stack. Additionally, since kernel modules
  receive both interrupt events and system call events, they must maintain
  maintain two separate stacks to ensure interrupts do not corrupt the
  system call handler stack. See the "ADM3A driver" module for an example
  of best practices.

* BDOS and CCP maintain their own stack.  If best practices are followed
  as mentioned above, the default CP/M stack sizes are sufficient,
  regardless of the number of complexity of active modules.

ZISA-X Memory Map

```
Startup/Console/Temporary Stack, Run_High Target = $8000:$C000 (16K)
CCP = $C000:$C8F9 (2297)
BDOS = $C8F9:$DA00 (4212 used + 147 free = 4359)
BIOS = $DA00:$EE00 (4825 used + 295 free = 5120)
Interrupt Stack = $EE00:$F000 (512)
Video FB = $F000:$FFFF (4096)

Note: BDOS and BIOS areas include unused buffer for future additions. Memory map currently subject to change.
```
