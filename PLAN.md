# padSpace — reproduction plan

Everything needed to recreate the exact behavior of this setup from this
directory alone. Compressed from the build session (full transcript in
`logs/session-2026-07-14.jsonl`).

## Target behavior

Launchpad Mini MK3 as a desk controller for KDE Plasma:

1. **Workspace grids** — top two pad rows are two side-by-side 2×4 grids,
   fixed per display (left = screen 0, right = screen 1; upper row =
   desktops 1–4, lower = 5–8). Press a pad → that display switches to that
   desktop; hold a pad ≥ ~0.55 s to also MOVE the window that was active at
   press time to that pad's desktop/screen (hardware sends fixed velocity 127,
   so hold substitutes for a "hard hit"). White pad = that screen's current
   desktop; dim = has windows; unlit = empty workspace. Right grid dark when
   only one display is connected.
2. **App markers** — workspaces holding VS Code glow red, Slack blue, a
   browser whose active tab is "Vineet Work Log" (Notion) green, and
   worklog+Slack together cyan — per screen (a window only marks the grid of
   the display it is on). Multiple marked workspaces per app supported.
   Updates are event-driven (~10 ms; persistent KWin signal listener), with a
   5 s poll as fallback. Windows demanding attention (alerts) hardware-flash
   their workspace pad between bright/dim of its current color.
3. **Command pads** — any other pad/round button can run a shell command via
   `~/.config/padspace/bindings.conf` (hot-reloaded, `<button> [@color] = cmd`).
   Current binding: pad 18 → "science, bitch!" TTS sample.
4. **Session gate** (round button row 1 col 5, cc95) — arms/disarms bottom-row
   command pads. Disarmed on every start. Purple = armed.
5. **Drum mode** (round button row 1 col 6, cc96) — bottom two rows become a
   16-pad EDM kit (3 kicks + sub-drop + snare/clap/hats/crash/toms/percussion),
   preloaded into PipeWire for low-latency overlapping hits. Amber = on.
   Mutually exclusive with the Session gate.
6. **Numpad mode** (Keys button, cc97) — bottom-left 3×4 pads become a
   digit pad (numpad layout, wide zero across the bottom three pads), typing
   via ydotoold; digit pads breathe green at 1/N Hz each, zero steady (0 Hz).
   Exclusive with Session gate and Drum mode.
7. **Arrow buttons** (round row 1 cols 1–4, cc91–94, printed ↑↓←→) — send
   real keyboard arrow-key events to the focused window via a user-level
   ydotoold (virtual uinput keyboard).
8. **Skill launcher** (User button, cc98) — bottom two rows launch Claude
   Code skills (bottom, amber) and Hermes skills (above, blue) in konsole
   windows, configured by symlinks in `~/.ctrl/claude/` and `~/.ctrl/hermes/`
   (re-read at each toggle-on; `N-` prefixes order the pads).
9. On stop/music use, the pad reverts to normal standalone mode.

## Requirements

- Hardware: Novation Launchpad Mini MK3 (USB); second display optional.
- For the skill-launcher rows: Claude Code (in the claudebox distrobox) and
  the Hermes agent (`~/.local/bin/hermes`); recreate `~/.ctrl` from
  `config/ctrl-seed.txt` (plain `ln -s` lines) — install.sh does NOT manage it.
- OS: Bazzite / Fedora Kinoite with **Plasma 6.7+** on Wayland
  (per-screen virtual desktops are a 6.7 feature — hard requirement).
- Tools (all preinstalled on Bazzite): `amidi`, `aseqdump`, `busctl`,
  `journalctl`, `python3`, `pactl`, `paplay`, `kwriteconfig6`, `espeak-ng`,
  `ydotool`/`ydotoold` (arrow keys; needs the seated-user ACL on `/dev/uinput`,
  standard on Bazzite).

## Reproduce

```sh
cp -r padSpace ~/projects/padSpace   # or clone; any location works
cd ~/projects/padSpace
./install.sh
```

`install.sh` is idempotent and does, in order:

1. Dependency check (fails loudly if a tool is missing).
2. KWin version check (warns below 6.7).
3. kwinrc: `[Windows] PerOutputVirtualDesktops=true`, `Number=8`,
   then live-reconfigures KWin over D-Bus.
4. Installs `bin/launchpad-workspaces` → `~/.local/bin/` plus two systemd user
   units → `~/.config/systemd/user/`: the daemon (tied to
   graphical-session.target) and `ydotoold.service` (virtual keyboard for the
   arrow buttons). Both enabled and (re)started.
5. Installs `config/bindings.conf` → `~/.config/padspace/` (only if absent —
   personal bindings are never clobbered).
6. Copies `assets/*` (soundboard WAVs) → `~/.local/share/padspace/` (no
   overwrite). Regenerable via `tools/make-soundboard.sh` if assets are lost.
