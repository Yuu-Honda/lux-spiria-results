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

## Public and private scope

Public: frozen method description, target-hit aggregates, MRR@5, Q01–Q24 ranks/counts/tie flags, local timing, verification flags and retained-bundle identifiers.

Private: original conversations, question and evidence text, native source IDs, feature vocabulary, SQLite, experiment code and detailed execution artifacts. Public files permit aggregate recalculation, **not independent source auditing or engine reruns**. Reproduction reported here was internally verified with the same private frozen inputs. It is not external peer review, natural-conversation accuracy, a full LRE Wake/Emotion experiment, or evidence of personality continuity.

No private repository credentials, source files or runtime fetches are required by this website.

## Build and verify the website

Python 3 standard library only:

```sh
python3 tools/build_pages.py
python3 -m unittest discover -s tests -v
python3 -m http.server 8769 --bind 127.0.0.1
```

The builder reads only `data/shiori-pilot-2026-10-13.json`. These commands rebuild and verify the **public website**, not the private SHIORI experiment. Generated Results listings (`results.html` / `results.en.html`) and study pages are committed. The builder leaves the migrated overview and historical pages intact. GitHub Pages serves `main` at the repository root; no dependencies or CI secrets are used.

## Preservation

Study v1 pages and data retain their date and scope. Corrections must be documented in CHANGELOG; new studies receive separate dated paths. Historical LUX SPIRIA README, releases and research records remain in the original project.

## Rights

The existing project [LSP-1.0 license](LICENSE) is retained unchanged. Copyright attribution is legal metadata; public study narratives use **user / AI**.
