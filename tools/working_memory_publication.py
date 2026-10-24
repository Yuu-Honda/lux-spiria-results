"""Plan publication writes only from the audited working-memory public export.

Absent data returns no plan. Existing invalid data fails before any write.
Historical dated pages/data and the four overview stories are never plan targets.
"""
from html import escape
import importlib.util
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('working_memory_public_builder', ROOT / 'tools/build_working_memory.py')
study = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(study)
t = study.t
LATEST = re.compile(r'<section class="latest-study"(?=\s).*?</section>', re.S)
README_START = '<!-- WORKING_MEMORY_STUDY_START -->'
README_END = '<!-- WORKING_MEMORY_STUDY_END -->'


def optional_summary(root=ROOT):
    return study.optional_summary(root)


def _metrics(d, lang, home=False):
    rows = d['cohorts']['fresh']['conditions']
    before, after = rows['plain_reread']['metrics'], rows['structured_state']['metrics']
    definitions = [('correct_supported', 6, t('根拠あり・正答', 'Correct supported', lang), t('新規・対象あり6問', 'Fresh: six supported queries', lang)),
                   ('correct_abstention', 6, t('正しい棄権', 'Correct abstention', lang), t('新規・コーパス内に対象なし6問', 'Fresh: six corpus-unsupported queries', lang)),
                   ('wrong_or_unsupported', 12, t('誤り・根拠なし', 'Wrong / unsupported', lang), t('新規12問', 'Fresh 12 queries', lang))]
    if home:
        return ''.join(f'<div class="latest-study-metric"><dt>{name}<span>{den}</span></dt><dd><span>{before[key]}<small>/{total}</small></span><span class="latest-study-arrow" aria-hidden="true">→</span><span>{after[key]}<small>/{total}</small></span></dd></div>' for key, total, name, den in definitions)
    return ''.join(f'<span><strong>{before[key]}/{total} → {after[key]}/{total}</strong>{name}</span>' for key, total, name, _ in definitions)


def latest_home(d, lang):
    study.validate_summary(d)
    href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    return f'''<section class="latest-study" aria-labelledby="latest-study-title" data-source="{study.DATA_FILE}">
        <div class="latest-study-copy"><p class="latest-study-kicker">RECORDED STUDY <span aria-hidden="true">/</span> <time datetime="{d['date']}">{d['date']}</time></p>
          <h2 id="latest-study-title">{t('同じ原文を読み直し、<br>作業状態を構造化する。', 'Reread the same source.<br>Structure the working state.', lang)}</h2>
          <p class="latest-study-summary">{t('原文を特権的に固定し、同じ初回回答から通常の読み直しと構造化した作業状態を比較。新規2出典・保存された全78メッセージから作った12問と、選択した既知8問の回帰確認を別々に報告します。保存された各出典行の全発言を使用しましたが、プラットフォームの全履歴を取得したものではありません。', 'With source material fixed by privilege, ordinary rereading and structured working state started from the same first answer. Fresh 12-query results from two unused sources and all 78 retained messages are separate from eight selected known regressions. All messages retained in each archived source row were used; the archives are partial relative to the platform history.', lang)}</p>
          <a class="latest-study-link" href="{href}">{t('結果と、比較の範囲を読む', 'Read results and comparison limits', lang)} <span aria-hidden="true">↗</span></a></div>
        <div class="latest-study-results"><p class="latest-study-order">{t('新規12問 ／ 通常の読み直し → 構造化した作業状態', 'Fresh 12 queries / ordinary reread → structured working state', lang)}</p>
          <dl class="latest-study-metrics">{_metrics(d, lang, True)}</dl>
          <p class="latest-study-boundary">{t('主比較は同じ段階・許可上限・証拠を用います。provider token数や計算量の一致は未検証。初回回答は段階の少ない診断で、検索・速度・網・全Wake・Emotionの効果は測っていません。', 'The primary arms share stages, permitted caps and evidence; equal provider tokens or compute are unverified. First answers are a lower-stage diagnostic. Retrieval, speed, graph, full Wake and Emotion effects were not measured.', lang)}</p>
          <a class="latest-study-source" href="{study.DATA_FILE}">{t('集計データ / JSON', 'Aggregate data / JSON', lang)}</a></div>
      </section>'''


def integrate_home(html, lang, d):
    if d is None:
        return html
    study.validate_summary(d)
    if len(LATEST.findall(html)) != 1:
        raise ValueError('Exactly one home latest-study section is required')
    return LATEST.sub(lambda _: latest_home(d, lang), html, count=1)


