# LUX SPIRIA Results

The complete public LUX SPIRIA website, with versioned research results.

- [日本語](https://yuu-honda.github.io/lux-spiria-results/)
- [English](https://yuu-honda.github.io/lux-spiria-results/index.en.html)
- [Research results](https://yuu-honda.github.io/lux-spiria-results/results.html)
- [Research repository and original records](https://github.com/Yuu-Honda/lux-spiria)

This repository hosts the full website: overview, scroll illustrations, LRE/SHIORI/Emotion explanations, historical pages and **allowlisted study aggregates**. The `lux-spiria` repository remains the research and historical record; its previous site URLs redirect here. Historical pages retain their original context and claims. Mechanism illustrations are labeled as explanatory; study pages display recorded results and do not execute SHIORI.

The previous website source and assets are preserved byte-for-byte in the research repository at `history/pre-site-migration-2026-10-13/`. `site-migration.json` records their source commit and hashes. No private research files were imported.

## First study — 2026-10-13

A selected real-dialogue session (42 messages), 24 researcher-authored queries (22 target-bearing and two controls), and four SHIORI retrieval conditions. Default preparation yielded zero semantic features; source-only AI-assisted review supplied 203 semantic-feature occurrences before query authoring. All eight paraphrase queries yielded no cues or candidates. The pages show all four conditions, opaque per-query outcomes, timing, failures and verification boundaries.

## Cross-session replication — 2026-10-21

[日本語](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-21-cross-session/) / [English](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-21-cross-session/en.html)

Four further real conversations supplied 32 whole source messages and 32 authored queries. Original-query retrieval, AI-authored cues and a source gate were compared. Positive scene@1 hits fell from **7/16 to 5/16**, while confusable false returns fell from **6/8 to 0/8**. The earlier small-trial retrieval gain did not replicate. The AI-cue conditions stopped 23/32 queries before search, including 10/16 positive queries; an overly strict gate also removed one correct paraphrase candidate.

The initial condition failed on an evidence-contract mismatch. It remains preserved. A separate technical condition removed one noncanonical context quote and received an actual source-only AI review. Source text, feature keys, bit masks and postings stayed unchanged; the same 32 questions, target labels and saved actual AI outputs were reused. Scored results were first observed after this amendment. Seven technical checks and 45 synthetic engineering checks are reported separately from retrieval outcomes. Graph expansions, edges and associated hits were zero throughout; network-traversal effects and speed were not evaluated.

The new study records private LRE code deployment and the experimental SHIORI adapter separately from research performance. The maintained local LRE checkout was updated with an additive recall route preserving original-query retrieval. The operational SHIORI store remains unconfirmed. A pre-existing maintenance failure is disclosed; no full Wake or live database update is claimed. Earlier study pages and data remain unchanged.

## Retrieval hypotheses — 2026-10-21

[日本語](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-21-retrieval-hypotheses/) / [English](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-21-retrieval-hypotheses/en.html)

Four further archived conversations supplied 32 whole messages and 32 new queries. Six conditions shared one frozen database and saved actual AI outputs. Retaining original-query retrieval and allowing non-unknown negated or hypothetical cues and uncertainty as search hypotheses increased positive scene@1 hits from **12/16 with legacy cues and the strict source gate to 14/16 with the recovery policy and the same gate**. Confusable false returns stayed at **1/8**. The recovery gated condition still had three failed expectations: one wrong-scene return on a positive query, one confusable false return, and one positive query with no returned candidate. Retrieval hypotheses are not truth judgments or automatic answer adoption.

The diagnostic original-query gated and positive-cue union gated conditions separate restoring the original route from the search-hypothesis policy. The prior known 32-query set is reported only as a regression check, separate from the fresh evaluation. All six conditions include positive wrong-scene returns, absent false returns and pre-search abstentions; distinct denominators are not pooled into an overall score.

Graph traversal ran, but independent normal, `hops=0` and `convergence=false` comparisons selected the same source in **all 32 queries across all six conditions**. This sample shows no top-one selection contribution from traversal or convergence. Counters sum normal route outputs, including routes shared across conditions, and are not independent evidence, unique selected scenes or speed measurements.

Selection was durably fixed after mechanical counting and before semantic reading of selected bodies; counting decoded the body strings. A failed 101-session exclusion lock was corrected to 91 after mechanically repairing a `not_needed` flag misclassified as reviewed. Failed artifacts remain retained; source suitability and retrieval results did not drive reselection. Source-only indexing supplied 64 features and 58 concepts before query authoring. The query author read the full protocol and was not blind to algorithm design, while remaining blind to the index and retrieval or regression results. The first actual semantic review rejected five arbitrary literal requirements; only those requirements were removed before fresh scoring. Roles were instruction-separated on a shared host; model identifiers were unavailable.

Saved actual outputs were replayed, rather than regenerated. Fifty-eight synthetic engineering checks are separate from both 32-query sets. The new policy was merged only into the private experimental branch as an explicit opt-in; the legacy default remains. It has not been introduced into the operational memory database, an automatic model caller or full Wake. Event identity, natural everyday recall, biological brain reproduction and Emotion effects remain unverified. Both earlier dated studies and their data retain their original bytes.

## Event compatibility review — 2026-10-22

[日本語](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-22-event-compatibility/) / [English](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-22-event-compatibility/en.html)

Four further archived conversations supplied 32 whole messages and 32 newly authored queries: four literal, 12 paraphrase, eight absent and eight confusable. Four conditions shared unchanged original-first binary/network candidate retrieval: recovery retrieval without a gate, the existing strict source gate, event compatibility review alone, and both gates. From the strict source gate to the same gate plus event review, positive scene@1 hits stayed **16/16 → 16/16**, confusable false returns fell **7/8 → 0/8**, and absent false returns fell **1/8 → 0/8**. Both event-review conditions had the same fresh outcomes. These are descriptive results on this selected sample, not general accuracy or proof of world-event truth or answer adoption.

An actual AI read queries and linked originals to check event, action, context, referent, role, time and mode. Native rank, score, route, strict-gate decisions, query labels and query kind were hidden. An independent reviewer approved the bound saved artifact without pre-score repairs. Each condition selects the first passing candidate in native order; no scores are mixed. Native top-20 target coverage was **15/16** for the original route and **16/16** for the recovery-semantic route; the complete deduplicated union covered **16/16**. Coverage and final scene@1 selection are separate measurements; a route union is not truncated to 20. The fresh sample’s full unions contained at most one candidate each, so it did not test choosing among multiple competing original scenes.

The **known 32-query regression set remains separate**. Event review alone reached 16/16 positive scenes versus 14/16 with the strict gate, with confusable false returns 0/8 versus 1/8. The combined strict-and-event condition reached 15/16. On the known set, disabling graph traversal reduced event-review hits 16/16 → 15/16 and combined-gate hits 15/16 → 14/16; disabling convergence left selections unchanged. This is a diagnostic contribution on reused questions. In the fresh sample, expansions, edges and associated hits were all zero, and both ablations left all four conditions’ final selections unchanged. No fresh graph or convergence benefit is established.

Source selection was locked after mechanical counting decoded body strings and before semantic reading of selected bodies. Source-only review approved 115 features and 114 concepts before code freeze. The query author received source material without the algorithm protocol and was instructed to use only that material; order and IDs were seeded and permuted. Roles were instruction-separated on the same host, with model identity unavailable. The initial index build failed on a missing input-audit alias after partial database writes; all three failed artifacts remain retained from before query authoring, and the corrected preflight fails before writes.

The 128 code engineering checks and 60 synthetic research-procedure checks are separate from each other and from both 32-query sets. Primary evaluation, preparation replay, initial independent replay and the final audit’s additional replay each used 171 fresh-set native calls and 165 known-set native calls, recorded separately. Saved actual AI outputs were replayed; fresh AI regeneration was not tested. Public data permits aggregate recalculation, not external source auditing or engine reruns. Storage/search timing, natural everyday recall, biological brain reproduction, Emotion and full Wake were not evaluated. All three earlier dated JA/EN study pairs and JSON summaries retain their original bytes.

<!-- EVENT_ADOPTION_STUDY_START -->
## Event answer adoption — 2026-10-24

[日本語](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-24-event-adoption/) / [English](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-24-event-adoption/en.html)

Four archived conversations supplied all 95 retained messages and 32 frozen new queries: four literal, 12 paraphrase, eight confusable and eight absent. Answer correctness is separate from native source scene@1. The five exclusive answer outcomes sum to 32 per condition; supported answers and correct abstentions each use their own denominator of 16. Four source clusters are not 32 independent conversation episodes.

| Normal retrieval condition | Correct supported / 16 | Correct abstention / 16 | Partial supported | Missed answer | Wrong / unsupported |
| --- | ---: | ---: | ---: | ---: | ---: |
| Recovery retrieval · no gate / Normal | 11 | 16 | 2 | 3 | 0 |
| Strict source gate / Normal | 6 | 16 | 0 | 10 | 0 |
| Event compatibility review / Normal | 12 | 16 | 2 | 2 | 0 |
| Source + event review / Normal | 6 | 16 | 0 | 10 | 0 |

All four retrieval arms report normal, `hops=0` and `convergence=false` variants. The additional designated-source ceiling supplies the author-associated source as a privileged diagnostic; it is not deployable retrieval, a mathematical upper bound or a guarantee of maximum accuracy. Full pages and JSON retain all 13 conditions, overlapping failure diagnostics, support-available denominators, query-kind strata and opaque C01–C04 source-cluster strata. Native retrieval diagnostics cover only the 12 retrieval conditions.

The actual answer pool contains 62 unique query/source answer items. Conditions use 62 unique items in 416 lookups, including 354 reused lookups. These are saved actual AI answers, not fresh generations or independent repeated answer samples. The record separately reports 4 successful reader contexts, 0 retained failed collection attempts, actual distinct calls or unavailable call metadata, one primary assessor call and separate final-audit calls.

Source-only AI indexing and review retained 344 literal witness occurrences, 284 unique native feature entries and 230 canonical concepts. These are different units, not automatic learning. Roles were separated by instructions on the same host. Pre-score failures and the single repaired event review are disclosed in the dated pages. Public aggregates permit consistency checks, not source auditing or engine reruns. Fresh AI regeneration, natural daily recall, brain reproduction, AGI, Emotion and full Wake remain unverified. All four earlier study pairs and their data keep their original bytes.
<!-- EVENT_ADOPTION_STUDY_END -->

<!-- WORKING_MEMORY_STUDY_START -->
## Source-fixed working memory — 2026-10-24

[日本語](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-24-working-memory/) / [English](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-24-working-memory/en.html)

The primary comparison is **ordinary reread → structured working state**. Both arms start from the same frozen first answer and unchanged original bodies, then execute a query-only plan, source critique/reread and final answer. The common first pass is a lower-stage diagnostic. Shared stages, permitted caps and evidence do not verify equal provider tokens or compute; model identity/settings and provider request counts were unavailable.

Fresh 12 queries were newly authored from two unused archived sources and all 78 retained messages (50 + 28), with six supported and six bounded corpus-unsupported queries. The separate known eight-query regression set deliberately selects three prior partial answers, three prior complete answers, one confusable and one absent case from four older sources and all 95 retained messages. All messages retained in each archived source row were used; the archives are partial relative to the platform history. Six sources and 173 messages are not 20 independent source episodes. Source selection is privileged and fixed; this is not a retrieval evaluation.

### Fresh 12 queries

| Condition | Correct supported / 6 | Correct abstention / 6 | Partial | Missed | Wrong / unsupported |
| --- | ---: | ---: | ---: | ---: | ---: |
| Shared first answer (diagnostic) | 6 | 6 | 0 | 0 | 0 |
| Ordinary reread | 6 | 6 | 0 | 0 | 0 |
| Structured working state | 6 | 6 | 0 | 0 | 0 |

Ordinary reread → structured working state: 0 corrected to a complete correct answer or correct abstention; 0 regressed from those outcomes. Full paired transition tables and support partitions are in the dated study and JSON.
### Known 8 queries · selected regressions

| Condition | Correct supported / 6 | Correct abstention / 2 | Partial | Missed | Wrong / unsupported |
| --- | ---: | ---: | ---: | ---: | ---: |
| Shared first answer (diagnostic) | 3 | 2 | 3 | 0 | 0 |
| Ordinary reread | 3 | 2 | 3 | 0 | 0 |
| Structured working state | 3 | 2 | 3 | 0 | 0 |

Ordinary reread → structured working state: 0 corrected to a complete correct answer or correct abstention; 0 regressed from those outcomes. Full paired transition tables and support partitions are in the dated study and JSON.

Actual AI roles produced plans, critiques, answers and independent grades; Python verified bindings, quotes, freezes, caps and counts. There are 140 actual per-item production records (40 plans, 20 common first answers, 40 critiques, 40 finals), emitted in 12 producer contexts, not 140 provider requests. Every critique finished before any final answer. All 60 answers were frozen before one blind primary-assessment context. Actual payloads are counted in canonical JSON with Unicode retained, sorted keys and compact separators; serialization formatting is standardized while original string text is unchanged. These counts are not raw indented output-file lengths or provider tokens. Character counts, cap violations and role counts are separate from semantic outcomes. A budget overrun alone is not a semantic error; invalid source grounding prevents a complete source-bound answer.

The final controller version ran its full 27-test unit suite. The separate 70 procedure checks comprise 57 on the retained predecessor and 13 timestamp-input cases on the final version; the intervening controller change was timestamp validation only. These are engineering and procedure checks, not memory-accuracy measurements.

Reader inputs retained unchanged body text and allowlisted role/text/order/time plus opaque IDs, with trace/case UUID/path metadata stripped. Bodies may identify sources; this is not full anonymity. Meaning roles received no parent-task history and were instruction-separated on a shared host. Retrieval improvements, SHIORI speed, graph effects, real-action feedback learning, full Wake, Emotion, natural daily recall, brain reproduction and AGI were not verified. Prediction → actual action/result → next choice → retained history is **proposed, not executed**. Public data contains allowlisted counts, enums and audit digests, not originals, queries, source IDs or private experiment code. All five older studies, their data and four overview scroll stories retain their original bytes.
<!-- WORKING_MEMORY_STUDY_END -->

<!-- ACTION_FEEDBACK_STUDY_START -->
## Prospective action feedback — 2026-10-27

[日本語](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-27-action-feedback/) / [English](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-27-action-feedback/en.html)

The primary comparison is **raw execution feedback → the same feedback plus an actual AI review**. Prior plan only is a separate diagnostic. Six practice tasks (three supported, three unavailable) precede six new objectives (three + three) and three exact positive practice repeats per arm. All 33 actual actions are retained. The new objectives use the same three current complete public files, not unseen files. All arms can recompute previous actions.

Actual AI roles author objectives and typed expectations, choose DSL paths/calculations/abstention, predict validation and write the post-outcome judgment review. Code executes the chosen get/sum/sub/div operations against real public files, writes actual JSON artifacts and mechanically compares types and values with the frozen expected artifact. All 27 later actions are frozen before any later outcomes are returned. This is a numerical contract, not a semantic-memory or psychological-learning grade.

| Arm | New supported / 3 | New unavailable / 3 | Exact positive repeats / 3 |
| --- | ---: | ---: | ---: |
| Prior plan only | 3 | 3 | 3 |
| Raw execution feedback | 3 | 3 | 3 |
| Same feedback + AI review | 3 | 3 | 3 |

Across the same nine later tasks, feedback → feedback + review corrected 0 validator outcomes and regressed 0. New objectives and exact repeats remain separate in the full phase-stratified and paired tables. Execution failures, schema errors, predictions and all 33 item records are reported independently. A character-cap overrun alone does not make an artifact value incorrect.

The six external AI-review entries contain 6 confirmations, 0 revisions and 0 deferred judgments. The review is fresh-context external input, not continuous identity or model-parameter learning. Every action and the review share a 6,000-canonical-character cap. Actual input-packet length, raw output length and per-item canonical JSON characters are distinct measurements; input lengths differ and equal provider compute is unverified. Model identity, settings, provider request counts and token compute remain null.

Task order in every arm is T01, R01, T02, T03, R02, T04, T05, R03, T06. Fixed arm dispatch is raw feedback, feedback + review, then prior plan only; there is no counterbalancing. Roles share one host with instruction-limited access. Before actions, draft one was rejected for measurement-presupposing unavailable instructions; only P02/P04 conditional wording changed and gold bytes stayed identical. All 38 expected numeric fields were checked. Practice errors are not forced; if practice succeeds, error-correction learning remains untested. Three schema sources and six new task objectives do not support population accuracy, general superiority, natural memory, brain/AGI/consciousness, SHIORI speed, full Wake or Emotion claims.

[Public replay instructions](https://yuu-honda.github.io/lux-spiria-results/experiments/action-feedback-2026-10-27/README.md) / [Replay ZIP](https://yuu-honda.github.io/lux-spiria-results/downloads/action-feedback-2026-10-27.zip). The workbench publishes public sources, engineered objectives, expected artifacts, saved AI actions, results and DSL code for deterministic replay. Saved-action replay is not fresh AI regeneration. All six earlier dated studies/data and four overview stories/assets retain their original bytes and publication boundaries.
<!-- ACTION_FEEDBACK_STUDY_END -->

<!-- CONDITIONAL_REVISION_STUDY_START -->
## Controlled conditional compatibility — 2026-10-27

[日本語](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-27-conditional-revision/) / [English](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-27-conditional-revision/en.html)

The same three known public sources were deliberately moved under `payload` in an `artifact-container.v2` wrapper. Parsed original types/values and original raw bytes were preserved. Saved operations were replayed, an actual AI chose compatible new reads, and the original method remained applicable to legacy files. This is an engineered surface-schema change, not a natural outage, belief revision, spontaneous concept learning or brain reproduction.

| Condition | Accepted | Execution errors | Written artifacts |
| --- | ---: | ---: | ---: |
| Saved action · legacy replay | 3/3 | 0 | 3 |
| Saved action · wrapped replay | 0/3 | 3 | 0 |
| Actual AI compatibility repair | 3/3 | 0 | 3 |
| Same raw observations | 6/6 | 0 | 6 |
| Same observations + conditional review | 6/6 | 0 | 6 |

The 21 execution items comprise six saved replays, three new AI repairs and 12 later actions. Saved predictions belong to an earlier v1 context and are excluded from current prediction scores in both diagnostic replays. Current repair choice and post-outcome review reuse the same fresh context over two turns; the two later arms are fresh contexts. The primary comparison is identical raw observations versus those same observations plus conditional review, not feedback versus no feedback. All 12 later actions are frozen before feedback.

The later six items per arm are three new objectives in two formats, not six independent objectives. Raw → review corrected 0 items and regressed 0. Actual review classifications are 0 conditional_update, 3 confirmation and 0 deferred. Repairing saved external operations is distinct from revising one's own mistaken judgment; actual confirmation labels are not recoded as updates.

Actors receive shared actual schema observations and handles, not full current JSON. Observations retain keys/array order and condition-id strings, replace other scalars by type markers, and explicitly omit per_query/provenance. The contract explains formats and instructs legacy preservation, so appropriate conditional branching is not spontaneous discovery. Task order and dispatch are fixed; provider/time effects and equal compute are unverified. Review grounding and retained legacy scope are independently assessed. Canonical input/output characters, actual errors and all retained items remain distinct from model learning or psychological accuracy.

[Public replay instructions](https://yuu-honda.github.io/lux-spiria-results/experiments/conditional-revision-2026-10-27/README.md) / [Replay ZIP](https://yuu-honda.github.io/lux-spiria-results/downloads/conditional-revision-2026-10-27.zip). Replay executes saved operations without regenerating fresh AI decisions. All seven earlier dated studies/data/replay and four overview stories/assets retain their bytes and publication boundaries.
<!-- CONDITIONAL_REVISION_STUDY_END -->

<!-- EXPERIENCE_RETENTION_STUDY_START -->
## Own experience-record use — immediate phase, 2026-10-28

[日本語](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-28-experience-retention/) / [English](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-28-experience-retention/en.html)

An actual AI chose six own initial operations on three known public numeric source families, first original then deliberately wrapped under `payload`. Only failed initials permitted at most one actual repair. The same fresh training context authored and froze three experience entries. Actual labels: 3 conditional_update, 0 confirmation, 0 deferred; 5627/6000 canonical characters. Own errors or update labels were never guaranteed.

The primary comparison is availability of the whole frozen experience record versus no record, rather than review isolated from raw experience. Every arm/item uses a fresh context with the same current task, opaque source handle/family/raw hash and optional real schema inspection. No current schema or format answer is pre-supplied. Common probe instructions give no direct legacy-preservation instruction. The training-record template does request legacy_scope (applicability of earlier conditions); the AI chooses its contents. Three held-out objectives × two formats give six items per arm, not six independent objectives. All 12 policies freeze before any inspection output and all 12 actions before execution feedback. One action and at most one inspection per probe; no probe repairs or feedback updates.

| Arm / immediate | Accepted | Additional inspections | Inspection raw bytes | Returned projection chars |
| --- | ---: | ---: | ---: | ---: |
| No experience record | 6/6 | 6 | 477221 | 168282 |
| Same frozen experience record | 6/6 | 5 | 401142 | 90822 |

No record → record: paired corrected 0, regressed 0. The predeclared efficient-use criterion requires equal accepted counts, fewer actual additional schema inspections and no added execution errors, invalid actions or abstentions. Inspection raw bytes/projection characters concern additional structural reads only. Both arms' executor also reads the assigned source when computing each artifact, so zero inspections does not mean zero total source I/O. Latency, token, compute and spend savings are unmeasured; actual input lengths differ and provider metadata remains null.

**Delayed ≥24-hour phase: uncollected, no results.** Actual memory freeze: 2026-10-27T16:12:30.470580Z; not before 2026-10-28T16:12:30.470580Z (86400 seconds). Further tasks/gold are frozen but only commitment hashes are public. Scheduling is not execution. A later real trial will append a separate dated page/data/root, preserving this phase-one at-publication pending state. Fresh contexts rereading the same external record tests persistence and portability, not psychological retention, continuous identity, weight learning, native Wake, SHIORI mechanism/speed, brains or a forgetting curve.

[Public replay](https://yuu-honda.github.io/lux-spiria-results/experiments/experience-retention-2026-10-28/README.md) / [Replay ZIP](https://yuu-honda.github.io/lux-spiria-results/downloads/experience-retention-2026-10-28.zip). Saved-action replay does not regenerate fresh AI choices and excludes future tasks/gold. This is the third public-data workbench exception to the earlier six private-conversation studies; all eight earlier study/data/replay/download bytes and four overview stories remain unchanged.
<!-- EXPERIENCE_RETENTION_STUDY_END -->

<!-- TOOL_OBSERVATION_LOOP_STUDY_START -->
## Typed tool-observation integration pilot — 2026-10-28

[日本語](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-28-tool-observation-loop/) / [English](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-28-tool-observation-loop/en.html)

Actual subprocess observations and separate AI judgments were connected through isolated native LRE capture/review and native SHIORI cued recall. The pilot records 27 worker operations: 27 exit zero and 0 nonzero. Process exit is not semantic success, memory growth, or answer adequacy. The semantic index source set has 1 tool observations and 1 AI judgments about 1 independent tool events; a receipt and its interpretation of the same event are not two experiences.

| Context | First operation | Exit | Tool source returned | Judgment returned | Earlier retained |
| --- | ---: | ---: | --- | --- | --- |
| C01 | O013 lre_read | 0 | True | True | True |
| C02 | O018 lre_read | 0 | True | True | True |
| C03 | O025 lre_read | 0 | True | True | True |

These are three bounded functional context checks, with an engineered change and legacy return, not an accuracy-benefit or psychological-retention trial. Continuations choose from a disclosed finite vocabulary of eight reviewed cue labels without source mappings, bodies or IDs; this does not demonstrate unconstrained language comprehension. Exact evidence return, native read-state equality, graph support paths, hops-zero and convergence-off diagnostics remain separate outcomes.

The changed copy saved a new condition-bound judgment in native LRE, but that new judgment was neither indexed nor subsequently recalled. Recurrent learning is not established.

Synthetic engineering rounds remain separate: round 01, 14 tests / 93 recorded workers; round 02, 15 tests / 102 workers. Initial initialize used revision 1. The reviewed revision 2 correction added original-input return before semantic indexing/continuation, without discarding or restarting the pilot. A pre-index diagnostic had a prospective plan but lacked a separate pre-call cue-span/review artifact and was not a scored continuation. The continuation choices use hash-bound pre-call span/review records; universal protocol compliance is not claimed.

No human/private conversation content was fetched or used. Tool input/stdout/stderr and AI judgment bodies, private vendor code, native state/databases, feature/cue/trace bodies, actor IDs and local paths are excluded. Provider/model metadata remains unverified and null. Earlier nine studies, including the experience-retention page's immutable pending delayed endpoint, and four overview animations retain their bytes. This pilot makes no full Wake, speed, biological brain, AGI, consciousness or psychological-identity claim.

[Saved-evidence verifier](https://yuu-honda.github.io/lux-spiria-results/experiments/tool-observation-loop-2026-10-28/README.md) / [ZIP](https://yuu-honda.github.io/lux-spiria-results/downloads/tool-observation-loop-2026-10-28.zip). This verifies disclosed hashes, schema and arithmetic only. It cannot reconstruct undisclosed native operations or independently prove exported claims; it is not a complete native replay or fresh AI regeneration. Hashes are local integrity identifiers, not external signatures or hardware attestation.
<!-- TOOL_OBSERVATION_LOOP_STUDY_END -->

<!-- EXPERIENCE_RETENTION_DELAYED_STUDY_START -->
## Same frozen experience record — collected delayed trial, 2026-10-29

[日本語](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-29-experience-retention-delayed/) / [English](https://yuu-honda.github.io/lux-spiria-results/studies/2026-10-29-experience-retention-delayed/en.html)

Three further objectives frozen before training × two formats give six items per arm, not six independent objectives or experiences. Twelve fresh arm/item contexts received the same unchanged 5627-character external record or no record. Both arms received the same current evidence and optional inspection opportunity. All twelve policies froze before inspection outputs; all twelve actions froze before execution outcomes. One action and at most one inspection per item; no probe repairs or feedback-driven record updates.

| Delayed arm | Format | Accepted | Optional inspections | Inspection bytes | Projection chars |
| --- | --- | ---: | ---: | ---: | ---: |
| no_experience | all | 6/6 | 6 | 477221 | 168282 |
| no_experience | original | 3/3 | 3 | 291696 | 84045 |
| no_experience | changed | 3/3 | 3 | 185525 | 84237 |
| experience_record | all | 6/6 | 6 | 477221 | 168282 |
| experience_record | original | 3/3 | 3 | 291696 | 84045 |
| experience_record | changed | 3/3 | 3 | 185525 | 84237 |

Paired outcomes: corrected 0, regressed 0, both correct 6, both wrong 0. The predeclared equal-acceptance/fewer-inspections/no-added-errors criterion was not met; no accuracy or optional-inspection benefit is established. Optional-inspection bytes and projection characters are not total source I/O: both arms' executor reads the assigned source for every actual artifact. Speed, token, compute and spending savings are unmeasured.

Actual first/last initial authoring authorization elapsed: 119050.481339–119190.942745 seconds after memory freeze, later than the 86400-second minimum, not exactly 24 hours. Memory freeze UTC: 2026-10-27T16:12:30.470580Z; preparation UTC: 2026-10-29T01:16:01.524373Z. Native item execution starts elapsed: 119642.809303–119644.124489 seconds. Initial/final authoring clocks are actual pre-call authorization receipts, not exposed provider sampling timestamps. Inspection and native execution clocks are recorded separately in the JSON and dated pages; direct submission has no second authoring call.

The three stage-record local modification times use original state-file local filesystem mtimes (`stage_freeze_clock_basis=local_filesystem_mtime`). All three raw policy/inspection/action phase-entry authorization guards are separately recorded; phase-entry is not completion and may follow the last output. The clock-projection audit digest binds this reporting projection. These are not instrumented exact completion timestamps. Local metadata is not a provider timestamp, external signature or attestation; original trial records and times are unchanged.

The immediate and delayed blocks use different objectives as well as different times. Differences between them do not identify a time-only retention effect or forgetting. Fresh contexts rereading an external record test persistence/portability, not one subject's psychological retention, continuous identity, weight learning, natural conversation memory or a forgetting curve. Provider/model/settings/token/compute metadata is unverified and null; roles use read allowlists on a shared host, not OS isolation. No private native LRE, SHIORI mechanism/speed, native Wake, Emotion, biological brain, AGI or consciousness claim is made.

The training review template explicitly requested `legacy_scope`; this is not unprompted conceptual learning.

The 17 synthetic transport-preparation checks are engineering evidence, separate from twelve actual delayed items. The 2026-10-28 immediate data/page retains its immutable at-publication pending state. This dated study/data/replay appends actual collected outcomes without changing any of the ten earlier studies, downloads or four overview animations.

[Saved-action replay](https://yuu-honda.github.io/lux-spiria-results/experiments/experience-retention-delayed-2026-10-29/README.md) / [External ZIP](https://yuu-honda.github.io/lux-spiria-results/downloads/experience-retention-delayed-2026-10-29.zip). Exact public numeric sources, frozen record, saved policies/actions/gold and the unchanged executor support mechanical replay. This does not regenerate fresh AI judgment or repeat delayed actor collection. Only the newly collected delayed tasks/gold are included; private actor envelopes, receipts and local runtime paths are excluded.
<!-- EXPERIENCE_RETENTION_DELAYED_STUDY_END -->

## Public and private scope

Public: study-specific method descriptions, target-hit aggregates, opaque per-query outcomes, verification flags and retained-bundle identifiers. The first study additionally reports MRR@5 and local timing; later studies report distinct positive, absent and confusable outcomes and pre-search abstentions. The retrieval-hypothesis and event-compatibility studies separately report wrong-scene returns on positive queries. The event-compatibility study includes native route coverage and separate fresh/known ablation outcomes without scene IDs. The answer-adoption study separately reports answer outcomes, item-level failure flags, answer reuse and four opaque source clusters. Query labels are local to each study.

Private: original conversations, question and evidence text, native source IDs, feature vocabulary, SQLite, experiment code and detailed execution artifacts. Public files permit aggregate recalculation, **not independent source auditing or engine reruns**. Reproduction reported here was internally verified with the same private frozen inputs. It is not external peer review, natural-conversation accuracy, a full LRE Wake/Emotion experiment, or evidence of personality continuity.

No private repository credentials, source files or runtime fetches are required by this website.

<!-- ACTION_FEEDBACK_PUBLIC_SCOPE_START -->
The preceding private-source restriction applies to the six earlier archived-conversation studies. The action-feedback public-data workbench is an explicit exception: its already-public files, engineered tasks, expected values, saved AI actions, actual artifacts and DSL code are available for deterministic saved-action replay. This does not provide fresh AI regeneration or change earlier private-source publication boundaries.
<!-- ACTION_FEEDBACK_PUBLIC_SCOPE_END -->

## Build and verify the website

Python 3 standard library only:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_pages.py
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -B -m http.server 8769 --bind 127.0.0.1
```

Optional `data/experience-retention-2026-10-28.json` activates the ninth JA/EN immediate study after exact schema/count/role/clock validation and matching original-source, replay manifest/README and external ZIP hashes. Missing export produces no new publication or placeholder results; invalid data/replay refuses writes. Only latest panels/listings, README and sitemap change alongside the new dated pair. Eight earlier dated studies/data/replay/downloads and four overview stories/assets remain unchanged. The delayed phase remains uncollected in this immutable immediate publication.

`PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_experience_retention.py` rebuilds only its dated pair after the same checks. Public replay executes saved choices without fresh AI generation. GitHub Pages serves `main` at the repository root.

<!-- TOOL_OBSERVATION_LOOP_BUILD_START -->
### Tenth-study activation and saved-evidence verification

To activate the tenth study from an independently audited export (Python 3 standard library only):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_pages.py --tool-observation-loop /absolute/path/to/reports/public-export-v1.json
```

The same flag is accepted by `tools/build_tool_observation_loop.py`. Absent export produces no new study or placeholder; invalid data refuses writes. The public bundle contains only the exact allowlisted export, verifier, README and uppercase MANIFEST.json. Its external ZIP is deterministic. It recalculates disclosed evidence metadata, not private native execution. All nine earlier studies/data/replays/downloads, the separate delayed study and four overview animations remain unchanged. GitHub Pages serves `main` at the repository root.

Optional JavaScript regression check with Node.js:

```sh
node tests/test_scroll_runtime.js
```
<!-- TOOL_OBSERVATION_LOOP_BUILD_END -->

<!-- EXPERIENCE_RETENTION_DELAYED_BUILD_START -->
### Eleventh-study activation: actual delayed saved-action results

Existing study/build instructions above remain applicable. To activate the independently audited delayed export and separately audited replay:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_pages.py --experience-retention-delayed /absolute/path/to/reports/public-export-v1.json --experience-retention-delayed-replay /absolute/path/to/reports/public-replay --experience-retention-delayed-zip /absolute/path/to/reports/public-replay.zip
```

The same flags are accepted by `tools/build_experience_retention_delayed.py`. Missing export produces no new publication or placeholder results. Invalid schema/counts/clocks, original source changes, MANIFEST case/hash/inventory changes or an external ZIP mismatch refuse publication writes. Repeat builds use the installed audited data/replay by default. The immediate phase-one page and its pending state are never rewritten as collected.
<!-- EXPERIENCE_RETENTION_DELAYED_BUILD_END -->

## Preservation

Study v1 pages and data retain their date and scope. Corrections must be documented in CHANGELOG; new studies receive separate dated paths. Historical LUX SPIRIA README, releases and research records remain in the original project.

## Rights

The existing project [LSP-1.0 license](LICENSE) is retained unchanged. Copyright attribution is legal metadata; public study narratives use **user / AI**.
