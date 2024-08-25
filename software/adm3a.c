/*
 * Note: Some hacks are in place until official z88dk target is made:
 *
 * z88dk modules/programs should maintain their own stack due to the 
 * large amount of space consumed by standard C libraries. However,
 * the default z80 z88dk target will not restore SP if REGISTER_SP is 
 * set to a specific location. For now, REGISTER_SP set to -1 
 * to maintain the caller's SP, and then functions are wrapped in
 * CALLBACK_START/END to reset SP to a module/program specific stack.
 * 
 * However, normally the compiler will unwind the stack for any local 
 * variables AFTER the function ends, which breaks if resetting SP
 * before the end of the function (using CALLBACK_END).  Therefore,
 * any functions that make use of CALLBACK_START/END must be marked
 * __naked, and CALLBACK_END includes a RET operation since return
 * statements will not be converted for naked functions.
 */

#pragma output CRT_ORG_CODE = 0x0200 
#pragma output CRT_ORG_BSS = 0x6000 
#pragma output REGISTER_SP = -1
#pragma output CRT_ON_EXIT = 0x10002
#pragma output CLIB_EXIT_STACK_SIZE = 0

// Interrupt and standard stack are each 512 bytes
#define CALLBACK_START_INT asm("ld (_int_sp), sp"); asm("ld sp, $8000");
#define CALLBACK_START_STD asm("ld (_std_sp), sp"); asm("ld sp, $7E00");
#define CALLBACK_END_INT asm("ld sp, (_int_sp)"); asm("ret");
#define CALLBACK_END_STD asm("ld sp, (_std_sp)"); asm("ret");

#define CALLBACK_RET(val) return_val = val;  asm("ld a, (_return_val)"); asm("ld c, a");
#define CALLBACK_BLOCK(val) asm("ld a, " #val); 

#include <stdio.h>
#include "zisax.h"

/* Driver memory map
 *
 * 0x0100: Header: RST callback/config jump table (driver supplied)
 * 0x0120: Header: Driver description (driver supplied)
 * 0x0160: Header: Driver filename (loader supplied)
 * 0x0170: Header: Reserved
 * 0x0200: Executable: Main and callbacks
 */

struct Registers {
    char b;
    char c;
    char d;
    char e;
};

struct Registers registers;
char return_val;
char * int_sp;
char * std_sp;
int load_state;
char load_y;
char config_kaypro;

void copy_registers() __naked {
    __asm
        ld a, b
        ld (_registers+0), a
        ld a, c
        ld (_registers+1), a
        ld a, d
        ld (_registers+2), a
        ld a, e
        ld (_registers+3), a
        ret
    __endasm;
}

void halt() __naked {
    __asm
        halt
    __endasm;
}

int fputc_cons_native(char c) {
    video_print_char(c);
    return 0;
}

void rst1() __naked {
    CALLBACK_START_INT
    CALLBACK_BLOCK(0)
    CALLBACK_END_INT
}

void rst2() __naked {
    CALLBACK_START_INT
    CALLBACK_BLOCK(0)
    CALLBACK_END_INT
}

void rst3() __naked {
    CALLBACK_START_INT
    CALLBACK_BLOCK(0)
    CALLBACK_END_INT
}

void rst4() __naked {
    CALLBACK_START_INT
    CALLBACK_BLOCK(0)
    CALLBACK_END_INT
}

