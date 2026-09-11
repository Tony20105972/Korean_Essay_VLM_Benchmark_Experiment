# NonsulFit Agent Guide

This repository is built for AI-native development.

Canonical project knowledge lives in `docs/`.
This file is only an entrypoint and operating guide.

## Start Here

Read in this order:

1. `docs/index.md`
2. `ARCHITECTURE.md`
3. Task-relevant canonical docs
4. Relevant code
5. Relevant tests

Do not scan the entire repository without a reason.

## Core System

```text
Student Answer Image
→ Perception
→ Evidence
→ Decision
→ Generation
```

Current engineering priority:

```text
Perception + Evaluation Harness
```

## Critical Invariants

* Perception preserves what the student actually wrote.
* Do not correct spelling, grammar, awkward wording, or student mistakes.
* `Unreadable ≠ Guess`.
* Insufficient visual evidence must remain uncertain or unreadable.
* Uncertain output must not propagate as confirmed evidence.
* Capture quality and handwriting difficulty are separate risks.
* Provider-specific SDKs and response types stay behind the Model Gateway.
* Final Golden holdout data is never used for training or optimization.
* Original student images are immutable source artifacts.

Canonical rules:

```text
docs/architecture/boundaries.md
docs/ai/perception/verbatim-contract.md
docs/ai/evaluation/metrics.md
docs/ai/datasets/dataset-policy.md
```

## Work

For non-trivial tasks:

```text
Understand
→ Inspect
→ Plan
→ Implement
→ Verify
→ Review
```

Use an ExecPlan when the work is multi-step, architecture-affecting, AI-behavior-affecting, or difficult to verify.

```text
docs/exec-plans/active/
```

Prefer repository commands:

```bash
./scripts/dev
./scripts/test
./scripts/lint
./scripts/typecheck
./scripts/verify
./scripts/agent/doctor
```

## AI Changes

Treat model, prompt, preprocessing, parsing, verification, routing, and threshold changes as experiments.

```text
Baseline
→ Controlled Change
→ Same Dataset
→ Benchmark
→ Regression Review
→ Accept / Reject
```

Do not claim improvement from examples or CER alone.

## Completion

A task is complete only when supported by evidence.

Check the relevant:

* acceptance criteria
* tests
* typecheck / lint
* architecture boundaries
* AI benchmarks
* dataset integrity
* canonical docs

Full rules:

```text
docs/quality/definition-of-done.md
```

## Harness Improvement

When a failure repeats, improve the environment instead of extending prompts.

```text
Docs
→ Skill
→ Script
→ Test / Lint
→ CI
```
