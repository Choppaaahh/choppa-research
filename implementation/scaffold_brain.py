#!/usr/bin/env python3
"""
Scaffold Brain — Closed-Loop Self-Learning Meta-Controller

Reads all task outputs (eigenform, autopoiesis, topology, scheduler logs),
detects gaps, generates proposals, measures outcomes, and self-tunes.

Runs every 6 hours via CC scheduler. Pure filesystem, zero API calls.

Architecture:
    SCHEDULED TASKS (existing 12) → write logs + JSONL
        ↓
    scaffold_brain.py (this file)
        ├→ TaskOutputReader:   ingests all data sources
        ├→ GapDetector:        topology, health, freshness, coverage, fidelity
        ├→ PriorityScorer:     ranks gaps by severity × persistence × impact
        ├→ ActionGenerator:    converts gaps → proposals
        ├→ FeedbackMeasurer:   did past proposals work? learning velocity?
        ├→ SelfTuner:          recommend frequency/parameter changes
        └→ BrainState:         snapshot for sessions + human summary
             ├→ logs/brain_state.json
             └→ logs/brain_proposals.jsonl

Guardrails:
    - NEVER writes to vault notes, MEMORY.md, or scaffold files directly
    - Only writes to its own output files (brain_state.json, brain_proposals.jsonl)
    - Critical proposals default to review_mode: "human"
    - Kill switch: health_score < 40 → report-only mode
    - Max 5 proposals per cycle, max 10 files affected per proposal
    - Task frequency bounds: min 1x/week, max 1x/hour

Usage:
    python3 scripts/scaffold_brain.py              # run brain cycle, human output
    python3 scripts/scaffold_brain.py --json        # structured JSON output
    python3 scripts/scaffold_brain.py --proposals    # show active proposals
    python3 scripts/scaffold_brain.py --velocity     # show learning velocity
"""

import json
import os
import re
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# ─── Configuration ──────────────────────────────────────────────────────────

BASE_DIR = Path.home() / "Flex" / "Trading"
VAULT_DIR = BASE_DIR / "knowledge" / "notes"
# Auto-detect memory dir (Pi vs Mac)
if (Path.home() / ".claude" / "projects" / "YOUR-PROJECT-PATH" / "memory").exists():
    MEMORY_DIR = Path.home() / ".claude" / "projects" / "YOUR-PROJECT-PATH" / "memory"
else:
    MEMORY_DIR = Path.home() / ".claude" / "projects" / "YOUR-PROJECT-PATH" / "memory"
LOGS_DIR = BASE_DIR / "logs"
SCHED_LOGS = Path.home() / ".claude" / "scheduled" / "logs"

EIGENFORM_FILE = LOGS_DIR / "eigenform_tracking.jsonl"
MODIFICATIONS_FILE = LOGS_DIR / "scaffold_modifications.jsonl"
BRAIN_STATE_FILE = LOGS_DIR / "brain_state.json"
BRAIN_PROPOSALS_FILE = LOGS_DIR / "brain_proposals.jsonl"

MAX_PROPOSALS_PER_CYCLE = 5
MAX_FILES_PER_PROPOSAL = 10
HEALTH_KILL_SWITCH = 40
FRESHNESS_STALE_DAYS = 14
ROLLING_AVG_WINDOW = 3
HEALTH_REGRESSION_THRESHOLD = 0.10  # 10% drop

# ─── TaskOutputReader ───────────────────────────────────────────────────────