void rst5() __naked {
    CALLBACK_START_STD

    // Only listen for video_print_char (0x2E)
    copy_registers();
    if (registers.e != 0x2E) {
        CALLBACK_BLOCK(0)
        CALLBACK_END_STD
    }

    // Process load mode first
    if (load_state > 0) {
        switch (load_state) {
            case 1:
                load_state = 0;

                // Cursor position continues
                if (registers.b == '=') {
                    load_state = 2;
                }

                // Insert line
                if (config_kaypro && (registers.b == 'E')) {
                    char x, y;
                    video_get_cursor_pos(&x, &y);
                    video_insert_row(y);
                }

                // Delete line
                if (config_kaypro && (registers.b == 'R')) {
                    char x, y;
                    video_get_cursor_pos(&x, &y);
                    video_delete_row(y);
                }

                break;
            case 2:
                load_y = (registers.b - 32);
                load_state = 3;
                break;
            case 3:
                video_set_cursor_pos(registers.b - 32, load_y);
                load_state = 0;
                break;
        }

        CALLBACK_BLOCK(1)
        CALLBACK_END_STD
    }

    switch (registers.b) {
        // BEL - Bell
        case 0x07:
            CALLBACK_BLOCK(1);
            CALLBACK_END_STD

        // BS - Backspace
        case 0x08:
            CALLBACK_BLOCK(0);
            CALLBACK_END_STD

        // ETB - Clear EOS
        case 0x17:
            if (config_kaypro) {
                video_clear_eos();
                CALLBACK_BLOCK(1)
                CALLBACK_END_STD
            }

            CALLBACK_BLOCK(0);
            CALLBACK_END_STD

        // CAN - Clear EOL
        case 0x18:
            if (config_kaypro) {
                video_clear_eol();
                CALLBACK_BLOCK(1)
                CALLBACK_END_STD
            }

            CALLBACK_BLOCK(0)
            CALLBACK_END_STD

        // LF - Linefeed
        case 0x0A:
            CALLBACK_BLOCK(0)
            CALLBACK_END_STD

        // VT - Upline
        case 0x0B:
            video_cursor_up();
            CALLBACK_BLOCK(1)
            CALLBACK_END_STD

        // FF - Forward Space
        case 0x0C:
            video_cursor_right();
            CALLBACK_BLOCK(1)
            CALLBACK_END_STD

        // CR - Carriage Return
        case 0x0D:
            CALLBACK_BLOCK(0);
            CALLBACK_END_STD

        // SUB - Clear Screen
        case 0x1A:
            video_clear_screen();
            video_set_cursor_pos(0, 0);
            CALLBACK_BLOCK(1)
            CALLBACK_END_STD

        // ESC - Start Cursor Load
        case 0x1B:
            load_state = 1;
            CALLBACK_BLOCK(1);
            CALLBACK_END_STD

        // RS - Home Cursor
        case 0x1E:
            video_set_cursor_pos(0, 0);
            CALLBACK_BLOCK(1)
            CALLBACK_END_STD
    }

    CALLBACK_BLOCK(0)
    CALLBACK_END_STD
}

char get_yn() {
    char key;

    while (1) {
        key = keyboard_get_key(1);
        if ((key == 'n') || (key == 'N')) return 0;
        if ((key == 'y') || (key == 'Y')) return 1;
    }
}

void configure() __naked {
    CALLBACK_START_STD

    char key;

    printf("ADM-3A settings:\r\n\r\n");
    printf("Kaypro mode: %d\r\n\r\n", config_kaypro);
    printf("Update (Y/N): ");
    if (get_yn() == 0) {
        printf("N\r\n");
        CALLBACK_END_STD
    }

    printf("Y\r\n");
    printf("Kaypro mode (Y/N): ");
    config_kaypro = get_yn();
    printf(config_kaypro ? "Y\r\n" : "N\r\n");
    printf("\r\nSettings updated!\r\n");

    CALLBACK_END_STD
}

void main() {
    char * driver_header = 0x0100;

    // Initialize driver header
    for (int x = 0 ; x < 256 ; x++) {
        driver_header[x] = 0x00;
    }

    // Set callbacks and configure
    for (int x = 0 ; x < 6 ; x++) {
        driver_header[x * 3] = 0xC3;
    }

    driver_header[1] = rst1 & 0x00FF;
    driver_header[2] = (rst1 & 0xFF00) >> 8;
    driver_header[4] = rst2 & 0x00FF;
    driver_header[5] = (rst2 & 0xFF00) >> 8;
    driver_header[7] = rst3 & 0x00FF;
    driver_header[8] = (rst3 & 0xFF00) >> 8;
    driver_header[10] = rst4 & 0x00FF;
    driver_header[11] = (rst4 & 0xFF00) >> 8;
    driver_header[13] = rst5 & 0x00FF;
    driver_header[14] = (rst5 & 0xFF00) >> 8;
    driver_header[16] = configure & 0x00FF;
    driver_header[17] = (configure & 0xFF00) >> 8;

    // Set driver name
    sprintf(((char *) driver_header) + 32, "ADM-3A Terminal Driver");

    // Initialize driver vals
    load_state = 0;
    config_kaypro = 1;

    // Done!
    printf("ADM-3A driver initialized");
    CALLBACK_BLOCK(0)
}
