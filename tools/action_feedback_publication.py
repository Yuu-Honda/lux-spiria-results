"""Prepare optional seventh-study publication without writes.

Only an audited allowlisted export and matching public replay files activate
publication. An absent export is an identity operation. Invalid data or missing
replay files fail before any output or existing page is touched.
"""
from html import escape
import importlib.util
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('action_feedback_public_builder', ROOT / 'tools/build_action_feedback.py')
study = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(study)
t = study.t
LATEST = re.compile(r'<section class="latest-study"(?=\s).*?</section>', re.S)
CARD = re.compile(r'<article class="study-card" data-study="action-feedback">.*?</article>', re.S)
README_START = '<!-- ACTION_FEEDBACK_STUDY_START -->'
README_END = '<!-- ACTION_FEEDBACK_STUDY_END -->'
SCOPE_START = '<!-- ACTION_FEEDBACK_PUBLIC_SCOPE_START -->'
SCOPE_END = '<!-- ACTION_FEEDBACK_PUBLIC_SCOPE_END -->'


def optional_summary(root=ROOT):
    return study.optional_summary(root)


def _metrics(d, lang, home=False):
    definitions = [('transfer', 'correct_supported', 3, t('新規目的・正しい完了', 'New objectives: correct completion', lang), t('対象あり3課題', 'Three supported tasks', lang)),
                   ('transfer', 'correct_abstention', 3, t('新規目的・正しい棄権', 'New objectives: correct abstention', lang), t('対象なし3課題', 'Three unavailable tasks', lang)),
                   ('repeat', 'correct_supported', 3, t('同じ練習目的の完了', 'Exact practice-repeat completion', lang), t('新規目的と別の3課題', 'Three tasks separate from new objectives', lang))]
    pairs = [(d['arms']['raw_feedback'][group][key], d['arms']['raw_feedback_and_review'][group][key], total, name, denominator)
             for group, key, total, name, denominator in definitions]
    if home:
        return ''.join(f'<div class="latest-study-metric"><dt>{name}<span>{den}</span></dt><dd><span>{before}<small>/{total}</small></span><span class="latest-study-arrow" aria-hidden="true">→</span><span>{after}<small>/{total}</small></span></dd></div>' for before, after, total, name, den in pairs)
    return ''.join(f'<span><strong>{before}/{total} → {after}/{total}</strong>{name}</span>' for before, after, total, name, _ in pairs)


def latest_home(d, lang):
    study.validate_summary(d)
    href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    return f'''<section class="latest-study" aria-labelledby="latest-study-title" data-source="{study.DATA_FILE}">
        <div class="latest-study-copy"><p class="latest-study-kicker">RECORDED STUDY <span aria-hidden="true">/</span> <time datetime="{d['date']}">{d['date']}</time></p>
          <h2 id="latest-study-title">{t('予測し、実行し、<br>次の行動を比べる。', 'Predict. Execute.<br>Compare the next action.', lang)}</h2>
          <p class="latest-study-summary">{t('公開済みの実データ3ファイルで、AIが選んだ処理を実行し、実際にJSON成果物を書きました。同じフィードバックにAIレビューを追加する違いを、新しい目的6件と同じ練習目的3件で分けて比べます。', 'AI-selected operations over three real public data files wrote actual JSON artifacts. Adding an AI review to the same feedback is compared on six new objectives and, separately, three exact practice repeats.', lang)}</p>
          <a class="latest-study-link" href="{href}">{t('結果・限界・公開リプレイを読む', 'Read results, limits and public replay', lang)} <span aria-hidden="true">↗</span></a></div>
        <div class="latest-study-results"><p class="latest-study-order">{t('フィードバックだけ → 同じフィードバック＋AIレビュー', 'Raw feedback → the same feedback + AI review', lang)}</p>
          <dl class="latest-study-metrics">{_metrics(d, lang, True)}</dl>
          <p class="latest-study-boundary">{t('全条件に同じ現在の完全な公開ファイルを渡しました。新しい目的は未見ファイルではなく、機械的な型付き成果物の評価です。入力長は異なり、計算量の一致・自然な記憶・脳・SHIORIの速度は検証していません。', 'All arms received the same current complete public files. New objectives are not unseen files; artifacts are mechanically checked against typed values. Input lengths differ. Equal compute, natural memory, brains and SHIORI speed were not verified.', lang)}</p>
          <a class="latest-study-source" href="{study.DATA_FILE}">{t('全33行と集計 / JSON', 'All 33 rows and aggregates / JSON', lang)}</a></div>
      </section>'''


