#!/usr/bin/env python3
"""
Eigenform Convergence Tracker

Logs vault metrics per session to track whether the scaffold is converging
on a stable eigenform (Von Foerster/Kauffman prediction).

Convergence signals:
  - Note growth rate -> 0 (stabilizing)
  - Refinement ratio -> high (editing > creating)
  - Domain map count stabilizes
  - Link density converges to stable ratio
  - Core belief drift -> 0

Health metrics (9 dimensions):
  - MEMORY.md line count (optimal 100-160)
  - Scratchpad staleness (days since last timestamp)
  - Active-tasks completion ratio (done / total)
  - Orphan notes (zero incoming wikilinks)
  - Dangling links (wikilinks to non-existent notes)
  - Trading journal activity (recent momo log lines)
  - Autopoiesis loop closure rate (non-none modifications)
  - Schema violations (missing required frontmatter)
  - Session recency (days since last journal.md entry)

Composite scaffold health score: 0-100 weighted across all 9 dimensions.

Run at session end or via CC scheduler. Zero API cost.

Usage:
    python3 scripts/eigenform_tracker.py              # log current state
    python3 scripts/eigenform_tracker.py --report      # show convergence report
    python3 scripts/eigenform_tracker.py --plot         # ASCII convergence plot
"""

import json
import os
import sys
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# ─── Configuration ──────────────────────────────────────────────────────────

BASE_DIR = Path.home() / "Flex" / "Trading"
VAULT_DIR = BASE_DIR / "knowledge" / "notes"
MEMORY_DIR = Path.home() / ".claude" / "projects" / "-Users-claude" / "memory"
LOGS_DIR = BASE_DIR / "logs"
TRACKING_FILE = LOGS_DIR / "eigenform_tracking.jsonl"

# Required frontmatter fields for schema validation
REQUIRED_FRONTMATTER = ["summary", "type", "status"]

# Core beliefs to track for drift — these are the claims that should stabilize
CORE_BELIEFS = [
    "RCO = FEP = Buddhist dependent arising",
    "Bot IS consciousness experiment",
    "Scaffold fidelity: WHAT 100%, WHY 80-93%, CONTEXT 50-60%",
    "Pulsed consciousness",
    "Causal emergence",
]


# ─── Existing Vault Metrics ─────────────────────────────────────────────────

def count_notes():
    """Count total .md files in notes/ (excluding domain maps and index)."""
    if not VAULT_DIR.exists():
        return 0
    count = 0
    for f in VAULT_DIR.rglob("*.md"):
        # Skip domain maps (they're in the top-level notes/ dir and are MOCs)
        # Count everything else
        count += 1
    return count


def count_domain_maps():
    """Count domain map files (top-level .md files in notes/ that are MOCs)."""
    if not VAULT_DIR.exists():
        return 0
    # Domain maps are top-level .md files that serve as MOCs
    moc_patterns = ["index.md", "grid-mechanics.md", "fee-model.md", "bug-patterns.md",
                    "coin-evaluation.md", "safety-systems.md", "microstructure-signals.md",
                    "regime-detection.md", "operational-procedures.md", "lessons-learned.md",
                    "build-roadmap.md", "consciousness-trading.md"]
    count = 0
    for f in VAULT_DIR.iterdir():
        if f.suffix == ".md" and f.is_file():
            # Check if it looks like a domain map (has many [[ links)
            try:
                content = f.read_text()
                link_count = content.count("[[")
                if link_count >= 5:  # domain maps have many links
                    count += 1
            except Exception:
                pass
    return count


def count_wiki_links():
    """Count total [[ wiki links across all vault notes."""
    if not VAULT_DIR.exists():
        return 0
    total = 0
    for f in VAULT_DIR.rglob("*.md"):
        try:
            content = f.read_text()
            total += len(re.findall(r'\[\[', content))
        except Exception:
            pass
    return total


