#!/bin/bash
# Session Start Brief — surfaces forgotten/stale items from todo.md
# Runs as SessionStart hook, outputs JSON with systemMessage.
#
# Wire as a SessionStart hook in your Claude Code settings.json.
# [PLACEHOLDER] Update TODO and MEMORY paths to match your project structure.

# [PLACEHOLDER] Update these paths to your project
TODO="$HOME/your-project/tasks/todo.md"
MEMORY="$HOME/.claude/projects/YOUR-PROJECT/memory/MEMORY.md"

if [ ! -f "$TODO" ]; then
    echo '{}'
    exit 0
fi

# Count open items
OPEN=$(grep -c '^\- \[ \]' "$TODO" 2>/dev/null || echo 0)
DONE=$(grep -c '^\- \[x\]' "$TODO" 2>/dev/null || echo 0)

# Check todo.md age
TODO_AGE_DAYS=$(( ($(date +%s) - $(stat -f %m "$TODO")) / 86400 ))

# Check MEMORY.md age
MEM_AGE_DAYS=0
if [ -f "$MEMORY" ]; then
    MEM_AGE_DAYS=$(( ($(date +%s) - $(stat -f %m "$MEMORY")) / 86400 ))
fi

# Check breadcrumbs
# [PLACEHOLDER] Update this path to your breadcrumbs log
CRUMBS="$HOME/your-project/logs/session_breadcrumbs.jsonl"
CRUMB_COUNT=0
if [ -f "$CRUMBS" ]; then
    CRUMB_COUNT=$(wc -l < "$CRUMBS" | tr -d ' ')
fi

# Build the brief
BRIEF="--- SESSION BRIEF ---"
BRIEF="$BRIEF\n  Todo: $OPEN open / $DONE done"

if [ "$TODO_AGE_DAYS" -gt 1 ]; then
    BRIEF="$BRIEF\n  ! todo.md is ${TODO_AGE_DAYS}d old — may be stale"
fi

if [ "$MEM_AGE_DAYS" -gt 3 ]; then
    BRIEF="$BRIEF\n  ! MEMORY.md is ${MEM_AGE_DAYS}d old — UPDATE IT"
fi

if [ "$CRUMB_COUNT" -gt 30 ]; then
    BRIEF="$BRIEF\n  ! ${CRUMB_COUNT} breadcrumbs — consider archiving"
fi

# Surface items with dates that have passed
OVERDUE=$(grep -E '^\- \[ \].*\d{2}/\d{2}|^\- \[ \].*\d{4}-\d{2}-\d{2}' "$TODO" | head -5)
if [ -n "$OVERDUE" ]; then
    BRIEF="$BRIEF\n  Dated items (check if overdue):"
    while IFS= read -r line; do
        SHORT=$(echo "$line" | sed 's/^- \[ \] /  /' | cut -c1-80)
        BRIEF="$BRIEF\n  $SHORT"
    done <<< "$OVERDUE"
fi

# Remind about breadcrumb capture
BRIEF="$BRIEF\n  REMEMBER: capture breadcrumbs as you go (decisions/findings/insights → logs/session_breadcrumbs.jsonl)"
BRIEF="$BRIEF\n---"

echo "{\"systemMessage\":\"$(echo -e "$BRIEF" | sed 's/"/\\"/g' | tr '\n' ' ')\"}"
