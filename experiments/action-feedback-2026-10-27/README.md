# 実アクションと結果レビュー：保存済みアクションの再実行 / Actual actions and feedback: saved-action replay

このパッケージは、過去に公開済みの実在する3つのResults JSONを入力に、AIが選んだ抽出・計算アクションを実行し、実際にJSON作成物を書いた小規模な工学課題の記録です。新しいブラウザ操作や検索エンジン実行、過去研究の再実験は行っていません。公開ファイルに記載された測定値を読み、指定された計算とファイル作成を行いました。

This is a small engineered artifact-production task over three real, previously published Results JSON files. AI-selected extraction and arithmetic actions wrote actual JSON artifacts. The new task did not run a browser, retrieval engine, or the earlier studies again; it processed measurements already present in the public files.

## 観測結果 / Observed result

練習は6/6件が検証を通過しました。その後の3条件はすべて9/9件を通過し、各条件で新しい転移課題6件と練習の再提示3件が通過しました。実行失敗・形式エラー・文字数上限違反はいずれも0件でした。結果レビューは6件すべてが確認で、判断の修正は0件でした。

Practice passed 6/6. Each later condition passed 9/9, comprising six new transfer tasks and three repeated practice tasks. There were no execution failures, schema errors, or character-cap violations. All six review entries confirmed the previous judgment; none revised it.

| 条件 / Condition | 受理 / Accepted | 内容 / Available history |
| --- | ---: | --- |
| `practice` | 6/6 | 結果を見る前のアクション / Actions selected before outcomes |
| `prior_plan_only` | 9/9 | 過去の課題・アクション・予測 / Prior tasks, actions, predictions |
| `raw_feedback` | 9/9 | 同じ履歴と実際の結果 / Same history plus actual feedback |
| `raw_feedback_and_review` | 9/9 | 同じ結果とAIによるレビュー / Same feedback plus AI-authored review |

全条件が満点に達しており、追加レビューによる学習・性能改善は観測されませんでした。練習で失敗がなかったため、誤りから判断を修正する学習は評価できていません。レビューを作成し、次の別コンテキストへ渡し、実作成物を検証する経路は動きましたが、持続的学習や脳の成立を示す結果ではありません。

All conditions reached the ceiling. No performance improvement from added review was observed, and successful practice leaves learning through error correction untested. The record demonstrates an external feedback/review path and actual artifact production. It does not establish persistent learning or a brain-like system.

## 実行と条件の範囲 / Execution and condition boundaries

課題と期待作成物はアクターの実行前に独立したAIによる作成・確認を経て固定しました。練習、結果レビュー、後続3条件の担当AIは、それぞれ過去の会話を継承しない新しいコンテキスト（`fork_turns="none"`）でした。AIは操作・参照パス・公開原本に要求された値がない場合の判断・予測・理由を選択しました。Pythonは固定された公開入力を読み、`get`・`sum`・`sub`・`div`を実行し、作成物を保存して独立した期待値と機械的に比較しました。自然言語の意味や「学んだか」をPythonが採点したものではありません。

Tasks and expected artifacts were fixed after independent AI authoring/review before actor execution. Practice, post-outcome review, and each later arm used fresh contexts without inherited conversation (`fork_turns="none"`). AI chose operations, source paths, source-unavailable decisions, predictions, and rationales. Python read the frozen public inputs, executed the four declared operations, wrote artifacts, and mechanically compared them with independently authored expected artifacts. It did not invent semantic grades or decide whether learning occurred.

3条件は同じ公開入力・現在の課題・操作言語・1回のアクション機会・各項目6000正規化JSON文字の上限を共有しました。入力履歴の長さは異なり、計算量が等しいとは言えません。共通の後続課題順序と条件の投入順序は固定で、順序の交差配置ではありません。`protocol/ADDENDUM_01.json`は、v1の曖昧な順序表現を実行前に明確化しています。すべての後続アクションは後続結果を開示する前に固定し、意味を修正する再試行はありません。

The arms shared the same public sources, current tasks, operation language, one action opportunity, and a 6000-canonical-character per-item cap. History lengths differed; equal compute is not established. Task order and dispatch order were fixed, not counterbalanced. The prospective addendum clarifies the ambiguous order wording in v1. All later actions were fixed before later outcomes were disclosed, with no semantic retry.

転移は同じ3ファイルに対する新しい課題であり、未見の情報源への転移ではありません。再提示は同一実行内の回帰確認で、遅延記憶や自律的想起の試験ではありません。各条件1コンテキストの記述的試行で、統計的な一般化や因果効果は示しません。役割は同じホスト上で指示により読み取り範囲を分けたもので、OSで隔離していません。モデル名・設定・プロバイダー要求数・トークン計算量は未取得です。

Transfer means new objectives over the same three files, not unseen-source transfer. Repeats are same-run regression checks, not delayed retention or autonomous retrieval. This descriptive pilot has one context per arm and supports no statistical generalization or causal effect claim. Roles shared a host with instructed read boundaries, not OS isolation. Model identity, settings, provider request counts, and token compute were unavailable.

## 内容 / Contents

