---
name: padspace
description: Launchpad Mini MK3 → KDE workspace switcher on Vin's Bazzite machine. Use when the user asks about the Launchpad workspace buttons, wants to remap buttons/pads, change LED colors, stop/start it for music use, debug why a button does nothing, or reinstall the daemon. All protocol facts below are verified on the device — no research needed.
---

# padSpace — Launchpad Mini MK3 workspace switcher

## Workflow: keep small requests small

Vin explicitly pushed back (2026-08-05) on burning excess time/tokens on
simple asks. Default posture for a clearly-scoped change ("move X to Y",
"make this a toggle", "fix this button"):
1. Read the relevant part of `~/.local/bin/launchpad-workspaces` (it's not
   large — grep for the constant/CC/note in question).
2. Edit it.
3. `python3 -m py_compile ~/.local/bin/launchpad-workspaces` to catch typos.
4. Restart: `busctl --user call org.freedesktop.systemd1
   /org/freedesktop/systemd1 org.freedesktop.systemd1.Manager RestartUnit ss
   launchpad-workspaces.service replace` (systemctl start/restart fails
   inside the claudebox toolbox — see below).
5. One `journalctl --user -u launchpad-workspaces -n 5-10` check for a clean
   "connected on [...]" line, no traceback.
6. Update the relevant section of this skill file to match, report back.
That's the whole loop for a small change — don't add extra verification
theater beyond it.

**Don't over-ask.** Only reach for `AskUserQuestion` when an interpretation
gap would genuinely send the work in a different direction (e.g. the
agentic-session tracker needed one round on cross-user privacy scope before
touching Polaris). If there's one obvious reading, implement it — don't ask
just because an alternate reading is theoretically possible. When a question
is genuinely needed, batch it into one call rather than serial rounds.

**Don't over-verify what can't be verified this way.** I (the assistant)
cannot simulate a physical button press — confirmed: writing raw MIDI via
`amidi -S` to the device only drives its LEDs (output), it does not appear
as an input event in `aseqdump`, so it can't fake a press. For anything that
depends on an actual press, the ceiling of what I can check myself is:
static code review, `py_compile`, a clean daemon restart, and one live KWin
D-Bus/journal query for state that doesn't require a physical press (e.g.
current desktop, window list, occupancy). Say plainly that the interactive
path is unverified and needs Vin's hands on the device — don't spiral into
more probe scripts or repeated journal-watch attempts hoping to catch a
press indirectly (multiple attempts at that on 2026-08-05 wasted real time
for no signal).

