#!/usr/bin/env python3
"""
Local Inference Router — sends mechanical tasks to a local LLM via Ollama API.

Host (orchestration brain) → local network → GPU machine (Ollama) → response back.

Architecture: hybrid local+cloud. Mechanical tasks (compile checks, schema validation,
breadcrumb classification) stay on the local model. Reasoning tasks escalate to cloud.

Usage:
    python3 local_inference.py "Does this compile?" --context "import os; print('hi')"
    python3 local_inference.py --compile some_script.py
    python3 local_inference.py --classify "User deployed new config"

Configuration:
    Set OLLAMA_HOST env var to your Ollama endpoint, e.g.:
        export OLLAMA_HOST="http://YOUR_MACHINE_IP:11434"
    Or edit OLLAMA_URL directly below.
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://[PLACEHOLDER_OLLAMA_HOST]:11434") + "/api/generate"
MODEL = os.getenv("LOCAL_MODEL_NAME", "your-model-name-here")  # e.g. "llama3", "qwen2.5", etc.
MAX_TOKENS = 100  # prevent repeat loops
TIMEOUT = 30


def query_local(prompt, context="", max_tokens=MAX_TOKENS):
    """Send a prompt to the local model via Ollama API."""
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
        return {"error": str(e), "fallback": "cloud"}


def compile_check(filepath):
    """Ask local model if a Python file looks correct."""
    path = Path(filepath)
    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    code = path.read_text()[:2000]  # first 2K chars
    return query_local(
        "Does this Python code have any syntax errors? Answer YES or NO, then one line explanation.",
        context=f"```python\n{code}\n```",
        max_tokens=50,
    )


def classify_breadcrumb(text):
    """Ask local model to classify a breadcrumb type."""
    return query_local(
        f"Classify this event as one of: decision, finding, insight, action, dialogue. Answer with ONE WORD only.\n\nEvent: {text}",
        max_tokens=10,
    )


def schema_check(frontmatter):
    """Ask local model if vault note frontmatter is valid."""
    return query_local(
        "Is this vault note frontmatter valid? Must have: summary, type, status, domains. Answer YES or NO, then list missing fields.",
        context=frontmatter,
        max_tokens=50,
    )


def main():
    parser = argparse.ArgumentParser(description="Local Inference Router")
    parser.add_argument("prompt", nargs="?", help="Direct prompt")
    parser.add_argument("--context", type=str, default="", help="Context to prepend")
    parser.add_argument("--compile", type=str, help="Compile check a .py file")
    parser.add_argument("--classify", type=str, help="Classify a breadcrumb")
    parser.add_argument("--schema", type=str, help="Check frontmatter schema")
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    args = parser.parse_args()

    if args.compile:
        result = compile_check(args.compile)
    elif args.classify:
        result = classify_breadcrumb(args.classify)
    elif args.schema:
        result = schema_check(args.schema)
    elif args.prompt:
        result = query_local(args.prompt, args.context, args.max_tokens)
    else:
        parser.print_help()
        return

    if "error" in result:
        print(f"ERROR: {result['error']} (fallback to cloud)", file=sys.stderr)
        sys.exit(1)
    else:
        print(result["response"])
        print(f"  [{result['time_s']}s, {result['tokens']} tokens, {result['model']}]", file=sys.stderr)


if __name__ == "__main__":
    main()
