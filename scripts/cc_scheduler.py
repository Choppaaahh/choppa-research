#!/usr/bin/env python3
"""
CC Scheduler — Native launchd task scheduling for Claude Code sessions.

Creates/removes/lists macOS launchd agents that run `claude -p "prompt"`
on a schedule. Our code, our plumbing, no third-party dependencies.

Usage:
    python3 scripts/cc_scheduler.py list                    # show all scheduled tasks
    python3 scripts/cc_scheduler.py add <name> <cron> <prompt>  # add a task
    python3 scripts/cc_scheduler.py remove <name>           # remove a task
    python3 scripts/cc_scheduler.py logs <name>             # tail task logs
    python3 scripts/cc_scheduler.py run <name>              # run a task immediately
    python3 scripts/cc_scheduler.py install-defaults        # install scaffold daemon tasks

Cron format: "minute hour day month weekday" (standard 5-field)
    Examples: "0 * * * *" = every hour, "0 9 * * 1-5" = weekdays 9am,
              "*/30 * * * *" = every 30 min, "0 6 * * *" = daily 6am

Each task creates:
    ~/Library/LaunchAgents/com.flex.cc.<name>.plist
    ~/.claude/scheduled/<name>.json (task config)
    logs/scheduled/<name>.log (execution log)
"""

import json
import os
import plistlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────

LAUNCH_AGENTS = Path.home() / "Library" / "LaunchAgents"
SCHEDULE_DIR = Path.home() / ".claude" / "scheduled"
LOG_DIR = SCHEDULE_DIR / "logs"
CLAUDE_BIN = Path.home() / ".local" / "bin" / "claude"
WORKING_DIR = Path.home() / "Flex" / "Trading"
PLIST_PREFIX = "com.flex.cc"

# ─── Default Tasks (mirror scaffold_daemon.py intervals) ────────────────────

_AUTOPOIESIS_SUFFIX = (
    " IMPORTANT: After completing your task, append a JSON line to "
    "~/Flex/Trading/logs/scaffold_modifications.jsonl with this exact format: "
    '{"timestamp": "<ISO8601>", "task_name": "<this task name>", '
    '"files_read": ["<list of files you read>"], '
    '"files_modified": ["<list of files you wrote/modified, empty if none>"], '
    '"modifications_type": "<one of: none|maintenance|evolution|repair|archive|new_connection>", '
    '"reasoning": "<one sentence: why you did/didn\'t modify anything>"}'
)