def check_core_belief_drift():
    """Check how many core beliefs are still present in MEMORY.md."""
    memory_file = MEMORY_DIR / "MEMORY.md"
    if not memory_file.exists():
        return 0, len(CORE_BELIEFS)

    content = memory_file.read_text().lower()
    found = 0
    for belief in CORE_BELIEFS:
        # Check for key phrases from each belief
        key_phrase = belief.lower().split("=")[0].strip() if "=" in belief else belief.lower()[:30]
        if key_phrase in content:
            found += 1
    return found, len(CORE_BELIEFS)


def get_last_entry():
    """Get the last tracking entry for delta calculations."""
    if not TRACKING_FILE.exists():
        return None
    try:
        lines = TRACKING_FILE.read_text().strip().splitlines()
        if lines:
            return json.loads(lines[-1])
    except Exception:
        pass
    return None


# ─── Vault Graph Helpers (shared by health metrics) ─────────────────────────

def _build_vault_graph():
    """Build note inventory and link maps for orphan/dangling analysis.

    Returns:
        note_titles: set of normalized note titles (stem, lowered)
        note_files: dict mapping normalized title -> Path
        outgoing_links: dict mapping Path -> list of raw link targets
        all_raw_links: list of all raw link targets across vault
    """
    if not VAULT_DIR.exists():
        return set(), {}, {}, []

    note_files = {}
    outgoing_links = {}
    all_raw_links = []

    for f in VAULT_DIR.rglob("*.md"):
        title_norm = f.stem.lower()
        note_files[title_norm] = f

        try:
            content = f.read_text()
        except Exception:
            continue

        # Extract all [[link targets]] (strip any alias after |)
        links = re.findall(r'\[\[([^\]]+)\]\]', content)
        cleaned = []
        for link in links:
            target = link.split("|")[0].strip()
            cleaned.append(target)
        outgoing_links[f] = cleaned
        all_raw_links.extend(cleaned)

    note_titles = set(note_files.keys())
    return note_titles, note_files, outgoing_links, all_raw_links


def _parse_frontmatter(filepath):
    """Parse YAML frontmatter from a markdown file.

    Returns a dict of frontmatter fields, or None if no frontmatter found.
    """
    try:
        content = filepath.read_text()
    except Exception:
        return None

    if not content.startswith("---"):
        return None

    end_idx = content.find("---", 3)
    if end_idx == -1:
        return None

    fm_text = content[3:end_idx].strip()
    # Simple YAML-ish parser — good enough for flat key: value frontmatter
    fields = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', line)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip().strip('"').strip("'")
            fields[key] = value
    return fields


# ─── Health Metric Functions ─────────────────────────────────────────────────

def measure_memory_line_count():
    """Metric 1: MEMORY.md line count. Optimal range 100-160."""
    memory_file = MEMORY_DIR / "MEMORY.md"
    if not memory_file.exists():
        return 0
    try:
        lines = memory_file.read_text().splitlines()
        return len(lines)
    except Exception:
        return 0


def measure_scratchpad_staleness():
    """Metric 2: Days since most recent timestamp in scratchpad.md.

    Looks for patterns like 'HH:MM' at line start or '### Mon DD, YYYY' date headers.
    Returns float days since most recent timestamp, or -1 if no timestamps found.
    """
    scratchpad = MEMORY_DIR / "scratchpad.md"
    if not scratchpad.exists():
        return -1.0

    try:
        content = scratchpad.read_text()
    except Exception:
        return -1.0

    now = datetime.now()
    most_recent = None

    # Strategy: find date headers like "### Mar 7, 2026" or "### Mar 10, 2026"
    # then combine with time stamps like "- HH:MM —" under them
    date_pattern = re.compile(r'###\s+(\w{3})\s+(\d{1,2}),?\s+(\d{4})')
    time_pattern = re.compile(r'-\s+(\d{1,2}):(\d{2})\s')

    current_date = None
    for line in content.splitlines():
        date_match = date_pattern.search(line)
        if date_match:
            month_str, day_str, year_str = date_match.groups()
            try:
                current_date = datetime.strptime(f"{month_str} {day_str} {year_str}", "%b %d %Y")
            except ValueError:
                pass
            # Even a date header alone counts
            if current_date and (most_recent is None or current_date > most_recent):
                most_recent = current_date
            continue

        if current_date:
            time_match = time_pattern.search(line)
            if time_match:
                h, m = int(time_match.group(1)), int(time_match.group(2))
                ts = current_date.replace(hour=h, minute=m)
                if most_recent is None or ts > most_recent:
                    most_recent = ts

    if most_recent is None:
        return -1.0

    delta = now - most_recent
    return round(delta.total_seconds() / 86400, 2)


