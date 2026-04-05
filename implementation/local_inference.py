#!/usr/bin/env python3
"""
Local Inference Router — sends mechanical tasks to Qwen on PC via Ollama API.

Mac (CC brain) → Tailscale → PC (Ollama GPU) → response back.

Usage:
    python3 scripts/local_inference.py "Does this compile?" --context "import os; print('hi')"
    python3 scripts/local_inference.py --compile scripts/market_recorder.py
    python3 scripts/local_inference.py --classify "User deployed new config"
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

OLLAMA_URL = "http://100.72.186.13:11434/api/generate"
MODEL = "scaffold:e1"
MAX_TOKENS = 100  # prevent repeat loops
TIMEOUT = 30


def query_local(prompt, context="", max_tokens=MAX_TOKENS):
    """Send a prompt to the local Qwen model via Ollama API."""
    full_prompt = f"{context}\n\n{prompt}" if context else prompt

    payload = {
        "model": MODEL,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "repeat_penalty": 1.5,
            "temperature": 0.3,  # low temp for mechanical tasks
        }
    }

    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=TIMEOUT)
        result = json.loads(resp.read())
        return {
            "response": result.get("response", "").strip(),
            "time_s": round(result.get("total_duration", 0) / 1e9, 1),
            "tokens": result.get("eval_count", 0),
            "model": MODEL,
        }
    except Exception as e:
        return {"error": str(e), "fallback": "CC"}


def compile_check(filepath):
    """Ask local model if a Python file looks correct."""
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    code = path.read_text()[:2000]
    return query_local(
        "TASK: Check this Python code for syntax errors.\n"
        "RULES: Answer EXACTLY in this format:\n"
        "RESULT: [YES_ERROR or NO_ERROR]\n"
        "LINE: [line number or N/A]\n"
        "ISSUE: [one sentence or N/A]\n\n"
        f"CODE:\n```python\n{code}\n```",
        max_tokens=40,
    )


def classify_breadcrumb(text):
    """Ask local model to classify a breadcrumb type."""
    return query_local(
        "TASK: Classify this event into exactly ONE category.\n"
        "CATEGORIES: decision | finding | insight | action | dialogue\n"
        "RULES: Reply with ONLY the category name. Nothing else.\n\n"
        f"EVENT: {text}\n\n"
        "CATEGORY:",
        max_tokens=5,
    )


def schema_check(frontmatter):
    """Ask local model if vault note frontmatter is valid."""
    return query_local(
        "TASK: Check if this YAML frontmatter has all required fields.\n"
        "REQUIRED: summary, type, status, domains\n"
        "RULES: Answer EXACTLY in this format:\n"
        "VALID: [YES or NO]\n"
        "MISSING: [comma-separated field names or NONE]\n\n"
        f"FRONTMATTER:\n{frontmatter}",
        max_tokens=30,
    )


def diff_summary(diff_text):
    """Ask local model to summarize a git diff in one sentence."""
    return query_local(
        "TASK: Summarize what changed in this diff.\n"
        "RULES: Answer in EXACTLY one sentence. Start with a verb (Added, Fixed, Updated, Removed).\n\n"
        f"DIFF:\n{diff_text[:1500]}",
        max_tokens=30,
    )


def dedup_check(summary1, summary2):
    """Ask local model if two note summaries are duplicates."""
    return query_local(
        "TASK: Are these two notes duplicates of each other?\n"
        "RULES: Answer EXACTLY: DUPLICATE or UNIQUE. Then one sentence why.\n\n"
        f"NOTE 1: {summary1}\n\n"
        f"NOTE 2: {summary2}\n\n"
        "VERDICT:",
        max_tokens=20,
    )


def sentiment_tag(text):
    """Tag text as positive, negative, or neutral."""
    return query_local(
        "TASK: What is the sentiment of this text?\n"
        "RULES: Answer with ONLY one word: positive | negative | neutral\n\n"
        f"TEXT: {text}\n\n"
        "SENTIMENT:",
        max_tokens=3,
    )


def format_frontmatter(raw_text):
    """Convert raw text into vault note frontmatter."""
    return query_local(
        "TASK: Create YAML frontmatter for this text.\n"
        "RULES: Output ONLY the frontmatter block. Format:\n"
        "---\n"
        "summary: \"one line summary of the text\"\n"
        "type: finding\n"
        "status: current\n"
        "domains: [\"domain-name\"]\n"
        "date: 2026-04-04\n"
        "---\n\n"
        f"TEXT: {raw_text[:500]}",
        max_tokens=60,
    )


def log_count(log_text, condition):
    """Count entries matching a condition in log data."""
    return query_local(
        f"TASK: Count how many lines match this condition: {condition}\n"
        "RULES: Answer with ONLY the number. Nothing else.\n\n"
        f"LOG DATA:\n{log_text[:1500]}\n\n"
        "COUNT:",
        max_tokens=5,
    )


def bug_scan(code_snippet):
    """Ask local model to scan for common bugs."""
    return query_local(
        "TASK: List bugs in this code. Known bug patterns:\n"
        "- Variable shadowing (loop var overwrites parameter)\n"
        "- Continue skipping state updates\n"
        "- Threshold read but never used\n"
        "- Missing return value\n"
        "RULES: List each bug on one line. Format: LINE X: [description]\n"
        "If no bugs found, say: NO BUGS FOUND\n\n"
        f"CODE:\n```python\n{code_snippet}\n```",
        max_tokens=80,
    )


def log_anomaly(log_lines):
    """Detect anomalies in log output."""
    return query_local(
        "TASK: Check these log lines for anomalies.\n"
        "ANOMALIES TO DETECT:\n"
        "- Repeated errors (same error 3+ times)\n"
        "- Balance dropping unexpectedly\n"
        "- Process crashes or restarts\n"
        "- Timeouts dominating (>50% of exits)\n"
        "- Long gaps between entries (>5 min)\n"
        "RULES: Answer EXACTLY:\n"
        "STATUS: [NORMAL or ANOMALY]\n"
        "DETAIL: [one sentence or N/A]\n\n"
        f"LOGS:\n{log_lines}",
        max_tokens=30,
    )


def journal_stats(journal_lines):
    """Compute trading stats from journal entries."""
    return query_local(
        "TASK: Compute stats from these trade journal entries (JSON, one per line).\n"
        "RULES: Answer EXACTLY in this format:\n"
        "TRADES: [count]\n"
        "WINS: [count]\n"
        "WR: [percentage]\n"
        "TOTAL_BP: [sum of pnl_after_fees_bp]\n"
        "AVG_BP: [average pnl_after_fees_bp]\n"
        "TOTAL_USD: [sum of pnl_usd]\n\n"
        f"DATA:\n{journal_lines}",
        max_tokens=40,
    )


def orphan_scan(note_titles, all_links):
    """Find notes with zero incoming links."""
    return query_local(
        "TASK: Find orphan notes (notes that NO other note links to).\n"
        "RULES: List each orphan on its own line. Format: ORPHAN: [title]\n"
        "If all notes have incoming links, say: NO ORPHANS\n\n"
        f"ALL NOTE TITLES:\n{note_titles}\n\n"
        f"ALL WIKILINKS FOUND:\n{all_links}",
        max_tokens=100,
    )


def cron_health_parse(health_log):
    """Parse cron health log into structured alert."""
    return query_local(
        "TASK: Parse this health check log and list failures.\n"
        "RULES: Answer EXACTLY:\n"
        "PASS: [count]\n"
        "FAIL: [count]\n"
        "FAILURES: [comma-separated names of failed checks]\n"
        "SEVERITY: [OK or WARN or CRITICAL]\n\n"
        f"LOG:\n{health_log}",
        max_tokens=40,
    )


def import_check(filepath):
    """Check if a Python file's imports are valid."""
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}
    # Extract import lines only
    imports = [l.strip() for l in path.read_text().splitlines()[:50]
               if l.strip().startswith(("import ", "from "))]
    return query_local(
        "TASK: Check if these Python imports look correct.\n"
        "RULES: Answer EXACTLY:\n"
        "VALID: [YES or NO]\n"
        "ISSUES: [list problems or NONE]\n"
        "Common problems: misspelled module, importing from wrong package, circular import risk\n\n"
        f"IMPORTS:\n" + "\n".join(imports),
        max_tokens=30,
    )