class TaskOutputReader:
    """Reads all existing data sources produced by scheduled tasks."""

    def __init__(self):
        self.eigenform_entries = []
        self.modification_entries = []
        self.topology_data = None
        self.scheduler_log_patterns = {}

    def read_all(self):
        """Read all data sources. Returns self for chaining."""
        self._read_eigenform()
        self._read_modifications()
        self._read_topology()
        self._read_scheduler_logs()
        return self

    def _read_eigenform(self):
        """Read eigenform tracking JSONL."""
        if not EIGENFORM_FILE.exists():
            return
        for line in EIGENFORM_FILE.read_text().strip().splitlines():
            try:
                self.eigenform_entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    def _read_modifications(self):
        """Read scaffold modifications JSONL."""
        if not MODIFICATIONS_FILE.exists():
            return
        for line in MODIFICATIONS_FILE.read_text().strip().splitlines():
            try:
                self.modification_entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    def _read_topology(self):
        """Import vault_topology functions and run analysis."""
        try:
            # Import vault_topology from same directory
            sys.path.insert(0, str(BASE_DIR / "scripts"))
            import vault_topology as vt

            notes = vt.extract_notes(str(VAULT_DIR))
            if not notes:
                return

            outgoing, incoming, dangling = vt.build_graph(notes)
            clusters = vt.find_clusters(notes, outgoing, incoming)
            metrics = vt.compute_metrics(notes, outgoing, incoming)
            domains = vt.auto_discover_domains(notes, outgoing, metrics)

            self.topology_data = {
                "notes": notes,
                "outgoing": outgoing,
                "incoming": incoming,
                "dangling": dangling,
                "clusters": clusters,
                "metrics": metrics,
                "domains": domains,
                "total_notes": len(notes),
                "total_links": sum(len(v) for v in outgoing.values()),
                "avg_degree": (
                    sum(m["total"] for m in metrics.values()) / len(notes)
                    if notes else 0
                ),
                "isolated_count": sum(
                    1 for m in metrics.values() if m["role"] == "isolated"
                ),
                "dangling_count": sum(len(v) for v in dangling.values()),
            }
        except Exception as e:
            # Topology is optional — don't crash if it fails
            self.topology_data = None
            print(f"  [warn] topology import failed: {e}", file=sys.stderr)

    def _read_scheduler_logs(self):
        """Parse scheduler logs for key patterns."""
        if not SCHED_LOGS.exists():
            return

        patterns = {
            "errors": re.compile(r"(?:ERROR|FAIL|CRITICAL)", re.IGNORECASE),
            "repairs": re.compile(r"(?:FIX|REPAIR|ADDED|PROMOTED)", re.IGNORECASE),
            "warnings": re.compile(r"(?:WARN|STALE|BLOAT|MISSING)", re.IGNORECASE),
        }

        for log_path in sorted(SCHED_LOGS.glob("*.log")):
            if log_path.name.endswith(".err.log"):
                continue
            task_name = log_path.stem
            try:
                content = log_path.read_text(errors="replace")
                lines = content.splitlines()
                task_patterns = {
                    "line_count": len(lines),
                    "last_modified": datetime.fromtimestamp(
                        log_path.stat().st_mtime
                    ).isoformat(),
                    "errors": 0,
                    "repairs": 0,
                    "warnings": 0,
                }
                for line in lines[-200:]:  # scan last 200 lines
                    for name, pattern in patterns.items():
                        if pattern.search(line):
                            task_patterns[name] += 1
                self.scheduler_log_patterns[task_name] = task_patterns
            except Exception:
                continue

    def latest_eigenform(self):
        """Get most recent eigenform entry."""
        return self.eigenform_entries[-1] if self.eigenform_entries else None

    def latest_health_score(self):
        """Get most recent health score."""
        entry = self.latest_eigenform()
        return entry.get("health_score", 0) if entry else 0


# ─── GapDetector ────────────────────────────────────────────────────────────


