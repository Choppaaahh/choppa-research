#!/bin/bash
# SessionStart Hook: Scaffold fidelity probe
# Self-scoring scaffold health with metrics tracking, drift detection,
# decision log awareness, and scaffold snapshots.
#
# Wire as a SessionStart hook in your Claude Code settings.json.
# [PLACEHOLDER] Update paths below to match your project structure.
# Timeout: 10s

CWD=$(echo "$(cat)" | jq -r '.cwd')
# [PLACEHOLDER] Update this to your claude memory directory path
MEMORY_DIR="$HOME/.claude/projects/YOUR-PROJECT/memory"
NOTES_DIR="$CWD/knowledge/notes"
SESSION_DIR="$CWD/knowledge/ops/sessions"
HOOKS_DIR="$CWD/.claude/hooks"
NOW=$(date +%s)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S")

CRITICALS=()
WARNINGS=()
ISSUES=()
STATS=()

# --- Helper: file age in days ---
file_age_days() {
  local mtime
  mtime=$(stat -f %m "$1" 2>/dev/null) || return 1
  echo $(( (NOW - mtime) / 86400 ))
}

# --- 1. MEMORY.md ---
MEMORY_LINES=0
MEMORY_AGE=0
if [ -f "$MEMORY_DIR/MEMORY.md" ]; then
  MEMORY_AGE=$(file_age_days "$MEMORY_DIR/MEMORY.md")
  MEMORY_LINES=$(wc -l < "$MEMORY_DIR/MEMORY.md" | tr -d ' ')
  STATS+=("MEMORY.md: ${MEMORY_LINES} lines, ${MEMORY_AGE}d old")
  if [ "$MEMORY_LINES" -ge 180 ]; then
    CRITICALS+=("MEMORY.md is ${MEMORY_LINES} lines — TRUNCATION IMMINENT (limit ~200). Prune NOW.")
  elif [ "$MEMORY_LINES" -ge 160 ]; then
    WARNINGS+=("MEMORY.md is ${MEMORY_LINES} lines — approaching truncation. Consider pruning.")
  fi
  if [ "$MEMORY_AGE" -ge 3 ]; then
    WARNINGS+=("MEMORY.md not modified in ${MEMORY_AGE} days — may be drifting.")
  fi
else
  CRITICALS+=("MEMORY.md MISSING")
fi

# --- 2. journal.md ---
JOURNAL_AGE=0
if [ -f "$MEMORY_DIR/journal.md" ]; then
  JOURNAL_AGE=$(file_age_days "$MEMORY_DIR/journal.md")
  STATS+=("journal.md: ${JOURNAL_AGE}d old")
  if [ "$JOURNAL_AGE" -ge 2 ]; then
    WARNINGS+=("journal.md not updated in ${JOURNAL_AGE} days — rehydration point may be stale.")
  fi
else
  ISSUES+=("journal.md MISSING")
  JOURNAL_AGE=-1
fi

# --- 3. scratchpad.md ---
SCRATCH_LINES=0
if [ -f "$MEMORY_DIR/scratchpad.md" ]; then
  SCRATCH_LINES=$(wc -l < "$MEMORY_DIR/scratchpad.md" | tr -d ' ')
  STATS+=("scratchpad.md: ${SCRATCH_LINES} lines")
  if [ "$SCRATCH_LINES" -gt 100 ]; then
    WARNINGS+=("scratchpad.md is ${SCRATCH_LINES} lines — consider archiving")
  fi
else
  ISSUES+=("scratchpad.md MISSING")
fi

# --- 4. Vault health ---
NOTE_COUNT=0
if [ -d "$NOTES_DIR" ]; then
  NOTE_COUNT=$(find "$NOTES_DIR" -name "*.md" -not -path "*/archived/*" | wc -l | tr -d ' ')
  STATS+=("vault: ${NOTE_COUNT} notes")
else
  ISSUES+=("vault directory MISSING")
fi

# --- 5. Transcript backups ---
EXPORT_COUNT=0
if [ -d "$SESSION_DIR" ]; then
  EXPORT_COUNT=$(find "$SESSION_DIR" -name "*.jsonl" -mtime -3 | wc -l | tr -d ' ')
  STATS+=("recent transcripts: ${EXPORT_COUNT}")
fi

# --- 6. Decision log ---
DECISIONS_FILE="$MEMORY_DIR/decisions.jsonl"
DECISIONS_COUNT=0
if [ -f "$DECISIONS_FILE" ]; then
  DECISIONS_COUNT=$(wc -l < "$DECISIONS_FILE" | tr -d ' ')
  STATS+=("decisions logged: ${DECISIONS_COUNT}")
else
  touch "$DECISIONS_FILE" 2>/dev/null
  STATS+=("decisions: initialized (empty)")
fi

# --- 7. Metrics time series ---
METRICS_FILE="$MEMORY_DIR/scaffold-metrics.jsonl"
[ ! -f "$METRICS_FILE" ] && touch "$METRICS_FILE" 2>/dev/null
python3 -c "
import json
metrics = {
    'timestamp': '$TIMESTAMP',
    'memory_lines': $MEMORY_LINES,
    'journal_age_days': $JOURNAL_AGE,
    'scratchpad_lines': $SCRATCH_LINES,
    'vault_notes': $NOTE_COUNT,
    'decisions_logged': $DECISIONS_COUNT,
    'transcript_backups': $EXPORT_COUNT
}
print(json.dumps(metrics))
" >> "$METRICS_FILE" 2>/dev/null

# --- 8. Scaffold snapshot + diff ---
if [ -f "$HOOKS_DIR/lib/scaffold-snapshot.sh" ]; then
  SNAPSHOT_OUTPUT=$(bash "$HOOKS_DIR/lib/scaffold-snapshot.sh" stdout 2>/dev/null)
fi

# --- 9. Auto-journal from last session ---
AUTO_JOURNAL="$MEMORY_DIR/auto-journal-latest.md"
if [ -f "$AUTO_JOURNAL" ]; then
  AJ_AGE=$(file_age_days "$AUTO_JOURNAL")
  STATS+=("auto-journal: ${AJ_AGE}d old")
fi

# --- Output report ---
echo "--- Scaffold Fidelity ---"
for s in "${STATS[@]}"; do echo "  $s"; done

if [ -n "$SNAPSHOT_OUTPUT" ]; then
  echo ""
  echo "$SNAPSHOT_OUTPUT"
fi

if [ ${#CRITICALS[@]} -gt 0 ]; then
  echo ""
  echo "CRITICAL:"
  for c in "${CRITICALS[@]}"; do echo "  !! $c"; done
fi

if [ ${#WARNINGS[@]} -gt 0 ]; then
  echo ""
  echo "WARNING:"
  for w in "${WARNINGS[@]}"; do echo "  ! $w"; done
fi

if [ ${#ISSUES[@]} -gt 0 ]; then
  echo ""
  echo "ISSUES:"
  for i in "${ISSUES[@]}"; do echo "  - $i"; done
fi

if [ ${#CRITICALS[@]} -eq 0 ] && [ ${#WARNINGS[@]} -eq 0 ] && [ ${#ISSUES[@]} -eq 0 ]; then
  echo ""
  echo "  All clear."
fi

echo "---"
exit 0