def rag_answer(question, context_notes):
    """Answer a question using provided vault context (RAG)."""
    return query_local(
        "TASK: Answer this question using ONLY the provided context.\n"
        "RULES: If the context doesn't contain the answer, say: NOT FOUND IN CONTEXT\n"
        "Keep answer under 3 sentences.\n\n"
        f"QUESTION: {question}\n\n"
        f"CONTEXT:\n{context_notes[:2000]}",
        max_tokens=80,
    )


def discord_format(raw_message, channel_purpose=""):
    """Format a raw message for Discord posting."""
    return query_local(
        "TASK: Format this message for Discord.\n"
        "RULES: Use markdown. Keep under 200 words. Add relevant emoji at start.\n"
        f"CHANNEL PURPOSE: {channel_purpose}\n\n"
        f"RAW MESSAGE:\n{raw_message[:500]}",
        max_tokens=100,
    )


def main():
    parser = argparse.ArgumentParser(description="Local Inference Router")
    parser.add_argument("prompt", nargs="?", help="Direct prompt")
    parser.add_argument("--context", type=str, default="", help="Context to prepend")
    parser.add_argument("--compile", type=str, help="Compile check a .py file")
    parser.add_argument("--classify", type=str, help="Classify a breadcrumb")
    parser.add_argument("--schema", type=str, help="Check frontmatter schema")
    parser.add_argument("--bug", type=str, help="Scan code for common bugs")
    parser.add_argument("--diff", type=str, help="Summarize a git diff")
    parser.add_argument("--dedup", nargs=2, help="Check if two summaries are duplicates")
    parser.add_argument("--sentiment", type=str, help="Tag sentiment: positive/negative/neutral")
    parser.add_argument("--frontmatter", type=str, help="Generate vault frontmatter from raw text")
    parser.add_argument("--count", nargs=2, help="Count log entries matching condition: LOG_FILE CONDITION")
    parser.add_argument("--anomaly", type=str, help="Detect anomalies in log file")
    parser.add_argument("--journal-stats", type=str, help="Compute stats from journal file")
    parser.add_argument("--orphans", nargs=2, help="Find orphan notes: TITLES_FILE LINKS_FILE")
    parser.add_argument("--cron-health", type=str, help="Parse cron health log")
    parser.add_argument("--imports", type=str, help="Check imports in a .py file")
    parser.add_argument("--rag", nargs=2, help="RAG answer: QUESTION CONTEXT_FILE")
    parser.add_argument("--discord", type=str, help="Format message for Discord")
    parser.add_argument("--discord-channel", type=str, default="", help="Channel purpose for Discord formatting")
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    args = parser.parse_args()

    if args.compile:
        result = compile_check(args.compile)
    elif args.classify:
        result = classify_breadcrumb(args.classify)
    elif args.schema:
        result = schema_check(args.schema)
    elif args.bug:
        code = Path(args.bug).read_text()[:2000] if Path(args.bug).exists() else args.bug
        result = bug_scan(code)
    elif args.diff:
        diff_text = Path(args.diff).read_text()[:1500] if Path(args.diff).exists() else args.diff
        result = diff_summary(diff_text)
    elif args.dedup:
        result = dedup_check(args.dedup[0], args.dedup[1])
    elif args.sentiment:
        result = sentiment_tag(args.sentiment)
    elif args.frontmatter:
        result = format_frontmatter(args.frontmatter)
    elif args.count:
        log_text = Path(args.count[0]).read_text()[-1500:] if Path(args.count[0]).exists() else args.count[0]
        result = log_count(log_text, args.count[1])
    elif args.anomaly:
        log_text = Path(args.anomaly).read_text()[-2000:] if Path(args.anomaly).exists() else args.anomaly
        result = log_anomaly(log_text)
    elif args.journal_stats:
        j = Path(args.journal_stats)
        lines = j.read_text().splitlines()[-50:] if j.exists() else []
        result = journal_stats("\n".join(lines))
    elif args.orphans:
        titles = Path(args.orphans[0]).read_text()[:2000] if Path(args.orphans[0]).exists() else args.orphans[0]
        links = Path(args.orphans[1]).read_text()[:2000] if Path(args.orphans[1]).exists() else args.orphans[1]
        result = orphan_scan(titles, links)
    elif args.cron_health:
        health = Path(args.cron_health).read_text()[-1500:] if Path(args.cron_health).exists() else args.cron_health
        result = cron_health_parse(health)
    elif args.imports:
        result = import_check(args.imports)
    elif args.rag:
        ctx_file = Path(args.rag[1])
        ctx = ctx_file.read_text()[:2000] if ctx_file.exists() else args.rag[1]
        result = rag_answer(args.rag[0], ctx)
    elif args.discord:
        result = discord_format(args.discord, args.discord_channel)
    elif args.prompt:
        result = query_local(args.prompt, args.context, args.max_tokens)
    else:
        parser.print_help()
        return

    if "error" in result:
        print(f"ERROR: {result['error']} (fallback to CC)", file=sys.stderr)
        sys.exit(1)
    else:
        print(result["response"])
        print(f"  [{result['time_s']}s, {result['tokens']} tokens, {result['model']}]", file=sys.stderr)


if __name__ == "__main__":
    main()
