# Raspberry Pi Screen Metrics

A compact, high-contrast status dashboard rendered directly to a Linux RGB565
framebuffer. It shows:

- USD/JPY
- visual weather and temperature
- green/red Tailscale host indicators
- a combined backup-health indicator

The project is intentionally small and dependency-light. It is currently also
a reproducible case for an orientation/clipping problem on a 3.5-inch Raspberry
Pi display.

## Known review target

The tested device reports:

```text
mode "320x480"
geometry 320 480 320 480 16
rgba 5/11,6/5,5/0,0/0
/sys/class/graphics/fb0/rotate = 90
```

PNG previews and software framebuffer readback are complete, but the physical
panel shows rotated and clipped content. Live diagnostics found reversed native
controller dimensions in the boot overlay: `width=480,height=320,rotate=90`.
The ILI9486 driver defines native 320x480 dimensions and applies rotation itself.
The first correction to test for this portrait layout is
`width=320,height=480,rotate=0`. Physical verification is still pending.

See [KNOWN_ISSUE.md](KNOWN_ISSUE.md) for evidence, kernel references, and the repair
and validation procedure. See [CODE_REVIEW.md](CODE_REVIEW.md) for separate
application findings. Neither document claims a verified hardware fix.

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
```

Edit `config.json`, then make a safe PNG preview:

```bash
python dashboard.py --config config.json --output preview.png
```

Write to the configured framebuffer (typically requires suitable permissions):

```bash
python dashboard.py --config config.json
```

Inspect the actual framebuffer before assuming its geometry:

```bash
fbset -s
cat /sys/class/graphics/fb0/virtual_size
cat /sys/class/graphics/fb0/rotate
python tools/inspect_framebuffer.py --device /dev/fb0
```

The inspection tool opens the device read-only and prints geometry, stride,
offsets, pixel bitfields, and the number of framebuffer bytes read. It does not
print pixel contents or write to the display. It requires Linux and framebuffer
read permission, and uses only the Python standard library.

No API keys are required. FX data comes from Yahoo Finance and weather data
comes from Open-Meteo. Host status requires the local Tailscale CLI.

## Tests

```bash
python -m unittest discover -s tests
```

## License

MIT
