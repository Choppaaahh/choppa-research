#!/usr/bin/env python3
"""
Self-Organizing Agent Dispatch -- Sequential protocol from Dochkina (2603.28990).

Spawns N agents in sequence. Each sees all prior outputs before deciding
their role. No fixed assignments. 14% better than centralized coordination.

Usage:
    # Dispatch a task to 3 self-organizing agents
    python3 scripts/self_org_dispatch.py "Review the toxicity adjustment code in equities_mm.py" --agents 3

    # With specific model
    python3 scripts/self_org_dispatch.py "Analyze DQN V3 performance" --agents 4 --model sonnet

    # Dry run (show what would be dispatched)
    python3 scripts/self_org_dispatch.py "task" --agents 3 --dry-run
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).parent.parent

parser = argparse.ArgumentParser(description="Self-organizing agent dispatch")
parser.add_argument("task", help="Task description")
parser.add_argument("--agents", type=int, default=3, help="Number of sequential agents")
parser.add_argument("--model", type=str, default="sonnet", choices=["opus", "sonnet", "haiku"])
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("--timeout", type=int, default=120, help="Timeout per agent (seconds)")
args = parser.parse_args()


def build_prompt(task, prior_outputs, agent_num, total_agents):
    """Build the prompt for agent N in the sequence."""
    prompt = f"""SELF-ORGANIZING SEQUENTIAL PROTOCOL (Agent {agent_num}/{total_agents})

TASK: {task}

"""
    if prior_outputs:
        prompt += "PRIOR AGENT OUTPUTS (factual work products — read before deciding your role):\n"
        prompt += "=" * 60 + "\n"
        for i, output in enumerate(prior_outputs):
            prompt += f"\n--- Agent {i+1} ---\n{output}\n"
        prompt += "=" * 60 + "\n\n"
    else:
        prompt += "You are FIRST in the sequence. No prior outputs.\n\n"

    prompt += """INSTRUCTIONS:
1. Read the task and any prior outputs above
2. Self-assess: what role would be most valuable NOW?
3. If prior agents already covered this well, ABSTAIN
4. Otherwise, pick your role and execute

Start your response with:
ROLE: [your chosen role]
RATIONALE: [why this role, given what's been done]

Then produce your work product.

If abstaining:
ABSTAIN: [reason]
CONFIDENCE: [0-100]%
"""
    return prompt


def run_agent(prompt, model="sonnet", timeout=120):
    """Run a single agent via claude CLI."""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", model, "--dangerously-skip-permissions"],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(REPO)
        )
        return result.stdout.strip() if result.returncode == 0 else f"ERROR: {result.stderr[:200]}"
    except subprocess.TimeoutExpired:
        return "TIMEOUT: agent exceeded time limit"
    except Exception as e:
        return f"ERROR: {e}"


def main():
    print(f"Self-Org Dispatch: {args.agents} agents, model={args.model}")
    print(f"Task: {args.task}")
    print()

    prior_outputs = []
    results = []

    for i in range(1, args.agents + 1):
        prompt = build_prompt(args.task, prior_outputs, i, args.agents)

        if args.dry_run:
            print(f"Agent {i}/{args.agents}: would run {args.model} with {len(prompt)} char prompt")
            print(f"  Prior outputs: {len(prior_outputs)}")
            continue

        print(f"Agent {i}/{args.agents} running ({args.model})...", flush=True)
        t0 = time.time()
        output = run_agent(prompt, args.model, args.timeout)
        elapsed = time.time() - t0

        # Check for abstention
        abstained = "ABSTAIN:" in output[:200]
        role = "ABSTAINED"
        if not abstained:
            for line in output.split("\n")[:5]:
                if line.startswith("ROLE:"):
                    role = line.replace("ROLE:", "").strip()
                    break

        print(f"  Role: {role} ({elapsed:.0f}s, {len(output)} chars)")
        if abstained:
            print(f"  {output[:200]}")
        else:
            # Show first 3 lines of actual output
            content_lines = [l for l in output.split("\n") if l.strip() and not l.startswith("ROLE:") and not l.startswith("RATIONALE:")]
            for l in content_lines[:3]:
                print(f"  {l[:100]}")

        prior_outputs.append(output)
        results.append({
            "agent": i,
            "role": role,
            "abstained": abstained,
            "elapsed": elapsed,
            "output_len": len(output),
        })

    if args.dry_run:
        return

    # Summary
    print(f"\n{'='*60}")
    print(f"DISPATCH COMPLETE: {args.agents} agents")
    active = sum(1 for r in results if not r["abstained"])
    abstained = sum(1 for r in results if r["abstained"])
    print(f"  Active: {active}, Abstained: {abstained}")
    print(f"  Roles: {', '.join(r['role'] for r in results)}")
    total_time = sum(r["elapsed"] for r in results)
    print(f"  Total time: {total_time:.0f}s")

    # Save log
    log_path = REPO / "logs" / "self_org_dispatches.jsonl"
    log_entry = {
        "ts": datetime.now(timezone.utc).isoformat()[:19],
        "task": args.task[:200],
        "n_agents": args.agents,
        "model": args.model,
        "active": active,
        "abstained": abstained,
        "roles": [r["role"] for r in results],
        "total_time": round(total_time, 1),
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Save full outputs for review
    output_path = REPO / "logs" / f"self_org_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_path, "w") as f:
        f.write(f"# Self-Org Dispatch: {args.task}\n\n")
        f.write(f"Agents: {args.agents}, Model: {args.model}\n")
        f.write(f"Active: {active}, Abstained: {abstained}\n\n")
        for i, output in enumerate(prior_outputs):
            f.write(f"## Agent {i+1}\n\n{output}\n\n---\n\n")
    print(f"  Full outputs: {output_path}")


if __name__ == "__main__":
    main()