def integrate_home(html, lang, d):
    if d is None:
        return html
    study.validate_summary(d)
    if len(LATEST.findall(html)) != 1:
        raise ValueError('Exactly one overview latest-study panel is required')
    return LATEST.sub(lambda _: latest_home(d, lang), html, count=1)


def listing_card(d, lang):
    study.validate_summary(d)
    href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    return f'''<article class="study-card" data-study="action-feedback"><span class="study-status">STUDY / PROSPECTIVE ACTION FEEDBACK</span><time datetime="{d['date']}">{d['date']}</time><h3><a href="{href}">{t('実行した結果から、次の行動を比べる。', 'Compare the next action after real execution.', lang)} ↗</a></h3><p>{t('3つの公開ファイルで、実際の予測・DSL行動・JSON書き込み・検証・AIレビューを記録。練習6件の後、各条件は同じ新規目的6件と同じ練習目的3件を実行し、全33行動を保持します。', 'Three public files supplied actual predictions, DSL actions, JSON writes, validation and AI review. After six practice actions, every arm executes the same six new objectives and three exact practice repeats. All 33 actions are retained.', lang)}</p><p>{t('以下はフィードバックだけ → 同じフィードバック＋AIレビュー。以前の計画だけは別の診断条件です。', 'Below: raw feedback → the same feedback + AI review. Prior plan only is a separate diagnostic arm.', lang)}</p><div class="study-stats">{_metrics(d, lang)}</div><p>{t('全条件に同じ現在の完全なデータを渡す設計課題です。新規目的は未見ファイルではありません。型付き期待値との機械的一致で採点し、自然な記憶・一般的な学習能力・脳・SHIORIの速度は主張しません。', 'These are engineered tasks with the same current complete data in all arms. New objectives are not unseen files. Exact typed-value validation does not establish natural memory, general learning, brains or SHIORI speed.', lang)}</p><p><a href="{study.REPLAY}README.md">{t('公開リプレイの手順', 'Public replay instructions', lang)} ↗</a> · <a href="{study.ZIP_FILE}" download>ZIP ↓</a></p></article>'''