class GapDetector:
    """Detects gaps across five dimensions."""

    def __init__(self, reader):
        self.reader = reader

    def detect_all(self):
        """Run all gap detectors, return list of gap dicts."""
        gaps = []
        gaps.extend(self.detect_topology_gaps())
        gaps.extend(self.detect_health_gaps())
        gaps.extend(self.detect_freshness_gaps())
        gaps.extend(self.detect_coverage_gaps())
        gaps.extend(self.detect_fidelity_gaps())
        return gaps

    def detect_topology_gaps(self):
        """Find low-cohesion domains, orphans, dangling links, weak bridges."""
        gaps = []
        topo = self.reader.topology_data
        if not topo:
            return gaps

        # Low-cohesion domains
        for domain in topo.get("domains", []):
            if domain["cohesion"] < 0.15:
                gaps.append({
                    "type": "topology_low_cohesion",
                    "severity": "high",
                    "target": domain["folder"],
                    "detail": (
                        f"Domain '{domain['suggested_name']}' has "
                        f"{int(domain['cohesion'] * 100)}% cohesion "
                        f"({domain['size']} notes)"
                    ),
                    "metric_value": domain["cohesion"],
                })

        # Orphan notes (isolated)
        if topo["isolated_count"] > 3:
            gaps.append({
                "type": "topology_orphans",
                "severity": "medium",
                "target": "vault",
                "detail": (
                    f"{topo['isolated_count']} isolated notes with "
                    f"zero connections"
                ),
                "metric_value": topo["isolated_count"],
            })

        # Dangling links
        if topo["dangling_count"] > 5:
            gaps.append({
                "type": "topology_dangling",
                "severity": "medium",
                "target": "vault",
                "detail": (
                    f"{topo['dangling_count']} dangling links "
                    f"(references to non-existent notes)"
                ),
                "metric_value": topo["dangling_count"],
            })

        # Low average degree
        if topo["avg_degree"] < 3.0:
            gaps.append({
                "type": "topology_sparse",
                "severity": "high",
                "target": "vault",
                "detail": (
                    f"Avg degree {topo['avg_degree']:.1f} < 3.0 — "
                    f"weak connectivity"
                ),
                "metric_value": topo["avg_degree"],
            })

        return gaps

    def detect_health_gaps(self):
        """Read eigenform JSONL, flag regressions from rolling average."""
        gaps = []
        entries = self.reader.eigenform_entries
        if len(entries) < 2:
            return gaps

        latest = entries[-1]
        # Compare against rolling avg of prior entries
        window = entries[-(ROLLING_AVG_WINDOW + 1):-1]
        if not window:
            return gaps

        # Health score regression
        avg_health = sum(e.get("health_score", 0) for e in window) / len(window)
        current_health = latest.get("health_score", 0)
        if avg_health > 0 and current_health < avg_health * (1 - HEALTH_REGRESSION_THRESHOLD):
            gaps.append({
                "type": "health_regression",
                "severity": "critical",
                "target": "scaffold",
                "detail": (
                    f"Health score dropped: {current_health:.1f} vs "
                    f"rolling avg {avg_health:.1f} "
                    f"({(1 - current_health / avg_health) * 100:.0f}% drop)"
                ),
                "metric_value": current_health,
            })

        # Per-dimension regression check
        dimensions = [
            ("memory_lines", "MEMORY.md bloat", 180, "above"),
            ("orphan_count", "orphan notes growing", 3, "above"),
            ("dangling_count", "dangling links growing", 5, "above"),
            ("autopoiesis_closure_rate", "autopoiesis declining", 0.10, "below"),
            ("schema_violation_count", "schema violations", 5, "above"),
        ]
        for dim, label, threshold, direction in dimensions:
            val = latest.get(dim)
            if val is None:
                continue
            if direction == "above" and val > threshold:
                avg_val = sum(e.get(dim, 0) for e in window) / len(window)
                if val > avg_val * 1.5:  # 50% worse than avg
                    gaps.append({
                        "type": "health_dimension",
                        "severity": "high",
                        "target": dim,
                        "detail": f"{label}: {val} (avg was {avg_val:.1f})",
                        "metric_value": val,
                    })
            elif direction == "below" and val < threshold:
                gaps.append({
                    "type": "health_dimension",
                    "severity": "medium",
                    "target": dim,
                    "detail": f"{label}: {val:.3f} < {threshold}",
                    "metric_value": val,
                })

        return gaps

    def detect_freshness_gaps(self):
        """Find stale domains — no modifications in 14+ days."""
        gaps = []
        topo = self.reader.topology_data
        if not topo:
            return gaps

        now = datetime.now()
        notes = topo["notes"]

        # Group modification times by folder
        folder_latest = defaultdict(lambda: datetime.min)
        for path, note in notes.items():
            try:
                full_path = VAULT_DIR / path
                if full_path.exists():
                    mtime = datetime.fromtimestamp(full_path.stat().st_mtime)
                    folder = note["folder"]
                    if mtime > folder_latest[folder]:
                        folder_latest[folder] = mtime
            except Exception:
                continue

        for folder, latest_mod in folder_latest.items():
            days_stale = (now - latest_mod).total_seconds() / 86400
            if days_stale > FRESHNESS_STALE_DAYS:
                gaps.append({
                    "type": "freshness_stale",
                    "severity": "low",
                    "target": folder,
                    "detail": (
                        f"Domain '{folder}' has no modifications in "
                        f"{days_stale:.0f} days"
                    ),
                    "metric_value": days_stale,
                })

        return gaps

    def detect_coverage_gaps(self):
        """Find domains with low note density relative to incoming links."""
        gaps = []
        topo = self.reader.topology_data
        if not topo:
            return gaps

        for domain in topo.get("domains", []):
            size = domain["size"]
            # Small domains with high hub degree = heavily referenced but thin
            if size <= 3 and domain["hub_degree"] > 5:
                gaps.append({
                    "type": "coverage_thin",
                    "severity": "medium",
                    "target": domain["folder"],
                    "detail": (
                        f"Domain '{domain['suggested_name']}' has only "
                        f"{size} notes but hub has {domain['hub_degree']} "
                        f"connections — needs expansion"
                    ),
                    "metric_value": size,
                })

        return gaps

    def detect_fidelity_gaps(self):
        """Parse fidelity-test logs + active-tasks for WHY/CONTEXT decay."""
        gaps = []

        # Source 1: fidelity-test log scores
        fidelity_log = SCHED_LOGS / "fidelity-test.log"
        if fidelity_log.exists():
            try:
                content = fidelity_log.read_text(errors="replace")
                why_scores = []
                context_scores = []
                for line in content.splitlines()[-100:]:
                    why_match = re.search(
                        r"WHY[:\s]+(\d+\.?\d*)", line, re.IGNORECASE
                    )
                    ctx_match = re.search(
                        r"CONTEXT[:\s]+(\d+\.?\d*)", line, re.IGNORECASE
                    )
                    if why_match:
                        why_scores.append(float(why_match.group(1)))
                    if ctx_match:
                        context_scores.append(float(ctx_match.group(1)))

                if why_scores:
                    avg_why = sum(why_scores) / len(why_scores)
                    threshold = 0.70 if avg_why <= 1.0 else 70
                    if avg_why < threshold:
                        gaps.append({
                            "type": "fidelity_why_decay",
                            "severity": "high",
                            "target": "active-tasks",
                            "detail": (
                                f"WHY fidelity avg {avg_why:.2f} below "
                                f"threshold {threshold}"
                            ),
                            "metric_value": avg_why,
                        })

                if context_scores:
                    avg_ctx = sum(context_scores) / len(context_scores)
                    threshold = 0.50 if avg_ctx <= 1.0 else 50
                    if avg_ctx < threshold:
                        gaps.append({
                            "type": "fidelity_context_decay",
                            "severity": "medium",
                            "target": "active-tasks",
                            "detail": (
                                f"CONTEXT fidelity avg {avg_ctx:.2f} below "
                                f"threshold {threshold}"
                            ),
                            "metric_value": avg_ctx,
                        })
            except Exception:
                pass

        # Source 2: active-tasks DONE entries missing "Triggered by" / context
        tasks_file = MEMORY_DIR / "active-tasks.md"
        if tasks_file.exists():
            try:
                content = tasks_file.read_text()
                in_done = False
                done_total = 0
                done_missing_context = 0
                for line in content.splitlines():
                    stripped = line.strip()
                    if re.match(r"^##\s+DONE", stripped, re.IGNORECASE):
                        in_done = True
                        continue
                    elif re.match(r"^##\s", stripped):
                        in_done = False
                        continue
                    if in_done and (
                        stripped.startswith("- ") or stripped.startswith("* ")
                    ):
                        done_total += 1
                        has_context = any(
                            kw in stripped.lower()
                            for kw in [
                                "triggered by", "context:", "because we saw",
                                "when we noticed", "after observing",
                            ]
                        )
                        if not has_context:
                            done_missing_context += 1

                if done_total > 0:
                    missing_pct = done_missing_context / done_total
                    if missing_pct > 0.5:
                        gaps.append({
                            "type": "fidelity_context_missing",
                            "severity": "high",
                            "target": "active-tasks",
                            "detail": (
                                f"{done_missing_context}/{done_total} DONE "
                                f"entries ({missing_pct:.0%}) lack triggering "
                                f"context — CONTEXT fidelity will decay"
                            ),
                            "metric_value": missing_pct,
                        })
            except Exception:
                pass

        return gaps