DEFAULT_TASKS = {
    "health-check": {
        "cron": "0 */4 * * *",  # every 4 hours (was hourly — less noise)
        "prompt": (
            "Run a scaffold health check. Read ~/.claude/projects/-Users-claude/memory/MEMORY.md, "
            "check line count (warn >160, critical >180). Read scratchpad.md, check for stale entries "
            "(>7 days). Read active-tasks.md, report status. Check journal.md staleness "
            "(>2 days = warn). Output a 5-line health summary to "
            "logs/scheduled/health-check.log.\n\n"
            "ALSO: Update the vault dashboard at ~/Flex/Trading/knowledge/notes/dashboard.md. "
            "Run a vault health scan (count notes, check orphans, danglers, link density, schema). "
            "Check bot status (ps aux | grep patience_trader). Check balance via python3 HL API. "
            "Update the Quick Stats table, Bot Status section, and Balance Tracker with latest row. "
            "Keep the dashboard concise — just update the numbers, don't rewrite the whole file."
            + _AUTOPOIESIS_SUFFIX
        ),
    },
    "vault-fix": {
        "cron": "0 */8 * * *",  # every 8 hours
        "prompt": (
            "You are the vault repair agent. Your job is to FIND and FIX problems, not just report them. "
            "Work in ~/Flex/Trading/knowledge/notes/.\n\n"
            "STEP 1 — SCHEMA FIX: Scan all .md files in notes/ subfolders for YAML frontmatter. "
            "Every note MUST have: summary, type, status, domains. "
            "If 'summary' is missing, generate one from the title + first paragraph. "
            "If 'type' is missing, infer from content (lesson/bug/mechanism/parameter/procedure/decision/insight). "
            "If 'status' is missing, add 'status: current'. "
            "If 'domains' is missing, infer from the subfolder name. "
            "ACTUALLY EDIT the files to add missing fields. Do not just log them.\n\n"
            "STEP 2 — ORPHAN FIX: Find notes with zero incoming wikilinks (no other note links to them). "
            "For each orphan: read the note, identify the most relevant domain map (MOC) in notes/, "
            "and ADD a wikilink to it in the appropriate MOC with a brief context phrase. "
            "Format: '- [[note title]] — context phrase'\n\n"
            "STEP 3 — DANGLING LINK FIX: Find wikilinks [[that point to non-existent notes]]. "
            "For each: if the intended note exists under a slightly different name, fix the link. "
            "If no match exists, remove the dangling link or replace with plain text.\n\n"
            "LIMITS: Fix up to 10 issues per run. Be conservative — don't guess on ambiguous cases. "
            "Log all changes to logs/scheduled/vault-fix.log with before/after for each fix."
            + _AUTOPOIESIS_SUFFIX
        ),
    },
    "scaffold-maintenance": {
        "cron": "0 12,20 * * *",  # noon + 8pm (when machine is ON)
        "prompt": (
            "You are the scaffold maintenance agent. Execute ALL THREE tasks below in order. "
            "Be conservative — when in doubt, keep content rather than delete it.\n\n"
            "All scaffold files are at: ~/.claude/projects/-Users-claude/memory/\n\n"
            "=== TASK 1: SCRATCHPAD ARCHIVAL (with CONTEXT preservation) ===\n"
            "Read scratchpad.md. Any section with a date MORE than 7 days before today is stale.\n"
            "For each stale section:\n"
            "1. Scan for durable findings (measurements, confirmed patterns, key numbers).\n"
            "2. CRITICAL — CONTEXT PRESERVATION: For each DECISION or ACTION logged in the stale section, "
            "extract the TRIGGERING CONTEXT (what was being looked at, what event/observation caused it). "
            "Check active-tasks.md — if the decision is there but has no 'Triggered by:' or 'CONTEXT:', "
            "ADD it now. If the decision isn't in active-tasks, check if a vault note captures it. "
            "If NEITHER has the triggering context, create a one-line entry in active-tasks.md DONE ARCHIVE: "
            "'- [decision]. WHY: [reasoning]. Triggered by: [context from scratchpad]'.\n"
            "This is the #1 fidelity leak — CONTEXT decays from 50-87% to <43% when scratchpad is archived "
            "without promoting triggering moments. WHAT and WHY survive compression. CONTEXT doesn't unless "
            "explicitly preserved here.\n"
            "3. Check if each finding already exists in a vault note under ~/Flex/Trading/knowledge/notes/. "
            "If NOT found, log 'PROMOTION NEEDED: [finding]' in your output.\n"
            "4. DELETE the stale section from scratchpad.md. Keep the header and rules section intact.\n\n"
            "=== TASK 2: MEMORY.MD COMPACTION ===\n"
            "Read MEMORY.md, count lines. If OVER 180:\n"
            "- Keep latest 3 days of session summaries with full detail.\n"
            "- Older days → compress to ONE LINE each: 'Mar N: [single sentence].'\n"
            "- Remove DONE items already in active-tasks.md DONE ARCHIVE with WHY.\n"
            "- Target: under 160 lines. If already under 180, skip.\n\n"
            "=== TASK 3: ACTIVE-TASKS CLEANUP ===\n"
            "Read active-tasks.md.\n"
            "- DONE ARCHIVE sections older than 14 days → DELETE entirely.\n"
            "- IN PROGRESS items referencing dates >7 days old with no activity → "
            "append '(STALE?)' but do NOT delete.\n"
            "- NEVER delete IN PROGRESS or BLOCKED items.\n\n"
            "Log all changes to logs/scheduled/scaffold-maintenance.log."
            + _AUTOPOIESIS_SUFFIX
        ),
    },
    "connection-builder": {
        "cron": "18 8,14,20,2 * * *",  # 4x/day: 3:18am, 9:18am, 3:18pm, 9:18pm EST
        "prompt": (
            "You are the connection-building agent. Your job is to strengthen the knowledge graph "
            "by adding links between notes that SHOULD be connected but aren't.\n\n"
            "=== PHASE 1: DELIBERATE CONNECTIONS (recent notes) ===\n\n"
            "STEP 1: Find recently modified notes (last 48 hours) in ~/Flex/Trading/knowledge/notes/. "
            "Use: find ~/Flex/Trading/knowledge/notes -name '*.md' -mtime -2\n\n"
            "STEP 2: For each recent note, read it and identify its core claim/topic.\n\n"
            "STEP 3: Search the vault for related notes that DON'T already link to/from this note. "
            "Look for: shared domains, overlapping concepts, contradictions, extensions.\n\n"
            "STEP 4: For each genuine connection found:\n"
            "- Add a wikilink in the 'Relevant Notes' section of BOTH notes (bidirectional)\n"
            "- Use articulated relationships: 'extends [[X]]', 'contradicts [[X]]', "
            "'same mechanism as [[X]]', NOT just 'see also'\n\n"
            "LIMITS: Process up to 5 recent notes per run. Add up to 3 new connections per note. "
            "Only add connections where the relationship is REAL and specific — no vague 'related to' links.\n\n"
            "=== PHASE 2: STOCHASTIC DREAMING (random note pairs) ===\n\n"
            "This phase simulates biological dream recombination — random replay that explores "
            "the long tail of the connection space.\n\n"
            "STEP 5: List ALL .md files under ~/Flex/Trading/knowledge/notes/ (excluding index.md and "
            "domain map MOC files at the top level of each subfolder). Use: "
            "find ~/Flex/Trading/knowledge/notes -mindepth 2 -name '*.md' | sort -R | head -10\n\n"
            "STEP 6: From these 10 random notes, form 5 random PAIRS (note A, note B). "
            "For each pair:\n"
            "- Read both notes\n"
            "- Ask: is there a genuine connection that neither note currently captures? "
            "Look for: shared mechanisms across different domains, analogies, contradictions, "
            "causal chains, or surprising parallels\n"
            "- If YES: add bidirectional wikilinks with articulated relationships, "
            "and tag the connection as a 'dream connection' in your log\n"
            "- If NO: log the pair as 'no connection found' — this is expected most of the time\n\n"
            "IMPORTANT: Dream connections should have a HIGHER bar for quality than deliberate "
            "connections. Most random pairs will have nothing. That's correct — the value is in "
            "the rare surprising find, not in forcing connections.\n\n"
            "=== LOGGING ===\n\n"
            "Log to logs/scheduled/connection-builder.log with this format:\n"
            "- Date/time header\n"
            "- DELIBERATE section: list each connection added from Phase 1\n"
            "- DREAM section: list each pair examined, whether connection found, and if so what\n"
            "- SUMMARY: X deliberate connections, Y dream connections, Z pairs examined\n\n"
            "Over time this log tracks whether stochastic exploration produces genuine "
            "cross-domain insights that deliberate search misses."
            + _AUTOPOIESIS_SUFFIX
        ),
    },
    "fidelity-test": {
        "cron": "0 */12 * * *",  # every 12 hours
        "prompt": (
            "Run scaffold fidelity test. Read ~/.claude/projects/-Users-claude/memory/active-tasks.md "
            "and ~/.claude/projects/-Users-claude/memory/journal.md. "
            "Extract 5 recent decisions from the DONE archive and journal entries. "
            "Score each on WHAT (is the decision stated?), WHY (is reasoning documented?), "
            "CONTEXT (is the triggering moment recorded?). Each dimension 0/0.5/1. "
            "Calculate percentages. Compare against baseline: WHAT 100%, WHY 80-93%, CONTEXT 50-60%.\n\n"
            "If WHY drops below 70% on any decision: FIND that decision in active-tasks.md and "
            "ADD the missing WHY reasoning by reading journal.md and scratchpad.md for context. "
            "This is a REPAIR action, not just a score.\n\n"
            "Append JSONL result to logs/scheduled/fidelity-test.log"
            + _AUTOPOIESIS_SUFFIX
        ),
    },
    "morning-brief": {
        "cron": "10 7 * * *",  # daily 9am (more realistic wake time)
        "prompt": (
            "Generate morning brief. Read ~/.claude/projects/-Users-claude/memory/active-tasks.md, "
            "journal.md (latest entry), scratchpad.md. "
            "Check bot status (is momentum_scalp.py running? use: ps aux | grep momentum_scalp). "
            "Summarize: (1) what's active, (2) what's blocked, (3) what needs attention today, "
            "(4) bot status. Write brief to logs/scheduled/morning-brief.log"
            + _AUTOPOIESIS_SUFFIX
        ),
    },
    "self-reflection": {
        "cron": "36 19 * * *",  # daily 3pm EST (19 UTC)
        "prompt": (
            "Run self-reflection. Read today's entries in "
            "~/.claude/projects/-Users-claude/memory/journal.md and scratchpad.md. "
            "Answer: (1) What was accomplished today? (2) What assumptions were made? "
            "(3) What would I do differently? (4) What connections were missed? "
            "(5) What should tomorrow's session prioritize?\n\n"
            "ALSO: Check if any vault notes were created/modified today that lack connections. "
            "If found, add 1-2 wikilinks to the most relevant existing notes. This is a REPAIR action.\n\n"
            "Append reflection as JSONL to ~/.claude/projects/-Users-claude/memory/daemon-reflections.jsonl"
            + _AUTOPOIESIS_SUFFIX
        ),
    },
    "eigenform-tracker": {
        "cron": "0 */12 * * *",  # every 12 hours
        "prompt": (
            "Run the eigenform convergence tracker: "
            "cd ~/Flex/Trading && python3 scripts/eigenform_tracker.py. "
            "This logs vault metrics (note count, link density, domain maps, core belief stability) "
            "to logs/eigenform_tracking.jsonl. Zero API cost — pure filesystem scan. "
            "If 3+ data points exist, also run --report to check convergence trends."
            + _AUTOPOIESIS_SUFFIX
        ),
    },
    "topology-health": {
        "cron": "0 6 * * 0",  # weekly Sunday 6am
        "prompt": (
            "Run vault topology health check. Zero API cost — pure filesystem scan.\n\n"
            "cd ~/Flex/Trading && python3 scripts/vault_topology.py --auto-domain --suggest --json "
            "> logs/scheduled/topology-latest.json\n\n"
            "Then compare against previous run at logs/scheduled/topology-previous.json. "
            "Track: note count trend, avg degree trend, isolated notes, dangling links, "
            "domain cohesion changes.\n\n"
            "Flag regressions: avg degree dropping, orphans growing, new dangling links, "
            "cohesion dropping in any domain.\n\n"
            "After comparison, copy topology-latest.json to topology-previous.json for next run.\n\n"
            "Also run --onboard mode and save to topology-onboard.log for human review.\n\n"
            "Log summary to logs/scheduled/topology-health.log"
            + _AUTOPOIESIS_SUFFIX
        ),
    },
    "autoresearch": {
        "cron": "0 3 * * 0,3",  # twice weekly: Sunday + Wednesday 3am
        "prompt": (
            "You are the autoresearch intelligence scanner. Your job is to find recent papers, "
            "tools, and ideas relevant to our trading system and research.\n\n"
            "STEP 1: Read ~/Flex/Trading/scripts/autoresearch_program.md for research directions. "
            "If it doesn't exist, use these domains: crypto HFT/market making, AI agent memory, "
            "consciousness/IIT, knowledge graph evolution.\n\n"
            "STEP 2: Use WebSearch to search for recent (2025-2026) papers and tools in each domain. "
            "Run at least 8 searches across different domains. Example queries:\n"
            "- 'retail market making crypto 2026 paper'\n"
            "- 'AI agent persistent memory architecture 2026'\n"
            "- 'knowledge graph self-maintenance automated'\n"
            "- 'Hyperliquid trading bot github'\n"
            "- 'cross-exchange latency arbitrage crypto'\n\n"
            "STEP 3: For each promising result (relevance > 6/10), use WebFetch to read it. "
            "Score relevance to our specific work (patience trader, vault infra, consciousness research).\n\n"
            "STEP 4: Write a digest to ~/Flex/Trading/knowledge/captures/bot5_digest_$(date +%%Y-%%m-%%d).md "
            "with:\n"
            "- Top 3 findings with title, URL, relevance score, why it matters, actionable next step\n"
            "- 5 honorable mentions with one-line summaries\n"
            "- Any findings that CONTRADICT our current beliefs (red team)\n\n"
            "ALSO log summary to logs/scheduled/autoresearch.log.\n"
            "Quality over quantity. Only promote genuinely relevant findings."
        ),
    },
    "consolidated-digest": {
        "cron": "42 19 * * *",  # daily 9:30am (after morning-brief at 9am)
        "prompt": (
            "Generate consolidated daily digest. Read ALL scheduled task logs and combine "
            "into a single actionable summary.\n\n"
            "Read these files and extract the LATEST entry from each:\n"
            "- logs/scheduled/health-check.log\n"
            "- logs/scheduled/morning-brief.log\n"
            "- logs/scheduled/fidelity-test.log\n"
            "- logs/scheduled/connection-builder.log\n"
            "- logs/scheduled/self-reflection.log\n"
            "- logs/scheduled/vault-fix.log\n"
            "- logs/scheduled/eigenform-tracker.log\n"
            "- logs/scheduled/autoresearch.log (if exists)\n"
            "- ~/Flex/Trading/logs/intel_report_*.txt (latest, if exists)\n\n"
            "Combine into a single digest with these sections:\n"
            "1. HEALTH: scaffold status (line counts, staleness)\n"
            "2. FIDELITY: latest WHAT/WHY/CONTEXT scores + any repairs\n"
            "3. VAULT: fixes applied, connections built, topology changes\n"
            "4. INTEL: autoresearch findings, eigenform trends\n"
            "5. REFLECTION: yesterday's insights + today's priorities\n"
            "6. BOT: status (running/parked), recent trades if any\n"
            "7. ACTION ITEMS: top 3 things that need attention\n\n"
            "Write to logs/scheduled/daily-digest.log AND "
            "~/.claude/projects/-Users-claude/memory/scratchpad.md (append under '## Daily Digest' header).\n\n"
            "Keep it tight — one page max. This is the single doc Colby reads each morning."
            + _AUTOPOIESIS_SUFFIX
        ),
    },
    "scaffold-backup": {
        "cron": "0 5 * * *",  # daily 5am
        "prompt": (
            "Run scaffold backup. Zero API cost — pure filesystem operations.\n\n"
            "STEP 1: Create timestamped backup directory at "
            "~/Flex/Trading/backups/scaffold/$(date +%%Y%%m%%d)/\n\n"
            "STEP 2: Copy these files:\n"
            "- ~/.claude/projects/-Users-claude/memory/ (entire directory)\n"
            "- ~/Flex/Trading/knowledge/notes/ (entire directory)\n"
            "- logs/scheduled/ (all log files)\n\n"
            "STEP 3: Remove backups older than 7 days to prevent disk bloat.\n\n"
            "STEP 4: Git commit in both repos if there are changes:\n"
            "- cd ~/Flex/scaffold-tools && git add -A && git commit -m 'auto: daily backup' && git push\n"
            "- cd ~/Flex/Trading && git add -A && git commit -m 'auto: daily backup' && git push\n\n"
            "Log to logs/scheduled/scaffold-backup.log"
            + _AUTOPOIESIS_SUFFIX
        ),
    },
    "thread-freshness": {
        "cron": "0 8 * * 3",  # weekly Wednesday 8am
        "prompt": (
            "Check thread freshness in MEMORY.md. Zero API cost — filesystem only.\n\n"
            "STEP 1: Read ~/.claude/projects/-Users-claude/memory/MEMORY.md\n\n"
            "STEP 2: Parse the numbered threads (1-30+). For each thread, check if the "
            "vault notes it references have been modified in the last 14 days. "
            "Use: stat -f '%%m' on each referenced file.\n\n"
            "STEP 3: Flag threads where ALL referenced notes are >14 days stale as 'DORMANT'. "
            "Flag threads where referenced notes don't exist as 'BROKEN'.\n\n"
            "STEP 4: For DORMANT threads, check if the thread's topic has been superseded "
            "by newer work (search vault for related keywords in recently modified notes). "
            "If superseded, suggest removal or update.\n\n"
            "STEP 5: Report: active threads, dormant threads, broken threads. "
            "Suggest specific compaction targets if MEMORY.md is over 160 lines.\n\n"
            "Log to logs/scheduled/thread-freshness.log"
            + _AUTOPOIESIS_SUFFIX
        ),
    },
    "git-sync": {
        "cron": "0 */6 * * *",  # every 6 hours
        "prompt": (
            "Git sync for both repos. Zero API cost — git operations only.\n\n"
            "For each repo (~/Flex/Trading and ~/Flex/scaffold-tools):\n"
            "1. Check if there are uncommitted changes (git status)\n"
            "2. If yes: stage all changes, commit with message 'auto: sync <timestamp>'\n"
            "3. Push to origin\n\n"
            "IMPORTANT: Never commit .env files. Check .gitignore is respected.\n"
            "Log to logs/scheduled/git-sync.log"
            + _AUTOPOIESIS_SUFFIX
        ),
    },
    "brain-cycle": {
        "cron": "0 */6 * * *",  # every 6 hours
        "prompt": (
            "Run the scaffold brain meta-controller. Zero API cost — pure filesystem.\n\n"
            "cd ~/Flex/Trading && python3 scripts/scaffold_brain.py\n\n"
            "This reads all task outputs (eigenform, autopoiesis, topology, scheduler logs), "
            "detects gaps, generates proposals, measures learning velocity, and saves state to "
            "logs/brain_state.json and logs/brain_proposals.jsonl.\n\n"
            "The brain NEVER modifies vault notes or scaffold files directly — it only writes "
            "to its own output files. Tasks check brain_proposals.jsonl for targeted work.\n\n"
            "After running, append a brief summary of the brain state to "
            "logs/scheduled/brain-cycle.log"
            + _AUTOPOIESIS_SUFFIX
        ),
    },
    "journal-update": {
        "cron": "0 4 * * *",  # daily 11pm EST (04 UTC next day)
        "prompt": (
            "Update the session journal. Read these sources:\n"
            "- ~/.claude/projects/-Users-claude/memory/journal.md (current journal)\n"
            "- ~/.claude/projects/-Users-claude/memory/scratchpad.md (today's breadcrumbs)\n"
            "- ~/Flex/Trading/logs/patience_journal.jsonl (last 24h trades)\n"
            "- logs/scheduled/morning-brief.log (latest brief)\n"
            "- logs/scheduled/self-reflection.log (latest reflection)\n\n"
            "Create a new journal entry at the TOP (after the header, before the previous entry). "
            "Use this format:\n"
            "### <date> Session <N+1> — <2-3 word summary>\n"
            "**Context:** What happened today (bot status, any interactive sessions)\n"
            "**What happened:** Numbered list of key events (bot trades, config changes, builds, vault work)\n"
            "**Key findings:** Any non-obvious learnings\n"
            "**Trading state:** Current bot config, balance, positions\n\n"
            "Keep it under 20 lines. This is a factual log, not a reflection. "
            "If no interactive session happened, note that and summarize automated activity only.\n\n"
            "Log to logs/scheduled/journal-update.log"
        ),
    },
}


