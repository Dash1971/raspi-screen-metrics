#!/usr/bin/env python3
"""Render a compact status dashboard to PNG or a Linux RGB565 framebuffer."""

import argparse
import datetime as dt
import json
import math
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


FX_URL = "https://query1.finance.yahoo.com/v8/finance/chart/JPY=X?interval=1m&range=1d"
BG, WHITE, CYAN = "#000000", "#ffffff", "#00ffff"
GREEN, RED, AMBER = "#00ff66", "#ff3030", "#ffd400"
RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}
SNOW_CODES = {71, 73, 75, 77, 85, 86}


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def typeface(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"
        if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "RaspiScreenMetrics/1.0"})
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.load(response)


def cached(cache_path, key, fetcher):
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    try:
        value = fetcher()
        cache[key] = value
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache), encoding="utf-8")
        return value, False
    except Exception:
        if key not in cache:
            raise
        return cache[key], True


def get_fx():
    result = fetch_json(FX_URL)["chart"]["result"][0]
    return {"value": float(result["meta"]["regularMarketPrice"]), "fetched": int(time.time())}


def get_weather(config):
    params = urllib.parse.urlencode({
        "latitude": config["latitude"],
        "longitude": config["longitude"],
        "current": "temperature_2m,weather_code",
        "daily": "precipitation_probability_max",
        "timezone": config.get("timezone", "auto"),
        "forecast_days": 1,
    })
    raw = fetch_json("https://api.open-meteo.com/v1/forecast?" + params)
    return {
        "temp": round(float(raw["current"]["temperature_2m"])),
        "code": int(raw["current"]["weather_code"]),
        "rain": int(raw["daily"]["precipitation_probability_max"][0]),
        "fetched": int(time.time()),
    }


def weather_kind(weather):
    if weather["code"] in SNOW_CODES:
        return "snow", "SNOW"
    if weather["code"] in RAIN_CODES or weather["rain"] >= 50:
        return "rain", "RAIN LIKELY"
    if weather["temp"] > 30:
        return "hot", "HOT"
    if weather["temp"] < 14:
        return "cold", "COLD"
    return "clear", "CLEAR"


def host_states(config):
    try:
        raw = json.loads(subprocess.check_output(
            ["tailscale", "status", "--json"], text=True, timeout=5))
        peers = {p.get("HostName"): bool(p.get("Online"))
                 for p in raw.get("Peer", {}).values()}
        return [(item["label"], peers.get(item["tailscale_hostname"], False))
                for item in config.get("hosts", [])]
    except Exception:
        return [(item["label"], None) for item in config.get("hosts", [])]


def backups_ok(config):
    now = time.time()
    markers = config.get("backup_markers", [])
    if not markers:
        return False
    return all(Path(item["path"]).is_file() and
               now - Path(item["path"]).stat().st_mtime <= item.get("max_age_hours", 36) * 3600
               for item in markers)


def draw_text(draw, xy, value, size, color=WHITE, bold=False, anchor=None):
    draw.text(xy, str(value), font=typeface(size, bold), fill=color, anchor=anchor)


def centered_fit(draw, value, y, canvas_width, max_width, start_size):
    for size in range(start_size, 19, -2):
        face = typeface(size, True)
        box = draw.textbbox((0, 0), value, font=face)
        if box[2] - box[0] <= max_width:
            draw.text((canvas_width / 2, y), value, font=face, fill=WHITE, anchor="ma")
            return size
    raise ValueError("text cannot fit configured width")


