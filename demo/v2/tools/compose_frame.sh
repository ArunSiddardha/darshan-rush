#!/bin/bash
# Phone left, caption right. usage:
#   compose_frame.sh --src phone.mp4|png --out out.mp4 [--caption "One tap. Then she *just talks.*"] [--sponsor sarvam|nudgebee|flagsmith|all]
#                    [--subs cues.txt] [--dur 6] [--ss 0] [--fade 0.3] [--png still.png --png-at 2.5]
# cues.txt lines:  start | end | English subtitle   (seconds or m:ss.s, relative to the clip start; '#' comments)
exec /opt/homebrew/bin/node "$(dirname "$0")/compose.cjs" phone "$@"