# ─── PriorityScorer ─────────────────────────────────────────────────────────


class PriorityScorer:
    """Scores gaps 0-100 for prioritization."""

    SEVERITY_WEIGHTS = {
        "critical": 40,
        "high": 30,
        "medium": 20,
        "low": 10,
    }

    def __init__(self):
        self.history = self._load_history()

    def _load_history(self):
        """Load past proposals to track persistence and repeats."""
        history = defaultdict(lambda: {"count": 0, "fixed_count": 0})
        if not BRAIN_PROPOSALS_FILE.exists():
            return history
        try:
            for line in BRAIN_PROPOSALS_FILE.read_text().strip().splitlines():
                try:
                    entry = json.loads(line)
                    key = f"{entry.get('gap_type', '')}:{entry.get('target', '')}"
                    history[key]["count"] += 1
                    if entry.get("status") == "resolved":
                        history[key]["fixed_count"] += 1
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        return history

    def score(self, gap):
        """Score a single gap, return 0-100."""
        score = 0.0

        # Base severity weight
        score += self.SEVERITY_WEIGHTS.get(gap.get("severity", "low"), 10)

        # Persistence bonus: +5 per consecutive detection, cap +20
        key = f"{gap['type']}:{gap.get('target', '')}"
        persistence = self.history[key]["count"]
        score += min(persistence * 5, 20)

        # Novelty bonus: +15 for never-addressed gaps
        if persistence == 0:
            score += 15

        # Repeat penalty: -10 if same gap fixed 3x without metric improvement
        fixed = self.history[key]["fixed_count"]
        if fixed >= 3 and persistence > fixed:
            score -= 10  # anti-Goodhart

        return max(0, min(100, score))

    def rank_gaps(self, gaps):
        """Score and sort gaps by priority, highest first."""
        scored = []
        for gap in gaps:
            gap["priority_score"] = self.score(gap)
            scored.append(gap)
        scored.sort(key=lambda g: -g["priority_score"])
        return scored


# ─── ActionGenerator ────────────────────────────────────────────────────────