**When debugging "why is X doing Y":** ask the single highest-signal
question FIRST — usually "what visibly happens when you press it (nothing /
a flash / a desktop switch)?" — rather than row/column counting (people
count rows inconsistently — from the round-CC-button row vs. from the grid's
own top row are both real conventions people use) or indirect state-diffing
(contaminated by the user's own normal desktop-switching in parallel). The
2026-08-05 stuck-pad bug was solved by that one question, asked too late
after several rounds of counting confusion and failed diagnostic scripts —
ask it first next time.

Project: `~/projects/padSpace` (README, reference copies, install.sh, session transcript).
Live daemon: `~/.local/bin/launchpad-workspaces` · unit: `~/.config/systemd/user/launchpad-workspaces.service` (enabled).

Plasma 6.7 per-screen virtual desktops (kwinrc `[Windows]
PerOutputVirtualDesktops=true`). Top two pad rows = two side-by-side 2×4 grids, FIXED per display
(ordered by `workspace.screenOrder`, fallback `.screens` — index 0 = first):
- LEFT grid `GRID_S0` (81–84 / 71–74): screen 0, desktops 1–4 upper, 5–8 lower
- RIGHT grid `GRID_S1` (85–88 / 75–78): screen 1, same layout
Tap = switch. HOLD ≥ 0.55 s (`HOLD_MOVE_SECS`) = also move the window that
was active at press time to that pad's desktop+screen: the switch script emits
`PADSPACE-GRAB <internalId>` (captured pre-switch), and on a long Note-off the
MOVE_WINDOW script finds the window by internalId, sets
`w.desktops = [desktop]`, then relocates across displays by setting
`w.frameGeometry` into the target output's geometry (centered, size-clamped).
IMPORTANT: `workspace.sendClientToScreen` is UNRELIABLE under per-output
virtual desktops — it silently refuses when the window's desktop isn't the
target screen's current desktop (and in other post-switch states). Geometry
placement is the reliable move mechanism. Also: Output object identity
comparison (`===`) across API calls is meaningless — compare `.name`.
Verified screen order on this machine: HDMI-A-1 (index 0, left/ultrawide),
eDP-1 (index 1, right/laptop). NOTE: Mini MK3 pads have NO velocity sensing —
always 127 — so velocity gestures are impossible; hold duration is the
substitute.
Per pad: current desktop = white (3) > marker color > occupied = dim white (1)
> empty = unlit. Windows with `demandsAttention` (alert/urgency) flash their
pad high/low of its computed color: ch1 note-on = dim variant, ch2 note-on
(0x91) = bright — the device alternates them automatically. Palette rule:
bright N dims to N+2 (white 3 → 1), `dim_variant()`. Reporter tokens U0=/U1=
per screen; events script hooks `w.demandsAttentionChanged`. The property is
also WRITABLE from KWin scripts (handy for testing). Occupancy comes from `W0=`/`W1=` reporter tokens. Missing
screen 1 → right grid dark.
Idle pads dim white; app markers color occupied pads via the `MARKERS`
list — `(target, js_regex, palette_color)` per rule, target "class" matches
lowercased `w.resourceClass`, "caption" matches the lowercased window title
(browser caption = ACTIVE tab title only). Current rules: VS Code → red 5,
Notion "Vineet Work Log" caption → green 21 (regex tolerates worklog/work log), Slack → blue 45.
`MARKER_COMBOS` maps rule-index sets to blend colors (worklog+slack → cyan 37)
and beats single rules; otherwise earliest rule wins. White current-desktop
takes precedence over all markers.
Detection is PER SCREEN: the KWin REPORTER script scans `workspace.windowList()`,
filters `w.normalWindow`, buckets each match by which ordered screen owns
`w.output.name`, collects `w.desktops` (or all if `w.onAllDesktops`), and
reports `S0=n S1=n` (current desktop per screen) plus `M<i>S<s>=n,n` marker
tokens in PADSPACE-STATE. Each grid lights only from its own screen's tokens.
Add a rule = add a MARKERS entry; REPORTER JS is generated from it.
Round top-row buttons cc91–94 (printed ↑↓←→) inject real arrow-key events via
user-level ydotoold (`ARROW_CCS` maps cc → Linux keycode 103/108/105/106;
socket $XDG_RUNTIME_DIR/.ydotool_socket; unit ~/.config/systemd/user/
ydotoold.service; /dev/uinput user access via Bazzite's seat ACL). cc91–98
all reserved in bindings.conf — every round button is a mode toggle or arrow,
none are free for a custom binding. On stop, pad restored to
standalone mode. Screens: eDP-1 (laptop), HDMI-A-1 (external).

Per-screen switching has NO plain D-Bus API — it goes through KWin scripting:
`workspace.setCurrentDesktopForScreen(desktop, screen)` — **desktop first**
(screen-first throws "incompatible arguments"). Desktop objects:
`workspace.desktops[n-1]`, number via `.x11DesktopNumber`. Read with
`workspace.currentDesktopForScreen(screen)`. The daemon writes one-shot JS to
~/.local/share/padspace-{action,report}.js and runs it via
`busctl --user call org.kde.KWin /Scripting org.kde.kwin.Scripting`
(unloadScript → loadScript ss <path> <name> → start). KWin scripts' `print()`
goes to a disabled log category — use `console.error(...)`, which lands in the
plasma-kwin_wayland.service journal; the daemon follows that journal for
PADSPACE-STATE lines. LED sync is EVENT-DRIVEN: a persistent KWin script
(padspace-events, loaded per session, unloaded on teardown) connects
workspace.currentDesktopChanged / windowAdded / windowRemoved and per-window
desktopsChanged / captionChanged / outputChanged, emitting a state line within
~10 ms of any change. Grid presses also light optimistically before
confirmation. Every report starts with a `T=<epoch ms>` token; the daemon
DROPS reports older than its last press/move (`last_action_ms`) so a late
pre-press report can't drag the LEDs backwards — don't remove this guard,
removing it reintroduces visible LED flip-backs. The one-shot reporter poll
(5 s) is only a safety net.

**Numpad mode:** Keys button (row 1 col 7, cc97, `KEYS_CC`) → bottom-left
3×4 pads (`NUMPAD`: 41-43=789, 31-33=456, 21-23=123, 11-13 all = wide ZERO)
type digits via ydotoold (keycode = digit+1, except KEY_0=11). Digit LEDs breathe green
sinusoidally at 1/N Hz per pad N (zero row: 0 Hz = steady, g=110) via RGB SysEx
(`F0 00 20 29 02 0D 03 (03 <note> <R> <G> <B>)... F7`, values 0-127), refreshed
every 0.25 s from the daemon loop (`numpad_rgb`). Toggle; turning Keys off
returns to the default (bottom rows dark, just the workspace grid). Mutually
exclusive with Drums/Session/User. cc91–98 all reserved.

**User mode (skill launcher):** User button (row 1 col 8, cc98, `USER_CC`)
toggles the bottom two rows into a skill launcher: bottom row = Claude Code
skills (amber 9), second row = Hermes skills (blue 45), from
`~/.ctrl/claude/` and `~/.ctrl/hermes/` (symlinks/files, sorted, `N-` prefix
stripped, max 8, re-read on every toggle-on — no restart needed to
re-arrange). Press → konsole: `distrobox enter claudebox -- claude "/<name>"`
or `hermes --skills <name> chat` (templates `CLAUDE_CMD`/`HERMES_CMD`).
Off (`user_ctrl = None`) is the default, including at daemon start — bottom
rows dark, only the workspace grid (top two rows) is live. Mutually
exclusive with Drums/Keys/Session (LED: white 3 on, dim white 1 off). This
function lived on the Session button until 2026-08-05, then moved to User
the same day to free up Session for a planned feature (below).

**Session mode (agentic-session tracker, built 2026-08-05):** Session button
(row 1 col 5, cc95, `SESSION_CC`) toggles the bottom two rows into a live
map of running Claude Code sessions:
- bottom row (11-18) = local `claude` processes (`ps -eo pid,comm`, comm ==
  "claude"); second row (21-28) = Vin's own processes on Polaris (SSH alias
  `polaris`, `100.64.0.40`, user `vineet` — filtered to `POLARIS_USER`;
  deliberately does NOT surface other users' sessions on that shared box,
  e.g. `ian`'s — Vin was explicit about this scope when it was built).
- Each pid's cwd (`/proc/<pid>/cwd` locally, `os.readlink` over SSH for
  Polaris) maps to a Claude Code project dir the same way Claude Code itself
  does: `~/.claude/projects/<cwd with / replaced by ->/`. The newest
  `*.jsonl` there is that session's transcript; its `session_id` is the
  filename. **Known limitation:** if two processes share the exact same cwd
  there is no signal (checked: no session-id env var in `/proc/pid/environ`,
  no open fd to the transcript) to tell which transcript belongs to which
  pid — `group_sessions_by_cwd()` collapses them into one pad rather than
  showing duplicate/possibly-wrong pads. A press on that pad tries all of
  the group's pids for window-matching and unions them for --resume.
- Color = sentiment of the transcript's last message: green
  (`COLOR_SESSION_POS`, 21) if the last tool_result had no error, red
  (`COLOR_SESSION_NEG`, 5) if it did, dim white (`COLOR_SESSION_UNKNOWN`, 1)
  if the transcript couldn't be read. This is a structural heuristic (the
  `is_error` field on the last `tool_result` content block), not real
  sentiment analysis — there's no LLM call in this hot polling loop.
