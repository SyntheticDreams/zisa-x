#ifdef ZISA_PROG
    #define RST_ADDR $28
#endif

#ifdef ZISA_MODULE
    #define RST_ADDR $30
#endif

void system_cold_boot() __naked {
    __asm
        ld e, $00
        rst RST_ADDR
        ret
    __endasm;
}

void system_warm_boot() __naked {
    __asm
        ld e, $01
        rst RST_ADDR
        ret
    __endasm;
}

void system_run_high(char* start, short int size) __naked {
    __asm
        pop bc
        pop de
        pop hl
        push hl
        push de
        push bc
        ld bc, hl
        ld hl, de
        ld e, $02
        rst RST_ADDR
        ret
    __endasm;
}

char system_module_register() __naked {
    __asm
        ld e, $03
        rst RST_ADDR
        ld h, 0
        ld l, a
        ret
    __endasm;
}

char system_module_count() __naked {
    __asm
        ld e, $04
        rst RST_ADDR
        ld h, 0
        ld l, a
        ret
    __endasm;
}

void system_wait_tick() __naked {
    __asm
        ld e, $05
        rst RST_ADDR
        ret
    __endasm;
}

char system_load_settings() __naked {
    __asm
        ld e, $06
        rst RST_ADDR
        ld h, 0
        ld l, a
        ret
    __endasm;
}

void system_save_settings() __naked {
    __asm
        ld e, $07
        rst RST_ADDR
        ret
    __endasm;
}

char* system_get_settings() __naked {
    __asm
        ld e, $08
        rst RST_ADDR
        ret
    __endasm;
}

char mmu_get_mapped() __naked {
    __asm
        ld e, $10
        rst RST_ADDR
        ld h, 0
        ld l, a
        ret
    __endasm;
}

void mmu_set_mapped(char regions) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $11
        rst RST_ADDR
        ret
    __endasm;
}

char mmu_get_mode() __naked {
    __asm
        ld e, $12
        rst RST_ADDR
        ld h, 0
        ld l, a
        ret
    __endasm;
}

void mmu_set_mode(char mode) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $13
        rst RST_ADDR
        ret
    __endasm;
}

char mmu_get_bank() __naked {
    __asm
        ld e, $14
        rst RST_ADDR
        ld h, 0
        ld l, a
        ret
    __endasm;
}

void mmu_set_bank(char bank) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $15
        rst RST_ADDR
        ret
    __endasm;
}

char mmu_get_iobank() __naked {
    __asm
        ld e, $16
        rst RST_ADDR
        ld h, 0
        ld l, a
        ret
    __endasm;
}

void mmu_set_iobank(char bank) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $17
        rst RST_ADDR
        ret
    __endasm;
}

void video_set_cursor_pos(char x, char y) __naked {
    // Top of stack: Return, param2 (+4), param1 (+2)
    __asm
        pop bc
        pop de
        pop hl
        push hl
        push de
        push bc
        ld b, l
        ld c, e
        ld e, $20
        rst RST_ADDR
        ret
    __endasm;
}

void video_get_cursor_pos(char* x, char* y) __naked {
      __asm
        ld e, $21
        rst RST_ADDR
        ld hl, 2
        add hl, sp
        ld e, (hl)
        inc hl
        ld d, (hl)
        inc hl
        ld (de), b
        ld e, (hl)
        inc hl
        ld d, (hl)
        ld (de), a
        ret
    __endasm;
}

void video_cursor_up() __naked {
    __asm
        ld e, $22
        rst RST_ADDR
        ret
    __endasm;
}

void video_cursor_down() __naked {
    __asm
        ld e, $23
        rst RST_ADDR
        ret
    __endasm;
}

void video_cursor_left() __naked {
    __asm
        ld e, $24
        rst RST_ADDR
        ret
    __endasm;
}

void video_cursor_right() __naked {
    __asm
        ld e, $25
        rst RST_ADDR
        ret
    __endasm;
}

void video_cursor_return() __naked {
    __asm
        ld e, $26
        rst RST_ADDR
        ret
    __endasm;
}

void video_cursor_end() __naked {
    __asm
        ld e, $27
        rst RST_ADDR
        ret
    __endasm;
}

void video_clear_screen() __naked {
    __asm
        ld e, $28
        rst RST_ADDR
        ret
    __endasm;
}

void video_delete_row(char y) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $29
        rst RST_ADDR
        ret
    __endasm;
}

void video_insert_row(char y) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $2A
        rst RST_ADDR
        ret
    __endasm;
}

void video_clear_eol() __naked {
    __asm
        ld e, $2B
        rst RST_ADDR
        ret
    __endasm;
}

void video_clear_eos() __naked {
    __asm
        ld e, $2C
        rst RST_ADDR
        ret
    __endasm;
}

void video_set_char(char c) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $2D
        rst RST_ADDR
        ret
    __endasm;
}

void video_print_char(char c) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $2E
        rst RST_ADDR
        ret
    __endasm;
}

void video_print_str(char* str) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, d
        ld c, e
        ld e, $2F
        rst RST_ADDR
        ret
    __endasm;
}

void video_hardware_cursor() __naked {
    __asm
        ld e, $30
        rst RST_ADDR
        ret
    __endasm;
}

void video_set_attribute(char c) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $31
        rst RST_ADDR
        ret
    __endasm;
}

char keyboard_get_key(char blocking) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $40
        rst RST_ADDR
        ld h, 0
        ld l, a
        ret
    __endasm;
}

char keyboard_avail_key(char blocking) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $41
        rst RST_ADDR
        ld h, 0
        ld l, a
        ret
    __endasm;
}

void floppy_reset() __naked {
    __asm
        ld e, $50
        rst RST_ADDR
        ret
    __endasm;
}

void floppy_set_drive(char drive) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $51
        rst RST_ADDR
        ret
    __endasm;
}

void floppy_drive_recalibrate() __naked {
    __asm
        ld e, $52
        rst RST_ADDR
        ret
    __endasm;
}

void floppy_set_head(char head) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $53
        rst RST_ADDR
        ret
    __endasm;
}

void floppy_set_track(char track) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $54
        rst RST_ADDR
        ret
    __endasm;
}

void floppy_set_sector(char sector) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $55
        rst RST_ADDR
        ret
    __endasm;
}

void floppy_set_log_sector(char sector) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld b, e
        ld e, $56
        rst RST_ADDR
        ret
    __endasm;
}

void floppy_read(char* buffer) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld hl, de
        ld e, $57
        rst RST_ADDR
        ret
    __endasm;
}

void floppy_write(char* buffer) __naked {
    __asm
        pop bc
        pop de
        push de
        push bc
        ld hl, de
        ld e, $58
        rst RST_ADDR
        ret
    __endasm;
}

void floppy_boot() __naked {
    __asm
        ld e, $59
        rst RST_ADDR
        ret
    __endasm;
}
