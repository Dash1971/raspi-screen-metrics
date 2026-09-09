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

PNG previews are correct at 320x480, but direct row-major RGB565 writes appear
rotated on the physical panel. Roughly half the panel is blank and the top
USD/JPY section is clipped. The current framebuffer writer does not transform
pixels for the kernel-reported rotation. Review of the relationship among
logical geometry, physical geometry, rotation, stride, and byte order is the
main reason this repository was published.

See [KNOWN_ISSUE.md](KNOWN_ISSUE.md) for exact observations and review questions.

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
```

No API keys are required. FX data comes from Yahoo Finance and weather data
comes from Open-Meteo. Host status requires the local Tailscale CLI.

## Tests

```bash
python -m unittest discover -s tests
```

## License

MIT
