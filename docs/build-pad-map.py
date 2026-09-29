#!/usr/bin/env python3
"""Build docs/pad-map.html from docs/pad-map.src.html.

The page's own content lives in the .src file. The shared pieces are pasted in
unchanged from ~/.claude: the AI-disclosure style and script blocks and the
bottom-bar CSS (AI-DISCLOSURE.md), and the canonical editor body
(ARTIFACT-EDITOR.js). The disclosure JSON comes from docs/pad-map.disclosure.json.
"""

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.expanduser("~/.claude")


def fence_after(text, marker, lang):
    i = text.index(marker)
    m = re.compile(r"```" + lang + r"\n(.*?)\n```", re.S).search(text, i)
    return m.group(1)


def main():
    disc_md = open(os.path.join(KIT, "AI-DISCLOSURE.md")).read()
    dw_style = fence_after(disc_md, "The style block, before the host:", "html")
    bottom_bar = fence_after(disc_md, "The bottom-bar block, pasted verbatim", "css")
    dw_script = fence_after(disc_md, "The script, last in the file:", "html")
    editor = open(os.path.join(KIT, "ARTIFACT-EDITOR.js")).read().rstrip("\n")
    disclosure = json.load(open(os.path.join(HERE, "pad-map.disclosure.json")))

    src = open(os.path.join(HERE, "pad-map.src.html")).read()
    for key, val in (
        ("/*__BOTTOM_BAR_BLOCK__*/", bottom_bar),
        ("<!--__DW_STYLE__-->", dw_style),
        ("/*__CANONICAL_EDITOR__*/", editor),
        ("__DISCLOSURE_JSON__", json.dumps(disclosure, indent=2, ensure_ascii=False).replace("<", "\\u003c")),
        ("<!--__DW_SCRIPT__-->", dw_script),
    ):
        assert src.count(key) == 1, key
        src = src.replace(key, val)
    out = os.path.join(HERE, "pad-map.html")
    open(out, "w").write(src)
    print(f"wrote {out} ({len(src)} bytes)")


if __name__ == "__main__":
    main()