# ─── Cron Parsing ────────────────────────────────────────────────────────────

def cron_to_launchd(cron_str):
    """Convert 5-field cron string to launchd StartCalendarInterval dicts.

    Returns a list of dicts (multiple for ranges like 1-5).
    Supports: *, */N, N, N-M, and comma-separated values.
    """
    fields = cron_str.strip().split()
    if len(fields) != 5:
        raise ValueError(f"Expected 5 cron fields, got {len(fields)}: {cron_str}")

    minute, hour, day, month, weekday = fields
    launchd_keys = ["Minute", "Hour", "Day", "Month", "Weekday"]
    cron_vals = [minute, hour, day, month, weekday]

    def expand_field(field, max_val, min_val=0):
        """Expand a cron field to a list of integers, or None for *."""
        if field == "*":
            return None
        if field.startswith("*/"):
            step = int(field[2:])
            return list(range(min_val, max_val + 1, step))
        parts = []
        for part in field.split(","):
            if "-" in part:
                start, end = part.split("-", 1)
                parts.extend(range(int(start), int(end) + 1))
            else:
                parts.append(int(part))
        return parts

    max_vals = [59, 23, 31, 12, 7]
    min_vals = [0, 0, 1, 1, 0]
    expanded = []
    for i, (val, mx, mn) in enumerate(zip(cron_vals, max_vals, min_vals)):
        expanded.append(expand_field(val, mx, mn))

    # Build calendar interval dicts
    # For step intervals (*/N), launchd doesn't support "every N" natively.
    # We create multiple calendar entries.
    from itertools import product

    # Replace None with [None] for product
    lists = [v if v is not None else [None] for v in expanded]
    intervals = []
    for combo in product(*lists):
        entry = {}
        for key, val in zip(launchd_keys, combo):
            if val is not None:
                entry[key] = val
        if entry:
            intervals.append(entry)

    return intervals if intervals else [{}]


