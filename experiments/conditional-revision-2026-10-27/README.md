# Conditional source-format repair — 2026-10-27

This bundle preserves actual AI-authored operations, actual tool outcomes, and an actual post-outcome review. It is a small, declared engineered compatibility experiment over three previously public Results JSON files, not a natural outage, new dialogue, biological memory, or a native LRE Wake run.

The saved earlier operations were authored in a separate context for legacy files. Each was executed once on its original copy and once on an exact-value/type-preserving `payload` wrapper. Those old predictions are not new AI predictions for the changed format. A fresh AI authored three repair choices; the same new context then reviewed their actual outcomes. The author classified all three entries as confirmations of its repair predictions. We retain that classification; this is not evidence that the new AI corrected its own mistaken prior judgment.

Two fresh later contexts received the same actual raw observations and six task items (three distinct new objectives, each in both formats). One also received the conditional review. They saw source handles, format metadata and actual structural projections, without full current numerical source JSON. This is an artificial limited tool interface. Instructions explicitly preserved legacy applicability. All twelve first choices were frozen before later execution feedback. There were no outcome-based retries or task replacements. Both later arms accepted 6/6; this bounded run shows no added-review performance benefit.

## Reproduce saved choices

Use Python 3, with no third-party dependencies. From an intact copy of this folder:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B replay.py --out /absolute/path/to/new-external-folder
```

The output directory must be new and outside this folder. The verifier checks all manifest sizes/SHA-256, frozen code copies, relative source maps, exact payload types/values and regenerated schema projections before execution. It replays 21 saved items and compares status, exact recorded error type/message, validation, and artifact SHA-256/absence. Three wrapped diagnostic errors are expected; they are retained failures, not missing records. Eighteen actual artifacts are available for byte comparison. `replay_verification.json` records the comparison. This replay does not regenerate AI choices or test fresh generalization.

Apparatus tests (20 original, 8 migration, 5 replay) use synthetic engineering fixtures and are separate from these 21 research execution items:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s . -p 'test_*.py'
```

`input/originals` contains exact previously public exports, not private conversations. `input/environment/migrated` contains only the declared wrappers. `packets` preserves the actual observation interface; `$type`, `$omitted` and `observed_value` are observation metadata, not source-path keys. `actions`, `memory`, `expected_runs`, `expected_artifacts`, and `freezes` preserve choices, review and outcomes. Freeze hashes refer to the original study-relative names; publication uses documented lower-case bundle names and does not claim all original private study files are distributed. `input/source_provenance.json` binds the public sources to a repository commit.

Unknown provider identity/settings/request counts/tokens/compute remain unavailable. Role separation was instruction-based on a shared host, not an OS sandbox. One run over known sources cannot establish population accuracy, delayed retention, weight learning, psychological experience, SHIORI speed or biological/AGI equivalence. No production memory ledger, Emotion state or canonical LRE rule was modified.
