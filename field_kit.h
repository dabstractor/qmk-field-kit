#pragma once

#include QMK_KEYBOARD_H
#include "raw_hid.h"

// Field Kit specific protocol identifiers (different from qmk-notifier)
#define FIELD_KIT_ID1 0x82
#define FIELD_KIT_ID2 0x9E
#define ETX_TERMINATOR "\x03"

// Command response codes
#define RESPONSE_OK 0x01
#define RESPONSE_ERROR 0x00
#define RESPONSE_BOOTLOADER_TRIGGERED 0x02
#define RESPONSE_INFO 0x03

// Maximum message buffer size
#define FIELD_KIT_MSG_BUFFER_SIZE 256

// Command type definitions
typedef enum {
    CMD_BOOTLOADER,
    CMD_REBOOT_BOOTLOADER, 
    CMD_FIRMWARE_INFO,
    CMD_SIDE_INFO,
    CMD_STATUS,
    CMD_UNKNOWN
} field_kit_command_t;

// Response structure
typedef struct {
    uint8_t status;
    char message[FIELD_KIT_MSG_BUFFER_SIZE - 1];
} field_kit_response_t;

// Function declarations
void field_kit_process_message(uint8_t *data, uint8_t length);
bool field_kit_handle_command(const char *command, field_kit_response_t *response);
field_kit_command_t field_kit_parse_command(const char *command);
void field_kit_send_response(field_kit_response_t *response, uint8_t original_length);
void field_kit_trigger_bootloader(void);
void field_kit_get_firmware_info(char *buffer, size_t buffer_size);
void field_kit_get_side_info(char *buffer, size_t buffer_size);

// Helper function to check if message is for field kit
bool is_field_kit_message(uint8_t *data, uint8_t length);