def build_plist(name, prompt, cron_str):
    """Build a launchd plist dict for a scheduled CC task."""
    label = f"{PLIST_PREFIX}.{name}"
    log_path = str(LOG_DIR / f"{name}.log")
    err_path = str(LOG_DIR / f"{name}.err.log")

    # Build the claude command
    # --dangerously-skip-permissions needed for autonomous file modifications
    # WorkingDirectory is set in the plist itself — no --cwd flag needed
    program_args = [
        str(CLAUDE_BIN),
        "--dangerously-skip-permissions",
        "--permission-mode", "bypassPermissions",
        "--add-dir", str(Path.home() / ".claude"),
        "-p",
        prompt,
    ]

    intervals = cron_to_launchd(cron_str)

    plist = {
        "Label": label,
        "ProgramArguments": program_args,
        "StartCalendarInterval": intervals if len(intervals) > 1 else intervals[0],
        "StandardOutPath": log_path,
        "StandardErrorPath": err_path,
        "WorkingDirectory": str(WORKING_DIR),
        "EnvironmentVariables": {
            "PATH": "/usr/local/bin:/usr/bin:/bin:" + str(CLAUDE_BIN.parent),
            "HOME": str(Path.home()),
        },
        "RunAtLoad": False,
        "Nice": 10,  # lower priority than interactive work
    }

    return plist