- Press a lit pad (`handle_session_press`): for a local session, walk
  `/proc` ancestry up from the claude pid(s) (`process_ancestors`) — KWin
  only exposes a window's own pid (the terminal emulator), not the
  shell/claude process inside it, so matching means checking whether any
  ancestor pid equals some window's `w.pid`. This is done via a one-shot
  KWin script (`ACTIVATE_WINDOW`, run through the existing `ACTION_JS`
  one-shot-script mechanism) that takes the pid set and both focuses the
  matching window AND switches its screen to the matching desktop, reporting
  back "PADSPACE-ACTIVATE hit/miss" over the same kwin_wayland journal the
  daemon already follows (`try_activate_window` reads that response
  directly off `jrn.stdout`, blocking up to 0.4s — deliberately consumes
  from the shared journal stream outside the main select() loop, which can
  make the main loop miss one incidental STATE line on that pass; acceptable
  since this only happens on a manual press and the event-driven reporter
  emits a fresh line on the next change anyway). On a miss (no window found —
  always the case for Polaris, which never has a local window) it opens a
  new `konsole` running `claude --resume <session_id>` (over `ssh -t polaris
  ...` for Polaris) instead, so pressing a pad always either focuses the
  session or resumes it in a fresh window.
- Polling: local runs inline in the main loop every `SESSION_POLL_SECS` (3s)
  — cheap (ps + a few small file reads). Polaris runs in a background
  `threading.Thread` (`polaris_poller_loop`, `POLARIS_POLL_SECS` = 6s)
  started on toggle-on and stopped (`_polaris_stop.set()`) on toggle-off or
  when Drums/Keys/User take over the bottom rows — a blocking SSH round trip
  in the main loop would freeze the whole pad (arrows, workspace switching,
  everything) for however long it took; the thread hands results to the main
  loop via `_polaris_sessions` behind `_polaris_lock`. One SSH round trip per
  poll regardless of session count: `REMOTE_SESSION_SCRIPT` (python3 fed on
  stdin) does the pgrep + per-pid cwd + sentiment work remotely and prints
  `pid|sentiment|sid|cwd` lines.
