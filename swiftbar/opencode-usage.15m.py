#!/usr/bin/env python3
# <xbar.title>opencode usage</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.author>spacecr8ed</xbar.author>
# <xbar.desc>Shows opencode Zen (Go) usage windows in the macOS menu bar.</xbar.desc>
# <xbar.dependencies>python3</xbar.dependencies>
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>

import base64
import json
import os
import struct
import time
import urllib.request
import zlib
from datetime import datetime

AUTH_PATH = os.path.expanduser("~/.local/share/opencode/auth.json")
USAGE_URL = "https://opencode.ai/zen/go/v1/usage"
STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".opencode-usage-state.json")

MIN_INTERVAL_S = 60
MAX_BACKOFF_S = 900

WINDOWS = (
    ("rolling", "5h", 5 * 3600),
    ("weekly", "wk", 7 * 86400),
    ("monthly", "mo", 30 * 86400),
)

WIDTH = 56
HEIGHT = 17
SCALE = 2
MARGIN = 1
BAR_H = 6
GAP = 3
RADIUS = 2
PAD_RIGHT = 2
Y_NUDGE = 1
STALE_ALPHA = 0.45

OK = "#1c7c31,#30d158"
WARN = "#b06a00,#ff9f0a"
BAD = "#c0392b,#ff453a"
MUTED = "#8a8a8e,#98989d"

TRACK = (150, 150, 150, 90)
GRADIENT_STOPS = (
    (0.0, (48, 209, 88)),
    (0.5, (255, 214, 10)),
    (1.0, (255, 69, 58)),
)

DIM = False


def _gradient(t):
    t = max(0.0, min(1.0, t))
    for index in range(len(GRADIENT_STOPS) - 1):
        a, color_a = GRADIENT_STOPS[index]
        b, color_b = GRADIENT_STOPS[index + 1]
        if t <= b:
            span = b - a
            f = (t - a) / span if span else 0.0
            return tuple(round(color_a[k] + (color_b[k] - color_a[k]) * f) for k in range(3)) + (255,)
    return GRADIENT_STOPS[-1][1] + (255,)


def _draw_bar(buf, width, x0, y0, x1, y1, color, rl, rr):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            ok = True
            if rl > 0 and x < x0 + rl and (y < y0 + rl or y > y1 - rl):
                cx = x0 + rl
                cy = y0 + rl if y < y0 + rl else y1 - rl
                if (x - cx) ** 2 + (y - cy) ** 2 > rl * rl:
                    ok = False
            if ok and rr > 0 and x > x1 - rr and (y < y0 + rr or y > y1 - rr):
                cx = x1 - rr
                cy = y0 + rr if y < y0 + rr else y1 - rr
                if (x - cx) ** 2 + (y - cy) ** 2 > rr * rr:
                    ok = False
            if ok:
                index = (y * width + x) * 4
                buf[index:index + 4] = bytes(color(x) if callable(color) else color)


def _draw_round_rect(buf, width, x0, y0, x1, y1, color, radius):
    _draw_bar(buf, width, x0, y0, x1, y1, color, radius, radius)


def _encode_png(width, height, buf):
    if Y_NUDGE or DIM:
        row = width * 4
        out = bytearray(width * height * 4)
        for y in range(height):
            source = y - Y_NUDGE
            if 0 <= source < height:
                start = source * row
                segment = bytearray(buf[start:start + row])
                if DIM:
                    for i in range(3, len(segment), 4):
                        segment[i] = int(segment[i] * STALE_ALPHA)
                out[y * row:(y + 1) * row] = segment
        buf = out

    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw.extend(buf[y * width * 4:(y + 1) * width * 4])

    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    return base64.b64encode(png).decode()


