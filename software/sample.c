/*
 * ZISA-X sample C program for z88dk development environment
 */

#pragma output CRT_ORG_CODE = 0x0100 
#pragma output REGISTER_SP = -1
#pragma output CRT_ON_EXIT = 0x10002
#pragma output CLIB_EXIT_STACK_SIZE = 0
#pragma output CLIB_DISABLE_FGETS_CURSOR = 1

#include <stdio.h>
#include <string.h>
#include "zisax.h"

struct Registers {
    char b;
    char c;
    char d;
    char e;
};

struct Registers registers;

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

int fputc_cons_native(char c) {
    video_print_char(c);
    return 0;
}

int fgetc_cons() {
    return keyboard_get_key(1);
}

void main() {
    char buffer[64];
    int len;

    // Example system calls from zisax.h
    video_set_attribute(0x16);
    video_clear_screen();
    video_set_cursor_pos(0, 1);

    // Example usage of standard libs
    printf("This is a sample program making use of system calls and standard C libs.\r\n\r\n");
    printf("Enter your name: ");
    fgets(buffer, sizeof(buffer), stdin);
    buffer[strcspn(buffer, "\r")] = 0;

    video_set_attribute(0x1B);
    printf("\r\n\r\nHello, %s, enjoy ZISA-X!\r\n", buffer);
    video_set_attribute(0x1F);
}
