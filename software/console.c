#pragma output CRT_ORG_CODE = 0x0100
#pragma output CRT_ORG_BSS = 0x8000 // Console is in ROM (bank 1), write to mapped RAM area
#pragma output REGISTER_SP = -1
#pragma output CRT_ON_EXIT = 0x10002
#pragma output CLIB_EXIT_STACK_SIZE = 0
#pragma output CLIB_DISABLE_FGETS_CURSOR = 1

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "zisax.h"

#define BUFFER_SIZE 32

const char * COLORS[] = { "Black", "Blue", "Green", "Cyan", "Red", "Magenta", "Brown", "Lt Gray", "Gray", "Lt Blue", "Lt Green", "Lt Cyan", "Lt Red", "Lt Magenta", "Yellow", "White" };

struct Registers {
    char b;
    char c;
    char d;
    char e;
};

struct Registers registers;
char return_val;
struct BiosSettings * settings;

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

int fgetc_cons() {
    return keyboard_get_key(1);
}

void refresh_screen() {
    char * attrs = 0xF001;

    for (int x = 0 ; x < 2000 ; x++) {
        *attrs = settings->video_attr;
        attrs += 2;
    }
}
void cmd_help() {
    printf(
        "Supported Commands:\r\n"
        "   BOOT [DRIVE:]       Autoboot or boot using specified drive\r\n"
        "   LIST                List available settings\r\n"
        "   SHOW [SETTING]      Show value of setting(s)\r\n"
        "   SET <SETTING>       Set value of setting\r\n"
        "   SAVE                Save settings to NVRAM\r\n"
        "   REVERT              Revert to settings in NVRAM\r\n"
    );
}

void cmd_list() {
    printf(
        "Available Settings:\r\n"
        "   COLORS              Default screen colors\r\n"
        "   BOOTPRI             Primary boot drive\r\n"
        "   BOOTSEC             Secondary boot drive\r\n"
    );
}

void cmd_show_colors() {
    printf("Colors (F/B):     [%s, %s]\r\n", COLORS[settings->video_attr & 0x0F], COLORS[(settings->video_attr & 0x70) >> 4]);
}

void cmd_show_bootpri() {
    char none[] = "None";
    char drive[] = "A";

    drive[0] += settings->boot_pri;
    printf("Primary Boot:     %s\r\n", (settings->boot_pri == 0xFF) ? none : drive);
}

void cmd_show_bootsec() {
    char none[] = "None";
    char drive[] = "A";

    drive[0] += settings->boot_sec;
    printf("Secondary Boot:   %s\r\n", (settings->boot_sec == 0xFF) ? none : drive);
}

void cmd_set_colors() {
    char buffer[8];
    char fore, back;

    printf("Colors: \r\n\r\n");
    // Foreground
    for (int x = 0 ; x < 16 ; x++) {
        printf("%d. %s\r\n", x, COLORS[x]);
    }

    printf("\r\nFore: ");
    fgets(buffer, sizeof(buffer), stdin);
    printf("\r\n\r\n");
    fore = atoi(buffer);

    // Background
    for (int x = 0 ; x < 8 ; x++) {
        printf("%d. %s\r\n", x, COLORS[x]);
    }

    printf("\r\nBack: ");
    fgets(buffer, sizeof(buffer), stdin);
    printf("\r\n\r\n");
    back = atoi(buffer);

    // Update setting
    settings->video_attr = ((back & 0x07) << 4) | (fore & 0x0F);
    video_set_attribute(settings->video_attr);
    refresh_screen();
}

void cmd_set_bootpri() {
    char buffer[8];

    printf("Primary Boot Drive (Enter for none): ");
    fgets(buffer, sizeof(buffer), stdin);
    printf("\r\n");

    // Update setting
    settings->boot_pri = (buffer[0] < 32) ? 0xFF : buffer[0] - 'A';
}

