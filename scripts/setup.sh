#!/usr/bin/env bash
# One-time environment setup. Usage: setup.sh <work_dir>
# Creates <work_dir>/.venv with all deps, links ffmpeg, downloads the RVM matting model.
set -e
WORK="${1:-work}"
mkdir -p "$WORK/models"
cd "$WORK"
if [ ! -x .venv/bin/python ]; then
  uv venv -p 3.11 .venv >/dev/null 2>&1 || python3 -m venv .venv
fi
PIP="uv pip install -p .venv/bin/python"
command -v uv >/dev/null || PIP=".venv/bin/pip install"
$PIP -q imageio-ffmpeg faster-whisper numpy pillow torch torchvision skia-python
FF=$(.venv/bin/python -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
ln -sf "$FF" ./ffmpeg
if [ ! -f models/rvm_mobilenetv3.pth ]; then
  curl -sL -o models/rvm_mobilenetv3.pth https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3.pth
  curl -sL -o models/rvm.zip https://github.com/PeterL1n/RobustVideoMatting/archive/refs/heads/master.zip
  (cd models && unzip -qo rvm.zip)
fi
echo "setup ok: $(pwd)"
