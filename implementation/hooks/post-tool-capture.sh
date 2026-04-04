#!/bin/bash
# PostToolUse auto-capture hook
# Logs tool usage with file context. Reminds the model to breadcrumb on significant edits.
#
# Wire as a PostToolUse hook in your Claude Code settings.json.
# [PLACEHOLDER] Update CAPTURE_LOG path to your project's log directory.

# [PLACEHOLDER] Update this path to your project's log directory
CAPTURE_LOG="$HOME/your-project/logs/tool_observations.jsonl"
TOOL_NAME="${CLAUDE_TOOL_NAME:-unknown}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Extract file path from tool input (best effort)
FILE_PATH=""
if [ -n "$CLAUDE_TOOL_INPUT" ]; then
    FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | grep -oE '/[^ "]+\.(py|md|json|sh|yaml|ts|js)' | head -1)
fi

case "$TOOL_NAME" in
  Write|Edit)
    # Log with file context
    echo "{\"ts\":\"$TIMESTAMP\",\"tool\":\"$TOOL_NAME\",\"file\":\"$FILE_PATH\",\"session\":\"${CLAUDE_SESSION_ID:-unknown}\"}" >> "$CAPTURE_LOG"

    # Compile check on Python files
    if [[ "$FILE_PATH" == *.py ]]; then
        python3 -c "import py_compile; py_compile.compile('$FILE_PATH', doraise=True)" 2>&1 || true
        BASENAME=$(basename "$FILE_PATH")
        echo "📝 Edited $BASENAME — breadcrumb: what changed + WHY + what triggered it. Route to QA if code file."
    fi

    # Breadcrumb reminder on significant edits
    if [[ "$FILE_PATH" == *.py ]] || [[ "$FILE_PATH" == *SCAFFOLD.md ]] || [[ "$FILE_PATH" == *MEMORY.md ]] || [[ "$FILE_PATH" == *todo.md ]]; then
        echo "🧠 CONTEXT capture: log a breadcrumb with WHY this change was made and WHAT triggered it."
    fi
    ;;
  Bash)
    # Log commands (skip trivial)
    CMD_PREVIEW=$(echo "$CLAUDE_TOOL_INPUT" | head -c 100 | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g')
    echo "{\"ts\":\"$TIMESTAMP\",\"tool\":\"Bash\",\"cmd\":\"$CMD_PREVIEW\",\"session\":\"${CLAUDE_SESSION_ID:-unknown}\"}" >> "$CAPTURE_LOG"
    ;;
  *)
    ;;
esac