class ActionGenerator:
    """Converts ranked gaps into actionable proposals."""

    # Map gap types to action templates
    TEMPLATES = {
        "topology_low_cohesion": {
            "action": "research",
            "description": "Run autoresearch on low-cohesion domain to add internal links",
            "executor": "connection-builder",
        },
        "topology_orphans": {
            "action": "connect",
            "description": "Connect isolated notes to nearest domain hubs",
            "executor": "vault-fix",
        },
        "topology_dangling": {
            "action": "repair",
            "description": "Fix dangling links — create missing notes or fix targets",
            "executor": "vault-fix",
        },
        "topology_sparse": {
            "action": "connect",
            "description": "Increase vault connectivity — add cross-domain bridges",
            "executor": "connection-builder",
        },
        "health_regression": {
            "action": "diagnose",
            "description": "Investigate health score regression — check breakdown dimensions",
            "executor": "health-check",
            "review_mode": "human",
        },
        "health_dimension": {
            "action": "repair",
            "description": "Address specific health dimension degradation",
            "executor": "scaffold-maintenance",
        },
        "freshness_stale": {
            "action": "refresh",
            "description": "Review stale domain — update or archive outdated notes",
            "executor": "scaffold-maintenance",
        },
        "coverage_thin": {
            "action": "research",
            "description": "Expand thin but heavily-referenced domain",
            "executor": "connection-builder",
        },
        "fidelity_why_decay": {
            "action": "repair",
            "description": "Retroactive WHY repair — add missing reasoning to decisions",
            "executor": "fidelity-test",
            "review_mode": "human",
        },
        "fidelity_context_decay": {
            "action": "repair",
            "description": "Retroactive CONTEXT repair — add triggering moments",
            "executor": "fidelity-test",
        },
        "fidelity_context_missing": {
            "action": "repair",
            "description": "DONE entries missing 'Triggered by' — add context before it decays",
            "executor": "scaffold-maintenance",
            "review_mode": "human",
        },
    }

    def generate(self, ranked_gaps):
        """Generate proposals from top-ranked gaps. Max MAX_PROPOSALS_PER_CYCLE."""
        proposals = []
        for gap in ranked_gaps[:MAX_PROPOSALS_PER_CYCLE]:
            template = self.TEMPLATES.get(gap["type"], {
                "action": "investigate",
                "description": f"Unknown gap type: {gap['type']}",
                "executor": "health-check",
            })

            proposal = {
                "ts": datetime.now().isoformat(),
                "gap_type": gap["type"],
                "target": gap.get("target", "unknown"),
                "severity": gap.get("severity", "medium"),
                "priority_score": gap.get("priority_score", 0),
                "detail": gap.get("detail", ""),
                "metric_value": gap.get("metric_value"),
                "action": template["action"],
                "description": template["description"],
                "executor": template["executor"],
                "review_mode": template.get("review_mode", "auto"),
                "status": "proposed",
                "max_files": MAX_FILES_PER_PROPOSAL,
            }
            proposals.append(proposal)

        return proposals


# ─── FeedbackMeasurer ───────────────────────────────────────────────────────


class FeedbackMeasurer:
    """Tracks outcomes and learning velocity."""

    def __init__(self, reader):
        self.reader = reader

    def compute_learning_velocity(self):
        """Compute notes/day, links/day, gaps_closed/day, health_delta/day."""
        entries = self.reader.eigenform_entries
        if len(entries) < 2:
            return {
                "notes_per_day": 0,
                "links_per_day": 0,
                "health_delta_per_day": 0,
                "data_points": len(entries),
            }

        first = entries[0]
        last = entries[-1]

        try:
            t0 = datetime.fromisoformat(first["ts"])
            t1 = datetime.fromisoformat(last["ts"])
            days = max((t1 - t0).total_seconds() / 86400, 0.01)
        except (KeyError, ValueError):
            days = 1.0

        notes_delta = last.get("notes", 0) - first.get("notes", 0)
        links_delta = last.get("wiki_links", 0) - first.get("wiki_links", 0)
        health_delta = last.get("health_score", 0) - first.get("health_score", 0)

        # Count resolved proposals
        gaps_closed = 0
        if BRAIN_PROPOSALS_FILE.exists():
            try:
                for line in BRAIN_PROPOSALS_FILE.read_text().strip().splitlines():
                    entry = json.loads(line)
                    if entry.get("status") == "resolved":
                        gaps_closed += 1
            except Exception:
                pass

        return {
            "notes_per_day": round(notes_delta / days, 2),
            "links_per_day": round(links_delta / days, 2),
            "health_delta_per_day": round(health_delta / days, 2),
            "gaps_closed_per_day": round(gaps_closed / days, 2),
            "data_points": len(entries),
            "span_days": round(days, 1),
        }

    def measure_proposal_outcomes(self):
        """Compare metrics before/after past proposals."""
        if not BRAIN_PROPOSALS_FILE.exists():
            return {"total": 0, "resolved": 0, "pending": 0, "success_rate": 0}

        total = 0
        resolved = 0
        try:
            for line in BRAIN_PROPOSALS_FILE.read_text().strip().splitlines():
                entry = json.loads(line)
                total += 1
                if entry.get("status") == "resolved":
                    resolved += 1
        except Exception:
            pass

        return {
            "total": total,
            "resolved": resolved,
            "pending": total - resolved,
            "success_rate": round(resolved / total, 2) if total > 0 else 0,
        }

    def detect_goodhart(self):
        """Flag metric gaming: one metric up while correlated metrics down."""
        entries = self.reader.eigenform_entries
        if len(entries) < 3:
            return []

        warnings = []
        latest = entries[-1]
        prev = entries[-2]

        # Correlated pairs: if one goes up and its pair goes down, flag it
        pairs = [
            ("notes", "wiki_links", "Notes up but links down"),
            ("wiki_links", "orphan_count", "Links up but orphans also up"),
            ("health_score", "schema_violation_count",
             "Health up but schema violations also up"),
        ]
        for m1, m2, msg in pairs:
            v1_new = latest.get(m1, 0)
            v1_old = prev.get(m1, 0)
            v2_new = latest.get(m2, 0)
            v2_old = prev.get(m2, 0)

            # First metric improved, second degraded
            m1_improved = v1_new > v1_old
            m2_degraded = v2_new > v2_old  # higher = worse for these metrics

            # Special case: for health_score, higher is better
            if m1 == "health_score":
                m1_improved = v1_new > v1_old
            if m2 in ("orphan_count", "schema_violation_count"):
                m2_degraded = v2_new > v2_old
            elif m2 == "wiki_links":
                m2_degraded = v2_new < v2_old  # fewer links = worse

            if m1_improved and m2_degraded:
                warnings.append({
                    "type": "goodhart_warning",
                    "detail": msg,
                    "metric_1": f"{m1}: {v1_old} → {v1_new}",
                    "metric_2": f"{m2}: {v2_old} → {v2_new}",
                })

        return warnings


