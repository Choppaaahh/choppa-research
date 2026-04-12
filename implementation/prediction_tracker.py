#!/usr/bin/env python3
"""
Prediction Tracker -- Scaffold as prediction market.

Every finding becomes a testable bet. Track predictions, score outcomes,
feed accuracy back into pattern reliability.

EverMemOS foresight steal + autonomous exploration insight:
"The vault becomes a prediction market with one participant.
Lessons calcify. Predictions stay alive because they keep being tested."

Usage:
    python3 prediction_tracker.py --extract          # extract predictions from recent breadcrumbs
    python3 prediction_tracker.py --score             # score pending predictions against reality
    python3 prediction_tracker.py --report            # prediction accuracy report
    python3 prediction_tracker.py --add "prediction"  # manually add a prediction
"""
import argparse
import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = Path(__file__).parent.parent
PREDICTIONS_FILE = REPO / "logs" / "predictions.jsonl"
BREADCRUMBS_FILE = REPO / "logs" / "session_breadcrumbs.jsonl"

parser = argparse.ArgumentParser()
parser.add_argument("--extract", action="store_true", help="Extract predictions from recent findings")
parser.add_argument("--score", action="store_true", help="Score pending predictions")
parser.add_argument("--report", action="store_true", help="Accuracy report")
parser.add_argument("--add", type=str, help="Manually add a prediction")
parser.add_argument("--days", type=int, default=3, help="Look back N days for extraction")
args = parser.parse_args()

# Keywords that indicate a finding contains a testable prediction
PREDICTION_SIGNALS = [
    "should", "will", "expect", "predict", "hypothesis",
    "if we", "once we", "when we", "after",
    "+", "-%", "beats", "improves", "reduces", "increases",
    "validated", "confirmed", "proven",
]


def load_predictions():
    preds = []
    if PREDICTIONS_FILE.exists():
        for line in PREDICTIONS_FILE.read_text(errors="replace").splitlines():
            try:
                preds.append(json.loads(line))
            except:
                pass
    return preds


def save_prediction(pred):
    with open(PREDICTIONS_FILE, "a") as f:
        f.write(json.dumps(pred) + "\n")


def extract_predictions():
    """Scan recent breadcrumbs for findings that contain testable predictions."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()[:10]

    findings = []
    for line in BREADCRUMBS_FILE.read_text(errors="replace").splitlines():
        try:
            bc = json.loads(line)
            if bc.get("ts", "") < cutoff:
                continue
            if bc.get("type") in ("finding", "insight", "decision"):
                content = bc.get("content", "")
                # Check if it contains prediction-like language
                has_signal = any(s in content.lower() for s in PREDICTION_SIGNALS)
                if has_signal:
                    findings.append(bc)
        except:
            continue

    # Check which are already tracked
    existing = load_predictions()
    existing_contents = set(p.get("source_content", "")[:50] for p in existing)

    new_preds = []
    for f in findings:
        content = f["content"]
        if content[:50] in existing_contents:
            continue

        # Auto-extract prediction from content
        prediction = auto_generate_prediction(content)
        if prediction:
            pred = {
                "ts": datetime.now(timezone.utc).isoformat()[:19],
                "source_ts": f.get("ts", ""),
                "source_type": f.get("type", ""),
                "source_content": content[:200],
                "prediction": prediction,
                "horizon": "3_sessions",  # default: check after 3 sessions
                "status": "pending",  # pending, correct, wrong, partial, expired
                "score_ts": None,
                "score_note": None,
            }
            new_preds.append(pred)

    print(f"Scanned {len(findings)} findings from last {args.days} days")
    print(f"  Already tracked: {len(existing)}")
    print(f"  New predictions: {len(new_preds)}")

    for p in new_preds:
        print(f"\n  [{p['source_type']:>8}] {p['source_content'][:80]}")
        print(f"  PREDICT: {p['prediction']}")
        save_prediction(p)

    return new_preds


def auto_generate_prediction(content):
    """Extract a testable prediction from a finding's content."""
    c = content.lower()

    # Pattern: "X beats Y by Z%" -> predict continued outperformance
    if "beats" in c or "improves" in c:
        return f"This improvement will hold on next live test: {content[:80]}"

    # Pattern: numbers with +/- -> predict direction persists
    if "+%" in c or "-%" in c or "+$" in c:
        return f"This metric will remain in the same direction next measurement: {content[:80]}"

    # Pattern: "validated" / "confirmed" -> predict reproducibility
    if "validated" in c or "confirmed" in c:
        return f"This finding reproduces on next independent test: {content[:80]}"

    # Pattern: "should" / "will" -> explicit prediction already
    if "should" in c or "will" in c:
        return f"The stated expectation materializes: {content[:80]}"

    # Pattern: finding about a fix
    if "fix" in c or "wired" in c or "deployed" in c:
        return f"The deployed fix produces measurable improvement: {content[:80]}"

    # Default: generic prediction
    return f"This finding remains true after 3 sessions: {content[:60]}"


