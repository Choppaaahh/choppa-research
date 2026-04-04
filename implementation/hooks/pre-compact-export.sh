#!/bin/bash
# PreCompact Hook: Auto-export session state + extract reasoning chains before compaction.
# Phase 1: Copy transcript (fast, no API)
# Phase 2: Run insight extraction (async, background process)
#
# Wire as a PreCompact hook in your Claude Code settings.json.
# [PLACEHOLDER] Update paths to match your project structure.

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path')
TRIGGER=$(echo "$INPUT" | jq -r '.trigger')
CWD=$(echo "$INPUT" | jq -r '.cwd')

# [PLACEHOLDER] Update this to your sessions export directory
EXPORT_DIR="$CWD/knowledge/ops/sessions"
# [PLACEHOLDER] Update to your claude memory directory
MEMORY_DIR="$HOME/.claude/projects/YOUR-PROJECT/memory"
TIMESTAMP=$(date +%Y-%m-%d_%H%M)
EXPORT_FILE="$EXPORT_DIR/compact_${TIMESTAMP}_${SESSION_ID:0:8}.jsonl"

mkdir -p "$EXPORT_DIR"

if [ ! -f "$TRANSCRIPT" ]; then
  echo "Transcript not found: $TRANSCRIPT" >&2
  exit 1
fi

# Phase 1: Copy transcript (always, fast)
cp "$TRANSCRIPT" "$EXPORT_FILE"
LINES=$(wc -l < "$TRANSCRIPT")
SIZE=$(du -h "$TRANSCRIPT" | cut -f1)

echo "Session state exported: $EXPORT_FILE ($LINES messages, $SIZE, trigger: $TRIGGER)" >&2

# Phase 2: Extract reasoning chains via Python helper (async — don't block compaction)
# [PLACEHOLDER] Replace with your own insight extraction script if you have one
EXTRACTOR="$CWD/scripts/extract_insights.py"
if [ -f "$EXTRACTOR" ]; then
  # Run in background so we don't block the 30s timeout
  python3 "$EXTRACTOR" --transcript "$TRANSCRIPT" --source "pre-compact" &
  echo "Insight extraction started (background PID $!)" >&2
fi

exit 0
