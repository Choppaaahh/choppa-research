#!/bin/bash
# Vault health check — runs auto-linker + basic stats
# Usage: bash .claude/hooks/vault-health.sh
#
# [PLACEHOLDER] Update VAULT path to your knowledge vault directory.

HOOKS_DIR="$(cd "$(dirname "$0")" && pwd)"
# [PLACEHOLDER] Update this to your vault notes directory
VAULT="$HOME/your-project/knowledge/notes"

echo "========================================="
echo "  Vault Health Check"
echo "  $(date '+%Y-%m-%d %H:%M')"
echo "========================================="
echo ""

# Basic stats
if [ -d "$VAULT" ]; then
  TOTAL=$(find "$VAULT" -name "*.md" -not -path "*/archived/*" | wc -l | tr -d ' ')
  MOCS=$(find "$VAULT" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
  FOLDERS=$(find "$VAULT" -type d -not -path "*/archived/*" | wc -l | tr -d ' ')
  RECENT=$(find "$VAULT" -name "*.md" -mtime -3 -not -path "*/archived/*" | wc -l | tr -d ' ')
  STALE=$(find "$VAULT" -name "*.md" -mtime +30 -not -path "*/archived/*" | wc -l | tr -d ' ')

  echo "  Total notes: $TOTAL"
  echo "  MOCs (root): $MOCS"
  echo "  Folders: $FOLDERS"
  echo "  Modified last 3 days: $RECENT"
  echo "  Stale (30+ days): $STALE"
  echo ""
fi

# Run auto-linker (if present)
if [ -f "$HOOKS_DIR/lib/vault-auto-linker.sh" ]; then
  bash "$HOOKS_DIR/lib/vault-auto-linker.sh" "$VAULT"
else
  echo "  Auto-linker not found at $HOOKS_DIR/lib/vault-auto-linker.sh"
fi

echo ""
echo "========================================="
