#! /usr/bin/env python3

import argparse
import curses
import math
import os
import random
import signal
import sys
import queue
import z80

class MMU:
    PORT_BASE = 0x0000

    def __init__(self, cpu):
        self.cpu = cpu
        self.cpu.set_read_callback(self.read)
        self.cpu.set_write_callback(self.write)
        self.cpu.memory = None

        self.rom = memoryview(bytearray(b"\x00" * 1024 * 1024))
        self.ram = memoryview(bytearray(b"\x00" * 1024 * 1024))
        self.isa = memoryview(bytearray(b"\x00" * 1024 * 1024))
        self.nvram = memoryview(bytearray(b"\x00" * 1024 * 1024))

        self.r_mapped = 0x00
        self.r_mode = 0x00
        self.r_pri_bank = 0x00
        self.r_isa_bank = 0x00

        self.nvram_path = None
        self.stack_used = set()

        # Mapped
        # 0x01: CS=ram, ram_start=0x00000, z80_start=0x0000, len=256
        # 0x02: CS=ram, ram_start=0x08000, z80_start=0x8000, len=32K
        # 0x04: CS=isa, isa_start=isamap_bank, z80_start=0xF000, len=4K

        # Mode
        # 0x00: CS=rom
        # 0x01: CS=ram
        # 0x02: CS=isa
        # 0x03: CS=nvram

        # Primary Bank
        # 5 bits select 32K primary bank: reg:XXXBBBBB -> full address:BBBBBAAAAAAAAAAAAAAA (5B, 15A = 32 * 32K = 1024K)
        # X = Ignored, B = bank, A = Z80 address
        # NOTE: The Z80's A15 is added as carry-in to primary bank address since A15 overlaps B0. This ensures the upper
        # 32K of the Z80's address space maps to the next bank up when the bank is odd numbered.

        # ISA Mapping Bank
        # 8 bits select 4K ISA mapping bank: reg: BBBBBBBB -> full address:BBBBBBBBAAAAAAAAAAAA (8B, 12A = 256 * 4K = 1024K)
        # B = bank, A = Z80 address

    def _get_memory(self, addr):
        chip = self.rom

        # Select chip
        if self.r_mode == 0x00:
            chip = self.rom

        if self.r_mode == 0x01:
            chip = self.ram

        if self.r_mode == 0x02:
            chip = self.isa

        if self.r_mode == 0x03:
            chip = self.nvram

        # Mapping - page 0 in RAM
        if (self.r_mapped & 0x01) and not (addr & 0xFF00):
            chip = self.ram
            full_addr = addr

        # Mapping - text frame buffer on ISA bus (higher priority than upper 32K)
        elif (self.r_mapped & 0x04) and ((addr & 0xF000) == 0xF000):
            chip = self.isa
            full_addr = (self.r_isa_bank << 12) | (addr & 0xFFF)

        # Mapping - Upper 32K in RAM
        elif (self.r_mapped & 0x02) and ((addr & 0x8000) == 0x8000):
            chip = self.ram
            full_addr = addr

        # Map to destination's full address
        else:
            adj_bank = self.r_pri_bank + (1 if (addr & 0x8000) else 0)
            full_addr = (adj_bank << 15) | (addr & 0x7FFF)

        return chip[full_addr : full_addr + 1], chip

    def input(self, port):
        if port == MMU.PORT_BASE + 0:
            return self.r_mapped

        if port == MMU.PORT_BASE + 1:
            return self.r_mode

        if port == MMU.PORT_BASE + 2:
            return self.r_pri_bank

        if port == MMU.PORT_BASE + 3:
            return self.r_isa_bank

        return None

    def output(self, port, data):
        if port == MMU.PORT_BASE + 0:
            self.r_mapped = data
            return True

        if port == MMU.PORT_BASE + 1:
            self.r_mode = data
            return True

        if port == MMU.PORT_BASE + 2:
            self.r_pri_bank = data
            return True

        if port == MMU.PORT_BASE + 3:
            self.r_isa_bank = data
            return True

        return False

    def read(self, addr):
        # Record stack usage
        if args.debug:
            self.stack_used.add(self.cpu.sp)

        # Record registers
        #if (self.cpu.iy & 0xFF00 > 0) and (self._get_memory(addr)[0] == 0xfd):
        #    log(get_regs())

        val = self._get_memory(addr)[0][0]
        return val

    def write(self, addr, data):
        memory, chip = self._get_memory(addr)

        if chip is not self.rom:
            self._get_memory(addr)[0][0] = data
        else:
            log(f"ERROR: Writing to ROM: {hex(addr)}")
            sys.exit(0)

        if chip is self.nvram:
            self.save_nvram()

    def load_rom(self, path):
        with open(path, "rb") as handle:
            data = handle.read()
            self.rom[:len(data)] = data

    def load_nvram(self, path):
        self.nvram_path = path
        with open(self.nvram_path, "rb") as handle:
            data = handle.read()
            self.nvram[:len(data)] = data

    def save_nvram(self):
        with open(self.nvram_path, "wb") as handle:
            handle.write(self.nvram)

    def load_tpa(self, path):
        with open(path, "rb") as handle:
            data = handle.read()

            print(f"TPA page count: {math.ceil(len(data)/256)}\n\nPress enter to start VM")
            input("")

            self.ram[0x100:0x100 + len(data)] = data

