struct BiosSettings {
    char video_attr;
    char boot_pri;
    char boot_sec;
};

void system_cold_boot();
void system_warm_boot();
void system_run_high(char* start, short int size);
char system_module_register();
char system_module_count();
void system_wait_tick();
char system_load_settings();
void system_save_settings();
char* system_get_settings();

char mmu_get_mapped();
void mmu_set_mapped(char regions);
char mmu_get_mode();
void mmu_set_mode(char mode);
char mmu_get_bank();
void mmu_set_bank(char bank);
char mmu_get_iobank();
void mmu_set_iobank(char bank);

void video_set_cursor_pos(char x, char y);
void video_get_cursor_pos(char* x, char* y);
void video_cursor_up();
void video_cursor_down();
void video_cursor_left();
void video_cursor_right();
void video_cursor_return();
void video_cursor_end();
void video_clear_screen();
void video_delete_row(char y);
void video_insert_row(char y);
void video_clear_eol();
void video_clear_eos();
void video_set_char(char c);
void video_print_char(char c);
void video_print_str(char * str);
void video_hardware_cursor();
void video_set_attribute(char c);

char keyboard_get_key(char blocking);
char keyboard_avail_key(char blocking);

void floppy_reset();
void floppy_set_drive(char drive);
void floppy_drive_recalibrate();
void floppy_set_head(char head);
void floppy_set_track(char track);
void floppy_set_sector(char sector);
void floppy_set_log_sector(char sector);
void floppy_read(char* buffer);
void floppy_write(char* buffer);
void floppy_boot();
