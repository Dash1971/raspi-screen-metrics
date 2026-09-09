#!/usr/bin/env python3
"""Inspect Linux fbdev metadata and read length without exposing pixel contents."""

import argparse
import ctypes as c
import fcntl
import json


class Bitfield(c.Structure):
    _fields_ = [(name, c.c_uint32) for name in ("offset", "length", "msb_right")]


class VariableInfo(c.Structure):
    # Native Linux UAPI layout from include/uapi/linux/fb.h.
    _fields_ = (
        [(name, c.c_uint32) for name in (
            "xres", "yres", "xres_virtual", "yres_virtual", "xoffset", "yoffset",
            "bits_per_pixel", "grayscale")]
        + [(name, Bitfield) for name in ("red", "green", "blue", "transp")]
        + [(name, c.c_uint32) for name in (
            "nonstd", "activate", "height", "width", "accel_flags", "pixclock",
            "left_margin", "right_margin", "upper_margin", "lower_margin",
            "hsync_len", "vsync_len", "sync", "vmode", "rotate", "colorspace")]
        + [("reserved", c.c_uint32 * 4)]
    )


class FixedInfo(c.Structure):
    # unsigned long and native alignment intentionally follow the executing ABI.
    _fields_ = [
        ("id", c.c_char * 16), ("smem_start", c.c_ulong),
        ("smem_len", c.c_uint32), ("type", c.c_uint32),
        ("type_aux", c.c_uint32), ("visual", c.c_uint32),
        ("xpanstep", c.c_uint16), ("ypanstep", c.c_uint16),
        ("ywrapstep", c.c_uint16), ("line_length", c.c_uint32),
        ("mmio_start", c.c_ulong), ("mmio_len", c.c_uint32),
        ("accel", c.c_uint32), ("capabilities", c.c_uint16),
        ("reserved", c.c_uint16 * 2),
    ]


def read_ioctl(device, request, structure):
    data = bytearray(c.sizeof(structure))
    fcntl.ioctl(device, request, data, True)
    return structure.from_buffer_copy(data)


def inspect(device_path):
    with open(device_path, "rb", buffering=0) as device:
        var = read_ioctl(device, 0x4600, VariableInfo)  # FBIOGET_VSCREENINFO
        fix = read_ioctl(device, 0x4602, FixedInfo)  # FBIOGET_FSCREENINFO
        result = {
            "driver": fix.id.decode("ascii", errors="replace"),
            "var": {name: getattr(var, name) for name in (
                "xres", "yres", "xres_virtual", "yres_virtual", "xoffset",
                "yoffset", "bits_per_pixel", "rotate", "nonstd")},
            "fix": {name: getattr(fix, name) for name in (
                "smem_len", "line_length", "type", "visual")},
            "bitfields": {
                name: {key: getattr(getattr(var, name), key)
                       for key in ("offset", "length", "msb_right")}
                for name in ("red", "green", "blue", "transp")
            },
            "abi_sizes": [c.sizeof(VariableInfo), c.sizeof(FixedInfo)],
        }
        # Bound the diagnostic to small TFTs; never allocate the whole frame.
        if not 0 < fix.smem_len <= 8 * 1024 * 1024:
            raise ValueError("expected a framebuffer allocation between 1 byte and 8 MiB")
        count = 0
        while count < fix.smem_len:
            data = device.read(min(65536, fix.smem_len - count))
            if not data:
                break
            count += len(data)
        result["bytes_read"] = count
        result["complete_read"] = count == fix.smem_len
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default="/dev/fb0")
    args = parser.parse_args()
    result = inspect(args.device)
    print(json.dumps(result, indent=2))
    return 0 if result["complete_read"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