class CTC:
    PORT_BASE = 0x0010

    def __init__(self, cpu, mmu):
        self.cpu = cpu
        self.mmu = mmu

        # Channel format [ trigger, scaler, mode, interrupt, constant ]
        # Mode: 0 = Timer, 1 = Counter
        # Trigger: 0 = Automatic, 1 = CLK/TRG Pulse
        self.channel_configs = [ [ 0, 16, 0, False ] for _ in range(4) ]
        self.channel_constants = [ 256, 256, 256, 256 ]
        self.channel_counts = [ -1, -1, -1, -1 ]
        self.channel_scalers = [ 0, 0, 0, 0 ]
        self.channel_waiting = [ False, False, False, False ]
        self.channel_interrupted = [ False, False, False, False ]
        self.active_int = None
        self.vector_base = 0x0000
        self.reti_active = False
        self.cpu.set_reti_callback(self.reti_handler)
        self.cpu.set_get_int_vector_callback(self.int_vector_handler)

    def input(self, port):
        if port & 0xFFFC != CTC.PORT_BASE & 0xFFFC:
            return None

        channel = port & 0x000F
        if channel > 3:
            return None

        return self.channel_counts[channel]

    def output(self, port, data):
        if port & 0xFFFC != CTC.PORT_BASE & 0xFFFC:
            return False

        channel = port & 0x000F
        if channel > 3:
            return False

        # Receive constant if waiting
        if self.channel_waiting[channel]:
            self.channel_constants[channel] = 256 if data == 0 else data
            self.channel_waiting[channel] = False

            # If in automatic trigger mode or counter mode, and channel is stopped, automatically start
            if ((self.channel_configs[channel][0] == 0) or (self.channel_configs[channel][2] == 1)) and (self.channel_counts[channel] == -1):
                self.channel_counts[channel] = self.channel_constants[channel]

            return True

        # Vector
        if data & 0x01 == 0:
            self.vector_base = data & 0xF8
            return True

        # Control
        else:
            reset = (data & 0x02) > 0
            constant = (data & 0x04) > 0
            trigger = int((data & 0x08) > 0)
            scaler = 256 if data & 0x20 else 16
            mode = int((data & 0x40) > 0)
            interrupt = (data & 0x80) > 0

            # Update config
            self.channel_configs[channel] = [ trigger, scaler, mode, interrupt ]

            if constant:
                self.channel_waiting[channel] = True

            if reset:
                self.channel_counts[channel] = -1
                self.channel_scalers[channel] = 255

            return True

    def process_tick(self):
        # Check for RETI        
        if self.reti_active:
            self.end_int_handler()

        for channel in range(4):
            self.channel_scalers[channel] = (self.channel_scalers[channel] - 1) % 256

            # Skip if channel is disabled
            if self.channel_counts[channel] == -1:
                continue

            # If timer mode, decrement if scaler at 0
            if (self.channel_configs[channel][2] == 0) and ((self.channel_scalers[channel] % self.channel_configs[channel][1]) == 0):
                self.channel_counts[channel] -= 1

            # Process if count is 0
            if self.channel_counts[channel] == 0:
                # Raise interrupt if configured
                if self.channel_configs[channel][3]:
                    self.channel_interrupted[channel] = True

                # Automatically reset if in automatic trigger or counter mode
                if (self.channel_configs[channel][0] == 0) or (self.channel_configs[channel][2] == 1):
                    self.channel_counts[channel] = self.channel_constants[channel]

            # If ready and triggered, indicate interrupt line being held but interrupt not yet assigned (-1)
            if (self.active_int is None) and self.channel_interrupted[channel]:
                self.active_int = -1

            # While line held, continually signal interrupt to CPU
            if (self.active_int == -1):
                self.cpu.on_handle_active_int()

    def process_int(self, channel):
        # Ignore if channel is disabled
        if self.channel_counts[channel] == -1:
            return

        # If counter mode, decrement
        if self.channel_configs[channel][2] == 1:
            self.channel_counts[channel] -= 1

        # If timer mode and count is 0, reset
        if (self.channel_configs[channel][2] == 0 ) and (self.channel_counts[channel] == 0):
            self.channel_counts[channel] = self.channel_constants[channel]

    def int_vector_handler(self):
        # Interrupt accepted, prioritize and assign interrupt
        for channel in range(4):
            if self.channel_interrupted[channel]:
                self.active_int = channel
                return self.vector_base + (2 * channel)

        return self.vector_base

    def end_int_handler(self):
        # Clear RETI flag
        self.reti_active = False

        # Ignore RETI if no active interrupt
        if self.active_int is None:
            return

        self.channel_interrupted[self.active_int] = False
        self.active_int = None

    def reti_handler(self):
        self.reti_active = True