def measure_active_tasks_ratio():
    """Metric 3: Completion ratio from active-tasks.md.

    Returns (done_count, active_count, ratio) where ratio = done / (done + active).
    """
    tasks_file = MEMORY_DIR / "active-tasks.md"
    if not tasks_file.exists():
        return 0, 0, 0.0

    try:
        content = tasks_file.read_text()
    except Exception:
        return 0, 0, 0.0

    # Parse sections: IN PROGRESS and DONE
    active_count = 0
    done_count = 0
    current_section = None

    for line in content.splitlines():
        stripped = line.strip()

        # Detect section headers
        if re.match(r'^##\s+IN\s+PROGRESS', stripped, re.IGNORECASE):
            current_section = "active"
            continue
        elif re.match(r'^##\s+DONE', stripped, re.IGNORECASE):
            current_section = "done"
            continue
        elif re.match(r'^##\s+NEXT', stripped, re.IGNORECASE):
            current_section = "next"
            continue
        elif re.match(r'^##\s+BLOCKED', stripped, re.IGNORECASE):
            current_section = "blocked"
            continue
        elif re.match(r'^##\s', stripped):
            current_section = "other"
            continue

        # Count task items (lines starting with - )
        if stripped.startswith("- ") or stripped.startswith("* "):
            if current_section == "active":
                active_count += 1
            elif current_section == "done":
                done_count += 1

    total = done_count + active_count
    ratio = round(done_count / total, 3) if total > 0 else 0.0
    return done_count, active_count, ratio


def measure_orphan_notes(note_titles, outgoing_links):
    """Metric 4: Notes with zero incoming wikilinks.

    An orphan is a note that no other note links to.
    Domain maps (top-level notes/) are excluded since they're entry points.
    """
    # Build set of all link targets (normalized)
    incoming = set()
    for source, links in outgoing_links.items():
        for target in links:
            incoming.add(target.lower())

    orphans = []
    for f in VAULT_DIR.rglob("*.md"):
        # Skip top-level domain maps / MOCs — they're navigation hubs, not content notes
        if f.parent == VAULT_DIR:
            continue

        title_norm = f.stem.lower()
        if title_norm not in incoming:
            orphans.append(f.stem)

    return orphans


def measure_dangling_links(note_titles, all_raw_links):
    """Metric 5: Wikilinks pointing to non-existent notes.

    A dangling link is a [[target]] where no file with that stem exists in the vault.
    """
    dangling = set()
    for target in all_raw_links:
        target_norm = target.lower()
        if target_norm not in note_titles:
            dangling.add(target)
    return sorted(dangling)


def measure_trading_activity():
    """Metric 6: Line count in the most recent momo_*.log file.

    Returns (line_count, log_filename) or (0, None) if no logs found.
    """
    if not LOGS_DIR.exists():
        return 0, None

    momo_logs = sorted(LOGS_DIR.glob("momo_*.log"))
    if not momo_logs:
        return 0, None

    most_recent = momo_logs[-1]
    try:
        line_count = len(most_recent.read_text().splitlines())
        return line_count, most_recent.name
    except Exception:
        return 0, most_recent.name


