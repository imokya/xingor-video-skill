#!/bin/bash
# 并行渲染：整片切成 N 段同时导出（每段一个浏览器），再用 concat 无损拼接，最后核对帧数。
#   PAGE=film.html ./render_par.sh out.mp4 [N=4]
# 165 s / 60 fps / 1080×1440 在 M 系列芯片上：单进程 ≈ 8 min，N=4 ≈ 1 min 50 s。
set -e
HERE=$(cd "$(dirname "$0")" && pwd); OUT=$1; N=${2:-4}; FPS=${FPS:-60}
TOTAL=$(node "$HERE/render_film.mjs" --total | tail -1)
TMP=$(mktemp -d); STEP=$(( (TOTAL + N - 1) / N ))
for i in $(seq 0 $((N-1))); do
  A=$(python3 -c "print($i*$STEP/$FPS)"); B=$(python3 -c "print(min($TOTAL,($i+1)*$STEP)/$FPS)")
  node "$HERE/render_film.mjs" "$TMP/p$i.mp4" "$A" "$B" > "$TMP/log$i.txt" 2>&1 &
done
wait
for i in $(seq 0 $((N-1))); do echo "file '$TMP/p$i.mp4'"; done > "$TMP/list.txt"
ffmpeg -v error -y -f concat -safe 0 -i "$TMP/list.txt" -c copy "$OUT"
GOT=$(ffprobe -v error -count_packets -select_streams v -show_entries stream=nb_read_packets -of default=nw=1:nk=1 "$OUT" | tr -dc 0-9)
[ "$GOT" = "$TOTAL" ] && echo "done $OUT ($GOT frames)" || { echo "frame count $GOT != $TOTAL — see $TMP/log*.txt"; exit 1; }
