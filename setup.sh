#!/usr/bin/env bash
# Installs the reel engine dependencies in a fresh cloud session.
set -e
pip install -q --break-system-packages kokoro-onnx soundfile skia-python scipy numpy 2>&1 | grep -v -i warning || true
mkdir -p ~/.cache/ludogic-reels
U=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -s ~/.cache/ludogic-reels/$f ] || curl -sSL -o ~/.cache/ludogic-reels/$f $U/$f
done
command -v ffmpeg >/dev/null || { echo "ffmpeg missing"; exit 1; }
test -f /usr/share/fonts/opentype/inter/InterDisplay-Black.otf || echo "WARNING: Inter Display font missing"
python3 -c "import kokoro_onnx, skia, scipy, soundfile; print('reel engine ready')"
