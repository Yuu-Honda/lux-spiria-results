# Experience-record reuse / 外部経験記録の再利用 — 2026-10-28

実際のAIが選んだ方針・観察要求・アクション・訓練後の経験記録と、実際のJSON成果物を保存した限定的なファイル操作実験です。訓練は元形式3件＋変更形式3件がすべて合格し、自身の失敗0件・修復0件でした。自身の誤りからの修正を示す事例はありません。

即時試行は各armで3目的×2形式の6件です。no_experience は6/6合格・観察6回、experience_record は6/6合格・観察5回でした。精度向上は観測していません。省略された観察はP02（A02、X01の元形式）の1回だけです。任意観察で読み込んだ元ソースは477,221→401,142 bytes、返したcanonical投影は168,282→90,822文字でした。全アクションのexecutorは両armとも実ソースを読みます。この差は任意観察の費用であり、総I/O・処理速度・token・compute節約の測定ではありません。

経験armだけが同じ凍結済み外部記録全体を受け取る比較です。個別のレビュー効果やLRE/SHIORIのアーキテクチャを分離した実験ではありません。訓練レビュー様式は明示的に `legacy_scope` を求めており、その保持を自発的な概念学習とは呼びません。3つの目的を形式間・arm間で反復した小標本です。

24時間試行は未収集です。記録凍結は 2026-10-27T16:12:30.470580Z、最短収集時刻は 2026-10-28T16:12:30.470580Z です。遅延task/goldは事前commitmentのhashのみを収録し、本文・遅延結果は含みません。予定や保存は実行ではありません。外部記録の再読は同一モデルの心理的保持・重み学習・生物学的忘却曲線を示しません。native Wake、SHIORI速度、脳・AGIは検証していません。

## Replay saved choices / 保存済み選択の再実行

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B replay.py --out /absolute/path/to/new-external-folder
```

The manifest is `MANIFEST.json`, listing every other bundle file with exact SHA-256 and byte size. The output must be new and outside this folder. The verifier checks the complete manifest before loading the pinned engine/apparatus, regenerates only the 17 saved requested inspections, then replays the 18 saved actions with one assigned source alias per action. It compares exact recorded execution errors/statuses, validation, artifact SHA-256, inspection JSON SHA-256, and actual inspection byte/character costs. This replays saved choices; it does not regenerate fresh AI decisions or collect the delayed endpoint.

Training accepted all 6 initial actions (3 original, 3 changed), with no own failures and no repairs. Immediate no_experience accepted 6/6 with 6 inspections; experience_record accepted 6/6 with 5 inspections. There was no accuracy gain. The sole skipped optional inspection was P02, X01 original. Optional raw-source bytes were 477,221 versus 401,142; returned canonical projection characters were 168,282 versus 90,822. Executors still read actual sources for every action in both arms. These are optional-inspection costs, not total I/O, speed, token, compute, or spending measurements.

This compares availability of the whole frozen external experience record. It is not a separate review/architecture ablation. The review template explicitly requested `legacy_scope`; its preservation is not presented as unprompted conceptual learning. Each arm repeats 3 objectives in 2 formats. Instruction-based fresh contexts share a host; provider/configuration effects are unmeasured. Native Wake, SHIORI speed, biological memory, model-weight learning, and AGI are not tested.

The ≥24-hour endpoint remains uncollected. Freeze: 2026-10-27T16:12:30.470580Z; earliest collection: 2026-10-28T16:12:30.470580Z. Only delayed-task/gold commitments are included, never their bodies or fabricated delayed results. Freeze files commit to selected original study-relative files; they are not complete inventories of this publication bundle. `MANIFEST.json` is the publication inventory. Author/reviewer note text, actor runtime IDs, source-path execution records, and raw coordinator packets are excluded. Independent publication auditing is a separate step; this README does not claim its approval.

Synthetic engineering checks are separate from research execution:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest -v test_action_loop test_experience_io test_replay
```

Sources are unchanged previously public numerical exports; provenance is in `input/SOURCE_PROVENANCE.json`. The existing project [LICENSE](https://github.com/Yuu-Honda/lux-spiria-results/blob/main/LICENSE) applies as published; this bundle grants no new unrestricted/MIT license.