# ─── Task Config ─────────────────────────────────────────────────────────────

def save_task_config(name, cron_str, prompt):
    """Save task configuration to JSON."""
    SCHEDULE_DIR.mkdir(parents=True, exist_ok=True)
    config = {
        "name": name,
        "cron": cron_str,
        "prompt": prompt,
        "created": datetime.now().isoformat(),
        "plist": f"{PLIST_PREFIX}.{name}",
    }
    config_path = SCHEDULE_DIR / f"{name}.json"
    config_path.write_text(json.dumps(config, indent=2))
    return config_path


def load_task_config(name):
    """Load task configuration from JSON."""
    config_path = SCHEDULE_DIR / f"{name}.json"
    if config_path.exists():
        return json.loads(config_path.read_text())
    return None


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_add(name, cron_str, prompt):
    """Add a scheduled task."""
    # Validate cron
    try:
        cron_to_launchd(cron_str)
    except ValueError as e:
        print(f"ERROR: Invalid cron: {e}")
        return False

    # Create directories
    LAUNCH_AGENTS.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Build and write plist
    plist = build_plist(name, prompt, cron_str)
    plist_path = LAUNCH_AGENTS / f"{PLIST_PREFIX}.{name}.plist"

    # Unload existing if present
    if plist_path.exists():
        subprocess.run(["launchctl", "unload", str(plist_path)],
                       capture_output=True)

    with open(plist_path, "wb") as f:
        plistlib.dump(plist, f)

    # Save config
    save_task_config(name, cron_str, prompt)

    # Load into launchd
    result = subprocess.run(["launchctl", "load", str(plist_path)],
                            capture_output=True, text=True)
    if result.returncode != 0:
        print(f"WARNING: launchctl load failed: {result.stderr}")
    else:
        print(f"OK: Scheduled '{name}' ({cron_str})")
        print(f"   Plist: {plist_path}")
        print(f"   Log:   {LOG_DIR / f'{name}.log'}")

    return True


