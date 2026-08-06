# padSpace

> Reproducing this setup on a new machine? Start with [PLAN.md](PLAN.md).

Novation Launchpad Mini MK3 → KDE Plasma virtual desktop switcher (Bazzite, Wayland).

Per-screen desktop control (Plasma 6.7, kwinrc `[Windows] PerOutputVirtualDesktops=true`):

The top two pad rows form **two side-by-side 2×4 grids**, one per display
(fixed assignment via `workspace.screenOrder`, not focus-relative):

- **Left grid** (81–84 over 71–74): display 1, desktops 1–4 upper / 5–8 lower
- **Right grid** (85–88 over 75–78): display 2, same layout

Tap a pad to switch; **hold it ~½ s to also move the window you were using
to that workspace** (the Mini MK3 has no velocity sensing — every pad sends
velocity 127 — so hold duration stands in for "hit hard"). Cross-grid holds
move the window to the other display too.
Each screen's current desktop is **white**; workspaces with windows are dim
white; **empty workspaces are unlit**; a disconnected display's grid goes dark.

Idle pads dim white — except workspaces holding marked apps: **VS Code → red,
Slack → blue** (the `MARKERS` list in the daemon; JS regex vs window class +
palette color per rule, earlier rules win). Markers are per screen: a window
only colors the row of the screen it's actually on (`w.output` in the
reporter). The green current-desktop marker takes precedence over app colors. The second row goes dark with a single
display. Desktop
switches, window moves, and title changes sync to the LEDs near-instantly: a
persistent KWin script listens to workspace/window signals and reports within
~10 ms; grid presses light optimistically before confirmation. A 5 s poll
remains as a safety net. Per-screen switching uses KWin scripting
(`setCurrentDesktopForScreen(desktop, screen)` — desktop argument first); there
is no plain D-Bus API for it.

**Every other pad and round button can run an arbitrary shell command** via
`~/.config/padspace/bindings.conf` (starter copy in `config/`):

```
36 = konsole                      # pad note 36 launches konsole
12 @13 = playerctl play-pause     # pad 12, lit yellow
```

(all eight round buttons — cc91–98 — are reserved for arrows/modes; only grid
pads outside the workspace rows are bindable)

Bound buttons are lit (default blue) and flash white on press; commands run
detached via `systemd-run --user`. The file hot-reloads within ~3 s. To learn
any button's ID, press it and read the "unbound" line in
`journalctl --user -u launchpad-workspaces -f`.

**The four top-left round buttons (cc91–94, printed ↑↓←→) act as real
keyboard arrow keys** — each press injects an arrow-key event into the focused
window through a user-level `ydotoold` (`systemd/ydotoold.service`; Bazzite
grants the seated user `/dev/uinput` access by ACL, so no root needed). One
event per press; no key repeat on hold.