# ─── SelfTuner ──────────────────────────────────────────────────────────────


class SelfTuner:
    """Recommends frequency/parameter changes for tasks."""

    # Current task frequencies (from cc_scheduler DEFAULT_TASKS)
    TASK_FREQUENCIES = {
        "health-check": "0 */4 * * *",
        "vault-fix": "0 */8 * * *",
        "scaffold-maintenance": "0 12,20 * * *",
        "connection-builder": "0 14 * * *",
        "fidelity-test": "0 */12 * * *",
        "morning-brief": "0 9 * * *",
        "self-reflection": "0 22 * * *",
        "eigenform-tracker": "0 */12 * * *",
        "topology-health": "0 6 * * 0",
        "scaffold-backup": "0 5 * * *",
        "thread-freshness": "0 8 * * 3",
        "git-sync": "0 */6 * * *",
    }

    def recommend(self, reader, gaps):
        """Generate tuning recommendations based on gap patterns."""
        recommendations = []
        log_patterns = reader.scheduler_log_patterns

        # If many topology gaps, connection-builder might need higher frequency
        topology_gaps = [g for g in gaps if g["type"].startswith("topology_")]
        if len(topology_gaps) >= 3:
            recommendations.append({
                "task": "connection-builder",
                "current": self.TASK_FREQUENCIES.get("connection-builder", "?"),
                "suggestion": "Increase to 2x/day (add morning run)",
                "reason": f"{len(topology_gaps)} topology gaps detected",
            })

        # If health is regressing, health-check could run more often
        health_gaps = [g for g in gaps if g["type"].startswith("health_")]
        if health_gaps:
            recommendations.append({
                "task": "health-check",
                "current": self.TASK_FREQUENCIES.get("health-check", "?"),
                "suggestion": "Increase to every 2 hours temporarily",
                "reason": "Health regression detected",
            })

        # If fidelity is decaying, fidelity-test should run more
        fidelity_gaps = [g for g in gaps if g["type"].startswith("fidelity_")]
        if fidelity_gaps:
            recommendations.append({
                "task": "fidelity-test",
                "current": self.TASK_FREQUENCIES.get("fidelity-test", "?"),
                "suggestion": "Increase to every 6 hours",
                "reason": "Fidelity decay detected",
            })

        # Check for tasks with high error rates in logs
        for task, patterns in log_patterns.items():
            if patterns.get("errors", 0) > 5:
                recommendations.append({
                    "task": task,
                    "current": self.TASK_FREQUENCIES.get(task, "?"),
                    "suggestion": "Investigate — high error count in logs",
                    "reason": f"{patterns['errors']} errors in recent logs",
                })

        return recommendations


# ─── BrainState ─────────────────────────────────────────────────────────────


