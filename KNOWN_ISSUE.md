# Known issue: physical display rotation and clipping

## What works

- The renderer creates a complete 320x480 PNG.
- Text fitting is checked against a conservative 230-pixel content width.
- The framebuffer accepts exactly `320 * 480 * 2` RGB565 bytes.

## What fails on the panel

- The physical content is displayed sideways.
- A large blank area occupies roughly half of the physical screen.
- The USD/JPY section, which is at the logical top of the image, is not visible.
- Lower sections are visible but displaced and clipped.

## Environment evidence

```text
Framebuffer mode: 320x480, 16 bpp
Virtual size: 320,480
Rotation sysfs value: 90
RGB layout: 5/11,6/5,5/0,0/0
```

## Current implementation assumption

`write_rgb565()` serializes the logical 320x480 Pillow image in row-major order
and writes it directly to `/dev/fb0`. It assumes the kernel/driver handles any
panel rotation implied by sysfs. The physical result suggests that assumption
is wrong, or that the driver exposes a transformed geometry/stride not captured
by the simple mode report.

## Review questions

1. Should the userspace image be rotated before RGB565 conversion?
2. If so, should output geometry become 480x320 while byte count remains equal?
3. Is `/sys/class/graphics/fb0/stride` or `fix.line_length` required here?
4. Does the display driver expect a different framebuffer rotation setting?
5. Should the program inspect `FBIOGET_FSCREENINFO` and `FBIOGET_VSCREENINFO`
   rather than relying on configured dimensions?
6. Is the apparent blank half consistent with the wrong line stride?
