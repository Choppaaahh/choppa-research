# Query-to-Vault Pipeline — File Good Answers

When an agent produces a substantive analysis that crosses ANY of these thresholds:
- Contains data (numbers, tables, comparisons)
- Spans 3+ paragraphs of original synthesis
- Connects concepts across domains
- Produces a reusable framework or checklist
- Answers a question that would be asked again

Then IMMEDIATELY prompt: "This looks vault-worthy. Save as note?"

If yes (or user says "vault it", "save that", "note that"):
1. Write to `knowledge/captures/` with frontmatter
2. Follow the extract pipeline: `/extract` → `/connect` → `/validate`
3. Or shortcut: write directly to `knowledge/notes/` with proper frontmatter if the content is already well-formed

## Examples of vault-worthy outputs
- Instrument spread analysis (comparison across symbols with bp measurements)
- Self-tuning architecture design (fast/slow loop structure)
- Config validation results (win rate data from dry-run)
- Model fine-tuning findings (what the model learned and when)

## Examples of NOT vault-worthy
- "Git push commands" — operational, not knowledge
- "Check the log" — ephemeral
- Debug traces — temporary

## Why This Exists
Karpathy's LLM Wiki insight: "good answers can be filed back into the wiki as new pages. A comparison you asked for, an analysis, a connection you discovered — these are valuable and shouldn't disappear into chat history."

Chat history gets compacted. Vault notes persist. If the answer is worth computing, it's worth preserving.