def outline_image(percent, elapsed):
    width = WIDTH * SCALE
    height = HEIGHT * SCALE
    buf = bytearray(width * height * 4)
    margin = MARGIN * SCALE
    bar_h = BAR_H * SCALE
    gap = GAP * SCALE
    radius = RADIUS * SCALE
    thickness = max(1, SCALE)

    x0 = margin
    x1 = width - margin - 1 - PAD_RIGHT * SCALE

    top_y0 = margin
    top_y1 = top_y0 + bar_h - 1
    bot_y0 = top_y1 + gap + 1
    bot_y1 = bot_y0 + bar_h - 1

    for y0, y1 in ((top_y0, top_y1), (bot_y0, bot_y1)):
        _draw_round_rect(buf, width, x0, y0, x1, y1, TRACK, radius)
        _draw_round_rect(
            buf, width, x0 + thickness, y0 + thickness, x1 - thickness, y1 - thickness,
            (0, 0, 0, 0), max(0, radius - thickness),
        )

    inner_x0 = x0 + thickness
    inner_x1 = x1 - thickness
    inner_span = inner_x1 - inner_x0 + 1
    inner_radius = max(0, radius - thickness)
    usage_px = max(1, round(inner_span * min(percent, 100) / 100))
    time_px = max(1, round(inner_span * clamp01(elapsed)))
    gradient = lambda x: _gradient((x - inner_x0) / max(1, inner_span - 1))

    _draw_bar(
        buf, width, inner_x0, top_y0 + thickness, inner_x0 + usage_px - 1, top_y1 - thickness,
        gradient, min(inner_radius, usage_px // 2), min(inner_radius, usage_px // 2),
    )
    _draw_bar(
        buf, width, inner_x0, bot_y0 + thickness, inner_x0 + time_px - 1, bot_y1 - thickness,
        gradient, min(inner_radius, time_px // 2), min(inner_radius, time_px // 2),
    )

    return _encode_png(width, height, buf)


def clamp01(value):
    return max(0.0, min(1.0, float(value)))


def text_bar(percent, elapsed, width=10):
    level = min(percent, 100) / 100 * width
    cells = []
    for index in range(width):
        fill = level - index
        if fill >= 1:
            cells.append("█")
        elif fill <= 0:
            cells.append("░")
        elif fill >= 0.5:
            cells.append("▓")
        else:
            cells.append("▒")
    marker = min(width - 1, max(0, round(elapsed * width)))
    cells[marker] = "▌"
    return "".join(cells)


def color_for(percent, over_pace):
    if over_pace or percent >= 80:
        return BAD
    if percent >= 60:
        return WARN
    return OK


def severity(percent, over_pace):
    if over_pace:
        return "over pace"
    if percent >= 80:
        return "high"
    if percent >= 60:
        return "watch"
    return "ok"


def humanize(millis):
    seconds = max(0, int(millis / 1000))
    days, rem = divmod(seconds // 3600, 24)
    hours, minutes = divmod(rem, 60)
    if days:
        return f"{days}d{hours}h"
    if hours:
        return f"{hours}h{minutes}m"
    return f"{minutes}m"


def fmt_reset(millis):
    moment = datetime.fromtimestamp(millis / 1000)
    if moment.date() == datetime.now().date():
        return moment.strftime("%H:%M")
    return moment.strftime("%a %H:%M")


def parse_reset(value, fallback):
    if not isinstance(value, str):
        return fallback
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000
    except Exception:
        return fallback


def auth_key():
    try:
        with open(AUTH_PATH) as handle:
            return json.load(handle).get("opencode-go", {}).get("key")
    except Exception:
        return None


def fetch_usage(key):
    request = urllib.request.Request(
        USAGE_URL,
        headers={"Authorization": f"Bearer {key}", "User-Agent": "opencode-swiftbar/1.0"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def load_state():
    try:
        with open(STATE_PATH) as handle:
            return json.load(handle)
    except Exception:
        return {}


def save_state(state):
    try:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        tmp = STATE_PATH + ".tmp"
        with open(tmp, "w") as handle:
            json.dump(state, handle)
        os.replace(tmp, STATE_PATH)
    except Exception:
        pass


def render(usage, now, stale, state):
    rows = []
    for window_key, label, cycle_seconds in WINDOWS:
        window = usage.get(window_key)
        if not isinstance(window, dict) or not isinstance(window.get("percent"), (int, float)):
            continue
        percent = float(window["percent"])
        resets_at = parse_reset(window.get("resetsAt"), now)
        elapsed = clamp01((now - (resets_at - cycle_seconds * 1000)) / (cycle_seconds * 1000))
        over_pace = percent > elapsed * 100
        rows.append((label, percent, elapsed, over_pace, resets_at))

    if not rows:
        print(f"opencode: no data | sfimage=gauge.medium sfcolor={WARN} color={WARN}")
        return

    for label, percent, elapsed, _, _ in rows:
        print(f"{label} | image={outline_image(percent, elapsed)} width={WIDTH} height={HEIGHT} dropdown=false")

    print("---")
    for label, percent, elapsed, over_pace, resets_at in rows:
        color = color_for(percent, over_pace)
        pace = round(elapsed * 100)
        print(
            f"{label}  {text_bar(percent, elapsed)} {round(percent):>3}%   ▸{pace}%"
            f"   {severity(percent, over_pace)}"
            f"   reset {humanize(resets_at - now)} ({fmt_reset(resets_at)})"
            f" | font=Menlo size=12 color={color}"
        )

    print("---")
    if stale:
        age = humanize(now - state.get("last_success", now))
        print(f"⚠ last known value ({age} old) | color={WARN} size=11")
    print("Open opencode.ai | href=https://opencode.ai/")
    print("Refresh now | refresh=true")
    print(f"Updated {datetime.now().strftime('%H:%M:%S')} | color={MUTED} size=11")


def main():
    global DIM
    now = time.time() * 1000
    state = load_state()
    reason = os.environ.get("SWIFTBAR_PLUGIN_REFRESH_REASON", "")
    manual = reason in ("MenuAction", "RefreshAllMenu")
    cached = state.get("usage")
    key = auth_key()

    if not key:
        print(f"opencode n/a | sfimage=gauge.medium sfcolor={WARN} color={WARN}")
        return

    in_backoff = bool(state.get("retry_after")) and now < state["retry_after"]
    within_min = bool(state.get("last_attempt")) and (now - state["last_attempt"] < MIN_INTERVAL_S * 1000)

    stale = False
    if cached and not manual and (in_backoff or within_min):
        usage = cached
        stale = in_backoff
    else:
        try:
            data = fetch_usage(key)
            usage = data.get("usage", {}) if isinstance(data, dict) else {}
            state.update({"usage": usage, "last_attempt": now, "last_success": now, "failures": 0, "retry_after": 0})
            save_state(state)
        except Exception:
            failures = int(state.get("failures", 0)) + 1
            backoff = min(MAX_BACKOFF_S, MIN_INTERVAL_S * (2 ** (failures - 1))) * 1000
            state.update({"failures": failures, "last_attempt": now, "retry_after": now + backoff})
            save_state(state)
            usage = cached
            stale = True
            if not usage:
                print(f"opencode err | sfimage=gauge.medium sfcolor={BAD} color={BAD}")
                return

    DIM = stale
    render(usage, now, stale, state)


if __name__ == "__main__":
    main()
