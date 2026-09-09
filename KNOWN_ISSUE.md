# ILI9486 geometry mismatch: diagnosis and repair procedure

Reviewed 2026-09-09 against application revision
`9c6860376b9ee00d6e22358128f5fe006fa90262`.

**Status: the configuration mismatch is confirmed; the proposed correction has
not yet been applied or physically verified.**

## Symptoms and live evidence

The physical panel shows sideways content, an unused area, and a missing USD/JPY
section. Both the generated portrait image and software framebuffer readback
contain the full dashboard. Recent logs show successful five-minute refreshes.

Read-only ioctl inspection found:

| Property | Value |
| --- | --- |
| Kernel series / architecture | Raspberry Pi 6.18 / arm64 |
| Driver | `fb_ili9486` |
| Visible / virtual resolution | 320x480 / 320x480 |
| X/Y offsets | 0 / 0 |
| Rotation | 90 degrees |
| Line length | 640 bytes |
| Framebuffer allocation / bytes read | 307,200 / 307,200 |
| Bits per pixel | 16 |
| Red / green / blue offset,length | 11,5 / 5,6 / 0,5 |
| Bitfield `msb_right` | all zero |
| Transparency length | 0 |
| Framebuffer type / visual / nonstd | 0 / 2 / 1 |

The boot overlay, active device-tree properties, and initialization logs agree on
`width=480,height=320,rotate=90`.

The byte count, offsets, and stride match the renderer. Asymmetric RGB565 packing
is correct. These results make text fitting, missing padding, or missing software
framebuffer contents poor explanations for the failure. Software readback is
**not** a readback of the panel controller's display memory: it cannot prove
successful SPI transmission or physical mapping.

## Why the overlay is inconsistent

The [ILI9486 driver](https://github.com/raspberrypi/linux/blob/rpi-6.18.y/drivers/staging/fbtft/fb_ili9486.c)
defines native width 320 and height 480. Its `set_var()` programs the controller's
address mode for hardware rotation; `set_addr_win()` sends column and page
coordinates directly to the controller.

The [fbtft core](https://github.com/raspberrypi/linux/blob/rpi-6.18.y/drivers/staging/fbtft/fbtft-core.c)
first applies dimension overrides, then swaps width and height for 90/270-degree
rotation. It uses the resulting framebuffer coordinates for updates.

Overlay width and height therefore describe native controller geometry, not the
final rotated desktop. Reversing them to force a 320x480 framebuffer at 90 degrees
makes software geometry inconsistent with rotated controller addressing. This is
the leading explanation for the physical clipping.

The source checked is the Raspberry Pi `rpi-6.18.y` branch matching the running
kernel series, not a disassembly of the installed binary. Panel-specific behavior
still needs physical verification.

## Controlled correction

1. Confirm the active display overlay in `/boot/firmware/config.txt`. Record
   metadata with `python tools/inspect_framebuffer.py --device /dev/fb0`.
   Identify the TFT by driver name if framebuffer numbering differs.
2. Make a rollback copy of the boot configuration. Arrange a suitable reboot
   window with the owner because rebooting interrupts other Pi services.
3. Change only these parameters on the active ILI9486 overlay:

   ```diff
   -width=480,height=320,rotate=90
   +width=320,height=480,rotate=0
   ```

   Alternatively remove both dimension overrides and use `rotate=0` to use driver
   defaults. Preserve pins, SPI speed, color order, touch overlay, and unrelated
   settings for this first test.
4. Reboot once. Avoid repeated live overlay removal/re-addition; earlier tests
   produced overlay-property leak warnings.
5. Confirm a 320x480 framebuffer, 640-byte stride, zero offsets, and rotation 0.
6. Display a 320x480 diagnostic image with a one-pixel border, distinct TL/TR/BL/BR
   corner labels, numbered horizontal/vertical bands, and +X/+Y arrows. Coordinate
   with the refresh job so it does not overwrite the pattern before observation.
   Save the source and a stride-aware readback locally, then compare both with a
   fresh physical photo.
7. If the whole portrait pattern is correct but upside down, test rotation 180
   with the same native dimensions. If clipping remains, investigate panel
   variant, initialization, SPI transport, and register width using the new
   evidence instead of shrinking fonts.
8. Restore the dashboard and normal scheduling. Verify the full FX, weather,
   host, and backup layout physically, then verify a scheduled refresh and
   startup behavior after the controlled reboot.

| Intended orientation | Native dimensions | Rotation | Expected framebuffer |
| --- | --- | --- | --- |
| Portrait | 320x480 | 0 or 180 | 320x480 |
| Landscape | 320x480 | 90 or 270 | 480x320 |

Changing 90 to 270 alone with reversed native dimensions does not repair the
mismatch. An earlier rotation-0 test retained the 480x320 overrides, so it did not
test this correction. Landscape mode requires adapting the fixed portrait layout.

## Application transport improvements

Query both framebuffer ioctls, validate visible dimensions and bitfields, honor
stride/offsets, and check write completion. The live metadata happens to satisfy
the current assumptions, so these improvements are not the demonstrated fix.
Do not automatically rotate the image just because sysfs reports 90 degrees:
this driver applies hardware rotation.

Add a standalone test-pattern mode and stride-aware readback before claiming an
end-to-end fix. A correct PNG, successful write, or passing unit tests cannot
verify the panel. The included inspection utility is read-only; it does not
implement display writes or reconstruct images.

## Information needed for implementation

This document contains the generic technical evidence needed to attempt the
correction. The operator still needs private SSH access, the deployed renderer
and scheduling paths, a suitable reboot window, and someone able to observe the
panel. Network addresses, host inventories, backup locations, credentials, raw
logs, and live dashboard screenshots do not need to be published for this repair.