class Keyboard:
    PORT_BASE = 0x0020
    CODE_TRANS = {
        "a": "\x1C", "b": "\x32", "c": "\x21", "d": "\x23",
        "e": "\x24", "f": "\x2B", "g": "\x34", "h": "\x33",
        "i": "\x43", "j": "\x3B", "k": "\x42", "l": "\x4B",
        "m": "\x3A", "n": "\x31", "o": "\x44", "p": "\x4D",
        "q": "\x15", "r": "\x2D", "s": "\x1B", "t": "\x2C",
        "u": "\x3C", "v": "\x2A", "w": "\x1D", "x": "\x22",
        "y": "\x35", "z": "\x1A", "0": "\x45", "1": "\x16",
        "2": "\x1E", "3": "\x26", "4": "\x25", "5": "\x2E",
        "6": "\x36", "7": "\x3D", "8": "\x3E", "9": "\x46",
        "`": "\x0E", "-": "\x4E", "=": "\x55", "\\": "\x5D",
        "[": "\x54", "]": "\x5B", ";": "\x4C", "'": "\x52",
        ",": "\x41", ".": "\x49", "/": "\x4A", " ": "\x29",
        "\x08": "\x66", "\x09": "\x0D", "\x0D": "\x5A", "\x1b": "\x76",
        "A": "\x12\x1C", "B": "\x12\x32", "C": "\x12\x21", "D": "\x12\x23",
        "E": "\x12\x24", "F": "\x12\x2B", "G": "\x12\x34", "H": "\x12\x33",
        "I": "\x12\x43", "J": "\x12\x3B", "K": "\x12\x42", "L": "\x12\x4B",
        "M": "\x12\x3A", "N": "\x12\x31", "O": "\x12\x44", "P": "\x12\x4D",
        "Q": "\x12\x15", "R": "\x12\x2D", "S": "\x12\x1B", "T": "\x12\x2C",
        "U": "\x12\x3C", "V": "\x12\x2A", "W": "\x12\x1D", "X": "\x12\x22",
        "Y": "\x12\x35", "Z": "\x12\x1A", ")": "\x12\x45", "!": "\x12\x16",
        "@": "\x12\x1E", "#": "\x12\x26", "$": "\x12\x25", "%": "\x12\x2E",
        "^": "\x12\x36", "&": "\x12\x3D", "*": "\x12\x3E", "(": "\x12\x46",
        "~": "\x12\x0E", "_": "\x12\x4E", "+": "\x12\x55", "|": "\x12\x5D",
        "{": "\x12\x54", "}": "\x12\x5B", ":": "\x12\x4C", "\"": "\x12\x52",
        "<": "\x12\x41", ">": "\x12\x49", "?": "\x12\x4A",
        "\x01": "\x14\x1C", "\x02": "\x14\x32", "\x03": "\x14\x21", "\x04": "\x14\x23",
    }

    def __init__(self):
        self.queue = queue.Queue()
        self.cmd_active = False
        self.ack = 0x00

    def input(self, port):
        if port & 0xFFF0 != Keyboard.PORT_BASE & 0xFFF0:
            return None

        channel = port & 0x000F

        if channel == 0:
            if self.cmd_active:
                return 0x00

            return self.get_code()

        if channel == 3:
            return self.ack

    def output(self, port, data):
        if port & 0xFFF0 != Keyboard.PORT_BASE & 0xFFF0:
            return False

        channel = port & 0x000F

        if channel == 1:
            if self.cmd_active:
                # Process command
                self.ack = 0x01

            return True

        if channel == 2:
            self.cmd_active = (data % 2 == 1)
            return True

        return False

    def put_key(self, key):
        # Key down
        for code in Keyboard.CODE_TRANS[chr(key)]:
            self.queue.put(ord(code))

        # Key up 
        for code in Keyboard.CODE_TRANS[chr(key)]:
            if code != "\xE0":
                self.queue.put(ord("\xF0"))

            self.queue.put(ord(code))

    def get_code(self):
        try:
            code = self.queue.get(False)
        except queue.Empty:
            code = 0x00

        log(f"GET CODE: {code}")
        return code

