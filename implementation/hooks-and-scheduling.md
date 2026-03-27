# Hooks & Scheduled Tasks

The scaffold runs autonomously through hooks (event-driven) and scheduled tasks (time-driven).

## Hooks (settings.json)

Hooks fire on Claude Code events. Define them in `.claude/settings.json` or `.claude/settings.local.json`.

### Essential Hooks

**SessionStart — scaffold health check:**
```json
{
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "bash .claude/hooks/scaffold-health.sh",
        "timeout": 10
      }]
    }]
  }
}
```
The script checks: MEMORY.md age, scratchpad size, todo staleness, vault note count. Surfaces problems before the session starts.

**PostToolUse — capture context on edits:**
```json
{
  "PostToolUse": [{
    "matcher": "Write|Edit",
    "hooks": [{
      "type": "command",
      "command": "bash .claude/hooks/post-tool-capture.sh",
      "timeout": 5
    }]
  }]
}
```

**Stop — session end checklist:**
```json
{
  "Stop": [{
    "hooks": [{
      "type": "command",
      "command": "bash .claude/hooks/session-end.sh",
      "timeout": 30
    }]
  }]
}
```
Reminds: breadcrumbs written? Todo updated? MEMORY.md current? Git committed?

## Scheduled Tasks (macOS launchd)

Launchd plists in `~/Library/LaunchAgents/` run tasks on cron schedules. Each fires a `claude -p "prompt"` one-shot or a Python script.

### Template Plist

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.yourproject.task-name</string>
  <key>ProgramArguments</key>
  <array>
    <string>/path/to/python3</string>
    <string>/path/to/your/script.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/path/to/your/project</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>15</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/path/to/logs/task-name.log</string>
  <key>StandardErrorPath</key>
  <string>/path/to/logs/task-name.err.log</string>
</dict>
</plist>
```

Load: `launchctl load ~/Library/LaunchAgents/com.yourproject.task-name.plist`

### Recommended Task Schedule

| Task | Schedule | Purpose |
|------|----------|---------|
| Fidelity test | Daily | Measure WHAT/WHY/CONTEXT/BRIDGE scores |
| Vault fix | Daily | Orphans, danglers, schema compliance |
| Connection builder | Daily | Wire new cross-domain links |
| Metacog compile | 3x/day | Review reasoning chains, promote patterns |
| Breadcrumb compile | 2x/day | Compile session notes from breadcrumbs |
| Monitor audit | 2x/day | Check all tasks are alive, Discord alert if dead |
| Recorder health | Every 30min | Alert if data stream stale |
| Git sync | Every 6h | Auto-commit + push |
| Scaffold backup | Daily | Archive scaffold state |

### Monitor-the-Monitor Pattern

Critical: scheduled tasks die silently. Build a meta-monitor that checks whether all other tasks ran within their expected interval. Posts to Discord if anything is stale.

```python
# Simplified pattern
for each_task in all_tasks:
    age = time_since_last_log(task)
    if age > expected_interval * 1.5:
        alert_discord(f"{task} is stale: {age}h since last run")
```

### Key Principles

1. **Python for data capture, Claude for reasoning.** Don't use Claude tokens for things Python can do (tick recording, file watching, health checks). Use Claude for analysis, synthesis, and reasoning.

2. **Every scheduled task must log.** If it doesn't write a log, you can't tell if it ran. The monitor-the-monitor depends on log freshness.

3. **Degrade gracefully.** If Claude tokens are expensive, thin the reasoning layer. The Python data capture keeps running regardless. Add reasoning back when budget allows.

4. **Discord as notification layer.** Webhooks for alerts. User-Agent header required or Discord returns 403. Read webhook URLs from .env, never hardcode.