def measure_autopoiesis_closure():
    """Metric 7: Autopoiesis loop closure rate from scaffold_modifications.jsonl.

    Closure = entries where modifications_type != "none" and != "maintenance" / total entries.
    A "closed loop" means the scaffold actually modified itself, not just monitored.
    Returns (closure_count, total_count, rate).
    """
    jsonl_file = LOGS_DIR / "scaffold_modifications.jsonl"
    if not jsonl_file.exists():
        return 0, 0, 0.0

    try:
        lines = jsonl_file.read_text().strip().splitlines()
    except Exception:
        return 0, 0, 0.0

    total = 0
    closure = 0
    for line in lines:
        try:
            entry = json.loads(line)
            total += 1
            mod_type = entry.get("modifications_type", "none")
            if mod_type not in ("none", "maintenance"):
                closure += 1
        except json.JSONDecodeError:
            continue

    rate = round(closure / total, 3) if total > 0 else 0.0
    return closure, total, rate


def measure_schema_violations(note_files):
    """Metric 8: Notes missing required frontmatter fields (summary, type, status).

    Returns (violation_count, violations_detail) where detail is list of (filename, missing_fields).
    """
    violations = []
    for title_norm, filepath in note_files.items():
        fm = _parse_frontmatter(filepath)
        if fm is None:
            # No frontmatter at all — skip top-level MOCs which may have different schema
            if filepath.parent == VAULT_DIR:
                # MOCs might have minimal frontmatter, still check
                violations.append((filepath.stem, REQUIRED_FRONTMATTER[:]))
            else:
                violations.append((filepath.stem, REQUIRED_FRONTMATTER[:]))
            continue

        missing = [field for field in REQUIRED_FRONTMATTER if field not in fm or not fm[field]]
        if missing:
            violations.append((filepath.stem, missing))

    return len(violations), violations


def measure_session_recency():
    """Metric 9: Days since last journal.md entry.

    Looks for date headers like '### Mar 9 Session N' or '### Mar 9, 2026'.
    Returns float days, or -1 if no dates found.
    """
    journal = MEMORY_DIR / "journal.md"
    if not journal.exists():
        return -1.0

    try:
        content = journal.read_text()
    except Exception:
        return -1.0

    now = datetime.now()

    # Match patterns like "### Mar 9 Session 7" or "### Mar 9, 2026"
    # Journal entries use format: ### Mon D Session N — Title
    date_pattern = re.compile(r'###\s+(\w{3})\s+(\d{1,2})\b')

    most_recent = None
    current_year = now.year

    for line in content.splitlines():
        match = date_pattern.search(line)
        if match:
            month_str, day_str = match.groups()
            # Try to parse with current year (journal entries may omit year)
            for year in [current_year, current_year - 1]:
                try:
                    dt = datetime.strptime(f"{month_str} {day_str} {year}", "%b %d %Y")
                    # Sanity: don't accept future dates
                    if dt <= now and (most_recent is None or dt > most_recent):
                        most_recent = dt
                    break
                except ValueError:
                    continue

    if most_recent is None:
        return -1.0

    delta = now - most_recent
    return round(delta.total_seconds() / 86400, 2)


# ─── Composite Health Score ──────────────────────────────────────────────────

