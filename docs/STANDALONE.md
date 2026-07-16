# padSpace as a standalone app for KDE / Bazzite — planning

Goal: turn the personal daemon into an installable, configurable app any
KDE Plasma 6.7+ user (Bazzite first) can use with a Launchpad, without
editing Python.

## What we have (and what generalizes)

The prototype proves the whole mechanism stack:

| Capability | Current implementation | Standalone-ready? |
|---|---|---|
| MIDI I/O | subprocess `amidi`/`aseqdump` | replace with `alsa-midi`/`mido` lib |
| Per-screen desktop control | one-shot KWin JS via `busctl` | keep (only API that exists) |
| State back-channel | `console.error` → journald → `journalctl -f` | replace (fragile, biggest hack) |
| LED engine | palette + RGB SysEx, optimistic + T-guard | keep, formalize as state machine |
| Modes (grids/drums/numpad/launcher/soundboard) | hardcoded constants | move to config schema |
| Key injection | ydotoold user service | keep; document uinput ACL needs |
| Install | install.sh | replace with packaging (below) |

## Architecture decisions to make

1. **Language/runtime.** Options:
   - Stay Python (fast iteration, `mido`+`python-rtmidi`, `dbus-fast` for
     async D-Bus; ship as pip/pipx or bundle in Flatpak).
   - Rust or C++/Qt (native KDE citizenship, KConfig/KCM integration, harder).
   - Recommendation to evaluate: Python + dbus-fast async rewrite first;
     port later only if perf or packaging demands it.

2. **Kill the journald back-channel.** The KWin script should push state
   directly to the daemon over D-Bus: daemon owns `org.padspace.Daemon1`,
   KWin script calls `callDBus("org.padspace.Daemon1", "/", ..., "State", json)`.
   `callDBus` is fire-and-forget from KWin scripts — this works and removes
   journalctl, the T-guard race source, and log spam in one move.
   (Requires the daemon to own a bus name — trivial with dbus-fast.)

3. **Persistent KWin script lifecycle.** Install the event/action script as a
   proper KWin script package (`kpackagetool6 --type KWin/Script`) instead of
   loading JS files from ~/.local/share at runtime. Actions (switch/move)
   could then also flow daemon→script via a script-registered D-Bus…
   KWin scripts can't own bus names — keep one-shot action scripts, or have
   the persistent script poll a daemon property. Decide after prototyping.

4. **Configuration.**
   - Single TOML/INI at `~/.config/padspace/padspace.conf`: grids, marker
     rules (class/caption regex + color + combos), mode buttons, drum kit
     paths, launcher rows, hold threshold, colors.
   - Live-reload (the bindings.conf hot-reload pattern, generalized).
   - Later: a small Plasma config UI (KCM or standalone QML window) that
     edits the same file. Not required for v1.

5. **Device layer.**
   - Hotplug via ALSA sequencer announce port (we already reconnect-loop;
     do it event-driven).
   - Device profiles: Launchpad Mini MK3 first; X/Pro MK3 add velocity
     (velocity-gated actions become real). Abstract note/CC layout + LED
     protocol per profile.

6. **Packaging for Bazzite/KDE.**
   - v1: COPR RPM (`padspace` + systemd user units + udev note) — Bazzite
     users `rpm-ostree install` or it rides in a custom image; also works on
     any Fedora KDE.
   - Also ship a `ujust padspace-setup` style recipe (Bazzite convention).
   - Flatpak is a poor fit (raw ALSA + uinput + KWin scripting = heavy
     sandbox punches); document why not.
   - Depend on ydotool packaging or embed our own uinput writer (python-
     uinput via /dev/uinput directly — we already have the ACL story).

7. **Security/permissions story.** uinput access (Bazzite grants seat ACL;
   vanilla Fedora needs an input-group udev rule we must ship + document),
   KWin scripting (user session, fine), no root anywhere.

## Milestones

- **M0 — carve out**: split the monolith into modules (midi, kwin, leds,
  modes, config) in `src/padspace/`, keep behavior identical, add tests for
  the pure parts (state parsing, marker resolution, grid math).
- **M1 — transport swap**: dbus-fast daemon owning org.padspace.Daemon1;
  KWin script pushes state via callDBus; delete journal follower + T-guard.
- **M2 — config file**: everything now in constants becomes padspace.conf;
  live reload; ship migration from the prototype's layout.
- **M3 — native MIDI**: mido/python-rtmidi replaces amidi/aseqdump
  subprocesses; event-driven hotplug.
- **M4 — packaging**: RPM spec + COPR, systemd user units, udev rule for
  non-Bazzite, README quickstart. First releasable version.
- **M5 — polish**: device profiles (Launchpad X velocity), config UI,
  Plasma System Tray indicator, per-mode LED themes.

## Open questions

- Does `callDBus` from KWin scripts allow arbitrary destinations under the
  KWin sandbox in 6.7? (Prototype in M1 first — if blocked, fall back to a
  UNIX socket the script can't reach → keep journald path as plan B.)
- Naming: "padSpace" availability as RPM/COPR name.
- License (MIT/GPL — KWin script interop suggests GPL-friendly; decide).
- How much of the personal config (markers for Slack/Notion, .ctrl launcher)
  becomes example config vs. default behavior.
