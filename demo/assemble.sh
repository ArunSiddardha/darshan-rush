#!/bin/bash
# Build the final 1080p demo video from EDIT.txt.  usage: assemble.sh [EDIT.txt] [narration.(wav|m4a|mp3)]
# EDIT.txt lines:  file | in | out | layout | caption        (seconds; '#' comments)
#   layout: full | phone-left-with-caption | side-by-side | title | end     file '-' for title/end; 'a+b' for side-by-side
#   caption: lower-third text (full, side-by-side) or the big text beside the phone; title/end use "Main // sub line".
# Output: demo/darshan-rush-demo.mp4 and demo/contact-sheet.jpg.  No narration given = silent track (a dry run).
set -euo pipefail
D=/Users/arun/hackathon/festive/repo/demo
FF=/opt/homebrew/bin/ffmpeg
EDIT=${1:-$D/EDIT.txt}
NARR=${2:-}
W=$D/work; mkdir -p "$W/seg" "$W/cards"
node "$D/make_cards.cjs" "$EDIT" "$W/cards" >/dev/null
n=0; : > "$W/list.txt"
while IFS='|' read -r file tin tout layout cap; do
  file=$(echo "$file" | xargs); tin=$(echo "$tin" | xargs); tout=$(echo "$tout" | xargs); layout=$(echo "$layout" | xargs)
  [[ -z "$file" || "$file" == \#* ]] && continue
  n=$((n+1)); NN=$(printf %02d $n); card="$W/cards/$NN.png"; seg="$W/seg/$NN.mp4"; dur=$(echo "$tout - $tin" | bc)
  OPTS="-an -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -r 30 -t $dur"
  case "$layout" in
    title|end)
      $FF -y -v error -loop 1 -t "$dur" -i "$card" -vf "fade=t=in:st=0:d=0.4,fade=t=out:st=$(echo "$dur - 0.4" | bc):d=0.4" $OPTS "$seg" ;;
    full)
      $FF -y -v error -ss "$tin" -t "$dur" -i "$D/$file" -loop 1 -i "$card" -filter_complex \
        "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0xF3F1EC,fps=30[v];[v][1:v]overlay=shortest=1" $OPTS "$seg" ;;
    phone-left-with-caption)
      $FF -y -v error -ss "$tin" -t "$dur" -i "$D/$file" -loop 1 -i "$card" -filter_complex \
        "[0:v]scale=-2:960,pad=iw+16:ih+16:8:8:color=0x1A1917,fps=30[p];[1:v][p]overlay=(W-w)/2-560:(H-h)/2:shortest=1" $OPTS "$seg" ;;
    side-by-side)
      a=${file%%+*}; b=${file##*+}
      $FF -y -v error -ss "$tin" -t "$dur" -i "$D/$a" -ss "$tin" -t "$dur" -i "$D/$b" -loop 1 -i "$card" -filter_complex \
        "[0:v]scale=930:800:force_original_aspect_ratio=decrease,fps=30[a];[1:v]scale=930:800:force_original_aspect_ratio=decrease,fps=30[b];[2:v][a]overlay=15:(H-h)/2[x];[x][b]overlay=W-w-15:(H-h)/2:shortest=1" $OPTS "$seg" ;;
    *) echo "unknown layout '$layout' on line $n" >&2; exit 1 ;;
  esac
  echo "file '$seg'" >> "$W/list.txt"
done < "$EDIT"
$FF -y -v error -f concat -safe 0 -i "$W/list.txt" -c copy "$W/video.mp4"
VD=$(/opt/homebrew/bin/ffprobe -v error -show_entries format=duration -of csv=p=0 "$W/video.mp4")
if [[ -n "$NARR" ]]; then
  $FF -y -v error -i "$W/video.mp4" -i "$NARR" -filter_complex "[1:a]aresample=48000,loudnorm=I=-16:TP=-1.5:LRA=11,apad[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -t "$VD" -movflags +faststart "$D/darshan-rush-demo.mp4"
else
  $FF -y -v error -i "$W/video.mp4" -f lavfi -i anullsrc=r=48000:cl=stereo -map 0:v -map 1:a -c:v copy -c:a aac -b:a 128k -t "$VD" -movflags +faststart "$D/darshan-rush-demo.mp4"
  echo "NOTE: no narration given, silent track added"
fi
# contact sheet: one frame every 2 s, 5 columns
SH=$(python3 -c "import math,sys;print(max(1,math.ceil(float(sys.argv[1])/2/5)))" "$VD")
$FF -y -v error -i "$D/darshan-rush-demo.mp4" -vf "fps=1/2,scale=384:-1,tile=5x$SH" -frames:v 1 "$D/contact-sheet.jpg"
/opt/homebrew/bin/ffprobe -v error -show_entries format=duration:stream=codec_name,width,height -of default=nw=1 "$D/darshan-rush-demo.mp4"
echo "done: $D/darshan-rush-demo.mp4  $D/contact-sheet.jpg"
