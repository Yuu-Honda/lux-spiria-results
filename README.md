# LUX SPIRIA Results

Public, versioned research results for LUX SPIRIA.

- [日本語](https://yuu-honda.github.io/lux-spiria-results/)
- [English](https://yuu-honda.github.io/lux-spiria-results/en.html)
- [Project overview and historical records](https://yuu-honda.github.io/lux-spiria/)

This repository contains the website, its builder and **allowlisted aggregates**. It is separate from the historical `lux-spiria` repository and the private research bundle. The site displays recorded results, not a live SHIORI engine or generated demonstration.

## First study — 2026-10-13

A selected real-dialogue session (42 messages), 24 researcher-authored queries (22 target-bearing and two controls), and four SHIORI retrieval conditions. Default preparation yielded zero semantic features; source-only AI-assisted review supplied 203 features before query authoring. All eight paraphrase queries yielded no cues or candidates. The pages show all four conditions, opaque per-query outcomes, timing, failures and verification boundaries.

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

The builder reads only `data/shiori-pilot-2026-10-13.json`. These commands rebuild and verify the **public website**, not the private SHIORI experiment. Generated Japanese and English pages are committed. GitHub Pages serves `main` at the repository root; no dependencies or CI secrets are used.

## Preservation

Study v1 pages and data retain their date and scope. Corrections must be documented in CHANGELOG; new studies receive separate dated paths. Historical LUX SPIRIA README, releases and research records remain in the original project.

## Rights

The existing project [LSP-1.0 license](LICENSE) is retained unchanged. Copyright attribution is legal metadata; public study narratives use **user / AI**.