def listing_card(d, lang):
    study.validate_summary(d)
    href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    return f'''<article class="study-card" data-study="working-memory-source-fixed"><span class="study-status">STUDY / SOURCE-FIXED WORKING MEMORY</span><time datetime="{d['date']}">{d['date']}</time><h3><a href="{href}">{t('同じ原文を読み直し、作業状態を構造化する。', 'Reread the same source. Structure the working state.', lang)} ↗</a></h3><p>{t('同じ初回回答から、通常の読み直しと構造化した作業状態を比較。新規12問（対象あり6・対象なし6）を、意図して選んだ既知8問（対象あり6・対象なし2）と分けて報告します。', 'Ordinary rereading and structured working state start from the same first answer. Fresh 12 queries (six supported, six unsupported) are separate from eight deliberately selected known queries (six supported, two unsupported).', lang)}</p><p>{t('以下は新規12問の通常の読み直し → 構造化した作業状態。初回回答を含む全3条件、対応する遷移、既知の回帰確認、payloadのcanonical JSON文字数・回答文字数と上限超過は研究ページに記録します。', 'Below: ordinary reread → structured working state on fresh 12 queries. The study retains all three conditions including first answers, paired transitions, known regressions, canonical JSON payload counts, answer characters and cap overruns.', lang)}</p><div class="study-stats">{_metrics(d, lang)}</div><p>{t('原文選択は特権的な固定です。6出典・保存された全173メッセージ。保存された各出典行の全発言を使用しましたが、プラットフォームの全履歴を取得したものではありません。20問を20の独立した出典として扱いません。同じ許可上限でも、token数や計算量の一致は未検証です。検索改善・速度・網・実際の行動結果による学習・全Wake・Emotionの効果は測っていません。', 'Source selection is fixed by privilege: six sources and all 173 retained messages. All messages retained in each archived source row were used; the archives are partial relative to the platform history. The 20 queries are not 20 independent sources. Shared permitted caps do not verify equal tokens or compute. Retrieval improvements, speed, graph effects, learning from actual action outcomes, full Wake and Emotion effects were not measured.', lang)}</p></article>'''


