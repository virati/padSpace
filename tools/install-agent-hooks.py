#!/usr/bin/env python3
"""Register padspace-agent-hook in ~/.claude/settings.json. Idempotent.

Adds one hook entry per event and leaves every other key and hook alone.
Pass --remove to take the entries back out.
"""

import json
import os
import sys

SETTINGS = os.environ.get("PADSPACE_CLAUDE_SETTINGS", os.path.expanduser("~/.claude/settings.json"))
HOOK = os.path.expanduser("~/.local/bin/padspace-agent-hook")
EVENTS = {                       # event -> matcher (None = no matcher key)
    "Stop": None,
    "StopFailure": None,
    "Notification": None,
    "UserPromptSubmit": None,
    "PostToolUse": "*",
}


def ours(group):
    return any(h.get("command") == HOOK for h in group.get("hooks", []))


def main():
    remove = "--remove" in sys.argv[1:]
    with open(SETTINGS) as f:
        settings = json.load(f)
    hooks = settings.setdefault("hooks", {})
    changed = []
    for event, matcher in EVENTS.items():
        groups = hooks.get(event, [])
        kept = [g for g in groups if not ours(g)]
        if not remove:
            entry = {"hooks": [{"type": "command", "command": HOOK, "timeout": 5}]}
            if matcher is not None:
                entry = {"matcher": matcher, **entry}
            kept.append(entry)
        if kept != groups:
            changed.append(event)
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)
    if not hooks:
        settings.pop("hooks")
    if not changed:
        print("padspace agent hooks: already " + ("absent" if remove else "registered"))
        return
    tmp = SETTINGS + ".padspace.tmp"
    with open(tmp, "w") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")
    os.replace(tmp, SETTINGS)
    print(f"padspace agent hooks: {'removed from' if remove else 'registered for'} {', '.join(changed)}")


if __name__ == "__main__":
    main()