def compute_health_score(health):
    """Compute composite scaffold health score (0-100) from 9 health metrics.

    Weights:
      memory_lines:      10pts  (optimal 100-160, penalty above/below)
      scratchpad_stale:  10pts  (0 days=10, >7 days=0)
      tasks_ratio:       10pts  (higher completion = better)
      orphans:           10pts  (0 orphans=10, >5=0)
      dangling:          10pts  (0 dangling=10, >10=0)
      trading_activity:  10pts  (recent log lines=10, 0=0)
      autopoiesis:       15pts  (>30% closure=15, 0%=0)
      schema_violations: 10pts  (0=10, >20=0)
      session_recency:   15pts  (0 days=15, >3 days=0)
    """
    score = 0.0
    breakdown = {}

    # 1. Memory line count (10pts) — optimal 100-160
    lines = health.get("memory_lines", 0)
    if 100 <= lines <= 160:
        pts = 10.0
    elif lines < 100:
        # Scale: 0 lines = 0pts, 100 lines = 10pts
        pts = max(0.0, (lines / 100) * 10.0)
    else:
        # Scale: 160 lines = 10pts, 300+ lines = 0pts
        pts = max(0.0, 10.0 - ((lines - 160) / 140) * 10.0)
    breakdown["memory_lines"] = round(pts, 1)
    score += pts

    # 2. Scratchpad staleness (10pts) — 0 days=10, >7 days=0
    stale = health.get("scratchpad_staleness_days", -1)
    if stale < 0:
        pts = 0.0  # No data = worst
    elif stale <= 0.5:
        pts = 10.0  # Same day
    elif stale >= 7:
        pts = 0.0
    else:
        pts = max(0.0, 10.0 * (1 - stale / 7))
    breakdown["scratchpad_stale"] = round(pts, 1)
    score += pts

    # 3. Active-tasks ratio (10pts) — higher done/(done+active) = better
    ratio = health.get("tasks_completion_ratio", 0)
    pts = ratio * 10.0
    breakdown["tasks_ratio"] = round(pts, 1)
    score += pts

    # 4. Orphan notes (10pts) — 0=10, >5=0
    orphan_count = health.get("orphan_count", 0)
    if orphan_count == 0:
        pts = 10.0
    elif orphan_count >= 5:
        pts = 0.0
    else:
        pts = 10.0 * (1 - orphan_count / 5)
    breakdown["orphans"] = round(pts, 1)
    score += pts

    # 5. Dangling links (10pts) — 0=10, >10=0
    dangling_count = health.get("dangling_count", 0)
    if dangling_count == 0:
        pts = 10.0
    elif dangling_count >= 10:
        pts = 0.0
    else:
        pts = 10.0 * (1 - dangling_count / 10)
    breakdown["dangling"] = round(pts, 1)
    score += pts

    # 6. Trading activity (10pts) — log lines: 0=0, 100+=10
    log_lines = health.get("trading_log_lines", 0)
    if log_lines == 0:
        pts = 0.0
    elif log_lines >= 100:
        pts = 10.0
    else:
        pts = (log_lines / 100) * 10.0
    breakdown["trading_activity"] = round(pts, 1)
    score += pts

    # 7. Autopoiesis loop closure (15pts) — >30%=15, 0%=0
    closure_rate = health.get("autopoiesis_closure_rate", 0)
    if closure_rate >= 0.30:
        pts = 15.0
    elif closure_rate <= 0:
        pts = 0.0
    else:
        pts = (closure_rate / 0.30) * 15.0
    breakdown["autopoiesis"] = round(pts, 1)
    score += pts

    # 8. Schema violations (10pts) — 0=10, >20=0
    violations = health.get("schema_violation_count", 0)
    if violations == 0:
        pts = 10.0
    elif violations >= 20:
        pts = 0.0
    else:
        pts = 10.0 * (1 - violations / 20)
    breakdown["schema"] = round(pts, 1)
    score += pts

    # 9. Session recency (15pts) — 0 days=15, >3 days=0
    recency = health.get("session_recency_days", -1)
    if recency < 0:
        pts = 0.0
    elif recency <= 0.5:
        pts = 15.0  # Same day
    elif recency >= 3:
        pts = 0.0
    else:
        pts = max(0.0, 15.0 * (1 - recency / 3))
    breakdown["session_recency"] = round(pts, 1)
    score += pts

    return round(score, 1), breakdown


# ─── Main Logging ────────────────────────────────────────────────────────────