def cmd_remove(name):
    """Remove a scheduled task."""
    plist_path = LAUNCH_AGENTS / f"{PLIST_PREFIX}.{name}.plist"

    if plist_path.exists():
        subprocess.run(["launchctl", "unload", str(plist_path)],
                       capture_output=True)
        plist_path.unlink()
        print(f"OK: Removed plist {plist_path.name}")
    else:
        print(f"WARN: No plist found for '{name}'")

    config_path = SCHEDULE_DIR / f"{name}.json"
    if config_path.exists():
        config_path.unlink()
        print(f"OK: Removed config {config_path.name}")

    return True


def cmd_list():
    """List all scheduled tasks."""
    # Find our plists
    tasks = []
    if LAUNCH_AGENTS.exists():
        for plist_path in sorted(LAUNCH_AGENTS.glob(f"{PLIST_PREFIX}.*.plist")):
            name = plist_path.stem.replace(f"{PLIST_PREFIX}.", "")
            config = load_task_config(name)
            cron = config.get("cron", "?") if config else "?"

            # Check if loaded
            result = subprocess.run(
                ["launchctl", "list", f"{PLIST_PREFIX}.{name}"],
                capture_output=True, text=True
            )
            loaded = result.returncode == 0

            # Check log
            log_path = LOG_DIR / f"{name}.log"
            log_size = f"{log_path.stat().st_size}B" if log_path.exists() else "no log"

            status = "LOADED" if loaded else "UNLOADED"
            tasks.append((name, cron, status, log_size))

    if not tasks:
        print("No scheduled tasks found.")
        print(f"  Use: python3 {sys.argv[0]} install-defaults")
        return

    print(f"{'Name':<20} {'Schedule':<18} {'Status':<10} {'Log'}")
    print("-" * 65)
    for name, cron, status, log_size in tasks:
        print(f"{name:<20} {cron:<18} {status:<10} {log_size}")