7. Synthesizes the drum kit (`tools/make-drumkit.py` → 16 WAVs in
   `~/.local/share/padspace/drumkit/`) if not already present.
8. Enables + restarts the service via the systemd D-Bus API (works from
   toolbox containers where `systemctl --user start` refuses).

No hardware IDs or machine specifics are baked in: the daemon discovers the
Launchpad by name (any ALSA card number), screens by KWin's screenOrder, and
survives unplug/replug.

## Verify

1. `systemctl --user is-active launchpad-workspaces` → `active`.
2. Top-left pad of each grid lights green (both screens on desktop 1 → both
   grids' pad 1 green).
3. Press a right-grid pad → only the second display switches.
4. Open VS Code somewhere → that workspace's pad turns red within ~3 s, on the
   grid of the display it's on. Slack → blue.
5. Press Session (cc95) → pad 18 lights purple; press pad 18 → TTS plays;
   press Session again → dark and inert.
6. Press Drums (cc96) → bottom two rows light as the kit; hits are
   low-latency and overlap; press again → back to normal.
7. Hold a workspace pad ≥ ~0.55 s → the window that was focused at press time
   moves to that pad's desktop and display (and you're already there).
8. Press the four top-left round buttons (↑↓←→) in a text field → cursor moves.
9. Mash several workspace pads rapidly → each lights once, no flip-backs.
10. `journalctl --user -u launchpad-workspaces -f` shows every press and the
   `PADSPACE-STATE T=… S0=… S1=… W…= M…=` sync stream.

## Layout of this directory

| Path | Role |
|---|---|
| `install.sh` | one-shot bootstrap / refresh (start here) |
| `bin/launchpad-workspaces` | the daemon (python3 stdlib only) — canonical copy of `~/.local/bin/…` |
| `systemd/launchpad-workspaces.service` | daemon user unit |
| `systemd/ydotoold.service` | virtual-keyboard daemon for arrow buttons |
| `config/bindings.conf` | command-pad bindings (installed once, then user-owned) |
| `assets/` | soundboard WAVs referenced by bindings |
| `tools/make-drumkit.py` | synthesizes the 16-pad EDM kit (pure stdlib DSP) |
| `tools/make-soundboard.sh` | regenerates TTS soundboard samples |
| `skill/SKILL.md` | Claude Code `/padspace` skill (installed to `~/.claude/skills/padspace/`) |
| `README.md` | full mechanism documentation + verified device/KWin API facts |
| `logs/session-2026-07-14.jsonl` | complete build-session transcript |

## Tuning knobs (all in `bin/launchpad-workspaces`)

- `GRID_S0` / `GRID_S1` — workspace grid geometry (swap them if "first
  display" comes out wrong on new hardware).
- `MARKERS` — app-marker rules: `(js_regex_on_window_class, led_color)`.
- `DRUM_PADS` — pad → (sample name, color); WAV filenames in
  `~/.local/share/padspace/drumkit/` (drop in your own to upgrade sounds).
- `TOGGLE_CC` / `DRUMS_CC` / `GATED_NOTES` — mode buttons and gated row.
- `ARROW_CCS` — arrow buttons → Linux input keycodes (103/108/105/106).
- `MARKER_COMBOS` — blend colors when one workspace matches several rules.
- `HOLD_MOVE_SECS` — hold threshold for move-window-with-me (0.55 s).
- `POLL_SECS` — reporter safety-net poll (5 s; real updates are event-driven).

## Hard-won facts (cost real debugging — do not relearn)

Full detail in `README.md` and `skill/SKILL.md`; headlines:

1. kwinrc: `PerOutputVirtualDesktops` lives in **[Windows]**, not [Desktops]
   (`Number` does live in [Desktops]).
2. `workspace.sendClientToScreen` is **unreliable** under per-output desktops —
   move windows across displays by setting `frameGeometry` into the target
   output's rect instead.
3. KWin `Output` object identity (`===`) across API calls is meaningless —
   always compare `.name`.
4. KWin script `print()` goes to a disabled log category — use
   `console.error`, read from the plasma-kwin_wayland journal.
5. `setCurrentDesktopForScreen(desktop, screen)` — desktop argument FIRST.
6. Launchpad Mini MK3 pads have **no velocity sensing** (always 127) — use
   hold duration for pressure-like gestures.
7. Optimistic LED updates need the `T=` staleness guard: drop any state report
   generated before the last local action, or late reports flip LEDs back.
8. Inside toolbox containers `systemctl --user start` fails — use the systemd
   D-Bus API (`busctl … StartUnit/RestartUnit`); `kwriteconfig6` may be absent
   — install.sh has a python kwinrc patcher fallback.
9. Screen order on this machine: HDMI-A-1 = index 0 (left grid), eDP-1 =
   index 1 (right grid) — from `workspace.screenOrder`.
- LED palette reference and all protocol details: `README.md` §Facts.
