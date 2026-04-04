# Finetune / Local Model Workflow

## Architecture
- **Primary machine** = brain (LLM sessions, reasoning, code review)
- **GPU machine** = muscle (GPU training, local inference)
- **Connection:** Local network or VPN tunnel

## Training Pipeline
1. Export training data: `python3 scripts/finetune_data_formatter.py` → `data/training_data.jsonl`
2. Copy to GPU machine (or use shared path)
3. Train on GPU machine: `python finetune_scaffold.py --epochs N --batch 1`
4. Checkpoint saves at each epoch boundary (`save_strategy="epoch"`)
5. Merge: `python merge_and_export.py` (LoRA adapter + base model)
6. Convert: `convert_hf_to_gguf.py` → GGUF format
7. Load into Ollama: `ollama create scaffold-model-q4 --quantize q4_K_M -f Modelfile`
8. Test: ask system-specific questions WITH and WITHOUT context injection

## Evaluation Protocol
- **Without context:** Tests factual recall from weights alone. Hallucination = needs more training.
- **With context:** Tests context-following ability. Should be correct if model is functional.
- **Repeat loop check:** If model over-generates (loops on structured sections), needs `repeat_penalty 1.3` + more epochs.

## Which Tasks Go to Local Model
- Compile checks (pattern matching, no reasoning)
- Schema validation (format checking)
- Log entry classification (type assignment)
- Simple routing decisions

## Which Tasks Stay on Primary Model
- Adversarial review (needs deep reasoning)
- Cross-domain synthesis (needs full scaffold context)
- Experiment design and analysis
- Code changes to critical files

## Fallback
If local model output quality degrades, escalate to primary model. Don't trust local model for decisions — only for mechanical checks.

## Version Control
- Checkpoints saved at `scaffold-finetune/scaffold-model-lora/checkpoint-XXX`
- Merged models at `scaffold-finetune/merged-model/`
- GGUF at `scaffold-finetune/scaffold-model.gguf`
- Ollama model: `scaffold-model-q4`
- Training data version tied to vault snapshot date

## Retrain Cadence
Weekly or after major build sessions (50+ new vault notes or chains). The training data formatter pulls from current vault state.
