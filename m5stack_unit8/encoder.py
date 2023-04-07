# SPDX-FileCopyrightText: Copyright 2023 Neradoc, https://neradoc.me
# SPDX-License-Identifier: MIT
"""
Dev notes: the board expects a stop between write and read rather than a real restart,
so we cannot use "write_then_readinto", but a write followed by a read.
"""

from micropython import const
from adafruit_bus_device.i2c_device import I2CDevice
import struct
from adafruit_pixelbuf import PixelBuf

_DEFAULT_ADDRESS = const(0x41)
_ENCODER_REGISTER = const(0x00)
_INCREMENT_REGISTER = const(0x20)
_ENCODER_RESET_REGISTER = const(0x40)
_BUTTONS_REGISTER = const(0x50)
_SWITCH_REGISTER = const(0x60)
_PIXELS_REGISTER = const(0x70)

class _U8_Pixels(PixelBuf):
    def __init__(self, unit8, brightness, auto_write):
        self.unit8 = unit8
        super().__init__(8, byteorder="RGB", brightness=brightness, auto_write=auto_write)

    def _transmit(self, buffer: bytearray) -> None:
        """Update the pixels"""
        self.unit8._set_leds(buffer)

class Unit8Encoder:
    def __init__(self, i2c, address=_DEFAULT_ADDRESS, brightness=1.0, auto_write=True):
        self.device = I2CDevice(i2c, address)
        self.register = bytearray(1)
        self.buffer = bytearray(4 * 8)
        self.pixels = _U8_Pixels(self, brightness, auto_write)

    def read_encoder(self, num):
        """Return the value of one encoder"""
        if num not in range(0,8):
            raise ValueError(f"num must be one of 0-7")
        self.register[0] = _ENCODER_REGISTER + 4 * num
        with self.device as bus:
            bus.write(self.register)
            bus.readinto(self.buffer, end=4)
        return struct.unpack("<l", self.buffer[:4])[0]

    def read_encoders(self):
        """Return a list with the values of the 8 encoders"""
        with self.device as bus:
            for enc_num in range(8):
                self.register[0] = _ENCODER_REGISTER + enc_num * 4
                bus.write(self.register)
                bus.readinto(self.buffer, start=enc_num*4, end=(enc_num+1)*4)
        return struct.unpack("<8l", self.buffer)

    def read_increment(self, num):
        """
        Return the value of one encoder increment.
        This value is reset to 0 after read.
        """
        if num not in range(0,8):
            raise ValueError(f"num must be one of 0-7")
        self.register[0] = _INCREMENT_REGISTER + 4 * num
        with self.device as bus:
            bus.write(self.register)
            bus.readinto(self.buffer, end=4)
        return struct.unpack("<l", self.buffer[:4])[0]

    def read_increments(self):
        """
        Return a list with the values of the 8 encoders.
        These value is reset to 0 after read.
        """
        with self.device as bus:
            for enc_num in range(8):
                self.register[0] = _INCREMENT_REGISTER + enc_num * 4
                bus.write(self.register)
                bus.readinto(self.buffer, start=enc_num*4, end=(enc_num+1)*4)
        return struct.unpack("<8l", self.buffer)

    def reset(self):
        """Reset the encoder position values"""
        self.buffer[1] = 1
        with self.device as bus:
            for i in range(8):
                self.buffer[0] = 0x40 + i
                bus.write(self.buffer, end=2)

    def read_buttons(self):
        """Return a tuple with all the button values"""
        with self.device as bus:
            for bnum in range(8):
                self.register[0] = 0x50 + bnum
                bus.write(self.register)
                bus.readinto(self.buffer, start=bnum, end=bnum+1)
        return tuple(not b for b in struct.unpack("<8B", self.buffer[:8]))

    def set_led(self, position, color):
        """Set the color to one RGB LED"""
        if position not in range(0,8):
            raise ValueError(f"pixel position must be one of 0-7")
        register = _PIXELS_REGISTER + 3 * position
        if isinstance(color, (tuple, list)) and len(color) == 3:
            color = bytes(color)
        elif isinstance(color, int):
            color = color.to_bytes(3, "big")
        else:
            raise ValueError("color must be an int or (r,g,b) tuple")
        self.buffer[0] = _PIXELS_REGISTER + 3 * position
        self.buffer[1:4] = color
        with self.device as bus:
            bus.write(self.buffer, end=4)

    def get_led(self, position):
        """Get the current color of an RGB LED"""
        if position not in range(0,8):
            raise ValueError(f"pixel position must be one of 0-7")
        self.register[0] = _PIXELS_REGISTER + 3 * position
        with self.device as bus:
            bus.write(self.register)
            bus.read(self.buffer, end=3)
        return tuple(self.buffer[:3])

    def _set_leds(self, buffer):
        """Set all LEDs with a binary buffer"""
        self.register[0] = _PIXELS_REGISTER
        with self.device as bus:
            bus.write(self.register + buffer)

    def read_switch(self):
        """Read the value of the switch"""
        self.register[0] = _SWITCH_REGISTER
        with self.device as bus:
            bus.write(self.register)
            bus.readinto(self.buffer, end=1)
        return bool(self.buffer[0])

    def fill(self, color):
        self.pixels.fill(color)
