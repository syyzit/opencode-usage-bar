# opencode usage bar

A macOS menu bar widget that shows your opencode Zen (Go) usage windows at a glance.

For each window (5h rolling, weekly, monthly) it draws two small bars: the top bar is usage, the bottom bar is elapsed time. Both are gradient capsules inside an outline track, so you can compare how much you have used against how much of the window has passed.

It is a SwiftBar plugin, paired with a tiny opencode plugin that refreshes the bar right after each response.

![widget preview](docs/preview.png)

## What it shows

- Three windows: 5h rolling, weekly, monthly.
- Top bar: percent used, with a green to amber to red gradient whose leading edge color reflects the pressure.
- Bottom bar: percent of the window elapsed.
- The menu bar label cycles through `5h`, `wk`, `mo` every 5 seconds.
- The dropdown shows exact percentages, pace, a severity word, and both relative and absolute reset times.

## Requirements

- macOS
- SwiftBar
- python3 (ships with macOS)
- opencode with an opencode-go (Zen) login, so that `~/.local/share/opencode/auth.json` contains an `opencode-go` key

## Install

1. Install SwiftBar:

   ```
   brew install --cask swiftbar
   ```

2. Pick a plugin folder, for example `~/.swiftbar`, and point SwiftBar at it. In SwiftBar preferences you can choose the folder, or set it from the terminal:

   ```
   mkdir -p ~/.swiftbar
   defaults write com.ameba.SwiftBar PluginDirectory -string "$HOME/.swiftbar"
   ```

3. Copy the plugin and make it executable:

   ```
   cp swiftbar/opencode-usage.15m.py ~/.swiftbar/
   chmod +x ~/.swiftbar/opencode-usage.15m.py
   ```

4. Copy the opencode trigger plugin:

   ```
   mkdir -p ~/.config/opencode/plugins
   cp opencode/swiftbar-refresh.ts ~/.config/opencode/plugins/
   ```

5. Launch SwiftBar and restart your opencode client (terminal or desktop) so it loads the trigger plugin.

The `.15m` in the filename is the fallback refresh interval. See Refresh cadence below.

## How it works

- Reads your opencode-go key from `~/.local/share/opencode/auth.json`.
- Requests `https://opencode.ai/zen/go/v1/usage` with a Bearer token.
- Draws a base64 PNG in pure Python for each window and hands it to SwiftBar.
- Caches the last good response next to the script and applies the cadence rules below.

Note: this is the same endpoint the opencode client uses. It is not a documented public API, so it could change without notice.

## Refresh cadence

- Baseline: SwiftBar reruns the script every 15 minutes, from the filename.
- Events: the opencode plugin calls the SwiftBar refresh URL about 2 seconds after every response, throttled to at most once per minute.
- Cache: the script makes at most one network request per minute. If it runs sooner than that, it serves the cached response.
- Errors: on failure it keeps showing the last known value, dimmed, and backs off 60s, 120s, 240s, up to 900s.

The endpoint is therefore queried at most once per minute and at least once per 15 minutes.

## Customize

Open `opencode-usage.15m.py` and edit the constants near the top:

- `WIDTH`, `HEIGHT`: widget size in points
- `BAR_H`, `GAP`: bar thickness and spacing
- `RADIUS`: corner rounding, 0 is square and 3 is a full pill
- `PAD_RIGHT`: gap between the bars and the label
- `Y_NUDGE`: shift the widget up or down by device pixels
- `STALE_ALPHA`: dimming applied to the last known value
- `MIN_INTERVAL_S`, `MAX_BACKOFF_S`: network throttle and error backoff
- `OK`, `WARN`, `BAD`, `MUTED`: text colors
- `GRADIENT_STOPS`: gradient colors

After editing, click "Refresh now" in the dropdown.

## Troubleshooting

- Bar is invisible: a menu bar manager (Hidden Bar, Ice, Bartender, and similar) may be hiding it. Cmd+drag the item to the right of the manager's divider, or disable the manager. The item still exists even when hidden.
- No data: make sure you are logged in and `~/.local/share/opencode/auth.json` contains an `opencode-go` key.
- Stale value: when the last request fails the dropdown shows a warning and the bars are dimmed. It recovers on the next successful request.

## Uninstall

- Remove the plugin file from the SwiftBar plugin folder.
- Remove `~/.config/opencode/plugins/swiftbar-refresh.ts`.

## License

MIT. See LICENSE.
