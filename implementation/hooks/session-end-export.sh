#!/bin/bash
# SessionEnd Hook: Transcript export + auto-journal
# Also generates session stats summary.
#
# Wire as a Stop hook in your Claude Code settings.json.
# [PLACEHOLDER] Update paths to match your project structure.

INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path')
REASON=$(echo "$INPUT" | jq -r '.reason')
CWD=$(echo "$INPUT" | jq -r '.cwd')

# [PLACEHOLDER] Update these paths to your project structure
EXPORT_DIR="$CWD/knowledge/ops/sessions"
# [PLACEHOLDER] Update to your claude memory directory
MEMORY_DIR="$HOME/.claude/projects/YOUR-PROJECT/memory"
TIMESTAMP=$(date +%Y-%m-%d_%H%M)
EXPORT_FILE="$EXPORT_DIR/end_${TIMESTAMP}_${SESSION_ID:0:8}.jsonl"
HOOKS_DIR="$CWD/.claude/hooks"

mkdir -p "$EXPORT_DIR"

if [ -f "$TRANSCRIPT" ]; then
  # 1. Copy transcript
  cp "$TRANSCRIPT" "$EXPORT_FILE"
  LINES=$(wc -l < "$TRANSCRIPT")

  # 2. Generate auto-journal stats
  AUTO_JOURNAL="$MEMORY_DIR/auto-journal-latest.md"
  if [ -f "$HOOKS_DIR/lib/extract-session-stats.sh" ]; then
    bash "$HOOKS_DIR/lib/extract-session-stats.sh" "$TRANSCRIPT" "$AUTO_JOURNAL"
    # Append session metadata
    echo "" >> "$AUTO_JOURNAL"
    echo "### Metadata" >> "$AUTO_JOURNAL"
    echo "- Session ID: ${SESSION_ID:0:8}" >> "$AUTO_JOURNAL"
    echo "- End reason: $REASON" >> "$AUTO_JOURNAL"
    echo "- Export: $EXPORT_FILE" >> "$AUTO_JOURNAL"
  fi

  # 3. Auto-capture: append structured breadcrumbs to scratchpad
  if [ -f "$HOOKS_DIR/lib/auto-capture.sh" ]; then
    bash "$HOOKS_DIR/lib/auto-capture.sh" "$TRANSCRIPT" "$MEMORY_DIR/scratchpad.md" 2>&1 || true
  fi

  # 4. Auto-append to session log
  # [PLACEHOLDER] Update this path to your session log
  SESSION_LOG="$CWD/knowledge/ops/session-log.md"
  if [ -f "$SESSION_LOG" ]; then
    DATE=$(date '+%Y-%m-%d %H:%M')
    EDITS=$(grep -c '"name":"Edit"\|"name":"Write"' "$TRANSCRIPT" 2>/dev/null || echo 0)
    echo "- **$DATE** | ${LINES}msg ${EDITS}edits | reason: $REASON | ${SESSION_ID:0:8}" >> "$SESSION_LOG"
  fi

  echo "Session export: $EXPORT_FILE ($LINES msgs, reason: $REASON)" >&2
  exit 0
else
  echo "No transcript to export" >&2
  exit 1
fi
