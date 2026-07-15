#!/usr/bin/env bash
# padSpace bootstrap — sets up the Launchpad Mini MK3 workspace switcher on a
# fresh machine (Bazzite/Fedora Kinoite, Plasma 6.7+, Wayland) or refreshes an
# existing install from this repo. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

echo "== padSpace install =="

# ---- dependency check (all ship with Bazzite; nothing to install on the host)
missing=0
for bin in amidi aseqdump busctl journalctl python3; do
  command -v "$bin" >/dev/null || { echo "MISSING: $bin"; missing=1; }
done
[ "$missing" = 1 ] && { echo "install alsa-utils/systemd first (on Bazzite these are preinstalled — are you in a container without them?)"; exit 1; }

# ---- Plasma 6.7+ per-screen virtual desktops (required for the two-row model)
kwin_ver=$(busctl --user call org.kde.KWin /KWin org.kde.KWin supportInformation 2>/dev/null \
  | grep -oP 'KWin version: \K[0-9]+\.[0-9]+' | head -1 || true)
if [ -n "$kwin_ver" ]; then
  maj=${kwin_ver%%.*}; min=${kwin_ver#*.}; min=${min%%.*}
  if [ "$maj" -lt 6 ] || { [ "$maj" = 6 ] && [ "$min" -lt 7 ]; }; then
    echo "WARNING: KWin $kwin_ver < 6.7 — per-screen desktops unavailable; second row will not work"
  fi
else
  echo "WARNING: could not query KWin (is a Plasma session running?)"
fi

if command -v kwriteconfig6 >/dev/null; then
  kwriteconfig6 --file kwinrc --group Windows --key PerOutputVirtualDesktops true
  kwriteconfig6 --file kwinrc --group Desktops --key Number 8
  busctl --user call org.kde.KWin /KWin org.kde.KWin reconfigure 2>/dev/null || true
  echo "kwinrc: [Windows] PerOutputVirtualDesktops=true, [Desktops] Number=8 (KWin reconfigured)"
else
  # container-safe fallback: patch kwinrc directly (line-based; kwinrc is not
  # strict INI, so no configparser)
  python3 - <<'PYEOF'
import os, re
path = os.path.expanduser("~/.config/kwinrc")
lines = open(path).read().splitlines() if os.path.exists(path) else []

def set_key(lines, section, key, value):
    out, in_sec, done, seen = [], False, False, False
    for ln in lines:
        if ln.startswith("["):
            if in_sec and not done:
                out.append(f"{key}={value}")
                done = True
            in_sec = ln.strip() == f"[{section}]"
            seen = seen or in_sec
            out.append(ln)
            continue
        if in_sec and re.match(re.escape(key) + r"\s*=", ln):
            if not done:
                out.append(f"{key}={value}")
                done = True
            continue
        out.append(ln)
    if in_sec and not done:
        out.append(f"{key}={value}")
        done = True
    if not seen:
        out += [f"[{section}]", f"{key}={value}"]
    return out

lines = set_key(lines, "Windows", "PerOutputVirtualDesktops", "true")
lines = set_key(lines, "Desktops", "Number", "8")
open(path, "w").write("\n".join(lines) + "\n")
print("kwinrc: patched via fallback (kwriteconfig6 not in PATH)")
PYEOF
  busctl --user call org.kde.KWin /KWin org.kde.KWin reconfigure 2>/dev/null || true
fi

# ---- daemon + units (ydotoold provides arrow-key injection for cc91-94)
install -Dm755 bin/launchpad-workspaces "$HOME/.local/bin/launchpad-workspaces"
install -Dm644 systemd/launchpad-workspaces.service \
  "$HOME/.config/systemd/user/launchpad-workspaces.service"
install -Dm644 systemd/ydotoold.service \
  "$HOME/.config/systemd/user/ydotoold.service"

# ---- command bindings starter config (never overwrite an existing one)
if [ ! -e "$HOME/.config/padspace/bindings.conf" ]; then
  install -Dm644 config/bindings.conf "$HOME/.config/padspace/bindings.conf"
  echo "installed starter ~/.config/padspace/bindings.conf"
fi

# ---- soundboard samples referenced by bindings (never overwritten)
if [ -d assets ]; then
  mkdir -p "$HOME/.local/share/padspace"
  cp -n assets/* "$HOME/.local/share/padspace/" 2>/dev/null || true
fi

# ---- synthesize the drum kit if not present (pure-stdlib python, ~5 s)
if [ ! -e "$HOME/.local/share/padspace/drumkit/kick-punch.wav" ]; then
  python3 tools/make-drumkit.py
fi

# ---- Claude Code skill (optional but free)
install -Dm644 skill/SKILL.md "$HOME/.claude/skills/padspace/SKILL.md"

# ---- enable + (re)start; 'systemctl --user start' fails inside toolbox
#      containers, so drive systemd over D-Bus, which works everywhere.
systemctl --user daemon-reload
systemctl --user enable launchpad-workspaces.service ydotoold.service
busctl --user call org.freedesktop.systemd1 /org/freedesktop/systemd1 \
  org.freedesktop.systemd1.Manager RestartUnit ss ydotoold.service replace
busctl --user call org.freedesktop.systemd1 /org/freedesktop/systemd1 \
  org.freedesktop.systemd1.Manager RestartUnit ss launchpad-workspaces.service replace

echo "== done. plug in the Launchpad if it isn't already =="
echo "watch: journalctl --user -u launchpad-workspaces -f"
