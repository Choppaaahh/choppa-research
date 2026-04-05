#!/usr/bin/env python3
"""
Hybrid Router — decides which tasks go to local Qwen vs CC.

Architecture:
  CC (Opus/Sonnet on Mac) = THINKING — deep reasoning, synthesis, decisions
  Qwen (Q4 on PC GPU) = MECHANICAL — compile checks, schema validation, classification

Routing logic:
  1. Task arrives
  2. Router classifies: MECHANICAL or THINKING
  3. MECHANICAL → local_inference.py → PC Ollama → response
  4. THINKING → stays on CC
  5. If local model fails or quality is low → escalate to CC

Usage:
    python3 scripts/hybrid_router.py classify "User deployed Config B7"
    python3 scripts/hybrid_router.py compile scripts/equities_mm.py
    python3 scripts/hybrid_router.py schema "---\nsummary: test\n---"
    python3 scripts/hybrid_router.py route "Should we lower FARTCOIN threshold?"
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LOCAL_SCRIPT = BASE / "scripts" / "local_inference.py"

# Task classification rules
MECHANICAL_KEYWORDS = [
    "compile", "syntax", "import", "schema", "frontmatter",
    "classify", "type", "format", "validate", "check",
    "count", "anomaly", "stats", "orphan", "dangler",
    "health", "parse", "summarize diff", "sentiment",
    "dedup", "duplicate", "discord format",
]

THINKING_KEYWORDS = [
    "should we", "why", "analyze", "compare", "design",
    "strategy", "recommend", "review", "what if", "propose",
    "trade", "deploy", "threshold", "parameter", "experiment",
    "cross-domain", "synthesis", "architecture", "adversarial",
    "paper", "theory", "bridge", "connection",
]

# Direct task→flag mapping for route_to_local
TASK_FLAGS = {
    "compile": "--compile",
    "classify": "--classify",
    "schema": "--schema",
    "bug": "--bug",
    "diff": "--diff",
    "sentiment": "--sentiment",
    "frontmatter": "--frontmatter",
    "anomaly": "--anomaly",
    "imports": "--imports",
    "cron-health": "--cron-health",
    "discord": "--discord",
    "journal-stats": "--journal-stats",
}


def classify_task(task_description):
    """Classify a task as MECHANICAL or THINKING."""
    lower = task_description.lower()

    mech_score = sum(1 for kw in MECHANICAL_KEYWORDS if kw in lower)
    think_score = sum(1 for kw in THINKING_KEYWORDS if kw in lower)

    if mech_score > think_score:
        return "MECHANICAL"
    elif think_score > mech_score:
        return "THINKING"
    else:
        return "THINKING"  # default to CC when unclear


def route_to_local(task_type, *args):
    """Route a mechanical task to local Qwen model."""
    cmd = ["python3", str(LOCAL_SCRIPT)]

    flag = TASK_FLAGS.get(task_type)
    if flag:
        cmd.extend([flag, args[0]])
    elif task_type == "dedup" and len(args) >= 2:
        cmd.extend(["--dedup", args[0], args[1]])
    elif task_type == "rag" and len(args) >= 2:
        cmd.extend(["--rag", args[0], args[1]])
    elif task_type == "count" and len(args) >= 2:
        cmd.extend(["--count", args[0], args[1]])
    elif task_type == "orphans" and len(args) >= 2:
        cmd.extend(["--orphans", args[0], args[1]])
    else:
        cmd.extend([args[0] if args else "", "--max-tokens", "50"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return {"source": "local", "response": result.stdout.strip()}
        else:
            return {"source": "cc_fallback", "reason": result.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {"source": "cc_fallback", "reason": "local model timeout"}
    except Exception as e:
        return {"source": "cc_fallback", "reason": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Hybrid Router — Local vs CC")
    parser.add_argument("action",
                        choices=list(TASK_FLAGS.keys()) + ["dedup", "rag", "count", "orphans", "route"],
                        help="Task type")
    parser.add_argument("input", help="Task input (text or filepath)")
    args = parser.parse_args()

    if args.action == "route":
        # Auto-classify and route
        task_class = classify_task(args.input)
        print(f"Classification: {task_class}")

        if task_class == "MECHANICAL":
            result = route_to_local("classify", args.input)
            print(f"Routed to: {result['source']}")
            if "response" in result:
                print(f"Response: {result['response']}")
            else:
                print(f"Fallback reason: {result.get('reason', '?')}")
        else:
            print("→ Stays on CC (deep reasoning required)")
    else:
        # Direct routing
        result = route_to_local(args.action, args.input)
        print(f"Source: {result.get('source', '?')}")
        if "response" in result:
            print(f"Response: {result['response']}")
        else:
            print(f"Fallback: {result.get('reason', '?')}")


if __name__ == "__main__":
    main()
