#!/usr/bin/env python3
"""
Autogenesis B6 — Typed commit-gate invariants.

Run BEFORE any auto-deploy commit. Checks six invariants:

  I_orphan                   : len(new_orphans) == 0
                               No new orphan notes (notes with zero incoming wikilinks under knowledge/notes/).
  I_dangler_delta            : dangler_count_after - dangler_count_before <= 0
                               No new broken wikilinks introduced by this change.
  I_compile                  : py_compile.compile(changed_py_file) passes
                               Every changed .py file compiles cleanly.
  I_link_density             : avg_links_per_note_after >= avg_links_per_note_before - 0.5
                               Link density doesn't regress more than 0.5/note.
  I_prose_infrastructure_gap : every logs/scripts/hooks/rules/agents/tasks ref in
                               {.claude/rules, .claude/agents, .claude/hooks, CLAUDE.md}
                               points to a real file on disk (modulo grandfathered
                               exceptions at .claude/commit-gate-exceptions.json).
                               Prevents the class of bug where a rule documents
                               infrastructure that was never built.
  I_frontmatter_schema       : every knowledge/notes/**/*.md has frontmatter with
                               summary (non-empty string), type (non-empty string),
                               status (in the VALID_STATUS enum), domains (non-empty list).
                               Pre-existing violations grandfathered into exceptions
                               file under "frontmatter_schema" section with
                               action_needed:true so cleanup dispatches can triage.
                               NEW violations (notes touched by this change) FAIL.

Operating modes:
  --staged       : compare HEAD vs staged index (default for pre-commit)
  --working      : compare HEAD vs working tree (used for pre-deploy verification)
  --no-baseline  : skip baseline comparison; only enforce I_compile + I_orphan absolute counts
  --invariant N  : run only one invariant (orphan | dangler-delta | compile |
                   link-density | prose-infra-gap | frontmatter-schema)

Usage:
  python3 scripts/commit_gate.py --staged
  python3 scripts/commit_gate.py --working --json
  python3 scripts/commit_gate.py --invariant prose-infra-gap
  python3 scripts/commit_gate.py --invariant frontmatter-schema
  python3 scripts/commit_gate.py --add-exception .claude/rules/foo.md:42:logs/bar.jsonl

If ANY invariant fails: prints failure summary, exits 1, AND appends a blocked
entry to logs/scaffold_changes.jsonl with `auto_approved: false, blocked_by: [...]`.

If ALL pass: exits 0. Caller may then proceed with the auto-deploy commit and
log it to scaffold_changes.jsonl with `auto_approved: true`.

Wire from .claude/rules/auto-deploy-safe-changes.md — every auto-deploy MUST run
this first.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = ROOT / "knowledge" / "notes"
LOG_PATH = ROOT / "logs" / "scaffold_changes.jsonl"
EXCEPTIONS_PATH = ROOT / ".claude" / "commit-gate-exceptions.json"

# Files the prose-infrastructure-gap invariant scans
PROSE_SCAN_GLOBS = [
    (ROOT / ".claude" / "rules", "*.md"),
    (ROOT / ".claude" / "agents", "*.md"),
    (ROOT / ".claude" / "hooks", "*.sh"),
]
PROSE_SCAN_SINGLE = [ROOT / "CLAUDE.md"]

# Reference detector: catches paths under logs/, scripts/, tasks/, .claude/{hooks,rules,agents}/
# whether backticked, parenthesized, or bare in prose. Uses a negative lookbehind to avoid
# matching inside longer paths (e.g., "foo/bar/logs/x.jsonl" won't double-match).
_PROSE_REF_RE = re.compile(
    r'(?<![A-Za-z0-9/_.-])'
    r'((?:\.claude/(?:hooks|rules|agents)/|logs/|scripts/|tasks/)'
    r'[A-Za-z0-9_./-]+\.(?:jsonl|log|py|sh|md))'
)


# --------- vault graph (lightweight, self-contained) ---------

WIKILINK_RE = re.compile(r"\[\[([^\]\|]+)(?:\|[^\]]*)?\]\]")
CODE_FENCE_RE = re.compile(r"```[\s\S]*?```")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


def collect_notes(notes_dir: Path) -> dict:
    """Return {title_lower: {title, links_lower_set}} for all .md notes under notes_dir."""
    notes = {}
    if not notes_dir.exists():
        return notes
    for path in notes_dir.rglob("*.md"):
        try:
            text = path.read_text()
        except Exception:
            continue
        clean = INLINE_CODE_RE.sub("", CODE_FENCE_RE.sub("", text))
        links = {m.group(1).strip().lower() for m in WIKILINK_RE.finditer(clean)}
        title = path.stem
        notes[title.lower()] = {"title": title, "path": str(path), "links": links}
    return notes


def graph_metrics(notes: dict) -> dict:
    """Return {orphans:set[str], dangler_targets:set[str], danglers:int, avg_links:float, total_notes:int}.

    `danglers` counts UNIQUE missing-target slugs (so adding one new broken slug
    bumps the count by 1, even if another note already had a different broken slug).
    `dangler_targets` is the set itself for delta computation (set difference is
    sharper than count delta — catches "removed one, added one" exchanges).
    """
    if not notes:
        return {"orphans": set(), "dangler_targets": set(), "danglers": 0,
                "avg_links": 0.0, "total_notes": 0}
    incoming = {t: 0 for t in notes}
    dangler_targets = set()
    total_links = 0
    for n in notes.values():
        for link in n["links"]:
            total_links += 1
            if link in notes:
                incoming[link] += 1
            else:
                dangler_targets.add(link)
    orphans = {t for t, c in incoming.items() if c == 0}
    avg = total_links / len(notes)
    return {
        "orphans": orphans,
        "dangler_targets": dangler_targets,
        "danglers": len(dangler_targets),
        "avg_links": avg,
        "total_notes": len(notes),
    }


# --------- git helpers ---------

def git(*args: str, cwd: Path = ROOT) -> tuple[int, str, str]:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def changed_files(mode: str) -> list[Path]:
    """Return list of changed file paths relative to ROOT.

    Checks BOTH the parent (Trading) and knowledge/ separate-repo for changes,
    since vault notes live in a separate git repo.
    """
    files = []
    knowledge_repo = ROOT / "knowledge"

    def collect_from(cwd: Path, prefix: Path = ROOT):
        if mode == "staged":
            rc, out, _ = git("diff", "--cached", "--name-only", "--diff-filter=AM", cwd=cwd)
            if rc == 0:
                for line in out.splitlines():
                    line = line.strip()
                    if line:
                        files.append(prefix / line)
        elif mode == "working":
            rc, out, _ = git("diff", "--name-only", "--diff-filter=AM", cwd=cwd)
            if rc == 0:
                for line in out.splitlines():
                    line = line.strip()
                    if line:
                        files.append(prefix / line)
            rc2, out2, _ = git("ls-files", "--others", "--exclude-standard", cwd=cwd)
            if rc2 == 0:
                for line in out2.splitlines():
                    line = line.strip()
                    if line:
                        files.append(prefix / line)

    collect_from(ROOT, ROOT)
    if (knowledge_repo / ".git").exists():
        collect_from(knowledge_repo, knowledge_repo)

    return [p for p in files if p.exists()]


def get_baseline_notes() -> dict:
    """Build vault graph from HEAD's view of knowledge/notes/.

    Knowledge vault is a SEPARATE git repo (not a submodule of Trading), so we
    must run git operations from within knowledge/ to find baseline state.

    Approach: cd into knowledge/, use `git ls-tree -r HEAD notes/` to enumerate,
    then `git show HEAD:<path>` per .md file.
    """
    knowledge_repo = ROOT / "knowledge"
    if not (knowledge_repo / ".git").exists():
        return {}
    rc, out, _ = git("ls-tree", "-r", "HEAD", "--name-only", "notes/", cwd=knowledge_repo)
    if rc != 0:
        return {}
    notes = {}
    for line in out.splitlines():
        line = line.strip()
        if not line.endswith(".md"):
            continue
        rc2, content, _ = git("show", f"HEAD:{line}", cwd=knowledge_repo)
        if rc2 != 0:
            continue
        clean = INLINE_CODE_RE.sub("", CODE_FENCE_RE.sub("", content))
        links = {m.group(1).strip().lower() for m in WIKILINK_RE.finditer(clean)}
        title = Path(line).stem
        notes[title.lower()] = {"title": title, "path": line, "links": links}
    return notes


# --------- prose-infrastructure-gap helpers ---------

def load_exceptions() -> set:
    """Load grandfathered (source, line, target) triples from exceptions file.

    Returns a set of (source_str, line_int, target_str) tuples.
    If the file doesn't exist or is malformed, returns an empty set (fail-open
    on exceptions — but the invariant will still FAIL for any ungranted broken
    refs, so this is safe).
    """
    if not EXCEPTIONS_PATH.exists():
        return set()
    try:
        data = json.loads(EXCEPTIONS_PATH.read_text())
    except Exception:
        return set()
    out = set()
    for entry in data.get("exceptions", []):
        try:
            src = str(entry["source"]).strip()
            line = int(entry["line"])
            tgt = str(entry["target"]).strip()
            out.add((src, line, tgt))
        except (KeyError, ValueError, TypeError):
            continue
    return out


def save_exception(source: str, line: int, target: str, note: str = "") -> None:
    """Append a new exception to the exceptions file (create if missing)."""
    EXCEPTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if EXCEPTIONS_PATH.exists():
        try:
            data = json.loads(EXCEPTIONS_PATH.read_text())
        except Exception:
            data = {}
    else:
        data = {}
    data.setdefault("_schema_version", 1)
    data.setdefault("_comment",
                    "Pre-existing broken refs grandfathered from I_prose_infrastructure_gap. "
                    "New broken refs (not in this list) will FAIL the invariant.")
    data["_last_updated"] = time.strftime("%Y-%m-%d", time.gmtime())
    entries = data.setdefault("exceptions", [])
    # Dedup
    for e in entries:
        if (e.get("source") == source and e.get("line") == line and e.get("target") == target):
            return
    entries.append({"source": source, "line": line, "target": target,
                    "note": note or f"added {time.strftime('%Y-%m-%d', time.gmtime())}"})
    EXCEPTIONS_PATH.write_text(json.dumps(data, indent=2) + "\n")


def _classify_ref(tgt: str) -> str:
    """Classify a reference string by its top-level directory. Returns '' if unknown."""
    if tgt.startswith("logs/"):
        return "logs"
    if tgt.startswith("scripts/"):
        return "scripts"
    if tgt.startswith(".claude/hooks/"):
        return "hooks"
    if tgt.startswith(".claude/rules/"):
        return "rules"
    if tgt.startswith(".claude/agents/"):
        return "agents"
    if tgt.startswith("tasks/"):
        return "tasks"
    return ""


def _scan_files_for_prose() -> list[Path]:
    """Return the list of files the prose-infra invariant scans."""
    files = []
    for base, pattern in PROSE_SCAN_GLOBS:
        if base.exists():
            files.extend(sorted(base.glob(pattern)))
    for p in PROSE_SCAN_SINGLE:
        if p.exists():
            files.append(p)
    return files


def scan_prose_infrastructure_refs() -> list[dict]:
    """Scan prose files for infrastructure refs and return broken ones.

    Returns a list of dicts: {source, line, target, kind, context}.
    Dedups on (source, line, target).
    """
    broken = {}
    for f in _scan_files_for_prose():
        try:
            text = f.read_text()
        except Exception:
            continue
        src = str(f.relative_to(ROOT))
        for i, line in enumerate(text.splitlines(), 1):
            for m in _PROSE_REF_RE.finditer(line):
                tgt = m.group(1).rstrip(").,;:")
                kind = _classify_ref(tgt)
                if not kind:
                    continue
                if (ROOT / tgt).exists():
                    continue
                key = (src, i, tgt)
                if key in broken:
                    continue
                broken[key] = {
                    "source": src,
                    "line": i,
                    "target": tgt,
                    "kind": kind,
                    "context": line.strip()[:120],
                }
    return list(broken.values())


def check_prose_infrastructure_gap() -> tuple[bool, list[dict], dict]:
    """Run the I_prose_infrastructure_gap invariant.

    Returns (ok, new_broken_list, stats_dict).
    stats_dict has {grandfathered_count, total_broken, new_broken_count}.
    """
    exceptions = load_exceptions()
    all_broken = scan_prose_infrastructure_refs()
    new_broken = [b for b in all_broken
                  if (b["source"], b["line"], b["target"]) not in exceptions]
    stats = {
        "grandfathered_count": len(exceptions),
        "total_broken": len(all_broken),
        "new_broken_count": len(new_broken),
    }
    return (len(new_broken) == 0, new_broken, stats)


# --------- frontmatter-schema helpers ---------

# Vault frontmatter convention (observed across 852 notes 2026-04-19 audit).
# "current" is overwhelmingly most common (724), rest are lifecycle states.
VALID_STATUS = {"current", "emerging", "superseded", "archived", "archive-candidate", "stub"}

_FM_DELIM_RE = re.compile(r"^---\s*$")
_FM_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")
_FM_LIST_ITEM_RE = re.compile(r"^\s+-\s+(.+)$")


def parse_frontmatter(text: str) -> dict | None:
    """Minimal YAML-lite frontmatter parser (stdlib only).

    Handles:
      - flat `key: value` pairs
      - inline list values: `domains: ["a", "b"]` or `domains: [a, b]`
      - block list values: key followed by `  - item` lines
      - quoted strings (single or double)

    Returns the dict, or None if no complete frontmatter block found.
    Does NOT attempt full YAML — sufficient for vault-convention notes.
    """
    lines = text.splitlines()
    if not lines or not _FM_DELIM_RE.match(lines[0]):
        return None
    fm = {}
    i = 1
    closed = False
    while i < len(lines):
        line = lines[i]
        if _FM_DELIM_RE.match(line):
            closed = True
            break
        m = _FM_KEY_RE.match(line)
        if m:
            k = m.group(1)
            v = m.group(2).strip()
            if v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                if inner:
                    items = [x.strip().strip('"').strip("'")
                             for x in inner.split(",") if x.strip()]
                else:
                    items = []
                fm[k] = items
            elif v == "" or v == "|" or v == ">":
                # Possible block list — peek ahead
                items = []
                j = i + 1
                while j < len(lines):
                    nxt = lines[j]
                    if _FM_DELIM_RE.match(nxt):
                        break
                    m2 = _FM_LIST_ITEM_RE.match(nxt)
                    if m2:
                        items.append(m2.group(1).strip().strip('"').strip("'"))
                        j += 1
                    else:
                        break
                if items:
                    fm[k] = items
                    i = j - 1
                else:
                    fm[k] = v
            else:
                fm[k] = v.strip('"').strip("'")
        i += 1
    return fm if closed else None


def check_note_frontmatter(path: Path) -> list[str]:
    """Return list of violation codes for a single note. Empty list = valid.

    Violation codes:
      no_frontmatter              — no `---` block at top
      missing:<field>             — required field absent
      bad_type:<field>            — wrong type (e.g. string where list expected)
      empty:<field>               — empty value where non-empty required
      bad_value:status=<v>        — status not in VALID_STATUS enum
    """
    try:
        text = path.read_text()
    except Exception:
        return ["read_error"]

    fm = parse_frontmatter(text)
    if fm is None:
        return ["no_frontmatter"]

    violations = []
    # summary: non-empty string
    if "summary" not in fm:
        violations.append("missing:summary")
    elif not isinstance(fm["summary"], str):
        violations.append("bad_type:summary")
    elif not fm["summary"].strip():
        violations.append("empty:summary")

    # type: non-empty string
    if "type" not in fm:
        violations.append("missing:type")
    elif not isinstance(fm["type"], str):
        violations.append("bad_type:type")
    elif not fm["type"].strip():
        violations.append("empty:type")

    # status: string in VALID_STATUS
    if "status" not in fm:
        violations.append("missing:status")
    elif not isinstance(fm["status"], str):
        violations.append("bad_type:status")
    elif fm["status"] not in VALID_STATUS:
        violations.append(f"bad_value:status={fm['status']}")

    # domains: non-empty list
    if "domains" not in fm:
        violations.append("missing:domains")
    elif not isinstance(fm["domains"], list):
        violations.append("bad_type:domains")
    elif len(fm["domains"]) == 0:
        violations.append("empty:domains")

    return violations


def scan_frontmatter_schema() -> list[dict]:
    """Scan all notes for frontmatter violations.

    Returns a list of dicts: {source, violations, context}.
    """
    broken = []
    if not NOTES_DIR.exists():
        return broken
    for p in sorted(NOTES_DIR.rglob("*.md")):
        v = check_note_frontmatter(p)
        if v:
            broken.append({
                "source": str(p.relative_to(ROOT)),
                "violations": v,
                "context": ",".join(v[:3]),
            })
    return broken


def load_frontmatter_exceptions() -> set:
    """Load grandfathered frontmatter-schema violations.

    Returns a set of source_str strings (source path relative to ROOT).
    Exception entries live under `frontmatter_schema` key in the exceptions
    file. A grandfathered source passes the invariant regardless of current
    violations — cleanup is tracked via `action_needed:true` flag.
    """
    if not EXCEPTIONS_PATH.exists():
        return set()
    try:
        data = json.loads(EXCEPTIONS_PATH.read_text())
    except Exception:
        return set()
    out = set()
    for entry in data.get("frontmatter_schema", []):
        try:
            out.add(str(entry["source"]).strip())
        except (KeyError, TypeError):
            continue
    return out


def check_frontmatter_schema(scope: str) -> tuple[bool, list[dict], dict]:
    """Run the I_frontmatter_schema invariant.

    scope: "staged" or "working" — determines which changed notes we
    enforce against. Pre-existing violations (grandfathered) always pass.
    New violations (touched notes with bad frontmatter not in exceptions) fail.

    Returns (ok, new_violations, stats).
    stats has {grandfathered_count, total_violations, new_violations_count}.
    """
    exceptions = load_frontmatter_exceptions()
    all_broken = scan_frontmatter_schema()

    # Touched notes under knowledge/notes/
    changed = changed_files(scope)
    touched_notes = {
        str(p.relative_to(ROOT)) for p in changed
        if p.exists() and p.suffix == ".md"
        and (str(p).startswith(str(NOTES_DIR)) or "knowledge/notes/" in str(p))
    }

    # New violations = touched AND has violations AND not grandfathered
    new_violations = []
    for b in all_broken:
        if b["source"] in exceptions:
            continue
        if b["source"] not in touched_notes:
            continue
        new_violations.append(b)

    stats = {
        "grandfathered_count": len(exceptions),
        "total_violations": len(all_broken),
        "touched_notes": len(touched_notes),
        "new_violations_count": len(new_violations),
    }
    return (len(new_violations) == 0, new_violations, stats)


def _priority_sort_key(source: str) -> tuple[int, str]:
    """Priority ordering for grandfathering triage: lower = more important.

    cc-operational / research-consciousness > session-notes > auto-repair > other.
    """
    if "/cc-operational/" in source:
        return (0, source)
    if "/research-consciousness/" in source or "/consciousness/" in source:
        return (1, source)
    if "/cc-session-notes/" in source or "/session-notes/" in source:
        return (2, source)
    if "/auto-repair/" in source:
        return (3, source)
    return (4, source)


def seed_frontmatter_exceptions(dry_run: bool = False) -> dict:
    """Populate the exceptions file with current violations.

    Each grandfathered entry gets action_needed:true so a future cleanup
    dispatch can triage them. Entries are sorted by priority so high-value
    notes (cc-operational, consciousness) appear first.

    Returns a stats dict.
    """
    all_broken = scan_frontmatter_schema()
    # Sort by priority then source
    all_broken_sorted = sorted(all_broken, key=lambda b: _priority_sort_key(b["source"]))

    # Load existing exceptions file (merge, not overwrite)
    if EXCEPTIONS_PATH.exists():
        try:
            data = json.loads(EXCEPTIONS_PATH.read_text())
        except Exception:
            data = {}
    else:
        data = {}

    existing_fm = {e.get("source") for e in data.get("frontmatter_schema", [])}
    entries = data.get("frontmatter_schema", [])

    added = 0
    for b in all_broken_sorted:
        if b["source"] in existing_fm:
            continue
        entries.append({
            "source": b["source"],
            "violations": b["violations"],
            "action_needed": True,
            "priority": _priority_sort_key(b["source"])[0],
            "note": f"seeded {time.strftime('%Y-%m-%d', time.gmtime())} — pending cleanup",
        })
        added += 1

    if not dry_run:
        data["frontmatter_schema"] = entries
        data.setdefault("_schema_version", 1)
        data["_last_updated"] = time.strftime("%Y-%m-%d", time.gmtime())
        EXCEPTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        EXCEPTIONS_PATH.write_text(json.dumps(data, indent=2) + "\n")

    return {
        "total_violations": len(all_broken),
        "new_grandfathered": added,
        "total_grandfathered": len(entries),
        "by_priority": _priority_counts(entries),
    }


def _priority_counts(entries: list[dict]) -> dict:
    """Count entries by priority bucket for reporting."""
    buckets = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
    for e in entries:
        p = e.get("priority", 4)
        if p in buckets:
            buckets[p] += 1
    return {
        "cc_operational": buckets[0],
        "consciousness": buckets[1],
        "session_notes": buckets[2],
        "auto_repair": buckets[3],
        "other": buckets[4],
    }


# --------- invariants ---------

def check_compile(changed: list[Path]) -> tuple[bool, list[str]]:
    """Return (ok, errors)."""
    failures = []
    for p in changed:
        if p.suffix != ".py":
            continue
        if not p.exists():
            continue
        try:
            import py_compile
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as e:
            failures.append(f"{p.relative_to(ROOT)}: {e}")
        except Exception as e:
            failures.append(f"{p.relative_to(ROOT)}: {e}")
    return (len(failures) == 0, failures)


VALID_INVARIANTS = {
    "orphan": "I_orphan",
    "dangler-delta": "I_dangler_delta",
    "compile": "I_compile",
    "link-density": "I_link_density",
    "prose-infra-gap": "I_prose_infrastructure_gap",
    "frontmatter-schema": "I_frontmatter_schema",
}


def _run_prose_infra_check() -> dict:
    """Run the I_prose_infrastructure_gap invariant and return result dict."""
    ok, new_broken, stats = check_prose_infrastructure_gap()
    if ok:
        detail = (f"0 new broken refs ({stats['grandfathered_count']} grandfathered, "
                  f"{stats['total_broken']} total broken)")
    else:
        sample = [f"{b['source']}:{b['line']} -> {b['target']}" for b in new_broken[:5]]
        detail = (f"{stats['new_broken_count']} NEW broken refs "
                  f"({stats['grandfathered_count']} grandfathered, "
                  f"{stats['total_broken']} total): {sample}")
    return {"pass": ok, "detail": detail, "new_broken": new_broken, "stats": stats}


def _run_frontmatter_schema_check(mode: str) -> dict:
    """Run the I_frontmatter_schema invariant and return result dict."""
    ok, new_violations, stats = check_frontmatter_schema(mode)
    if ok:
        detail = (f"0 new frontmatter violations in {stats['touched_notes']} touched notes "
                  f"({stats['grandfathered_count']} grandfathered, "
                  f"{stats['total_violations']} total violations — cleanup-queue)")
    else:
        sample = [f"{b['source']} [{','.join(b['violations'][:2])}]" for b in new_violations[:5]]
        detail = (f"{stats['new_violations_count']} NEW frontmatter violations "
                  f"({stats['grandfathered_count']} grandfathered, "
                  f"{stats['total_violations']} total): {sample}")
    return {"pass": ok, "detail": detail, "new_violations": new_violations, "stats": stats}


def check_invariants(mode: str, no_baseline: bool, only: str | None = None) -> dict:
    """Run invariants. Returns {invariant_name: {pass: bool, detail: str}}.

    If `only` is set (one of VALID_INVARIANTS keys), runs that invariant alone
    and skips the rest.
    """
    results = {}

    def _want(short_key: str) -> bool:
        return only is None or only == short_key

    changed = changed_files(mode)
    changed_py = [p for p in changed if p.suffix == ".py"]

    # I_compile
    if _want("compile"):
        ok, errs = check_compile(changed_py)
        results["I_compile"] = {
            "pass": ok,
            "detail": (f"{len(changed_py)} .py files OK" if ok else f"compile failed: {errs}"),
        }

    # I_prose_infrastructure_gap (independent of baseline / changed files — scans all prose)
    if _want("prose-infra-gap"):
        results["I_prose_infrastructure_gap"] = _run_prose_infra_check()

    # I_frontmatter_schema (independent of baseline — scans vault + filters by touched scope)
    if _want("frontmatter-schema"):
        results["I_frontmatter_schema"] = _run_frontmatter_schema_check(mode)

    # Short-circuit if only running prose-infra-gap / compile / frontmatter-schema
    if only in ("compile", "prose-infra-gap", "frontmatter-schema"):
        return results

    # Build current graph (working tree state — what would be committed)
    current = collect_notes(NOTES_DIR)
    cur_metrics = graph_metrics(current)

    if no_baseline:
        # Absolute orphan check: notes touched by this change must have at least one incoming link
        touched_titles = {p.stem.lower() for p in changed if str(p).startswith(str(NOTES_DIR)) and p.suffix == ".md"}
        new_orphans = touched_titles & cur_metrics["orphans"]
        if _want("orphan"):
            results["I_orphan"] = {
                "pass": len(new_orphans) == 0,
                "detail": f"{len(new_orphans)} touched notes are orphans: {sorted(new_orphans)[:5]}",
            }
        if _want("dangler-delta"):
            results["I_dangler_delta"] = {"pass": True, "detail": "skipped (--no-baseline)"}
        if _want("link-density"):
            results["I_link_density"] = {"pass": True, "detail": "skipped (--no-baseline)"}
        return results

    # Baseline graph from HEAD
    baseline = get_baseline_notes()
    base_metrics = graph_metrics(baseline)

    # I_orphan: new orphans introduced by this change
    if _want("orphan"):
        new_orphans = cur_metrics["orphans"] - base_metrics["orphans"]
        results["I_orphan"] = {
            "pass": len(new_orphans) == 0,
            "detail": (f"0 new orphans (baseline {len(base_metrics['orphans'])}, after {len(cur_metrics['orphans'])})"
                       if not new_orphans else f"{len(new_orphans)} new orphans: {sorted(new_orphans)[:5]}"),
        }

    # I_dangler_delta: NEW dangler targets (not in baseline) must be empty
    if _want("dangler-delta"):
        new_dangler_targets = cur_metrics["dangler_targets"] - base_metrics["dangler_targets"]
        results["I_dangler_delta"] = {
            "pass": len(new_dangler_targets) == 0,
            "detail": (f"danglers {base_metrics['danglers']} -> {cur_metrics['danglers']}; "
                       f"NEW targets: {len(new_dangler_targets)} {sorted(new_dangler_targets)[:3]}"),
        }

    # I_link_density: avg links must not regress more than 0.5
    if _want("link-density"):
        diff = cur_metrics["avg_links"] - base_metrics["avg_links"]
        results["I_link_density"] = {
            "pass": diff >= -0.5,
            "detail": f"avg links {base_metrics['avg_links']:.2f} -> {cur_metrics['avg_links']:.2f} (delta {diff:+.2f})",
        }

    return results


# --------- audit log ---------

def log_blocked(blocked_by: list[str], detail_map: dict) -> None:
    """Append a blocked entry to scaffold_changes.jsonl."""
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "doc": "(commit-gate)",
        "change": "auto-deploy blocked by commit-gate",
        "by": "commit_gate",
        "auto_approved": False,
        "blocked_by": blocked_by,
        "detail": {k: detail_map[k]["detail"] for k in blocked_by},
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


# --------- main ---------

def main() -> int:
    parser = argparse.ArgumentParser(description="Typed commit-gate invariants for auto-deploy")
    parser.add_argument("--staged", action="store_true", help="Check staged changes (default)")
    parser.add_argument("--working", action="store_true", help="Check working tree changes (incl. untracked)")
    parser.add_argument("--no-baseline", action="store_true",
                        help="Skip baseline comparison (faster; checks only I_compile + absolute orphans)")
    parser.add_argument("--invariant", choices=sorted(VALID_INVARIANTS.keys()),
                        help="Run only one invariant (orphan | dangler-delta | compile | link-density | prose-infra-gap | frontmatter-schema)")
    parser.add_argument("--add-exception", metavar="SRC:LINE:TGT",
                        help="Append an exception to .claude/commit-gate-exceptions.json "
                             "(format: path/to/src.md:42:logs/missing.jsonl) then exit 0")
    parser.add_argument("--seed-frontmatter-exceptions", action="store_true",
                        help="Grandfather current frontmatter-schema violations into "
                             ".claude/commit-gate-exceptions.json under frontmatter_schema key "
                             "with action_needed:true, then exit. Run once per audit.")
    parser.add_argument("--seed-dry-run", action="store_true",
                        help="Dry-run for --seed-frontmatter-exceptions (print stats, don't write)")
    parser.add_argument("--json", action="store_true", help="Emit JSON results to stdout")
    parser.add_argument("--no-log", action="store_true", help="Do not append blocked entries to scaffold_changes.jsonl")
    args = parser.parse_args()

    # --add-exception short-circuits everything else
    if args.add_exception:
        parts = args.add_exception.rsplit(":", 2)
        if len(parts) != 3:
            print(f"ERROR: --add-exception expects format SRC:LINE:TGT, got: {args.add_exception}")
            return 2
        src, line_str, tgt = parts
        try:
            line = int(line_str)
        except ValueError:
            print(f"ERROR: line must be an integer, got: {line_str}")
            return 2
        save_exception(src.strip(), line, tgt.strip(), note="added via --add-exception CLI")
        print(f"[commit-gate] added exception: {src}:{line} -> {tgt}")
        print(f"  -> {EXCEPTIONS_PATH.relative_to(ROOT)}")
        return 0

    # --seed-frontmatter-exceptions short-circuits
    if args.seed_frontmatter_exceptions:
        stats = seed_frontmatter_exceptions(dry_run=args.seed_dry_run)
        tag = "[dry-run]" if args.seed_dry_run else "[written]"
        print(f"[commit-gate] frontmatter-schema seed {tag}")
        print(f"  total violations scanned:     {stats['total_violations']}")
        print(f"  new grandfathered this run:   {stats['new_grandfathered']}")
        print(f"  total grandfathered after:    {stats['total_grandfathered']}")
        print(f"  priority breakdown:")
        for k, c in stats["by_priority"].items():
            print(f"    {k}: {c}")
        if not args.seed_dry_run:
            print(f"  -> {EXCEPTIONS_PATH.relative_to(ROOT)}")
        return 0

    mode = "working" if args.working else "staged"
    results = check_invariants(mode=mode, no_baseline=args.no_baseline, only=args.invariant)

    blocked_by = [k for k, v in results.items() if not v["pass"]]
    summary = {
        "mode": mode,
        "no_baseline": args.no_baseline,
        "invariant_filter": args.invariant,
        "blocked_by": blocked_by,
        "results": results,
    }

    if args.json:
        # Strip non-serializable extras (nested dict lists)
        printable = {
            "mode": mode,
            "no_baseline": args.no_baseline,
            "invariant_filter": args.invariant,
            "blocked_by": blocked_by,
            "results": {k: {kk: vv for kk, vv in v.items()
                            if kk not in ("new_broken", "new_violations")}
                        for k, v in results.items()},
        }
        # Preserve details under separate keys for diagnostic use
        if "I_prose_infrastructure_gap" in results and results["I_prose_infrastructure_gap"].get("new_broken"):
            printable["prose_infra_new_broken"] = results["I_prose_infrastructure_gap"]["new_broken"]
        if "I_frontmatter_schema" in results and results["I_frontmatter_schema"].get("new_violations"):
            printable["frontmatter_schema_new_violations"] = results["I_frontmatter_schema"]["new_violations"]
        print(json.dumps(printable, indent=2))
    else:
        print(f"[commit-gate] mode={mode} no_baseline={args.no_baseline} invariant={args.invariant or 'ALL'}")
        for name, r in results.items():
            mark = "PASS" if r["pass"] else "FAIL"
            print(f"  [{mark}] {name}: {r['detail']}")
            # Extra detail for prose-infra-gap failures
            if (name == "I_prose_infrastructure_gap" and not r["pass"]
                    and r.get("new_broken")):
                print("    Missing targets:")
                for b in r["new_broken"][:20]:
                    print(f"      {b['source']}:{b['line']} -> {b['target']}")
                if len(r["new_broken"]) > 20:
                    print(f"      ... and {len(r['new_broken']) - 20} more")
            # Extra detail for frontmatter-schema failures
            if (name == "I_frontmatter_schema" and not r["pass"]
                    and r.get("new_violations")):
                print("    Frontmatter violations:")
                for b in r["new_violations"][:20]:
                    print(f"      {b['source']} — {','.join(b['violations'])}")
                if len(r["new_violations"]) > 20:
                    print(f"      ... and {len(r['new_violations']) - 20} more")
        if blocked_by:
            print(f"\nBLOCK: {len(blocked_by)} invariant(s) failed: {blocked_by}")
        else:
            print("\nALL CLEAR — auto-deploy may proceed.")

    if blocked_by and not args.no_log:
        log_blocked(blocked_by, results)

    return 1 if blocked_by else 0


if __name__ == "__main__":
    sys.exit(main())
