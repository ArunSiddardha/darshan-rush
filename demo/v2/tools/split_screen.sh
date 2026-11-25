#!/bin/bash
# Two sources side by side with a caption. usage:
#   split_screen.sh --src left.mp4 --src2 right.mp4 --out out.mp4 --caption "A person approves. Two flags flip." [--left-label NudgeBee --right-label Flagsmith]
#                   [--subs cues.txt] [--dur 6] [--ss 0] [--sponsor ..] [--png still.png]
exec /opt/homebrew/bin/node "$(dirname "$0")/compose.cjs" split "$@"
