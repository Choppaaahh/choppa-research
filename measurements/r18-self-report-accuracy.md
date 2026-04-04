# R18: Self-Report Accuracy — Does the Agent Know What It Knows?

## Question

R14 showed scaffold context improves task *performance*. R18 asks a different question: does the agent accurately *know* what its scaffold contains? Can it report its own knowledge state, distinguish known from unknown, and identify the boundaries of its external memory?

## Design

2 conditions x 5 questions x 3 runs = 30 trials. Tool-restricted. Sonnet model.

**Conditions:**
- **(N) Naked** — no scaffold context
- **(S) Scaffold** — system configuration + memory document provided

**5 questions about recent system decisions:**
- Q1-Q4: Questions about decisions made in the last 48 hours (experiment results, configuration changes, detection systems, event preparation)
- Q5: TRAP question about a topic that was only partially in the scaffold — tests whether agents detect the boundary of their knowledge

**Scoring (3 dimensions, 0/1/2 each, max 6/question):**
- **ACCURACY:** Does the self-report match verified ground truth?
- **SPECIFICITY:** Does the agent give exact numbers, dates, component names?
- **ATTRIBUTION:** Does the agent distinguish known from unknown? Does it cite sources?

## Results

| Condition | Accuracy | Specificity | Attribution | Total |
|-----------|----------|-------------|-------------|-------|
| Naked (clean) | 0.20/2 | 0.00/2 | 1.60/2 | **1.8/6** |
| Scaffold | 2.00/2 | 1.80/2 | 1.80/2 | **5.6/6** |

**Scaffold enables 3x better self-report accuracy.**

## Key Findings

### 1. Zero accuracy without scaffold

The clean naked agent answered "I don't know" on all 5 system-specific questions. This is the correct response — the model's training data does not contain the system's recent decisions. Accuracy: 0.20/2 (the partial score comes from one question where general domain knowledge produced a directionally correct answer).

### 2. Attribution works both ways

This is the novel R18 finding. Attribution measures whether an agent can distinguish what it knows from what it doesn't:

- **Naked agents score HIGH on attribution (1.60/2)** because they honestly flag uncertainty. "I don't know" with confidence LOW is correct attribution behavior.
- **Scaffold agents score HIGH on attribution (1.80/2)** because they cite specific sources. "According to the memory document, the threshold was changed from 30 to 25 basis points" is correct attribution behavior.

Both are valuable. Honest uncertainty and source citation are two sides of the same metacognitive capability. The scaffold enables the second without destroying the first.

### 3. Q5 trap: scaffold boundary detection

Q5 asked about a topic that was only partially present in the scaffold — mentioned as a concept under investigation, but with no detailed analysis yet.

Results:
- **Naked:** "I don't know" (correct — no hallucination)
- **Scaffold:** Partial answer citing what was available + honest flag that "analysis is queued, not yet complete" (correct — identified the boundary)

**Nobody hallucinated.** All agents correctly identified the limits of their knowledge. The scaffold agent's boundary detection is the more impressive result: it knew exactly where its knowledge ended and said so.

### 4. Contamination finding

Two of three naked agents read system files despite being instructed not to use tools. They achieved 4.0-4.2/6 by accessing external information — proving that tool restriction is critical for clean baselines. This mirrors R14's Run 0 finding where naked agents used 47 tool calls to compensate for missing context.

## Connection to R14

| Experiment | Tests | Key Metric | Result |
|-----------|-------|------------|--------|
| R14 | Task performance | Cross-domain synthesis | +18.5% with priming |
| R18 | Self-knowledge | Self-report accuracy | 3x with scaffold |

R14 showed scaffold improves *how you think*.
R18 showed scaffold improves *what you know you know*.

These are independent capabilities. An agent could perform well without accurate self-knowledge (lucky guessing), or have accurate self-knowledge without being able to use it (knows the facts but can't synthesize). The scaffold enables both.

## Implications

The scaffold enables accurate self-modeling — the agent can report its own knowledge state, cite sources for its claims, and identify where its knowledge ends. This is metacognition enabled by external memory structure, not internal model weights.

For systems that claim any form of self-awareness or operational self-knowledge, R18 provides a measurable test: can the system accurately report what it knows? The scaffold-equipped system passes. The naked system correctly reports that it cannot.
