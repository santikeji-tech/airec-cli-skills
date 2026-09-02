#!/usr/bin/env bash
# meeting-notes 技能安装脚本 —— 复制脚本到本地 bin 并验证可用
# 用法: bash install.sh
set -e

DEST="${MEETING_NOTES_DEST:-$HOME/bin}"
mkdir -p "$DEST"
cp "$(dirname "$0")/scripts/meeting_notes.py" "$DEST/meeting_notes"
chmod +x "$DEST/meeting_notes"

echo "✓ meeting-notes 已安装到 $DEST/meeting_notes"
echo "运行: meeting_notes --help"