def draw_icon(draw, x, y, size, kind):
    cx, cy = x + size // 2, y + size // 2
    if kind in {"hot", "clear"}:
        color = "#ff7a35" if kind == "hot" else AMBER
        for angle in range(0, 360, 45):
            a = math.radians(angle)
            draw.line((cx + math.cos(a) * size*.33, cy + math.sin(a) * size*.33,
                       cx + math.cos(a) * size*.46, cy + math.sin(a) * size*.46),
                      fill=color, width=5)
        r = size * .24
        draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=color)
    elif kind == "rain":
        draw.pieslice((x+5, y+size*.2, x+size-5, y+size*.78), 180, 360, fill=CYAN)
        draw.line((cx, y+size*.45, cx, y+size*.84), fill=WHITE, width=4)
        draw.arc((cx-2, y+size*.68, cx+size*.28, y+size*.94), 70, 190, fill=WHITE, width=4)
    elif kind == "snow":
        draw.ellipse((cx-size*.22, y+size*.48, cx+size*.22, y+size*.92), fill=WHITE)
        draw.ellipse((cx-size*.16, y+size*.20, cx+size*.16, y+size*.52), fill=WHITE)
    else:
        draw.polygon(((x+10, y+26), (x+size-24, y+12), (x+size-8, y+30),
                      (x+24, y+45)), fill="#9ae8f1")
        draw.polygon(((x+24, y+45), (x+size-8, y+30), (x+size-9, y+size-14),
                      (x+24, y+size-4)), fill="#55bfd1")


def render(config, fx, weather, hosts, backups_good, stale=False):
    width, height = config.get("width", 320), config.get("height", 480)
    if (width, height) != (320, 480):
        raise ValueError("current layout is designed for 320x480")
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    draw_text(draw, (width/2, 24), "USD / JPY", 20, CYAN, True, "ma")
    centered_fit(draw, f"{fx['value']:.2f}", 60, width, 230, 68)
    draw.line((30, 154, 290, 154), fill=WHITE, width=2)

    kind, label = weather_kind(weather)
    draw_icon(draw, 16, 170, 108, kind)
    draw_text(draw, (218, 198), f"{weather['temp']}°", 66, WHITE, True, "mm")
    draw_text(draw, (218, 262), label, 18, CYAN, True, "mm")
    draw.line((12, 300, 308, 300), fill=WHITE, width=2)

    count = max(1, len(hosts))
    spacing = 280 / count
    for index, (label, online) in enumerate(hosts):
        x = 20 + spacing * (index + .5)
        color = GREEN if online is True else RED if online is False else AMBER
        draw.ellipse((x-12, 308, x+12, 332), fill=color)
        draw_text(draw, (x, 354), label[:6].upper(), 12, WHITE, True, "mm")
    draw.line((12, 376, 308, 376), fill=WHITE, width=2)

    color = GREEN if backups_good else RED
    label = "BACKUP OK" if backups_good else "BACKUP NOT OK"
    draw.ellipse((44, 406, 66, 428), fill=color)
    draw_text(draw, (78, 417), label, 25, WHITE, True, "lm")
    draw_text(draw, (160, 466), dt.datetime.now().strftime("%H:%M") + (" CACHED" if stale else ""),
              10, AMBER if stale else WHITE, True, "mm")
    return image


def rgb565_bytes(image):
    """Pack an image row-by-row. This does not account for framebuffer rotation or stride."""
    raw = image.convert("RGB").tobytes()
    packed = bytearray(image.width * image.height * 2)
    out = 0
    for offset in range(0, len(raw), 3):
        red, green, blue = raw[offset:offset+3]
        value = ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)
        packed[out:out+2] = bytes((value & 255, value >> 8))
        out += 2
    return bytes(packed)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--output", help="write a PNG preview instead of the framebuffer")
    args = parser.parse_args()
    config = load_config(args.config)
    cache_path = Path(config.get("cache", "state.json"))
    fx, fx_stale = cached(cache_path, "fx", get_fx)
    weather, weather_stale = cached(cache_path, "weather", lambda: get_weather(config))
    image = render(config, fx, weather, host_states(config), backups_ok(config),
                   fx_stale or weather_stale)
    if args.output:
        image.save(args.output)
    else:
        Path(config.get("framebuffer", "/dev/fb0")).write_bytes(rgb565_bytes(image))


if __name__ == "__main__":
    main()