void cmd_set_bootsec() {
    char buffer[8];

    printf("Secondary Boot Drive (Enter for none): ");
    fgets(buffer, sizeof(buffer), stdin);
    printf("\r\n");

    // Update setting
    settings->boot_sec = (buffer[0] < 32) ? 0xFF : buffer[0] - 'A';
}

void cmd_save() {
    system_save_settings();
    printf("Settings saved in NVRAM\r\n");
}

void cmd_load() {
    if (system_load_settings()) {
        printf("NVRAM corrupted, loading failed\r\n");
    }
    else {
        printf("Settings loaded from NVRAM\r\n");
        settings = (struct BiosSettings *) system_get_settings();
        video_set_attribute(settings->video_attr);
        refresh_screen();
    }
}

void console() {
    char buffer[BUFFER_SIZE];
    char * arg;

    printf("ZISA-X Console v1.0\r\n\r\n");
    settings = (struct BiosSettings *) system_get_settings();
    
    while (1) {
        // Read command, strip CR/LF, and convert to lowercase
        printf("> ");
        fgets(buffer, sizeof(buffer), stdin);
        buffer[strcspn(buffer, "\r\n")] = 0;
        printf("\r\n");

        for (int x = 0 ; x < BUFFER_SIZE ; x++) {
            buffer[x] = toupper(buffer[x]);
        }

        arg = strtok(buffer, " ");

        // HELP
        if (strncmp(arg, "HELP", BUFFER_SIZE) == 0) {
            cmd_help();
        }

        // BOOT
        else if (strncmp(arg, "BOOT", BUFFER_SIZE) == 0) {
            arg = strtok(NULL, " ");

            // Autoboot if no arguments given
            if (arg == NULL) { return; }

            // Boot from selected drive
            settings->boot_pri = arg[0] - 'A';
            settings->boot_sec = arg[0] - 'A';
            return;
        }

        // LIST
        else if (strncmp(arg, "LIST", BUFFER_SIZE) == 0) {
            arg = strtok(NULL, " ");
            cmd_list();
        }

        // SHOW
        else if (strncmp(arg, "SHOW", BUFFER_SIZE) == 0) {
            arg = strtok(NULL, " ");

            if ((arg == NULL) || (strncmp(arg, "COLORS", BUFFER_SIZE) == 0)) {
                cmd_show_colors();
            }

            if ((arg == NULL) || (strncmp(arg, "BOOTPRI", BUFFER_SIZE) == 0)) {
                cmd_show_bootpri();
            }

            if ((arg == NULL) || (strncmp(arg, "BOOTSEC", BUFFER_SIZE) == 0)) {
                cmd_show_bootsec();
            }
        }

        // SET
        else if (strncmp(arg, "SET", BUFFER_SIZE) == 0) {
            arg = strtok(NULL, " ");

            if (arg == NULL) {
                printf("ERROR: Setting name required\r\n");
                continue;
            }
               
            if (strncmp(arg, "COLORS", BUFFER_SIZE) == 0) {
                cmd_set_colors();
            }

            if (strncmp(arg, "BOOTPRI", BUFFER_SIZE) == 0) {
                cmd_set_bootpri();
            }

            if (strncmp(arg, "BOOTSEC", BUFFER_SIZE) == 0) {
                cmd_set_bootsec();
            }
        }

        // SAVE
        else if (strncmp(arg, "SAVE", BUFFER_SIZE) == 0) {
            arg = strtok(NULL, " ");
            cmd_save();
        }

        // REVERT
        else if (strncmp(arg, "REVERT", BUFFER_SIZE) == 0) {
            arg = strtok(NULL, " ");
            cmd_load();
        }

        // ERROR
        else {
            printf("ERROR: Unknown command\r\n");
        }
    }
}


void main() {
    // Immediate mode
    if (*((char *) 0x0004) == 0xFF) {
        console();
    }

    // Escape mode
    else {
        printf("Press ESC to enter console...\r\n\r\n");

        for (int x = 0 ; x < 20 ; x++) {
            char c = keyboard_get_key(0);
            if (c == 27) {
                console();
                break;
            }

            system_wait_tick();
        }
    }
}
