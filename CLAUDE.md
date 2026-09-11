# NonsulFit Claude Code Guide

Use `AGENTS.md` and `docs/` as the source of truth.

## Bootstrap

Start with:

```text
AGENTS.md
docs/index.md
```

Then read only the context required for the task.

Do not use chat history as canonical project state.

## Perception Safety

NonsulFit optimizes for **visual evidence and verbatim fidelity**, not natural language plausibility.

```text
Unreadable ≠ Guess
```

If handwriting is ambiguous:

* do not guess from context
* do not silently correct it
* preserve uncertainty
* keep unreadable regions explicit

A high-quality image can still contain unreadable handwriting.

```text
Capture Quality ≠ Recognition Difficulty
```

Never allow uncertain transcription to become confirmed evidence without verification.

## Before Editing

For non-trivial work:

1. Read the governing docs.
2. Inspect the current implementation.
3. Inspect relevant tests.
4. Identify architecture constraints.
5. Create or update an ExecPlan when needed.

## Implementation

Prefer:

```text
explicit > implicit
simple > clever
deterministic > magical
existing abstraction > duplicate abstraction
```

Keep provider-specific behavior behind the Model Gateway.

## Verification

Use repository commands whenever possible:

```bash
./scripts/test
./scripts/lint
./scripts/typecheck
./scripts/verify
```

If AI behavior can change, run the relevant benchmark.

For AI failures, distinguish:

```text
Model
Prompt
Capture Quality
Handwriting Difficulty
Parser
Dataset
Evaluation
Harness
```

Do not blame the model before identifying the failure class.

## Completion

Report only:

```text
What changed
Why
What was verified
Remaining risks
```

Never claim verification that was not performed.