def cmd_logs(name):
    """Tail logs for a task."""
    log_path = LOG_DIR / f"{name}.log"
    err_path = LOG_DIR / f"{name}.err.log"

    if log_path.exists():
        print(f"=== {log_path} (last 30 lines) ===")
        lines = log_path.read_text().splitlines()
        for line in lines[-30:]:
            print(line)
    else:
        print(f"No log file: {log_path}")

    if err_path.exists() and err_path.stat().st_size > 0:
        print(f"\n=== {err_path} (last 10 lines) ===")
        lines = err_path.read_text().splitlines()
        for line in lines[-10:]:
            print(line)


def cmd_run(name):
    """Run a task immediately (bypass schedule)."""
    config = load_task_config(name)
    if not config:
        print(f"ERROR: No config found for '{name}'")
        return False

    print(f"Running '{name}' now...")
    result = subprocess.run(
        [str(CLAUDE_BIN), "-p", config["prompt"]],
        capture_output=True, text=True, timeout=300,
        cwd=str(WORKING_DIR)
    )
    print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr}")
    return result.returncode == 0


def cmd_install_defaults():
    """Install all default scaffold tasks."""
    print("Installing default scheduled tasks...")
    print()
    for name, task in DEFAULT_TASKS.items():
        cmd_add(name, task["cron"], task["prompt"])
        print()
    print(f"Done. {len(DEFAULT_TASKS)} tasks installed.")
    print(f"Logs: {LOG_DIR}/")
    print(f"Configs: {SCHEDULE_DIR}/")
    print()
    print("Manage:")
    print(f"  python3 {sys.argv[0]} list")
    print(f"  python3 {sys.argv[0]} logs <name>")
    print(f"  python3 {sys.argv[0]} remove <name>")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "list":
        cmd_list()
    elif cmd == "add" and len(sys.argv) >= 5:
        name = sys.argv[2]
        cron_str = sys.argv[3]
        prompt = " ".join(sys.argv[4:])
        cmd_add(name, cron_str, prompt)
    elif cmd == "remove" and len(sys.argv) >= 3:
        cmd_remove(sys.argv[2])
    elif cmd == "logs" and len(sys.argv) >= 3:
        cmd_logs(sys.argv[2])
    elif cmd == "run" and len(sys.argv) >= 3:
        cmd_run(sys.argv[2])
    elif cmd == "install-defaults":
        cmd_install_defaults()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
