"""Constants for the Idasen Desk integration."""

DOMAIN = "idasen"
UPDATE_INTERVAL_SECONDS = 60
DEVICE_TIMEOUT = 30
UUID_HEIGHT = "99fa0021-338a-1024-8a49-009c0215f78a" # Read height and speed
UUID_COMMAND = "99fa0002-338a-1024-8a49-009c0215f78a" # Write commands
UUID_DPG = "99fa0011-338a-1024-8a49-009c0215f78a" # Write ?
UUID_REFERENCE_INPUT = "99fa0031-338a-1024-8a49-009c0215f78a" # Write ?

COMMAND_REFERENCE_INPUT_STOP: bytearray = bytearray([0x01, 0x80])
COMMAND_UP: bytearray = bytearray([0x47, 0x00])
COMMAND_DOWN: bytearray = bytearray([0x46, 0x00])
COMMAND_STOP: bytearray = bytearray([0xFF, 0x00])

BASE_HEIGHT_CM = 62
MOVEMENT_RANGE_CM = 65