class Floppy:
    PORT_BASE = 0x03F0
    REG_DOR = 2
    REG_MSR = 4
    REG_DSR = 4
    REG_FIFO = 5
    REG_DIR = 7
    REG_CCR = 7
    HEAD_COUNT = 2
    TRACK_COUNT = 40
    SECTORS_TRACK = 32
    SECTOR_SIZE = 128
    DELAY = 1
    FAIL_RATE = 0.0

    @classmethod
    def logical_physical_pos(cls, log_pos):
        log_sector = log_pos // Floppy.SECTOR_SIZE
        head = (log_sector // Floppy.SECTORS_TRACK) % 2
        track = (log_sector // Floppy.SECTORS_TRACK) // 2
        sector = log_sector % Floppy.SECTORS_TRACK
        rel_pos = log_pos % Floppy.SECTOR_SIZE

        return (head * Floppy.TRACK_COUNT * Floppy.SECTORS_TRACK * Floppy.SECTOR_SIZE) + (track * Floppy.SECTORS_TRACK * Floppy.SECTOR_SIZE) + (sector * Floppy.SECTOR_SIZE) + rel_pos

    def __init__(self):
        self.initialized = False
        self.drive = 0
        self.head = 0
        self.tracks = [ 0, 0, 0, 0 ]
        self.sector = 0
        self.pos = 0
        self.motors = [ False, False, False, False ]
        self.rate = 500
        self.nondma = False
        self.dio = 0
        self.rqm = False
        self.disk_change = False
        self.phase = 0
        self.active_command = None
        self.command_byte = 0
        self.locked = False
        self.sim_delay = 1
        self.images = [[0x00] * self.get_max_count(), [0x00] * self.get_max_count(), [0x00] * self.get_max_count(), [0x00] * self.get_max_count()]
        self.paths = [ "", "", "", "" ]

    def get_pos(self):
        pos = self.head * Floppy.TRACK_COUNT * Floppy.SECTORS_TRACK * Floppy.SECTOR_SIZE
        pos += self.tracks[self.drive] * Floppy.SECTORS_TRACK * Floppy.SECTOR_SIZE
        pos += (self.sector - 1) * Floppy.SECTOR_SIZE
        pos += self.pos
        self.pos += 1

        return pos

    def get_max_count(self):
        return Floppy.HEAD_COUNT * Floppy.TRACK_COUNT * Floppy.SECTORS_TRACK * Floppy.SECTOR_SIZE

    def get_sim_rqm(self):
        if (self.active_command is not None) and (self.sim_delay % Floppy.DELAY != 0):
            return False

        return self.rqm

    def init_command(self):
        self.phase = 0
        self.active_command = None
        self.command_byte = 0
        self.rqm = True
        self.dio = 0

    def start_command(self, data):
        if (data & 0x1F) == 0x06:
            self.active_command = "READ"

        if (data & 0x2F) == 0x05:
            self.active_command = "WRITE"

        if data == 0x4D:
            self.active_command = "FORMAT"

        if data == 0x03:
            self.active_command = "SPECIFY"

        if data == 0x13:
            self.active_command = "CONFIGURE"

        if data == 0x07:
            self.active_command = "RECALIBRATE"

        if (data & 0x7F) == 0x14:
            self.active_command = "LOCK"

    def process_read_output(self, data, bits):
        if self.phase == 0:
            if self.command_byte == 0:
                self.command_byte += 1
                return

            if self.command_byte == 1:
                self.drive = data & 0x03
                self.head = bits[2]
                self.command_byte += 1
                return

            if self.command_byte == 2:
                self.tracks[self.drive] = data
                self.command_byte += 1
                return

            if self.command_byte == 3:
                self.head = data
                self.command_byte += 1
                return

            if self.command_byte == 4:
                self.sector = data
                self.command_byte += 1
                return

            if self.command_byte == 5:
                if data != 0x00:
                    log(f"WARNING: Incorrect sector size during READ: {data}");
                self.command_byte += 1
                return

            if self.command_byte == 6:
                if data != self.sector:
                    log(f"WARNING: EOT not set to correct sector during READ: {data}");
                self.command_byte += 1
                return

            if self.command_byte == 7:
                # Not sure GPL size for 128 byte sectors
                self.command_byte += 1
                return

            if self.command_byte == 8:
                if data != Floppy.SECTOR_SIZE:
                    log(f"WARNING: DTL incorrect size during READ: {data}");
                self.phase = 1
                self.dio = 1
                self.nondma = True
                self.pos = 0

                # Immediately indicate the FIFO is "filled"
                self.rqm = True
                return

        if self.phase == 1:
            # Invalid
            log(f"WARNING: Writing data to FIFO during READ execution phase");
            return

    def process_read_input(self):
        if self.phase == 1:
            if not self.motors[self.drive]:
                log(f"WARNING: Reading data from FIFO during READ without motor on ");

            val = self.images[self.drive][self.get_pos()]
            log(f"Floppy: Read - Drive {self.drive} Head {self.head} Track {self.tracks[self.drive]} Sector {self.sector} Pos {self.pos}")

            if self.pos >= Floppy.SECTOR_SIZE:
                self.phase = 2
                self.rqm = True
                self.nondma = False
                self.command_byte = 0

            return val

        if self.phase == 2:
            if self.command_byte == 0:
                self.command_byte += 1

                # Fail operation if no disk in drive
                read_fail = self.paths[self.drive] == ""

                # Fail operation at virtual failure rate
                read_fail = read_fail or (random.random() < Floppy.FAIL_RATE)

                val = [ self.drive & 0x01, self.drive & 0x02, self.head, 0, 0, 1, read_fail, False ]
                return int("".join([ str(int(x)) for x in reversed(val) ]), 2)

            if self.command_byte == 1:
                self.command_byte += 1
                return 0

            if self.command_byte == 2:
                self.command_byte += 1
                return 0

            if self.command_byte == 3:
                self.command_byte += 1
                return self.tracks[self.drive]

            if self.command_byte == 4:
                self.command_byte += 1
                return self.head

            if self.command_byte == 5:
                self.command_byte += 1
                return self.sector

            if self.command_byte == 6:
                self.init_command()
                return 0

        return 0

    def process_write_output(self, data, bits):
        if self.phase == 0:
            if self.command_byte == 0:
                self.command_byte += 1
                return

            if self.command_byte == 1:
                self.drive = data & 0x03
                self.head = bits[2]
                self.command_byte += 1
                return

            if self.command_byte == 2:
                self.tracks[self.drive] = data
                self.command_byte += 1
                return

            if self.command_byte == 3:
                self.head = data
                self.command_byte += 1
                return

            if self.command_byte == 4:
                self.sector = data
                self.command_byte += 1
                return

            if self.command_byte == 5:
                if data != 0x00:
                    log(f"WARNING: Incorrect sector size during WRITE: {data}");
                self.command_byte += 1
                return

            if self.command_byte == 6:
                if data != self.sector:
                    log(f"WARNING: EOT not set to correct sector during WRITE: {data}");
                self.command_byte += 1
                return

            if self.command_byte == 7:
                # Not sure GPL size for 128 byte sectors
                self.command_byte += 1
                return

            if self.command_byte == 8:
                if data != Floppy.SECTOR_SIZE:
                    log(f"WARNING: DTL incorrect size during WRITE: {data}");
                self.phase = 1
                self.dio = 0
                self.nondma = True
                self.pos = 0

                # Immediately indicate the FIFO is "empty"
                self.rqm = True
                return

        if self.phase == 1:
            if not self.motors[self.drive]:
                log(f"WARNING: Writing data to FIFO during WRITE without motor on");

            self.images[self.drive][self.get_pos()] = data
            log(f"Floppy: Write - Drive {self.drive} Head {self.head} Track {self.tracks[self.drive]} Sector {self.sector} Pos {self.pos}")

            if self.pos >= Floppy.SECTOR_SIZE:
                self.phase = 2
                self.dio = 1
                self.rqm = True
                self.nondma = False
                self.command_byte = 0

            return

    def process_write_input(self):
        if self.phase == 2:
            if self.command_byte == 0:
                self.command_byte += 1

                # Fail operation if no disk in drive
                write_fail = self.paths[self.drive] == ""

                # Fail operation at virtual failure rate
                write_fail = write_fail or (random.random() < Floppy.FAIL_RATE)

                val = [ self.drive & 0x01, self.drive & 0x02, self.head, 0, 0, 1, write_fail, False ]
                return int("".join([ str(int(x)) for x in reversed(val) ]), 2)

            if self.command_byte == 1:
                self.command_byte += 1
                return 0

            if self.command_byte == 2:
                self.command_byte += 1
                return 0

            if self.command_byte == 3:
                self.command_byte += 1
                return self.tracks[self.drive]

            if self.command_byte == 4:
                self.command_byte += 1
                return self.head

            if self.command_byte == 5:
                self.command_byte += 1
                return self.sector

            if self.command_byte == 6:
                self.init_command()
                return 0

        return 0

    def process_specify_output(self, data, bits):
        if self.phase == 0:
            if self.command_byte == 0:
                self.command_byte += 1
                return

            if self.command_byte == 1:
                log(f"Floppy specify: SRT: {(data >> 4) & 0x0F}, HUT: {data & 0x0F}")
                self.command_byte += 1
                return

            if self.command_byte == 2:
                if not bits[0]:
                    log(f"WARNING: ND incorrect: {bits[0]}");

                log(f"Floppy specify: HLT: {data >> 1}")
                self.init_command()
                return

    def process_configure_output(self, data, bits):
        if self.phase == 0:
            if self.command_byte == 0:
                self.command_byte += 1
                return

            if self.command_byte == 1:
                self.command_byte += 1
                return

            if self.command_byte == 2:
                if not bits[6]:
                    log(f"WARNING: EIS incorrect : {bits[6]}");

                if bits[5]:
                    log(f"WARNING: EFIFO incorrect : {bits[5]}");

                if bits[4]:
                    log(f"WARNING: POLL incorrect : {bits[4]}");

                if (data & 0x0F) != 10:
                    log(f"WARNING: FIFOTHR incorrect : {data & 0x0F}");

                self.command_byte += 1
                return

            if self.command_byte == 3:
                if data != 0:
                    log(f"WARNING: PRETRK incorrect : {data & 0x0F}");
                self.init_command()
                return

    def process_recalibrate_output(self, data, bits):
        if self.phase == 0:
            if self.command_byte == 0:
                self.command_byte += 1
                return

            if self.command_byte == 1:
                self.drive = data & 0x03
                if not self.motors[self.drive]:
                    log(f"WARNING: Recalibrate without running motor {self.drive} {self.motors[self.drive]}");
                self.tracks[self.drive] = 0

                self.init_command()

    def process_lock_output(self, data, bits):
        if self.phase == 0:
            self.locked = bits[7]
            self.dio = 1
            self.phase = 2
            return

    def process_lock_input(self):
        if self.phase == 2:
            self.init_command()
            return int(self.locked) << 4

    def load_image(self, drive):
        with open(self.paths[drive], "rb") as handle:
            data = handle.read()
            for log_pos in range(len(data)):
                phys_pos = Floppy.logical_physical_pos(log_pos)
                self.images[drive][phys_pos] = data[log_pos]

    def save_image(self, drive):
        with open(self.paths[drive], "wb") as handle:
            file_bytes = bytearray(self.get_max_count())
            for log_pos in range(len(file_bytes)):
                phys_pos = Floppy.logical_physical_pos(log_pos)
                file_bytes[log_pos] = self.images[drive][phys_pos]

            handle.write(file_bytes)

    def input(self, port):
        if port & 0xFFF0 != Floppy.PORT_BASE & 0xFFF0:
            return None

        register = port & 0x000F

        if register == Floppy.REG_DOR:
            val = [ (self.drive & 0x01) > 0, (self.drive & 0x02) > 0, False, False, self.motors[0], self.motors[1], self.motors[2], self.motors[3] ]
            return int("".join([ str(int(x)) for x in reversed(val) ]), 2)

        if register == Floppy.REG_MSR:
            # Simulate waiting for commands
            if (self.sim_delay % Floppy.DELAY != 0):
                self.sim_delay = (self.sim_delay + 1) % Floppy.DELAY

            val = [ 0, 0, 0, 0, self.active_command is not None, self.nondma, self.dio, self.get_sim_rqm() ]
            return int("".join([ str(int(x)) for x in reversed(val) ]), 2)

        if register == Floppy.REG_FIFO:
            # Report invalid operations
            if self.dio == 0:
                log(f"WARNING: Reading data from FIFO while DIO set to 0");
                return 0

            if not self.get_sim_rqm():
                log(f"WARNING: Reading data from FIFO while RQM set to 0");
                return 0

            if self.phase == 0:
                log(f"WARNING: Reading data from FIFO during command phase");
                return 0

            # Simulate delay processing command
            self.sim_delay = (self.sim_delay + 1) % Floppy.DELAY

            # Process existing command
            if self.active_command == "READ":
                return self.process_read_input()

            if self.active_command == "WRITE":
                return self.process_write_input()

            if self.active_command == "LOCK":
                return self.process_lock_input()

            return 0

        if register == Floppy.REG_DIR:
            return int(self.disk_change) << 7

    def output(self, port, data):
        if port & 0xFFF0 != Floppy.PORT_BASE & 0xFFF0:
            return False

        register = port & 0x000F
        bits = [ False if (data & 2**x) == 0 else True for x in range(8) ]

        if register == Floppy.REG_DOR:
            for x in range(4):
                if self.motors[x] != bits[4 + x]:
                    log(f"Floppy: motor {x} status changed: {bits[4 + x]}")

            self.motors[0], self.motors[1], self.motors[2], self.motors[3] = bits[4:]
            self.drive = 2 * int(bits[1]) + int(bits[0])
            return True

        if register == Floppy.REG_DSR:
            if data & 0x03 == 0: self.rate = 500
            if data & 0x03 == 1: self.rate = 300
            if data & 0x03 == 2: self.rate = 250
            if data & 0x03 == 3: self.rate = 1000
            if bits[7]:
                log("Floppy: Reset")
                if self.initialized and not self.locked:
                    log(f"WARNING: Reset without lock active");
                self.init_command()
                self.initialized = True

            return True

        if register == Floppy.REG_FIFO:
            # Report invalid operations
            if self.dio == 1:
                log(f"Floppy Warning: Writing data to FIFO while DIO set to 1");
                return True

            if not self.get_sim_rqm():
                log(f"Floppy Warning: Writing data to FIFO while RQM set to 0");
                return True

            if self.phase == 2:
                log(f"Floppy Warning: Writing data to FIFO during result phase");
                return True

            # Check for start of new command
            if (self.phase == 0) and (self.active_command is None):
                self.start_command(data)
                log(f"Floppy: Command={self.active_command}")

            # Simulate delay processing command
            self.sim_delay = (self.sim_delay + 1) % Floppy.DELAY

            # Process existing command
            if self.active_command == "READ":
                self.process_read_output(data, bits)

            if self.active_command == "WRITE":
                self.process_write_output(data, bits)

            if self.active_command == "SPECIFY":
                self.process_specify_output(data, bits)

            if self.active_command == "CONFIGURE":
                self.process_configure_output(data, bits)

            if self.active_command == "RECALIBRATE":
                self.process_recalibrate_output(data, bits)

            if self.active_command == "LOCK":
                self.process_lock_output(data, bits)

            return True

        if register == Floppy.REG_CCR:
            if not bits[1] and not bits[0]: self.rate = 500
            if not bits[1] and bits[0]: self.rate = 300
            if bits[1] and not bits[0]: self.rate = 250
            if bits[1] and bits[0]: self.rate = 1000
            return True

        return True

class CGA:
    FB_START = 0xB8000
    PORT_BASE = 0x03D0

    @classmethod
    def get_color(cls, attr):
        # Convert BGR -> RGB
        bits = "{:08b}".format(attr)
        bits = int(bits[0] + bits[3] + bits[2] + bits[1] + bits[4] + bits[7] + bits[6] + bits[5], 2)

        # Calculate fore, back, blink
        fore = bits & 0x0F
        back = (bits & 0x70) >> 4
        pair = curses.color_pair(fore * 8 + back)

        if bits & 0x80:
            pair |= curses.A_BLINK

        return pair

    def __init__(self, stdscr, memory):
        self.stdscr = stdscr
        self.memory = memory
        self.control_mode = 0x00
        self.cursor_high = 0x00
        self.cursor_low = 0x00

        curses.start_color()
        curses.use_default_colors()
        curses.curs_set(1)
        curses.set_escdelay(1)

        # Init colors
        for fore in range(16):
            for back in range(8):
                curses.init_pair(fore * 8 + back, fore, back)

    def input(self, port):
        if port & 0xFFF0 != CGA.PORT_BASE & 0xFFF0:
            return None

        channel = port & 0x000F

        return 0x00

    def output(self, port, data):
        if port & 0xFFF0 != CGA.PORT_BASE & 0xFFF0:
            return False

        channel = port & 0x000F

        if channel == 4:
            self.control_mode = data
            return True

        if channel == 5:
            if self.control_mode == 0x0F: self.cursor_low = data
            if self.control_mode == 0x0E: self.cursor_high = data
            return True

        return False

    def set_cursor(self):
        abs_pos = (self.cursor_high << 8) | (self.cursor_low)
        cursor_x = abs_pos % 80
        cursor_y = abs_pos // 80
        self.stdscr.move(cursor_y, cursor_x)

    def render(self):
        for y in range(25):
            for x in range(80):
                char = self.memory[CGA.FB_START + (y * 160) + (x * 2)]
                attr = self.memory[CGA.FB_START + (y * 160) + (x * 2) + 1]
                rchar = 0x20 if char == 0x00 else char
                self.stdscr.addch(y, x, chr(rchar), CGA.get_color(attr))
                self.set_cursor()

        self.stdscr.noutrefresh()
        curses.doupdate()

def log(message, dest="debug"):
    if dest == "debug":
        if not args.debug: return
        path = "debug.txt"

    if dest == "trace":
        if not args.trace: return
        path = "trace.txt"

    with open(path, "a") as handle:
        handle.write(f"{message}\n")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("bios", type=str, help="BIOS image path")
    parser.add_argument("nvram", type=str, help="NVRAM image path")
    parser.add_argument("--d0", type=str, help="Floppy A: image path")
    parser.add_argument("--d1", type=str, help="Floppy B: image path")
    parser.add_argument("--tpa", type=str, help="Program image path (Loaded at 0x0100)")
    parser.add_argument("--trace", action="store_true", help="Enable trace logging")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--iotest", action="store_true", help="Enter IO testing mode")
    return parser.parse_args()

def input_handler(addr):
    for component in io_bus:
        val = component.input(addr)
        if val is not None:
            return val

    return 0x00

def output_handler(addr, data):
    handled = False

    for component in io_bus:
        handled = handled or component.output(addr, data)

    if not handled:
        log(f"Unhandled Output: {hex(addr)}:{hex(data)}")

def signal_handler(sig, frame):
    sys.exit(0)

def get_regs():
    return "\t".join([f"PC:{mmu.r_mode}:{mmu.r_pri_bank}:{hex(cpu.pc)[2:]}", f"SP: {hex(cpu.sp)}", f"A:{hex(cpu.a)}", f"BC:{hex(cpu.bc)}", f"DE:{hex(cpu.de)}", f"HL:{hex(cpu.hl)}", f"IX:{hex(cpu.ix)}", f"IY:{hex(cpu.iy)}"])

def get_stack_usage():
    sections = { "PROG/MODULE": (0x0100, 0x8000), "STARTUP": (0x8000, 0xC000), "CCP": (0xC000, 0xC8F9), "BDOS": (0xC8F9, 0xDA00), "INT": (0xDA00, 0xF000)}
    addrs = list(sorted(mmu.stack_used))
    strs = []
    start = 0
    stop = 0

    for addr in addrs:
        if (addr > stop + 2) or (addrs[-1] == addr):
            secrange = "Unknown"

            for section in sections:
                if start > sections[section][0] and stop <= sections[section][1]:
                    secrange = f"{section}"

            strs.append(f"{hex(start)}:{hex(stop)} ({stop - start}) - ({secrange})")
            start = addr

        stop = addr

    strs.append("")

    for section in sections:
        start = 0x10000
        stop = 0

        for addr in addrs:
            if addr > sections[section][0] and addr <= sections[section][1]:
                if addr < start: start = addr
                if addr > stop: stop = addr

        strs.append(f"{section}  {hex(start)}:{hex(stop)} ({stop - start})")

    return "\n".join(strs)

def main_loop(stdscr):
    cga = CGA(stdscr, mmu.isa)
    io_bus.append(cga)
    stdscr.nodelay(True)
    tick = 0

    # Clock
    while True:
        cpu.ticks_to_stop = 1 if args.trace else 1000
        tick += 1

        if args.trace:
            log(get_regs(), "trace")

        cpu.run()
        ctc.process_tick()

        key = stdscr.getch()
        if key > 0:
            if key == 127: key = 8
            elif key == 330: key = 127
            elif key == 10: key = 13
            elif key == 360: key = 3
            keyboard.put_key(key)

        # Refresh screen periodically
        if (tick % 50  == 0):
            cga.render()

        if (args.debug and (cpu._Z80State__halted[0] > 0)):
            cga.render()
            print("**HALT**")
            input("")

def main():
    global io_bus, cpu, mmu, ctc, keyboard, floppy

    if args.debug:
        if os.path.exists("debug.txt"):
            os.remove("debug.txt")

    if args.trace:
        if os.path.exists("trace.txt"):
            os.remove("trace.txt")

    signal.signal(signal.SIGINT, signal_handler)

    # Create hardware
    cpu = z80.Z80Machine()
    mmu = MMU(cpu)
    ctc = CTC(cpu, mmu)
    keyboard = Keyboard()
    floppy = Floppy()
    io_bus = []
    io_bus.append(mmu)
    io_bus.append(ctc)
    io_bus.append(keyboard)
    io_bus.append(floppy)

    # Configure hardware
    cpu.set_input_callback(input_handler)
    cpu.set_output_callback(output_handler)

    mmu.load_rom(args.bios)
    mmu.load_nvram(args.nvram)

    if args.tpa:
        mmu.load_tpa(args.tpa)

    if args.d0:
        floppy.paths[0] = args.d0
        floppy.load_image(0)

    if args.d1:
        floppy.paths[1] = args.d1
        floppy.load_image(1)

    # Format: "i"/"o",PORT (4 hex),DATA (2 hex)
    if args.iotest:
        while True:
            cmd = input()
            cmd = cmd.replace(" ", "")
            if not cmd: break
            if cmd[0] == "#": continue

            addr = int(cmd[1:5], 16)

            if cmd[0] == "i":
                val = input_handler(addr)
                print(hex(val), chr(val))

            if cmd[0] == "o":
                data = int(cmd[5: 7], 16)
                output_handler(addr, data)

        sys.exit(0)

    curses.wrapper(main_loop)

def end():
    if not args:
        return

    # Update disks
    if args.d0:
        floppy.save_image(0)

    if args.d1:
        floppy.save_image(1)

    if not args.debug:
        return

    # Update memory dump
    with open("memdump.bin", "wb") as handle:
        handle.write(mmu.ram)

    # Print final report
    print(get_regs())
    print(get_stack_usage())

if __name__ == "__main__":
    try:
        args = None
        args = parse_args()
        main()

    finally:
        end()
