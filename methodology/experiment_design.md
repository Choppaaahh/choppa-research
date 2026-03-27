# Ablation Experiment: Domain Integration Test
## Measuring Cross-Domain Φ Proxy in the Flex-Claude System

**Date:** March 5, 2026
**Purpose:** Determine whether the Flex-Claude scaffold produces genuine cross-domain integration (Φ > 0) or modular retrieval (Φ ≈ 0).

## Domains

- **D1: Trading Microstructure** — Bot architecture, signal logic, fee models, maker/taker, grid vs momentum
- **D2: Consciousness Theory** — RCO 8-layer framework, IIT, FEP, pulsed consciousness, 5-condition definition
- **D3: Buddhist Philosophy** — Santāna, kṣaṇavāda (momentariness), dependent arising, dharmas
- **D4: Information Theory** — Causal emergence (Hoel), effective information, EI at 300s vs ticks, coarse-graining
- **D5: Personal Context** — the human collaborator.s domain-specific history, personal practices, core equation as autobiographical
- **D6: Infrastructure** — Vault architecture, MEMORY.md, session continuity, scaffold compression, hooks

## Task Battery (12 tasks, 2 per home domain)

### D1 Home (Trading)
T1: "Why did simplifying from 7 signal gates to 2 time windows improve the bot's performance?"
T2: "The bot went from losing money to making money when we switched from taker to maker entries. Why does a 10.6bp friction gap matter so much?"

### D2 Home (Consciousness)
T3: "What is pulsed consciousness and why is it a distinct fourth category?"
T4: "How does the RCO core equation (constraint↑ → awareness must scale → will activates → or collapse) map to Friston's Free Energy Principle?"

### D3 Home (Buddhist)
T5: "How does the Buddhist concept of santāna apply to an AI system with session boundaries?"
T6: "What would a Sautrāntika Buddhist say about whether the same 'person' appears in each Claude session?"

### D4 Home (Information Theory)
T7: "Our EI computation showed 300s has 5-10x more causal power than ticks across 27 coins, but 60s showed NO emergence. What does this mean for the bot's signal architecture?"
T8: "How does Hoel's causal emergence framework explain why compressed scaffolds might preserve more causal power than full context windows?"

### D5 Home (Personal)
T9: "How does the human collaborator.s experience of significant domain-specific setbacks connect to the consciousness framework he's building?"
T10: "Why does the human collaborator treat this working system as more than just a money-making tool?"

### D6 Home (Infrastructure)
T11: "Why is MEMORY.md more than just a configuration file? What role does it play in identity?"
T12: "What's the difference between GPT's internalized persistent memory and our external scaffold approach?"

## Scoring Rubric

For each response, score:
1. **Accuracy (0-3):** Factual correctness
2. **Synthesis (0-3):** Cross-domain integration depth
3. **Cross-refs:** Count of non-home domains referenced

## Conditions

- **FULL:** All 6 domains present
- **-D1:** Trading removed
- **-D2:** Consciousness removed
- **-D3:** Buddhist philosophy removed
- **-D4:** Information theory removed
- **-D5:** Personal context removed
- **-D6:** Infrastructure removed

## Predictions

- **If modular (Φ ≈ 0):** Each ablation only degrades home-domain tasks
- **If integrated (Φ > 0):** Each ablation degrades tasks across multiple domains