- **Not yet tested on real hardware** — I (the assistant) can only write TO
  the device (LEDs, via `amidi -S`) not simulate a button press FROM it
  (confirmed: raw `amidi -S` writes to `hw:X,0,0` do not appear in
  `aseqdump`), so the toggle-on rendering and the press-dispatch path
  (`handle_session_press`, window activation, resume fallback) are verified
  by static reading and by exercising the pure functions directly
  (`local_claude_sessions`/`build_session_map`/`sentiment_color` all checked
  against real running sessions), but not by an actual physical press. If a
  press doesn't do what's documented here, that's the first place to look —
  don't assume this description is proven correct in practice yet.
LED: white 3 on, dim white 1 off. Reserved in bindings.conf like the other
three mode buttons (not user-bindable).

Round buttons: arrows cc91-94, Session cc95 (session tracker), Drums cc96, Keys
cc97, User cc98 (skill launcher) — all four round mode buttons (95-98) are
real on/off toggles, mutually exclusive with each other, sharing the same
dark default when off.

## Command bindings (any button → any shell command)

`~/.config/padspace/bindings.conf` — hot-reloaded within ~3 s, no restart.
Line format: `<button> [@color] = <shell command>` where button is a pad note
number or `ccN` for round buttons (top row cc91–98, right column cc19–89).
Color = LED palette index, default 45 (blue). Workspace rows 81–88/71–78 and
cc91–98 (all four mode toggles + arrows) are reserved (binding attempts are
logged and ignored) — there is currently no free round button for a custom
command; if Vin wants one, he'll need to give up a mode or use a grid pad
outside the reserved rows. Commands run detached via `systemd-run --user
--collect`. Bound buttons stay lit; white flash on press.

**Drum mode:** the Drums button (round row 1 col 6, cc96, `DRUMS_CC`) toggles
the bottom TWO pad rows (notes 11–18, 21–28) into a 16-pad synthesized
909/808-style kit (`DRUM_PADS` maps note → (sample name, LED color); Drums LED
amber 9 when on). Mutually exclusive with Keys/Session/User — enabling any
of the four disables the others, and toggling off returns to the shared dark
default (workspace grid only), not to any other mode. WAVs live in
`~/.local/share/padspace/drumkit/`, generated
by `~/projects/padSpace/tools/make-drumkit.py` (pure stdlib synthesis; replace
any WAV with a same-named file to upgrade a pad, then re-toggle drum mode).
Low latency: samples preload into PipeWire-Pulse via `pactl upload-sample
<file> padspace-<name>` on mode entry; hits trigger `pactl play-sample`
(server-side, overlapping). EDM-tuned layout — bottom row: kick-punch,
kick-sub, kick-hard, snare, clap, hat-closed, hat-open, crash; second row:
sub-drop, tom-low, tom-high, shaker, pluck, snap, ride, reverse-cymbal.
cc95-98 are all reserved in bindings.conf (all four are mode toggles now).
To find a button's ID: press it, read the "unbound pad note N / control ccN"
line in the daemon journal. Starter config: `~/projects/padSpace/config/bindings.conf`.