class BrainState:
    """Builds and saves the brain state snapshot."""

    def build(self, reader, gaps, proposals, velocity, outcomes,
              goodhart_warnings, tuning_recs):
        """Build complete brain state dict."""
        latest = reader.latest_eigenform()
        health_score = latest.get("health_score", 0) if latest else 0
        report_only = health_score < HEALTH_KILL_SWITCH

        state = {
            "ts": datetime.now().isoformat(),
            "cycle": self._get_cycle_number(),
            "health_score": health_score,
            "report_only": report_only,
            "gaps_detected": len(gaps),
            "proposals_generated": len(proposals) if not report_only else 0,
            "top_gaps": [
                {
                    "type": g["type"],
                    "severity": g["severity"],
                    "target": g.get("target", ""),
                    "detail": g.get("detail", ""),
                    "priority_score": g.get("priority_score", 0),
                }
                for g in gaps[:10]
            ],
            "proposals": proposals if not report_only else [],
            "learning_velocity": velocity,
            "proposal_outcomes": outcomes,
            "goodhart_warnings": goodhart_warnings,
            "tuning_recommendations": tuning_recs,
            "data_sources": {
                "eigenform_entries": len(reader.eigenform_entries),
                "modification_entries": len(reader.modification_entries),
                "topology_available": reader.topology_data is not None,
                "scheduler_logs": len(reader.scheduler_log_patterns),
            },
            "for_human": self._human_summary(
                health_score, gaps, proposals, velocity, report_only
            ),
            "for_agent": self._agent_prompt(
                health_score, gaps, proposals, velocity, report_only
            ),
        }

        return state

    def _get_cycle_number(self):
        """Get next cycle number from existing state."""
        if BRAIN_STATE_FILE.exists():
            try:
                prev = json.loads(BRAIN_STATE_FILE.read_text())
                return prev.get("cycle", 0) + 1
            except Exception:
                pass
        return 1

    def _human_summary(self, health, gaps, proposals, velocity, report_only):
        """5-line summary for Colby."""
        lines = []
        lines.append(
            f"Health: {health:.0f}/100"
            + (" [REPORT-ONLY MODE]" if report_only else "")
        )
        if gaps:
            top = gaps[0]
            lines.append(
                f"Top gap: {top['type']} — {top.get('detail', '')[:60]}"
            )
        else:
            lines.append("No gaps detected — system healthy")
        lines.append(
            f"Learning: {velocity.get('notes_per_day', 0):.1f} notes/day, "
            f"{velocity.get('links_per_day', 0):.1f} links/day"
        )
        if proposals and not report_only:
            lines.append(
                f"Proposals: {len(proposals)} "
                f"(top: {proposals[0]['action']} on {proposals[0]['target']})"
            )
        else:
            lines.append("Proposals: 0 (report-only)" if report_only else "Proposals: 0")
        lines.append(
            f"Data: {velocity.get('data_points', 0)} eigenform points, "
            f"{velocity.get('span_days', 0):.0f} days tracked"
        )
        return "\n".join(lines)

    def _agent_prompt(self, health, gaps, proposals, velocity, report_only):
        """Prompt fragment for next Claude session startup."""
        parts = [f"Brain cycle: health={health:.0f}/100."]
        if gaps:
            gap_types = [g["type"] for g in gaps[:3]]
            parts.append(f"Active gaps: {', '.join(gap_types)}.")
        if proposals and not report_only:
            parts.append(
                f"{len(proposals)} proposals pending "
                f"(check logs/brain_proposals.jsonl)."
            )
        if velocity.get("notes_per_day", 0) > 0:
            parts.append(
                f"Velocity: {velocity['notes_per_day']:.1f}n/d, "
                f"{velocity['links_per_day']:.1f}l/d."
            )
        return " ".join(parts)

    def save(self, state):
        """Save brain state and append proposals."""
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        # Save brain state
        BRAIN_STATE_FILE.write_text(json.dumps(state, indent=2))

        # Append proposals to JSONL
        if state["proposals"]:
            with open(BRAIN_PROPOSALS_FILE, "a") as f:
                for proposal in state["proposals"]:
                    f.write(json.dumps(proposal) + "\n")


# ─── Main Brain Cycle ──────────────────────────────────────────────────────


def run_brain_cycle(json_output=False):
    """Execute one brain cycle. Returns state dict."""
    # 1. Read all data sources
    reader = TaskOutputReader().read_all()

    # 2. Detect gaps
    detector = GapDetector(reader)
    gaps = detector.detect_all()

    # 3. Score and rank
    scorer = PriorityScorer()
    ranked_gaps = scorer.rank_gaps(gaps)

    # 4. Generate proposals
    generator = ActionGenerator()
    proposals = generator.generate(ranked_gaps)

    # 5. Measure feedback
    measurer = FeedbackMeasurer(reader)
    velocity = measurer.compute_learning_velocity()
    outcomes = measurer.measure_proposal_outcomes()
    goodhart = measurer.detect_goodhart()

    # 6. Self-tune
    tuner = SelfTuner()
    tuning_recs = tuner.recommend(reader, ranked_gaps)

    # 7. Build and save state
    brain = BrainState()
    state = brain.build(
        reader, ranked_gaps, proposals, velocity, outcomes, goodhart, tuning_recs
    )
    brain.save(state)

    if json_output:
        print(json.dumps(state, indent=2))
    else:
        _print_human_report(state)

    return state


