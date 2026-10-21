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

## Public and private scope

Public: study-specific method descriptions, target-hit aggregates, opaque per-query outcomes, verification flags and retained-bundle identifiers. The first study additionally reports MRR@5 and local timing; later studies report distinct positive, absent and confusable outcomes and pre-search abstentions. The retrieval-hypothesis and event-compatibility studies separately report wrong-scene returns on positive queries. The latest study also includes native route coverage and separate fresh/known ablation outcomes without scene IDs. Query labels are local to each study.

Private: original conversations, question and evidence text, native source IDs, feature vocabulary, SQLite, experiment code and detailed execution artifacts. Public files permit aggregate recalculation, **not independent source auditing or engine reruns**. Reproduction reported here was internally verified with the same private frozen inputs. It is not external peer review, natural-conversation accuracy, a full LRE Wake/Emotion experiment, or evidence of personality continuity.

No private repository credentials, source files or runtime fetches are required by this website.

## Build and verify the website

Python 3 standard library only:

```sh
python3 tools/build_pages.py
python3 -m unittest discover -s tests -v
python3 -m http.server 8769 --bind 127.0.0.1
```

The builder reads only four public summaries: `data/shiori-pilot-2026-10-13.json`, `data/shiori-cross-session-2026-10-21.json`, `data/shiori-retrieval-hypotheses-2026-10-21.json` and `data/shiori-event-compatibility-2026-10-22.json`. These commands rebuild and verify the **public website**, not the private SHIORI experiment. Results listings (`results.html` / `results.en.html`) and all four dated JA/EN study pairs are generated. `python3 tools/build_event_compatibility.py` rebuilds only the latest dated pair and refuses to write pages if its audited public data is missing or inconsistent. `python3 tools/build_retrieval_hypotheses.py` remains available for the preceding pair. The builders leave the migrated overview, its scroll illustrations and historical pages intact. GitHub Pages serves `main` at the repository root; no dependencies or CI secrets are used.

## Preservation

Study v1 pages and data retain their date and scope. Corrections must be documented in CHANGELOG; new studies receive separate dated paths. Historical LUX SPIRIA README, releases and research records remain in the original project.

## Rights

The existing project [LSP-1.0 license](LICENSE) is retained unchanged. Copyright attribution is legal metadata; public study narratives use **user / AI**.
