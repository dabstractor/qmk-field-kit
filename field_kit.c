#include "field_kit.h"
#include <string.h>
#ifdef CONSOLE_ENABLE
#include "print.h"
#endif

// Message buffer for accumulating incoming data
static char msg_buffer[FIELD_KIT_MSG_BUFFER_SIZE];
static uint16_t msg_index = 0;

bool is_field_kit_message(uint8_t *data, uint8_t length) {
    return length >= 2 && data[0] == FIELD_KIT_ID1 && data[1] == FIELD_KIT_ID2;
}

field_kit_command_t field_kit_parse_command(const char *command) {
    if (strcmp(command, "BOOTLOADER") == 0) {
        return CMD_BOOTLOADER;
    } else if (strcmp(command, "REBOOT_BOOTLOADER") == 0) {
        return CMD_REBOOT_BOOTLOADER;
    } else if (strcmp(command, "FIRMWARE_INFO") == 0) {
        return CMD_FIRMWARE_INFO;
    } else if (strcmp(command, "SIDE_INFO") == 0) {
        return CMD_SIDE_INFO;
    } else if (strcmp(command, "STATUS") == 0) {
        return CMD_STATUS;
    }
    return CMD_UNKNOWN;
}

void field_kit_get_firmware_info(char *buffer, size_t buffer_size) {
    // Get keyboard name and other info from QMK
    snprintf(buffer, buffer_size, 
        "KEYBOARD=%s|BOOTLOADER=%s|MCU=%s|PROTOCOL=%s", 
        PRODUCT,
        "rp2040",  // From keyboard.json
        "rp2040",  // MCU family
        "serial"   // Transport protocol
    );
}

void field_kit_get_side_info(char *buffer, size_t buffer_size) {
    // Determine which side this is based on compile flags or configuration
    #ifdef MASTER_LEFT
        snprintf(buffer, buffer_size, "SIDE=left|SPLIT=true");
    #elif defined(MASTER_RIGHT)  
        snprintf(buffer, buffer_size, "SIDE=right|SPLIT=true");
    #else
        // Default or single keyboard
        snprintf(buffer, buffer_size, "SIDE=right|SPLIT=true");
    #endif
}

void field_kit_trigger_bootloader(void) {
    #ifdef CONSOLE_ENABLE
    uprintf("Field Kit: Triggering bootloader mode\n");
    #endif
    
    // Use QMK's built-in bootloader reset
    bootloader_jump();
}

void field_kit_send_response(field_kit_response_t *response, uint8_t original_length) {
    // Create response packet with field kit identifiers
    uint8_t response_data[32] = {0}; // Use smaller fixed size for responses
    uint8_t response_length = sizeof(response_data);
    
    response_data[0] = response->status;
    
    // Copy message if it fits
    size_t msg_len = strlen(response->message);
    if (msg_len > 0 && msg_len < (sizeof(response_data) - 1)) {
        memcpy(&response_data[1], response->message, msg_len);
    }
    
    raw_hid_send(response_data, response_length);
    
    #ifdef CONSOLE_ENABLE
    uprintf("Field Kit: Sent response status=%d msg=%s\n", response->status, response->message);
    #endif
}

bool field_kit_handle_command(const char *command, field_kit_response_t *response) {
    field_kit_command_t cmd_type = field_kit_parse_command(command);
    
    response->status = RESPONSE_OK;
    memset(response->message, 0, sizeof(response->message));
    
    switch (cmd_type) {
        case CMD_BOOTLOADER:
        case CMD_REBOOT_BOOTLOADER:
            strcpy(response->message, "Entering bootloader mode");
            response->status = RESPONSE_BOOTLOADER_TRIGGERED;
            
            #ifdef CONSOLE_ENABLE
            uprintf("Field Kit: Bootloader command received\n");
            #endif
            
            // Trigger bootloader after short delay
            wait_ms(100);  // Give time for response to be sent
            field_kit_trigger_bootloader();
            return true;
            
        case CMD_FIRMWARE_INFO:
            field_kit_get_firmware_info(response->message, sizeof(response->message));
            response->status = RESPONSE_INFO;
            return true;
            
        case CMD_SIDE_INFO:
            field_kit_get_side_info(response->message, sizeof(response->message));
            response->status = RESPONSE_INFO;
            return true;
            
        case CMD_STATUS:
            strcpy(response->message, "Field Kit active");
            response->status = RESPONSE_OK;
            return true;
            
        case CMD_UNKNOWN:
        default:
            strcpy(response->message, "Unknown command");
            response->status = RESPONSE_ERROR;
            return false;
    }
}

void field_kit_process_message(uint8_t *data, uint8_t length) {
    // Check for field kit identifiers - return early if not our message
    if (!is_field_kit_message(data, length)) {
        return;
    }
    
    // Strip off the identifying bytes
    data += 2;
    length -= 2;
    
    // Process each byte of the incoming packet
    for (uint8_t i = 0; i < length; i++) {
        char c = (char)data[i];
        
        // End of text indicates end of message
        if (c == ETX_TERMINATOR[0]) {
            msg_buffer[msg_index] = '\0';
            msg_index = 0;
            
            #ifdef CONSOLE_ENABLE
            uprintf("Field Kit: Received command: %s\n", msg_buffer);
            #endif
            
            // Process the complete command
            field_kit_response_t response;
            field_kit_handle_command(msg_buffer, &response);
            
            // Send response
            field_kit_send_response(&response, length + 2); // +2 for stripped bytes
            
            break;
        } else {
            // Append character if space available
            if (msg_index < (FIELD_KIT_MSG_BUFFER_SIZE - 1)) {
                msg_buffer[msg_index++] = c;
            } else {
                // Buffer overflow - reset
                msg_index = 0;
                
                #ifdef CONSOLE_ENABLE
                uprintf("Field Kit: Buffer overflow, resetting\n");
                #endif
            }
        }
    }
}