def integrate_listing(html, lang, d):
    if d is None:
        return html
    study.validate_summary(d)
    # Replacing the dated card also makes direct integration idempotent.
    old = re.compile(r'<article class="study-card" data-study="working-memory-source-fixed">.*?</article>', re.S)
    html = old.sub('', html)
    hero = f'''<div class="status-strip"><span>{t('実行済み結果を公開 · 小規模な選択標本', 'Recorded execution · small selected sample', lang)}</span><small>UPDATED / {d['date']}</small></div>
<div class="hero-metrics"><div class="metric"><strong>06</strong><span>{t('公開研究', 'Published studies', lang)}</span><small>2026-10-13 / {d['date']}</small></div><div class="metric"><strong>12</strong><span>{t('最新研究の新規質問', 'Fresh queries in latest study', lang)}</span><small>{t('未使用2出典・全78メッセージ', 'Two unused sources · all 78 messages', lang)}</small></div><div class="metric"><strong>8</strong><span>{t('別枠の既知回帰確認', 'Separate known regressions', lang)}</span><small>{t('選択した8問・4出典95メッセージ', 'Eight selected queries · four sources, 95 messages', lang)}</small></div></div>'''
    html, count = re.subn(r'<div class="status-strip">.*?</div>\n<div class="hero-metrics">.*?</div></div>', lambda _: hero, html, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Listing latest-metadata anchor is missing')
    anchor = re.search(r'<section class="section" id="studies"[^>]*><div class="section-heading">.*?</div>', html, re.S)
    if anchor is None:
        raise ValueError('Listing study-card anchor is missing')
    html = html[:anchor.end()] + listing_card(d, lang) + html[anchor.end():]
    old_scope = t('最新研究は保存済みの実際のAI回答を評価します。新しいAI生成による再現、自然な日常想起、人格連続性、脳の再現、AGI、Emotion、LREの全Wakeは検証していません。', 'The latest study assesses saved actual AI answers. Fresh AI regeneration, natural daily recall, personality continuity, brain reproduction, AGI, Emotion and full LRE Wake remain unverified.', lang)
    new_scope = t('最新研究は新しく生成して固定した実際のAI回答を評価します。新規12問と選択した既知8問は別枠です。自然な日常想起、人格連続性、脳の再現、AGI、Emotion、LREの全Wakeは検証していません。', 'The latest study assesses newly generated and frozen actual AI answers. Fresh 12 queries and eight selected known regressions remain separate. Natural daily recall, personality continuity, brain reproduction, AGI, Emotion and full LRE Wake remain unverified.', lang)
    return html.replace(old_scope, new_scope)


def integrate_readme(text, d):
    if d is None:
        return text
    study.validate_summary(d)
    version_note = study.verification_version_note(d['verification'], 'en')
    tables = []
    for cohort in study.COHORTS:
        _, positive, negative = study.COHORTS[cohort]
        rows = d['cohorts'][cohort]['conditions']
        lines = [f'### {study.cohort_label(cohort, "en")}', '', f'| Condition | Correct supported / {positive} | Correct abstention / {negative} | Partial | Missed | Wrong / unsupported |', '| --- | ---: | ---: | ---: | ---: | ---: |']
        for cid in study.CONDITIONS:
            row = rows[cid]['metrics']
            lines.append(f'| {study.label(cid, "en")} | ' + ' | '.join(str(row[key]) for key in study.OUTCOMES) + ' |')
        pair = d['cohorts'][cohort]['paired']['plain_to_structured']
        lines += ['', f'Ordinary reread → structured working state: {pair["corrected"]} corrected to a complete correct answer or correct abstention; {pair["regressed"]} regressed from those outcomes. Full paired transition tables and support partitions are in the dated study and JSON.']
        tables.append('\n'.join(lines))
    section = f'''{README_START}
## Source-fixed working memory — {d['date']}

[日本語]({study.BASE + study.STUDY}) / [English]({study.BASE + study.STUDY}en.html)

The primary comparison is **ordinary reread → structured working state**. Both arms start from the same frozen first answer and unchanged original bodies, then execute a query-only plan, source critique/reread and final answer. The common first pass is a lower-stage diagnostic. Shared stages, permitted caps and evidence do not verify equal provider tokens or compute; model identity/settings and provider request counts were unavailable.

Fresh 12 queries were newly authored from two unused archived sources and all 78 retained messages (50 + 28), with six supported and six bounded corpus-unsupported queries. The separate known eight-query regression set deliberately selects three prior partial answers, three prior complete answers, one confusable and one absent case from four older sources and all 95 retained messages. All messages retained in each archived source row were used; the archives are partial relative to the platform history. Six sources and 173 messages are not 20 independent source episodes. Source selection is privileged and fixed; this is not a retrieval evaluation.

{chr(10).join(tables)}

Actual AI roles produced plans, critiques, answers and independent grades; Python verified bindings, quotes, freezes, caps and counts. There are 140 actual per-item production records (40 plans, 20 common first answers, 40 critiques, 40 finals), emitted in 12 producer contexts, not 140 provider requests. Every critique finished before any final answer. All 60 answers were frozen before one blind primary-assessment context. Actual payloads are counted in canonical JSON with Unicode retained, sorted keys and compact separators; serialization formatting is standardized while original string text is unchanged. These counts are not raw indented output-file lengths or provider tokens. Character counts, cap violations and role counts are separate from semantic outcomes. A budget overrun alone is not a semantic error; invalid source grounding prevents a complete source-bound answer.

{version_note}

Reader inputs retained unchanged body text and allowlisted role/text/order/time plus opaque IDs, with trace/case UUID/path metadata stripped. Bodies may identify sources; this is not full anonymity. Meaning roles received no parent-task history and were instruction-separated on a shared host. Retrieval improvements, SHIORI speed, graph effects, real-action feedback learning, full Wake, Emotion, natural daily recall, brain reproduction and AGI were not verified. Prediction → actual action/result → next choice → retained history is **proposed, not executed**. Public data contains allowlisted counts, enums and audit digests, not originals, queries, source IDs or private experiment code. All five older studies, their data and four overview scroll stories retain their original bytes.
{README_END}

'''
    if README_START in text or README_END in text:
        text, count = re.subn(re.escape(README_START) + '.*?' + re.escape(README_END) + r'\n\n', lambda _: section, text, count=1, flags=re.S)
        if count != 1:
            raise ValueError('README working-memory block markers are inconsistent')
    else:
        anchor = '## Public and private scope\n'
        if text.count(anchor) != 1:
            raise ValueError('README public-scope anchor is missing')
        text = text.replace(anchor, section + anchor, 1)
    build = f'''## Build and verify the website

Python 3 standard library only:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_pages.py
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -B -m http.server 8769 --bind 127.0.0.1
```

The main builder reads only public summaries under `data/`. It validates the optional `{study.DATA_FILE}` before publication writes. If this export is absent, the five older studies remain current and the working-memory integration produces no changes or placeholder outcomes. An existing invalid export fails closed. An audited actual export adds the sixth dated JA/EN study, updates result listings, only the overview latest-study panel, this README and the sitemap. Five older dated studies and their data, and all four overview scroll stories/assets, remain unchanged.

`PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_working_memory.py` rebuilds only its dated pages and refuses missing or invalid data before writes. These commands rebuild the public website, not the private experiment. Earlier standalone builders remain available. GitHub Pages serves `main` at the repository root.

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
    """Construct the entire optional publication plan without touching files."""
    d = optional_summary(root) if summary is None else study.validate_summary(summary)
    if d is None:
        return {}
    updates = {study.STUDY + 'index.html': study.render('ja', d),
               study.STUDY + 'en.html': study.render('en', d)}
    for name, lang in [('index.html', 'ja'), ('index.en.html', 'en')]:
        updates[name] = integrate_home((root / name).read_text(encoding='utf-8'), lang, d)
    updates['README.md'] = integrate_readme((root / 'README.md').read_text(encoding='utf-8'), d)
    updates['sitemap.xml'] = integrate_sitemap((root / 'sitemap.xml').read_text(encoding='utf-8'), d)
    return updates
