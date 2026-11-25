#!/usr/bin/env python3
"""Turn a simple cue file into an .ass subtitle file (for Resolve, Premiere, VLC, or ffmpeg builds that have libass).
Input lines:  start | end | text      (seconds like 3.5, or m:ss.s; '#' comments; '\\n' or a second line break inside text)
Styles:  laptop (default, bottom centre, large, soft dark plate)   right (left-aligned in the right column of the phone layout)
Usage:   subtitles.py cues.txt out.ass [--style laptop|right] [--font Anek] [--size 50]
Note: the local ffmpeg has no libass, so compose_frame.sh / split_screen.sh burn subtitles from PNG plates drawn in
Chrome with the same look. Both read the same cue file. To use the .ass with fonts, install the Anek TTFs (the repo ships woff2 only)."""
import argparse, sys

STYLES = {  # alignment 2 = bottom centre, 1 = bottom left (ASS numpad layout)
    "laptop": dict(align=2, ml=160, mr=160, mv=70),
    "right": dict(align=1, ml=770, mr=150, mv=70),
}

def sec(s):
    s = s.strip()
    if ":" in s:
        m, r = s.split(":"); return int(m) * 60 + float(r)
    return float(s)

def ts(t):
    cs = int(round(t * 100)); h, cs = divmod(cs, 360000); m, cs = divmod(cs, 6000); s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cues"); ap.add_argument("out")
    ap.add_argument("--style", default="laptop", choices=STYLES); ap.add_argument("--font", default="Anek"); ap.add_argument("--size", type=int, default=50)
    a = ap.parse_args(); st = STYLES[a.style]; ev = []
    for n, line in enumerate(open(a.cues, encoding="utf8"), 1):
        l = line.strip()
        if not l or l.startswith("#"): continue
        p = l.split("\t") if "\t" in l else l.split("|")
        if len(p) < 3: sys.exit(f"line {n}: need start | end | text")
        text = "|".join(p[2:]).strip().replace("\\n", "\\N")
        ev.append(f"Dialogue: 0,{ts(sec(p[0]))},{ts(sec(p[1]))},Sub,,0,0,0,,{text}")
    # BorderStyle 3 = opaque box; BackColour &HE0 alpha = soft dark plate; Outline is the plate padding
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{a.font},{a.size},&H00FFFFFF,&H00FFFFFF,&H301E1111,&H301E1111,0,0,0,0,100,100,0,0,3,16,0,{st['align']},{st['ml']},{st['mr']},{st['mv']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    open(a.out, "w", encoding="utf8").write(hdr + "\n".join(ev) + "\n")
    print(f"{a.out}: {len(ev)} cues")

main()