**Numpad mode — the Keys button** (round top row, 7th from left, cc97) turns
the bottom-left 3×4 pads into a numpad: 7 8 9 / 4 5 6 / 1 2 3, with a wide
**0** spanning all three bottom pads (like a real numpad's 0 key). Presses
type the digit via ydotoold. Each digit pad breathes green at 1/N Hz — pad N
cycles once every N seconds; the zero row, at 1/0 = 0 Hz, glows steady —
driven by per-pad RGB SysEx frames every 0.25 s. Mutually exclusive with
Drums/Session/User.

**Skill launcher — the User button** (round top row, 8th from left, cc98)
turns the bottom two rows into agent-skill launchers, read fresh from
`~/.ctrl` at every toggle-on: `~/.ctrl/claude/` fills the bottom row (amber,
opens konsole → claudebox → `claude "/skill"`), `~/.ctrl/hermes/` the row
above (blue, opens konsole → `hermes --skills <name> chat`). Entries are
files/symlinks, sorted by name; a `N-` prefix orders and is stripped. Max 8
per row; empty slots stay dark. Seeded assignments: `config/ctrl-seed.txt`.
Exclusive with Drums/Keys/Session.

**Agentic-session tracker — the Session button** (round top row, 5th from
left, cc95) turns the bottom two rows into a live map of running Claude Code
sessions: bottom row = local `claude` processes, second row = your own
processes on the `polaris` SSH host (other users there are deliberately not
shown). Each lit pad is colored by the sentiment of that session's last
message — green for no error, red for an error, dim white if unreadable.
Press a lit pad to focus the window it's running in, or open a new one
resuming that session if no window is found (always the case for Polaris).
Full detail — the same-cwd ambiguity limitation, the polling architecture,
window-matching mechanics — lives in `skill/SKILL.md`, not here. Exclusive
with Drums/Keys/User.

**Drum mode — the Drums button** (round top row, 6th from left, cc96) turns
the bottom two pad rows into a 16-pad EDM kit: three kicks (punch/sub/hard),
snare, clap, hats, crash on the bottom row; sub-drop, toms, shaker, pluck,
snap, ride, reverse cymbal above. Samples are synthesized by `tools/make-drumkit.py`
(regenerate any time) and preloaded into PipeWire for low-latency, overlapping
triggering. Swap any WAV in `~/.local/share/padspace/drumkit/` to upgrade a
pad. Mutually exclusive with Keys/Session/User.

All four round mode buttons (Session/Drums/Keys/User, cc95-98) are real on/off
toggles: off is a shared dark default (just the workspace grid), turning one
on turns the other three off, and there's no "gate" concept anymore — that
existed only on the Session button early on and was removed 2026-08-05.

## Setting up a new computer

Same setup assumed: Bazzite/Kinoite with Plasma 6.7+ (Wayland) and a Launchpad
Mini MK3. Copy this folder over (or clone it), then:

```sh
./install.sh
```

That checks dependencies (all preinstalled on Bazzite), enables Plasma's
per-screen virtual desktops + 8 desktops in kwinrc, installs the daemon and
systemd user unit, installs the `/padspace` Claude Code skill, and starts the
service. Re-runnable any time to push repo changes to the live locations.
Nothing else is machine-specific — the daemon discovers the Launchpad by name
and the screens at runtime.

## Live locations (canonical copies)

- Daemon: `~/.local/bin/launchpad-workspaces` (python3, stdlib only)
- Unit:   `~/.config/systemd/user/launchpad-workspaces.service` (enabled, WantedBy=graphical-session.target)

This repo holds reference copies in `bin/` and `systemd/`. `logs/` has the full
Claude Code session transcript that built this (also covers the same-day boot-loop
debugging and the Vortex keymap work).

## How it works

1. On start (and on every replug) the daemon finds the Launchpad via `amidi -l`
   (name fragment `LPMiniMK3`) and sends the Programmer-mode SysEx
   `F0 00 20 29 02 0D 0E 01 F7` to both MIDI ports.
2. In Programmer mode grid pads send `Note on` with fixed numbers
   (note = 10·row + col, row 1 = bottom). The daemon reads events with
   `aseqdump -p "Launchpad Mini MK3:0,...:1"`.
3. Mapped press → one-shot KWin script (written to
   `~/.local/share/padspace-action.js`, run via
   `busctl --user call org.kde.KWin /Scripting org.kde.kwin.Scripting`
   unloadScript/loadScript/start) calling
   `workspace.setCurrentDesktopForScreen(workspace.desktops[n-1], screen)` —
   the active screen for row 1, the non-active screen for row 2. There is no
   plain D-Bus method for per-screen switching; scripting is the API.
4. LED sync: a reporter script (`padspace-report.js`) emits
   `PADSPACE-STATE A=<n> O=<n>` via `console.error` (KWin scripts' `print()`
   goes to a disabled log category), which lands in the
   `plasma-kwin_wayland.service` journal; the daemon follows that journal and
   re-lights on change. The reporter runs after every press and every 3 s.
5. LEDs are set with `amidi -S "90 <note> <color>"` (current-desktop pad green
   0x15 in both rows, idle 0x01, app markers per `MARKERS`; round-button row
   cleared with `B0 <cc> 00`).
6. On stop it sends `F0 00 20 29 02 0D 0E 00 F7` to restore standalone (Live)
   mode, so the pad works normally for music again.

Unmapped presses are logged — `journalctl --user -u launchpad-workspaces -f`
shows the CC/note of any button, which is how you extend the maps
(`ROW_ACTIVE` / `ROW_OTHER` dicts at the top of the daemon).

## Operations

```sh
systemctl --user stop launchpad-workspaces     # hand pad back to music apps
systemctl --user start launchpad-workspaces    # reclaim as workspace switcher
journalctl --user -u launchpad-workspaces -f   # watch presses / debug
./install.sh                                   # (re)install from this repo
```

Note: inside the claudebox toolbox, `systemctl --user start` refuses ("systemd
not running"); use the D-Bus API instead:
`busctl --user call org.freedesktop.systemd1 /org/freedesktop/systemd1 org.freedesktop.systemd1.Manager StartUnit ss launchpad-workspaces.service replace`

## Facts worth keeping

- Launchpad Mini MK3 = USB `Focusrite/Novation`, card name `MK3`, two MIDI ports:
  `hw:X,0,0` (DAW) and `hw:X,0,1` (MIDI). Programmer-mode SysEx acks arrive on the DAW port.
- Default standalone mode is a piano-style Keys mode — note numbers are pitches,
  not positions; useless for stable mappings. Programmer mode is the fix.
- Programmer-mode grid pads: note = 10·row + col (row 1 = bottom), so top grid
  row is 81–88. Right column: CC 89,79,…,19. LED palette: 0 off, 1 dim white,
  3 white, 5 red, 13 yellow, 21 green, 37 cyan, 45 blue, 53 purple.
- KWin D-Bus: `org.kde.KWin /KWin currentDesktop` → int (1-based),
  `setCurrentDesktop(i)` → bool (false = already there) — active screen only.
  8 desktops configured (kwinrc `[Desktops] Number=8`).
- Per-screen desktops require Plasma 6.7+ and kwinrc `[Desktops]
  PerOutputVirtualDesktops=true` (System Settings: "Switch desktop independently
  for each screen"). Scripting API: `workspace.currentDesktopForScreen(screen)`
  and `workspace.setCurrentDesktopForScreen(desktop, screen)` — desktop argument
  FIRST; screen-first throws "incompatible arguments". Desktop number via
  `.x11DesktopNumber`; screens via `workspace.screens` / `workspace.activeScreen`
  (here: eDP-1 laptop, HDMI-A-1 external).