def log_current_state():
    """Log current vault metrics + health metrics."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Existing metrics ---
    notes = count_notes()
    maps = count_domain_maps()
    links = count_wiki_links()
    beliefs_found, beliefs_total = check_core_belief_drift()
    link_density = round(links / notes, 2) if notes > 0 else 0

    last = get_last_entry()

    entry = {
        "ts": datetime.now().isoformat(),
        "notes": notes,
        "domain_maps": maps,
        "wiki_links": links,
        "link_density": link_density,
        "core_beliefs_stable": beliefs_found,
        "core_beliefs_total": beliefs_total,
        "belief_stability": round(beliefs_found / beliefs_total, 2) if beliefs_total > 0 else 0,
    }

    # Calculate deltas if we have a previous entry
    if last:
        entry["delta_notes"] = notes - last.get("notes", 0)
        entry["delta_links"] = links - last.get("wiki_links", 0)
        entry["delta_maps"] = maps - last.get("domain_maps", 0)
        new_notes = max(0, entry["delta_notes"])
        entry["refinement_ratio"] = 0.0  # Can't measure edits vs creates without git

    # --- Health metrics (9 dimensions) ---
    note_titles, note_files, outgoing_links, all_raw_links = _build_vault_graph()

    # 1. MEMORY.md line count
    memory_lines = measure_memory_line_count()
    entry["memory_lines"] = memory_lines

    # 2. Scratchpad staleness
    scratchpad_stale = measure_scratchpad_staleness()
    entry["scratchpad_staleness_days"] = scratchpad_stale

    # 3. Active-tasks ratio
    done, active, tasks_ratio = measure_active_tasks_ratio()
    entry["tasks_done"] = done
    entry["tasks_active"] = active
    entry["tasks_completion_ratio"] = tasks_ratio

    # 4. Orphan notes
    orphans = measure_orphan_notes(note_titles, outgoing_links)
    entry["orphan_count"] = len(orphans)
    entry["orphan_notes"] = orphans[:10]  # Cap detail at 10 to keep JSONL manageable

    # 5. Dangling links
    dangling = measure_dangling_links(note_titles, all_raw_links)
    entry["dangling_count"] = len(dangling)
    entry["dangling_links"] = dangling[:10]  # Cap detail at 10

    # 6. Trading journal activity
    log_lines, log_name = measure_trading_activity()
    entry["trading_log_lines"] = log_lines
    entry["trading_log_file"] = log_name

    # 7. Autopoiesis loop closure
    closure, total, closure_rate = measure_autopoiesis_closure()
    entry["autopoiesis_closure_count"] = closure
    entry["autopoiesis_total_entries"] = total
    entry["autopoiesis_closure_rate"] = closure_rate

    # 8. Schema violations
    violation_count, violations_detail = measure_schema_violations(note_files)
    entry["schema_violation_count"] = violation_count
    # Store first 10 violation summaries
    entry["schema_violations_sample"] = [
        {"note": name, "missing": fields} for name, fields in violations_detail[:10]
    ]

    # 9. Session recency
    session_recency = measure_session_recency()
    entry["session_recency_days"] = session_recency

    # --- Composite health score ---
    health_score, health_breakdown = compute_health_score(entry)
    entry["health_score"] = health_score
    entry["health_breakdown"] = health_breakdown

    # --- Write JSONL ---
    with open(TRACKING_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # --- Console output ---
    print(f"Eigenform Tracker — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")
    print(f"\n  Vault Metrics:")
    print(f"    Notes:          {notes}")
    print(f"    Domain maps:    {maps}")
    print(f"    Wiki links:     {links}")
    print(f"    Link density:   {link_density:.2f} links/note")
    print(f"    Core beliefs:   {beliefs_found}/{beliefs_total} stable ({entry['belief_stability']:.0%})")

    if last:
        print(f"\n  Deltas since last measurement:")
        print(f"    Notes:  {entry.get('delta_notes', 0):+d}")
        print(f"    Links:  {entry.get('delta_links', 0):+d}")
        print(f"    Maps:   {entry.get('delta_maps', 0):+d}")

    print(f"\n  Health Metrics:")
    print(f"    MEMORY.md lines:     {memory_lines}" +
          (" (optimal)" if 100 <= memory_lines <= 160 else
           " (bloated)" if memory_lines > 160 else " (thin)"))
    print(f"    Scratchpad stale:    {scratchpad_stale:.1f} days" if scratchpad_stale >= 0
          else f"    Scratchpad stale:    N/A (no timestamps)")
    print(f"    Tasks ratio:         {done}D / {active}A = {tasks_ratio:.1%} complete")
    print(f"    Orphan notes:        {len(orphans)}" +
          (f" ({', '.join(orphans[:3])}...)" if len(orphans) > 3
           else f" ({', '.join(orphans)})" if orphans else ""))
    print(f"    Dangling links:      {len(dangling)}" +
          (f" ({', '.join(dangling[:3])}...)" if len(dangling) > 3
           else f" ({', '.join(dangling)})" if dangling else ""))
    print(f"    Trading log lines:   {log_lines}" +
          (f" ({log_name})" if log_name else ""))
    print(f"    Autopoiesis closure: {closure}/{total} = {closure_rate:.1%}")
    print(f"    Schema violations:   {violation_count}")
    print(f"    Session recency:     {session_recency:.1f} days" if session_recency >= 0
          else f"    Session recency:     N/A (no journal dates)")

    print(f"\n  Scaffold Health Score: {health_score}/100")
    print(f"    Breakdown: " + " | ".join(f"{k}={v}" for k, v in health_breakdown.items()))

    print(f"\n  Logged to: {TRACKING_FILE}")
    return entry


def show_report():
    """Show convergence report from historical data."""
    if not TRACKING_FILE.exists():
        print("No tracking data yet. Run without --report first.")
        return

    entries = []
    for line in TRACKING_FILE.read_text().strip().splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    if len(entries) < 2:
        print(f"Only {len(entries)} data point(s). Need 2+ for trend analysis.")
        log_current_state()
        return

    print(f"Eigenform Convergence Report — {len(entries)} data points")
    print(f"{'='*60}")

    # Note growth trend
    note_counts = [e["notes"] for e in entries]
    note_deltas = [note_counts[i] - note_counts[i-1] for i in range(1, len(note_counts))]
    avg_growth = sum(note_deltas) / len(note_deltas) if note_deltas else 0

    print(f"\n  Note Growth:")
    print(f"    Range: {note_counts[0]} -> {note_counts[-1]} ({note_counts[-1] - note_counts[0]:+d})")
    print(f"    Avg growth per measurement: {avg_growth:.1f}")
    if len(note_deltas) >= 3:
        early = sum(note_deltas[:len(note_deltas)//2]) / (len(note_deltas)//2)
        late = sum(note_deltas[len(note_deltas)//2:]) / (len(note_deltas) - len(note_deltas)//2)
        print(f"    Early avg: {early:.1f}, Late avg: {late:.1f}")
        if late < early:
            print(f"    -> CONVERGING (growth decelerating)")
        else:
            print(f"    -> DIVERGING (growth accelerating)")

    # Link density trend
    densities = [e.get("link_density", 0) for e in entries]
    print(f"\n  Link Density:")
    print(f"    Range: {densities[0]:.2f} -> {densities[-1]:.2f}")
    density_variance = sum((d - sum(densities)/len(densities))**2 for d in densities) / len(densities)
    print(f"    Variance: {density_variance:.4f}")
    if density_variance < 0.5:
        print(f"    -> STABLE")
    else:
        print(f"    -> FLUCTUATING")

    # Domain map stability
    map_counts = [e.get("domain_maps", 0) for e in entries]
    print(f"\n  Domain Maps:")
    print(f"    Range: {min(map_counts)} -> {max(map_counts)}")
    if max(map_counts) - min(map_counts) <= 2:
        print(f"    -> STABLE")
    else:
        print(f"    -> CHANGING")

    # Core belief stability
    belief_stabs = [e.get("belief_stability", 0) for e in entries]
    print(f"\n  Core Belief Stability:")
    print(f"    Range: {min(belief_stabs):.0%} -> {max(belief_stabs):.0%}")
    if all(b >= 0.8 for b in belief_stabs):
        print(f"    -> EIGENFORM CANDIDATE (beliefs stable across all measurements)")
    elif belief_stabs[-1] >= 0.8:
        print(f"    -> CONVERGING (recent stability high)")
    else:
        print(f"    -> EVOLVING (beliefs still changing)")

    # Health score trend (if available)
    health_scores = [e.get("health_score") for e in entries if "health_score" in e]
    if health_scores:
        print(f"\n  Scaffold Health Score:")
        print(f"    Range: {min(health_scores):.1f} -> {max(health_scores):.1f}")
        avg_health = sum(health_scores) / len(health_scores)
        print(f"    Average: {avg_health:.1f}/100")
        if len(health_scores) >= 3:
            recent_3 = health_scores[-3:]
            early_3 = health_scores[:3]
            avg_recent = sum(recent_3) / len(recent_3)
            avg_early = sum(early_3) / len(early_3)
            if avg_recent > avg_early:
                print(f"    -> IMPROVING ({avg_early:.1f} -> {avg_recent:.1f})")
            elif avg_recent < avg_early:
                print(f"    -> DEGRADING ({avg_early:.1f} -> {avg_recent:.1f})")
            else:
                print(f"    -> STABLE")

    # Overall verdict
    print(f"\n{'='*60}")
    print(f"  OVERALL: ", end="")
    convergence_signals = 0
    if len(note_deltas) >= 3 and late < early:
        convergence_signals += 1
    if density_variance < 0.5:
        convergence_signals += 1
    if max(map_counts) - min(map_counts) <= 2:
        convergence_signals += 1
    if all(b >= 0.8 for b in belief_stabs):
        convergence_signals += 1

    total_signals = 4
    # Add health score signal if available
    if health_scores and len(health_scores) >= 2:
        total_signals += 1
        if health_scores[-1] >= 70:
            convergence_signals += 1

    if convergence_signals >= (total_signals - 1):
        print(f"CONVERGING ({convergence_signals}/{total_signals} signals)")
    elif convergence_signals >= (total_signals // 2):
        print(f"TRENDING toward convergence ({convergence_signals}/{total_signals} signals)")
    else:
        print(f"NOT YET converging ({convergence_signals}/{total_signals} signals) — need more data")


def show_plot():
    """ASCII plot of key metrics over time."""
    if not TRACKING_FILE.exists():
        print("No tracking data yet.")
        return

    entries = []
    for line in TRACKING_FILE.read_text().strip().splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    if len(entries) < 2:
        print(f"Need 2+ data points for a plot. Currently: {len(entries)}")
        return

    bars = "▁▂▃▄▅▆▇█"

    def sparkline(values, label, fmt="{:.0f}"):
        """Render a sparkline for a list of numeric values."""
        filtered = [v for v in values if v is not None]
        if not filtered:
            return
        min_v, max_v = min(filtered), max(filtered)
        range_v = max_v - min_v or 1
        line = ""
        for v in values:
            if v is None:
                line += " "
            else:
                idx = int((v - min_v) / range_v * (len(bars) - 1))
                line += bars[idx]
        print(f"{label} ({fmt.format(min_v)}-{fmt.format(max_v)}):")
        print(f"  {line}")

    # Simple ASCII sparkline for notes
    note_counts = [e["notes"] for e in entries]
    sparkline(note_counts, "Notes")

    # Link density
    densities = [e.get("link_density", 0) for e in entries]
    sparkline(densities, "\nLink density", fmt="{:.1f}")

    # Health score (if available)
    health_scores = [e.get("health_score") for e in entries]
    if any(h is not None for h in health_scores):
        sparkline(health_scores, "\nHealth score", fmt="{:.0f}")

    # Orphan count (if available)
    orphan_counts = [e.get("orphan_count") for e in entries]
    if any(o is not None for o in orphan_counts):
        sparkline(orphan_counts, "\nOrphan notes", fmt="{:.0f}")

    # Schema violations (if available)
    violation_counts = [e.get("schema_violation_count") for e in entries]
    if any(v is not None for v in violation_counts):
        sparkline(violation_counts, "\nSchema violations", fmt="{:.0f}")


def main():
    parser = argparse.ArgumentParser(description="Eigenform Convergence Tracker")
    parser.add_argument("--report", action="store_true", help="Show convergence report")
    parser.add_argument("--plot", action="store_true", help="Show ASCII convergence plot")
    args = parser.parse_args()

    if args.report:
        show_report()
    elif args.plot:
        show_plot()
    else:
        log_current_state()


if __name__ == "__main__":
    main()