## Editing the mapping

`GRID_S0` / `GRID_S1` dicts at the top of `~/.local/bin/launchpad-workspaces`
(grid note = 10·row + col with row 1 at bottom, so row N from the top is notes
(9−N)·10+1 … +8). `WORKSPACE_NOTES` is their union (reserved in bindings).
Switching runs the SWITCH_SCREEN one-shot KWin script with a screen index.
App-marker colors live in `MARKERS` there too. To find any button's ID, have the
user press it and read `journalctl --user -u launchpad-workspaces -f` — the
daemon logs all unmapped presses (grid pads as "Note on", round buttons as CC).
Round-button LEDs use `B0 <cc> <color>`; pad LEDs use `90 <note> <color>`.
After editing: copy to `~/projects/padSpace/bin/` too, then restart (below).

## Restart / stop / start (from claudebox container)

`systemctl --user start/restart` FAILS inside the toolbox ("systemd is not
running"). Use the D-Bus API (status/enable/daemon-reload work normally):

    busctl --user call org.freedesktop.systemd1 /org/freedesktop/systemd1 \
      org.freedesktop.systemd1.Manager RestartUnit ss launchpad-workspaces.service replace

(also StartUnit / StopUnit, same signature). `~/projects/padSpace/install.sh`
does install + enable + restart in one shot.

## Device protocol (Launchpad Mini MK3, verified)

- Appears in `amidi -l` as `LPMiniMK3`, two ports: `hw:X,0,0` DAW, `hw:X,0,1` MIDI
  (card number X varies; discover by name). ALSA seq client: "Launchpad Mini MK3".
- Programmer mode ON:  SysEx `F0 00 20 29 02 0D 0E 01 F7` (ack echoes on DAW port).
  Programmer mode OFF (standalone/Live): same with `00`.
- Default power-on mode is Keys (piano) — note numbers are pitches, NOT stable
  positions. Never map buttons outside Programmer mode.
- In Programmer mode: top row = CC 91–98 (press value 127, release 0);
  grid pads = notes 10·row+col; right column = CC 89,79,…,19.
- LEDs: `amidi -p <port> -S "B0 <cc> <color>"` for CC buttons,
  `"90 <note> <color>"` for pads. Palette: 0 off, 1 dim white, 3 white, 5 red,
  13 yellow, 21 green, 37 cyan, 45 blue, 53 purple. Flash = channel 2 (0x91…),
  pulse = channel 3 (0x92…).

## KWin D-Bus (Plasma 6, Wayland)

- Current: `busctl --user call org.kde.KWin /KWin org.kde.KWin currentDesktop` → `i N` (1-based)
- Switch:  `... setCurrentDesktop i N` → `b true` (false = already there)
- 8 virtual desktops configured. Also available: nextDesktop / previousDesktop.

## Debug checklist

1. `journalctl --user -u launchpad-workspaces -n 30` — "waiting for Launchpad..."
   means USB/ALSA can't see it (`cat /proc/asound/cards`, look for `MK3`).
2. Button press logged as "unmapped"/"unbound" → not in GRID_S0/GRID_S1 or
   bindings.conf; add it where it belongs.
3. Nothing logged on press → device not in programmer mode or aseqdump lost
   the port; restart the unit (it re-sends the mode SysEx).
4. Pad in factory mode after unplug/replug → aseqdump does NOT exit when the
   device vanishes (its seq client disappears silently), so EOF-based detection
   never fires. The daemon's 5 s poll compares `amidi_ports()` against the
   session's ports and reconnects on any change — if this regresses, that
   check is the place to look.
5. Container tools needed: alsa-utils + systemd (both already installed in claudebox);
   `/dev/snd` and the user D-Bus are shared with the host.