- `sources/D01.json`–`D03.json`: 公開ファイル全体の変更なしのコピー / Unchanged full public source files.
- `source_map.json`, `source_provenance.json`: 相対パスのみの参照と公開元・SHA256 / Relative source references, public origin and SHA256.
- `ACTION_CONTRACT.txt`, `tasks.json`, `gold_practice.json`, `gold_later.json`: 固定された契約、最終15課題、練習6件・後続9件の期待作成物 / Frozen contract, final 15 tasks, expected artifacts for six practice and nine later tasks.
- `actions/*.json`: AIが実際に出力した4配列の元バイト列 / Exact raw AI bytes for the four action arrays.
- `memory/review.json`: 実結果を見たAIレビュー6件の元バイト列 / Exact raw bytes of the six post-outcome review entries.
- `recorded/{condition}/{task}.json`: 実際に作成された33ファイルの元バイト列 / Exact bytes of the 33 actual recorded artifacts.
- `protocol/`: 実行前のプロトコルv1と追補 / Exact prospective protocol v1 and addendum.
- `history/tasks_draft_01.json`, `tasks_draft_02.json`: 実行前の文言履歴。実行に使ったのは`tasks.json` / Pre-action wording history; execution used `tasks.json`.
- `results.json`: 実結果から集計した件数・文字数・限界 / Counts, character costs, and limits computed from actual outcomes.
- `action_loop.py`, `test_action_loop.py`: 実行に使った固定コードと合成入力による20件の工学テスト / Frozen actual engine and 20 synthetic engineering tests.
- `replay.py`, `manifest.json`: バンドル検証と保存済みアクションの再実行 / Bundle verification and saved-action replay.
- `LICENSE`: 公開プロジェクトに既存のライセンスを変更せず同梱 / The existing public project license, unchanged.

元のマシンの絶対パス、非公開会話、役割の非公開レポート、生の実行ログ、保護対象のベースラインは含めていません。公開元は`source_provenance.json`に示すGitHubコミットに固定されています。公開元ファイルに含まれる以前の研究の説明・結果は、その以前の研究に属します。

The bundle excludes original machine paths, private conversations, private role reports, raw execution logs, and protection baselines. Source provenance is pinned to the GitHub commit in `source_provenance.json`. Descriptions and findings inside the source files belong to those earlier studies.

## 再実行 / Replay

Python標準ライブラリだけを使います。実行環境ではPython 3.14.8を確認しました。次の出力先は存在しない新しいディレクトリを指定し、バンドルの外に置いてください。バンドル内にファイルを追加するとマニフェスト検証で拒否されます。

Only the Python standard library is required. The observed local runtime was Python 3.14.8. Choose a new, nonexistent output directory outside the bundle. Added bundle files are rejected by manifest verification.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B replay.py --out ../action-feedback-replay-output
```

`replay.py`は、最初に`manifest.json`自身を除く全ファイルの一覧・サイズ・SHA256を検証します。その後、元の`action_loop.run_batch`を4回呼び出し、固定されたアクションから新しいファイルを実際に作成します。33ファイルすべてのバイト列SHA256を`recorded/`と比較し、期待値による検証結果も確認します。結果は標準出力と出力先の`replay_verification.json`に保存します。すべて一致したときだけ終了コード0となり、不一致や改変、出力先の再利用では非0となります。マニフェスト自身のSHA256は配布元が示す値と別途比較してください。マニフェストは完全性の確認であり、単独で配布元を証明するものではありません。

The script first verifies the complete file set, sizes, and SHA256 values for every bundle file except the manifest itself. It then calls the original `action_loop.run_batch` four times to write new files from the frozen actions, compares all 33 artifact-byte hashes with `recorded/`, and checks mechanical validator acceptance. It saves the result to stdout and `replay_verification.json` in the output directory. Exit code 0 requires every comparison to pass; mismatch, bundle modification, and output reuse return nonzero. Independently compare the manifest's own SHA256 with the distributor's published value; the manifest alone establishes integrity, not publisher identity.

これは保存済みAIアクションの再実行です。新しいAIに判断を再生成させる処理、LLM API呼び出し、モデル学習、実ブラウザ・検索エンジンの操作、SHIORIバイナリ速度、完全なLRE Wake、Emotion効果、native ChatGPT連携、脳・AGI・意識の実証は含みません。再実行が成功しても、意味の独立監査や科学的な有効性の証明にはなりません。

Replay executes saved AI actions. It does not regenerate decisions with fresh AI, call an LLM API, train a model, operate a browser or retrieval engine, measure SHIORI binary speed, run complete LRE Wake, establish an Emotion effect or native ChatGPT integration, or demonstrate a brain, AGI, or consciousness. Successful replay is not an independent semantic audit or proof of scientific benefit.

工学テストだけを実行する場合 / To run engineering tests only:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest -v
```

テストは合成入力を一時的に作り、削除します。再実行のローカル実行記録には、実行したマシン上の入力パスとUTC時刻が含まれます。それらは配布済みの実作成物とは別の新規記録です。

Tests create and remove synthetic temporary inputs. Local replay execution logs contain runtime input paths and UTC timestamps; they are newly generated local records, separate from the distributed recorded artifacts.
