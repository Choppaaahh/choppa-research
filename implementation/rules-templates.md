# Rules Templates

Rules are `.claude/rules/name.md` files that auto-load based on glob patterns. They enforce behavior that memory and conversation can't carry across sessions.

## Rule File Structure

```yaml
---
glob: "**/*.py"  # when editing Python files, load this rule
description: What this rule enforces
---

# Rule content — instructions that fire every time matching files are touched
```

## Essential Rules

### Breadcrumb Capture (automatic, proactive)
```yaml
---
glob: "**/*"
description: Capture decisions, findings, insights as they happen
---

Append to logs/session_breadcrumbs.jsonl IMMEDIATELY when:
- A decision is made
- Data reveals something
- A cross-domain connection is found
- Something is built or shipped
- A reframing happens

Format: {"ts":"ISO","type":"decision|finding|insight|action","content":"one line"}

DO NOT wait to be asked. DO NOT batch. Write each as it happens.
```

### Metacognitive Self-Tracking (automatic)
```yaml
---
glob: "**/*"
description: Save reasoning chains when deep multi-step reasoning happens
---

When you do multi-step reasoning that produces a real finding, log it:
{"ts":"ISO","trigger":"what started it","chain":"step1→step2→step3","outcome":"what it produced","pattern":"reusable-name","reusable":true}

Append to logs/reasoning_chains.jsonl.
```

### QA Routing (code changes)
```yaml
---
glob: "scripts/**/*.py"
description: Every code edit gets reviewed
---

After editing ANY code file:
1. Compile check passes
2. IMMEDIATELY send to QA agent for review
3. DO NOT move to next task until review is sent
```

### Living Document Freshness
```yaml
---
glob: "**/*"
description: Keep living documents current
---

Update these when their content changes:
- MEMORY.md — config, balance, state changes
- CLAUDE.md — quick status, current state
- todo.md — task completed or discovered
- Agent configs — context goes stale

Don't wait for session end. Update IMMEDIATELY when a change happens.
```

## Key Principle

Rules > memory > conversation for behavioral persistence. A rule that fires every session beats a memory note that says "remember to do X." If a behavior matters, make it a rule.