def integrate_listing(html, lang, d):
    if d is None:
        return html
    study.validate_summary(d)
    html = CARD.sub('', html)
    hero = f'''<div class="status-strip"><span>{t('実行済み結果を公開 · 範囲を絞った設計試験', 'Recorded execution · bounded engineered pilot', lang)}</span><small>UPDATED / {d['date']}</small></div>
<div class="hero-metrics"><div class="metric"><strong>07</strong><span>{t('公開研究', 'Published studies', lang)}</span><small>2026-10-13 / {d['date']}</small></div><div class="metric"><strong>6</strong><span>{t('最新研究の新しい目的', 'New objectives in latest study', lang)}</span><small>{t('同じ3公開ファイル上の課題', 'Tasks over the same three public files', lang)}</small></div><div class="metric"><strong>33</strong><span>{t('実際に実行した行動', 'Actual executed actions', lang)}</span><small>{t('練習6＋3条件各9', 'Six practice + nine in each of three arms', lang)}</small></div></div>'''
    html, count = re.subn(r'<div class="status-strip">.*?</div>\n<div class="hero-metrics">.*?</div></div>', lambda _: hero, html, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Listing latest-metadata anchor is missing')
    anchor = re.search(r'<section class="section" id="studies"[^>]*><div class="section-heading">.*?</div>', html, re.S)
    if anchor is None:
        raise ValueError('Listing study-card anchor is missing')
    html = html[:anchor.end()] + listing_card(d, lang) + html[anchor.end():]
    old_private = t('会話原文・質問本文・出典ID・特徴語・SQLite・実験用コードと詳細ログは非公開で保持します。公開集計は再計算できますが、第三者が公開ファイルだけで原文照合やエンジン再実行を行うことはできません。', 'Original conversations, question text, source IDs, feature terms, SQLite, experiment code and detailed logs remain private. Public aggregates can be recalculated; source auditing and engine reruns cannot be performed from public files alone.', lang)
    new_private = t('以前の6つの会話研究では、原文・質問・出典ID・特徴語・SQLite・実験コードを非公開で保持し、公開集計だけでは原文照合やエンジン再実行はできません。今回の公開データ作業台は例外で、公開ファイル・課題・期待値・保存済み行動・成果物・コードをリプレイ一式で確認できます。新しいAI生成の再現ではありません。', 'The six earlier conversation studies retain originals, questions, source IDs, feature terms, SQLite and experiment code privately; public aggregates alone do not permit source auditing or engine reruns. The present public-data workbench is an exception: public files, tasks, expectations, saved actions, artifacts and code are available in its replay bundle. This is not fresh AI regeneration.', lang)
    html = html.replace(old_private, new_private)
    old_scope = t('最新研究は新しく生成して固定した実際のAI回答を評価します。新規12問と選択した既知8問は別枠です。自然な日常想起、人格連続性、脳の再現、AGI、Emotion、LREの全Wakeは検証していません。', 'The latest study assesses newly generated and frozen actual AI answers. Fresh 12 queries and eight selected known regressions remain separate. Natural daily recall, personality continuity, brain reproduction, AGI, Emotion and full LRE Wake remain unverified.', lang)
    new_scope = t('最新研究は、公開済みデータ上の実際の数値処理と型付き成果物を評価します。自然な記憶、同一主体の連続性、パラメータ学習、脳、AGI、Emotion、全Wake、SHIORIの速度は検証していません。', 'The latest study evaluates actual numerical actions and typed artifacts over previously public data. Natural memory, continuous actor identity, parameter learning, brains, AGI, Emotion, full Wake and SHIORI speed remain unverified.', lang)
    return html.replace(old_scope, new_scope).replace('RESULT RECORD / 2026-10-24', 'RESULT RECORD / 2026-10-27')


def integrate_readme(text, d):
    if d is None:
        return text
    study.validate_summary(d)
    lines = ['| Arm | New supported / 3 | New unavailable / 3 | Exact positive repeats / 3 |', '| --- | ---: | ---: | ---: |']
    for arm in study.ARMS:
        transfer, repeat = d['arms'][arm]['transfer'], d['arms'][arm]['repeat']
        lines.append(f'| {study.label(arm, "en")} | {transfer["correct_supported"]} | {transfer["correct_abstention"]} | {repeat["correct_supported"]} |')
    pair = d['paired']['feedback_to_review']['all']
    memory = d['memory']
    section = f'''{README_START}
## Prospective action feedback — {d['date']}

[日本語]({study.BASE + study.STUDY}) / [English]({study.BASE + study.STUDY}en.html)

The primary comparison is **raw execution feedback → the same feedback plus an actual AI review**. Prior plan only is a separate diagnostic. Six practice tasks (three supported, three unavailable) precede six new objectives (three + three) and three exact positive practice repeats per arm. All 33 actual actions are retained. The new objectives use the same three current complete public files, not unseen files. All arms can recompute previous actions.

Actual AI roles author objectives and typed expectations, choose DSL paths/calculations/abstention, predict validation and write the post-outcome judgment review. Code executes the chosen get/sum/sub/div operations against real public files, writes actual JSON artifacts and mechanically compares types and values with the frozen expected artifact. All 27 later actions are frozen before any later outcomes are returned. This is a numerical contract, not a semantic-memory or psychological-learning grade.

{chr(10).join(lines)}

Across the same nine later tasks, feedback → feedback + review corrected {pair['corrected']} validator outcomes and regressed {pair['regressed']}. New objectives and exact repeats remain separate in the full phase-stratified and paired tables. Execution failures, schema errors, predictions and all 33 item records are reported independently. A character-cap overrun alone does not make an artifact value incorrect.

The six external AI-review entries contain {memory['confirmations']} confirmations, {memory['revisions']} revisions and {memory['deferred']} deferred judgments. The review is fresh-context external input, not continuous identity or model-parameter learning. Every action and the review share a 6,000-canonical-character cap. Actual input-packet length, raw output length and per-item canonical JSON characters are distinct measurements; input lengths differ and equal provider compute is unverified. Model identity, settings, provider request counts and token compute remain null.

Task order in every arm is T01, R01, T02, T03, R02, T04, T05, R03, T06. Fixed arm dispatch is raw feedback, feedback + review, then prior plan only; there is no counterbalancing. Roles share one host with instruction-limited access. Before actions, draft one was rejected for measurement-presupposing unavailable instructions; only P02/P04 conditional wording changed and gold bytes stayed identical. All 38 expected numeric fields were checked. Practice errors are not forced; if practice succeeds, error-correction learning remains untested. Three schema sources and six new task objectives do not support population accuracy, general superiority, natural memory, brain/AGI/consciousness, SHIORI speed, full Wake or Emotion claims.

[Public replay instructions]({study.BASE + study.REPLAY}README.md) / [Replay ZIP]({study.BASE + study.ZIP_FILE}). The workbench publishes public sources, engineered objectives, expected artifacts, saved AI actions, results and DSL code for deterministic replay. Saved-action replay is not fresh AI regeneration. All six earlier dated studies/data and four overview stories/assets retain their original bytes and publication boundaries.
{README_END}

'''
    if README_START in text or README_END in text:
        text, count = re.subn(re.escape(README_START) + '.*?' + re.escape(README_END) + r'\n\n', lambda _: section, text, count=1, flags=re.S)
        if count != 1:
            raise ValueError('README action-feedback block markers are inconsistent')
    else:
        anchor = '## Public and private scope\n'
        if text.count(anchor) != 1:
            raise ValueError('README public-scope anchor is missing')
        text = text.replace(anchor, section + anchor, 1)
    scope = f'''{SCOPE_START}
The preceding private-source restriction applies to the six earlier archived-conversation studies. The action-feedback public-data workbench is an explicit exception: its already-public files, engineered tasks, expected values, saved AI actions, actual artifacts and DSL code are available for deterministic saved-action replay. This does not provide fresh AI regeneration or change earlier private-source publication boundaries.
{SCOPE_END}

'''
    if SCOPE_START in text or SCOPE_END in text:
        text, count = re.subn(re.escape(SCOPE_START) + '.*?' + re.escape(SCOPE_END) + r'\n\n', lambda _: scope, text, count=1, flags=re.S)
        if count != 1:
            raise ValueError('README public-scope exception markers are inconsistent')
    else:
        text = text.replace('## Build and verify the website\n', scope + '## Build and verify the website\n', 1)
    build = f'''## Build and verify the website

Python 3 standard library only:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_pages.py
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -B -m http.server 8769 --bind 127.0.0.1
```

The main builder reads only audited public summaries under `data/`. Optional `{study.DATA_FILE}` activates the seventh dated JA/EN study only after validation and matching public source/README/ZIP hashes. Missing data leaves the six older studies current without placeholder outcomes. Invalid data or unavailable replay files fail before publication writes. It updates results listings, only the overview latest-study panel, this README and sitemap. Six older dated studies/data and all four overview scroll stories/assets remain unchanged.

`PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_action_feedback.py` rebuilds only its dated pair after the same checks. The public replay bundle has separate instructions. Saved-action replay is distinct from rebuilding this website and from fresh AI generation. GitHub Pages serves `main` at the repository root.

'''
    text, count = re.subn(r'## Build and verify the website\n.*?(?=## Preservation\n)', lambda _: build, text, count=1, flags=re.S)
    if count != 1:
        raise ValueError('README build-instructions anchor is missing')
    return text


def integrate_sitemap(text, d):
    if d is None:
        return text
    study.validate_summary(d)
    if text.count('</urlset>') != 1:
        raise ValueError('Sitemap closing anchor is missing')
    for url in (study.BASE + study.STUDY, study.BASE + study.STUDY + 'en.html'):
        if f'<loc>{url}</loc>' not in text:
            text = text.replace('</urlset>', f'  <url><loc>{escape(url)}</loc></url>\n</urlset>', 1)
    return text


def prepare_updates(root=ROOT, summary=None):
    d = optional_summary(root) if summary is None else study.validate_summary(summary)
    if d is None:
        return {}
    study.require_public_inputs(root, d)
    updates = {study.STUDY + 'index.html': study.render('ja', d),
               study.STUDY + 'en.html': study.render('en', d)}
    for name, lang in [('index.html', 'ja'), ('index.en.html', 'en')]:
        updates[name] = integrate_home((root / name).read_text(encoding='utf-8'), lang, d)
    updates['README.md'] = integrate_readme((root / 'README.md').read_text(encoding='utf-8'), d)
    updates['sitemap.xml'] = integrate_sitemap((root / 'sitemap.xml').read_text(encoding='utf-8'), d)
    return updates
