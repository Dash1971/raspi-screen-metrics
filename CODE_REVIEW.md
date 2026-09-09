# Application review follow-ups

Review of `9c6860376b9ee00d6e22358128f5fe006fa90262`, dated 2026-09-09.
These are separate from [the display configuration issue](KNOWN_ISSUE.md).
They remain open; this PR does not change application behavior.

## P2: an uncached API failure prevents all rendering

`cached()` rethrows an API exception if its key is absent. `main()` fetches FX and
weather before rendering. A first run during an outage therefore draws nothing,
including otherwise available host and backup status. Reproduced with an absent
cache and a fetcher raising `TimeoutError`.

Handle unavailable sources independently and render explicit unavailable values.

## P2: old upstream FX quotes are marked fresh

`get_fx()` records local fetch time but does not check or retain Yahoo's
`regularMarketTime`. A successful response containing an old quote produces
`stale=False`. Reproduced with a synthetic response containing a valid price and
quote timestamp 1.

Retain source timestamps, show age, and define freshness rules accounting for
market closures. Test stale successful responses as well as transport failures.

## P2: missing system fonts defeat the large-text layout

When neither DejaVu path exists, `typeface()` calls `ImageFont.load_default()`
without the requested size. With those paths mocked absent, requested sizes 20
and 68 produce identical text bounds. The dimension-only render test still passes.

Document/install the font dependency or use a sized fallback. Test that primary
text stays large without the system font. This font was present on the inspected
Pi, so this does not explain its physical clipping.

## P3: overcast weather appears as CLEAR

`weather_kind()` falls through to `clear` for moderate temperature, no rain, and
cloud code 3; the icon is a sun. Reproduced with
`{"temp": 23, "code": 3, "rain": 0}`.

Add a cloudy case/icon while preserving snow/rain/hot/cold precedence.

## Validation

The three original tests passed. Separate local characterization checks
reproduced the four behaviors above and confirmed asymmetric RGB565 byte order.
Those reproductions do not establish that the defects are fixed. An asymmetric
pixel test is now included to detect swapped channels, endianness errors, and
transpositions missed by a byte-count-only test.

All public examples use generic values. Operational paths and live data are
unnecessary to reproduce these application behaviors.
