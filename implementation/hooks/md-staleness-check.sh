#!/bin/bash
# MD Staleness Check — fires on git commit
# Warns if code files are staged but key context documents haven't been touched this session.
#
# Wire as a PostToolUse hook in your Claude Code settings.json, triggered on Bash tool calls.
# [PLACEHOLDER] Update paths below to match your project structure.

# Only trigger on git commit commands
if [[ "$CLAUDE_TOOL_INPUT" != *"git commit"* ]]; then
    exit 0
fi

# [PLACEHOLDER] Update this to your project root
PROJECT_ROOT="$HOME/your-project"
cd "$PROJECT_ROOT" 2>/dev/null || exit 0

# Check if code files are staged
CODE_STAGED=$(git diff --cached --name-only 2>/dev/null | grep -cE '\.(py|ts|js|go|rs)$')

if [ "$CODE_STAGED" -gt 0 ]; then
    # [PLACEHOLDER] Update these paths to your key context documents
    MEMORY="$HOME/.claude/projects/YOUR-PROJECT/memory/MEMORY.md"
    CONTEXT_DOC="$PROJECT_ROOT/SCAFFOLD.md"

    NOW=$(date +%s)
    MEM_MOD=$(stat -f %m "$MEMORY" 2>/dev/null || echo 0)
    CTX_MOD=$(stat -f %m "$CONTEXT_DOC" 2>/dev/null || echo 0)

    MEM_AGE=$(( (NOW - MEM_MOD) / 60 ))
    CTX_AGE=$(( (NOW - CTX_MOD) / 60 ))

    WARN=""
    if [ "$MEM_AGE" -gt 30 ]; then
        WARN="MEMORY.md last updated ${MEM_AGE}min ago."
    fi
    if [ "$CTX_AGE" -gt 30 ]; then
        WARN="$WARN SCAFFOLD.md last updated ${CTX_AGE}min ago."
    fi

    if [ -n "$WARN" ]; then
        echo "⚠️ MD STALENESS: Committing ${CODE_STAGED} code files but ${WARN} Update context docs to prevent scaffold drift."
    fi
fi