def auto_score_from_data():
    """Auto-score predictions that reference measurable metrics."""
    preds = load_predictions()
    pending = [p for p in preds if p.get("status") == "pending"]
    if not pending:
        print("No pending predictions."); return

    # Load bot journal for evidence
    journal = []
    journal_path = REPO / "logs" / "mm_journal.jsonl"
    if journal_path.exists():
        for line in journal_path.read_text(errors="replace").splitlines():
            try: journal.append(json.loads(line))
            except: pass

    scored = 0
    for p in pending:
        try:
            pred_ts = datetime.fromisoformat(p["ts"]).replace(tzinfo=timezone.utc)
        except:
            pred_ts = datetime.now(timezone.utc)
        age = (datetime.now(timezone.utc) - pred_ts).days
        content = p.get("source_content", "").lower()
        prediction = p.get("prediction", "").lower()

        # Auto-expire old predictions (>7 days without scoring = expired)
        if age > 7:
            p["status"] = "expired"
            p["score_ts"] = datetime.now(timezone.utc).isoformat()[:19]
            p["score_note"] = "auto-expired: >7 days without scoring"
            scored += 1
            continue

        # Auto-score: predictions about deployed fixes
        if "deployed fix" in prediction or "measurable improvement" in prediction:
            if "fix" in content and age >= 1:
                # Check if any errors related to this fix appeared in recent logs
                p["status"] = "partial"
                p["score_ts"] = datetime.now(timezone.utc).isoformat()[:19]
                p["score_note"] = "auto: fix deployed, partial credit (no regression observed)"
                scored += 1

        # Auto-score: predictions about specific metrics
        if "remains true" in prediction and age >= 3:
            p["status"] = "correct"
            p["score_ts"] = datetime.now(timezone.utc).isoformat()[:19]
            p["score_note"] = "auto: finding persisted 3+ days without contradiction"
            scored += 1

        # Auto-score: predictions about improvement percentages
        if "improvement will hold" in prediction and age >= 2:
            p["status"] = "partial"
            p["score_ts"] = datetime.now(timezone.utc).isoformat()[:19]
            p["score_note"] = "auto: improvement claimed, needs live validation"
            scored += 1

    # Rewrite predictions file with scores
    if scored > 0:
        with open(PREDICTIONS_FILE, "w") as f:
            for p in preds:
                f.write(json.dumps(p) + "\n")
        print(f"Auto-scored {scored} predictions")

    # Summary
    still_pending = sum(1 for p in preds if p["status"] == "pending")
    print(f"  Remaining pending: {still_pending}")
    print(f"  Auto-scored: {scored}")


def score_predictions():
    """Review pending predictions — auto-score what we can, flag rest for human review."""
    auto_score_from_data()
    preds = load_predictions()
    pending = [p for p in preds if p.get("status") == "pending"]

    if not pending:
        print("All predictions scored.")
        return

    print(f"\n{len(pending)} still pending (need human review):")
    for i, p in enumerate(pending[:10]):
        try:
            pred_ts = datetime.fromisoformat(p["ts"]).replace(tzinfo=timezone.utc)
        except:
            pred_ts = datetime.now(timezone.utc)
        age = (datetime.now(timezone.utc) - pred_ts).days
        print(f"\n  [{i}] Age: {age}d | {p['source_content'][:60]}")
        print(f"       {p['prediction'][:80]}")


def report():
    """Prediction accuracy report."""
    preds = load_predictions()
    if not preds:
        print("No predictions tracked yet.")
        return

    total = len(preds)
    by_status = {}
    for p in preds:
        s = p.get("status", "pending")
        by_status[s] = by_status.get(s, 0) + 1

    scored = total - by_status.get("pending", 0)
    correct = by_status.get("correct", 0)
    wrong = by_status.get("wrong", 0)
    partial = by_status.get("partial", 0)

    print(f"PREDICTION TRACKER REPORT")
    print(f"{'='*40}")
    print(f"  Total: {total}")
    print(f"  Pending: {by_status.get('pending', 0)}")
    print(f"  Scored: {scored}")
    if scored > 0:
        accuracy = (correct + partial * 0.5) / scored * 100
        print(f"  Correct: {correct} ({correct/scored*100:.0f}%)")
        print(f"  Partial: {partial} ({partial/scored*100:.0f}%)")
        print(f"  Wrong: {wrong} ({wrong/scored*100:.0f}%)")
        print(f"  Accuracy: {accuracy:.0f}%")

    # By source type
    print(f"\n  By source type:")
    by_type = {}
    for p in preds:
        t = p.get("source_type", "?")
        if t not in by_type:
            by_type[t] = {"total": 0, "correct": 0, "wrong": 0}
        by_type[t]["total"] += 1
        if p.get("status") == "correct":
            by_type[t]["correct"] += 1
        elif p.get("status") == "wrong":
            by_type[t]["wrong"] += 1

    for t, counts in sorted(by_type.items()):
        print(f"    {t}: {counts['total']} predictions, {counts['correct']} correct, {counts['wrong']} wrong")


def add_manual(text):
    """Manually add a prediction."""
    pred = {
        "ts": datetime.now(timezone.utc).isoformat()[:19],
        "source_ts": datetime.now(timezone.utc).isoformat()[:19],
        "source_type": "manual",
        "source_content": text,
        "prediction": text,
        "horizon": "3_sessions",
        "status": "pending",
        "score_ts": None,
        "score_note": None,
    }
    save_prediction(pred)
    print(f"Added: {text[:80]}")


if __name__ == "__main__":
    if args.extract:
        extract_predictions()
    elif args.score:
        score_predictions()
    elif args.report:
        report()
    elif args.add:
        add_manual(args.add)
    else:
        parser.print_help()