def _print_human_report(state):
    """Print human-readable brain cycle report."""
    print("=" * 60)
    print(f"SCAFFOLD BRAIN — Cycle #{state['cycle']}")
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    health = state["health_score"]
    print(f"\n  Health Score: {health:.0f}/100", end="")
    if state["report_only"]:
        print(f"  *** REPORT-ONLY MODE (< {HEALTH_KILL_SWITCH}) ***")
    else:
        print()

    # Data sources
    ds = state["data_sources"]
    print(f"\n  Data Sources:")
    print(f"    Eigenform entries:    {ds['eigenform_entries']}")
    print(f"    Modification entries: {ds['modification_entries']}")
    print(f"    Topology available:   {ds['topology_available']}")
    print(f"    Scheduler logs:       {ds['scheduler_logs']}")

    # Gaps
    gaps = state["top_gaps"]
    print(f"\n  Gaps Detected: {state['gaps_detected']}")
    if gaps:
        print(f"  {'Type':<30} {'Sev':<10} {'Score':>5}  Target")
        print(f"  {'-' * 70}")
        for g in gaps[:8]:
            print(
                f"  {g['type']:<30} {g['severity']:<10} "
                f"{g['priority_score']:>5.0f}  {g.get('target', '')}"
            )
            if g.get("detail"):
                print(f"    → {g['detail'][:65]}")

    # Proposals
    proposals = state["proposals"]
    print(f"\n  Proposals: {state['proposals_generated']}")
    for p in proposals:
        mode = " [HUMAN REVIEW]" if p.get("review_mode") == "human" else ""
        print(f"    {p['action']}: {p['description'][:55]}{mode}")
        print(f"      target={p['target']}, executor={p['executor']}")

    # Learning velocity
    v = state["learning_velocity"]
    print(f"\n  Learning Velocity ({v.get('span_days', 0):.0f} days, "
          f"{v.get('data_points', 0)} points):")
    print(f"    Notes/day:         {v.get('notes_per_day', 0):.1f}")
    print(f"    Links/day:         {v.get('links_per_day', 0):.1f}")
    print(f"    Health delta/day:  {v.get('health_delta_per_day', 0):+.1f}")
    print(f"    Gaps closed/day:   {v.get('gaps_closed_per_day', 0):.1f}")

    # Proposal outcomes
    o = state["proposal_outcomes"]
    if o["total"] > 0:
        print(f"\n  Proposal History: {o['resolved']}/{o['total']} resolved "
              f"({o['success_rate']:.0%})")

    # Goodhart warnings
    gw = state["goodhart_warnings"]
    if gw:
        print(f"\n  Goodhart Warnings:")
        for w in gw:
            print(f"    {w['detail']}")
            print(f"      {w['metric_1']} | {w['metric_2']}")

    # Tuning recommendations
    recs = state["tuning_recommendations"]
    if recs:
        print(f"\n  Tuning Recommendations:")
        for r in recs:
            print(f"    {r['task']}: {r['suggestion']}")
            print(f"      reason: {r['reason']}")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  {state['for_human']}")
    print(f"{'=' * 60}")

    print(f"\n  State saved: {BRAIN_STATE_FILE}")
    if proposals:
        print(f"  Proposals logged: {BRAIN_PROPOSALS_FILE}")


def show_proposals():
    """Show active proposals from brain_proposals.jsonl."""
    if not BRAIN_PROPOSALS_FILE.exists():
        print("No proposals yet. Run a brain cycle first.")
        return

    proposals = []
    for line in BRAIN_PROPOSALS_FILE.read_text().strip().splitlines():
        try:
            proposals.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not proposals:
        print("No proposals found.")
        return

    print(f"{'=' * 60}")
    print(f"BRAIN PROPOSALS ({len(proposals)} total)")
    print(f"{'=' * 60}")

    # Group by status
    by_status = defaultdict(list)
    for p in proposals:
        by_status[p.get("status", "unknown")].append(p)

    for status in ["proposed", "in_progress", "resolved", "rejected"]:
        group = by_status.get(status, [])
        if not group:
            continue
        print(f"\n  {status.upper()} ({len(group)}):")
        for p in group[-10:]:  # last 10 per status
            mode = " [HUMAN]" if p.get("review_mode") == "human" else ""
            print(f"    [{p.get('priority_score', 0):.0f}] "
                  f"{p['action']}: {p['description'][:50]}{mode}")
            print(f"         target={p['target']}, gap={p['gap_type']}")


def show_velocity():
    """Show learning velocity report."""
    reader = TaskOutputReader().read_all()
    measurer = FeedbackMeasurer(reader)
    velocity = measurer.compute_learning_velocity()

    print(f"{'=' * 60}")
    print(f"LEARNING VELOCITY")
    print(f"{'=' * 60}")
    print(f"\n  Span: {velocity.get('span_days', 0):.1f} days "
          f"({velocity.get('data_points', 0)} data points)")
    print(f"\n  Notes/day:         {velocity.get('notes_per_day', 0):.2f}")
    print(f"  Links/day:         {velocity.get('links_per_day', 0):.2f}")
    print(f"  Health delta/day:  {velocity.get('health_delta_per_day', 0):+.2f}")
    print(f"  Gaps closed/day:   {velocity.get('gaps_closed_per_day', 0):.2f}")

    # Trend from eigenform entries
    entries = reader.eigenform_entries
    if len(entries) >= 3:
        print(f"\n  Health Score Trend:")
        for e in entries[-5:]:
            ts = e.get("ts", "?")[:10]
            hs = e.get("health_score", 0)
            bar = "█" * int(hs / 5)
            print(f"    {ts}  {hs:5.1f}  {bar}")


# ─── CLI ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold Brain — Closed-Loop Self-Learning Meta-Controller"
    )
    parser.add_argument("--json", action="store_true",
                        help="Output as structured JSON")
    parser.add_argument("--proposals", action="store_true",
                        help="Show active proposals")
    parser.add_argument("--velocity", action="store_true",
                        help="Show learning velocity report")
    args = parser.parse_args()

    if args.proposals:
        show_proposals()
    elif args.velocity:
        show_velocity()
    else:
        run_brain_cycle(json_output=args.json)


if __name__ == "__main__":
    main()
