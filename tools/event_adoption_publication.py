"""Prepare publication updates only from the audited event-adoption export.

All functions return strings/plans without writing. No file is imported from a
private research location. An absent optional export returns no publication plan;
an existing invalid export fails closed rather than falling back to old results.
The main builder applies a complete plan only after all rendering succeeds.
"""
from html import escape
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('adoption_public_builder', ROOT / 'tools/build_event_adoption.py')
study = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(study)
t = study.t
LATEST_SECTION = re.compile(r'<section class="latest-study"(?=\s).*?</section>', re.S)
README_START = '<!-- EVENT_ADOPTION_STUDY_START -->'
README_END = '<!-- EVENT_ADOPTION_STUDY_END -->'


def optional_summary(root=ROOT):
    path = root / study.DATA_FILE
    if not path.is_file():
        return None
    return study.validate_summary(json.loads(path.read_text(encoding='utf-8')))


def _comparison(d):
    rows = {row['id']: row for row in d['conditions']}
    return rows['strict_source_gate:normal'], rows['strict_and_event_review:normal']


def _metrics(d, lang, *, home=False):
    before, after = _comparison(d)
    definitions = [
        ('correct_supported', 16, t('根拠あり・正答', 'Correct supported answers', lang), t('根拠あり16問', '16 supported queries', lang)),
        ('correct_abstention', 16, t('正しい棄権', 'Correct abstentions', lang), t('コーパス内に対象がない16問', '16 corpus-unsupported queries', lang)),
        ('wrong_or_unsupported', 32, t('誤り・根拠なしの回答', 'Wrong or unsupported answers', lang), t('固定した全32問', 'All 32 frozen queries', lang)),
    ]
    if home:
        return ''.join(f'<div class="latest-study-metric"><dt>{name}<span>{denominator}</span></dt><dd><span>{before[key]}<small>/{total}</small></span><span class="latest-study-arrow" aria-hidden="true">→</span><span>{after[key]}<small>/{total}</small></span></dd></div>' for key, total, name, denominator in definitions)
    return ''.join(f'<span><strong>{before[key]}/{total} → {after[key]}/{total}</strong>{name}</span>' for key, total, name, _ in definitions)


def listing_card(d, lang):
    study.validate_summary(d)
    href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    title = t('取り出した原文を、回答へ正しく使えたか。', 'Was retrieved source evidence used correctly in answers?', lang)
    description = t('実会話4件・全95メッセージ・固定32問。検索4方式の通常実行と網・合流の無効化、特権的な指定原文の比較を、保存済みの実際のAI回答で評価しました。', 'Four archived conversations, all 95 retained messages and 32 frozen queries. Saved actual AI answers compare four retrieval arms, graph/convergence ablations and a privileged designated-source diagnostic.', lang)
    comparison = t('以下は通常実行の厳格な原文ゲート → 原文＋出来事レビュー。全13条件と失敗の内訳は研究ページで報告します。', 'Below: normal strict source gate → source + event review. The study reports all 13 conditions and failure diagnostics.', lang)
    limits = t('場面の取得と回答の正しさは別の指標です。同じ質問・原文組の回答を条件間で再利用します。4つの出典クラスターを32の独立した会話として扱いません。', 'Scene selection and answer correctness are separate endpoints. Conditions reuse saved answers for identical query/source pairs. Four source clusters are not treated as 32 independent conversations.', lang)
    return f'<article class="study-card"><span class="study-status">STUDY / EVENT ANSWER ADOPTION</span><time datetime="{d["date"]}">{d["date"]}</time><h3><a href="{href}">{title} ↗</a></h3><p>{description}</p><p>{comparison}</p><div class="study-stats">{_metrics(d, lang)}</div><p>{limits}</p></article>'


def integrate_listing(html, lang, d):
    """Preserve the four previous cards; update only listing-level latest facts."""
    if d is None:
        return html
    study.validate_summary(d)
    sample = d['sample']
    hero = f'''<div class="status-strip"><span>{t('実行済み結果を公開 · 小規模な選択標本', 'Recorded execution · small selected sample', lang)}</span><small>UPDATED / {d['date']}</small></div>
<div class="hero-metrics"><div class="metric"><strong>05</strong><span>{t('公開研究', 'Published studies', lang)}</span><small>2026-10-13 / {d['date']}</small></div><div class="metric"><strong>{sample['source_sessions']}</strong><span>{t('最新試験の実会話', 'Real sessions in latest study', lang)}</span><small>{t(f'全{sample["whole_retained_messages"]}原文メッセージ', f'All {sample["whole_retained_messages"]} retained source messages', lang)}</small></div><div class="metric"><strong>{sample['queries']}</strong><span>{t('最新試験の質問', 'Queries in latest study', lang)}</span><small>{t('根拠あり16・コーパス内に対象なし16', '16 supported · 16 corpus-unsupported', lang)}</small></div></div>'''
    html, count = re.subn(r'<div class="status-strip">.*?</div>\n<div class="hero-metrics">.*?</div></div>', lambda _: hero, html, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Listing latest-metadata anchor is missing')
    anchor = re.search(r'<section class="section" id="studies"[^>]*><div class="section-heading">.*?</div>', html, re.S)
    if anchor is None:
        raise ValueError('Listing study-card anchor is missing')
    html = html[:anchor.end()] + listing_card(d, lang) + html[anchor.end():]
    html = html.replace('RESULT RECORD / 2026-10-22', f'RESULT RECORD / {d["date"]}')
    old_scope = t('LREの全Wake、Emotionの効果、応答生成、日常会話での自然な想起、人格連続性は今回の評価対象に含みません。', 'Full LRE Wake, Emotion effects, response generation, natural everyday recall and personality continuity were not evaluated.', lang)
    new_scope = t('最新研究は保存済みの実際のAI回答を評価します。新しいAI生成による再現、自然な日常想起、人格連続性、脳の再現、AGI、Emotion、LREの全Wakeは検証していません。', 'The latest study assesses saved actual AI answers. Fresh AI regeneration, natural daily recall, personality continuity, brain reproduction, AGI, Emotion and full LRE Wake remain unverified.', lang)
    return html.replace(old_scope, new_scope)


def latest_home(d, lang):
    study.validate_summary(d)
    href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    title = t('取り出した原文を、<br>回答へ正しく使えたか。', 'Was retrieved source evidence<br>used correctly in answers?', lang)
    description = t('実会話4件・全95メッセージから固定した新規32問。場面を取得できたかと、AIが原文を正しく回答へ使えたかを分けて記録しました。全4方式・3種類の実行と、特権的な指定原文の比較を公開します。', '32 frozen new queries from four archived conversations and all 95 retained messages. Scene retrieval and correct use of source evidence in AI answers are recorded separately. All four arms, three variants and the privileged designated-source diagnostic are reported.', lang)
    comparison = t('厳格な原文ゲート（strict_source_gate） → 原文＋出来事レビュー（strict_and_event_review）／通常実行', 'Strict source gate (strict_source_gate) → source + event review (strict_and_event_review) / normal execution', lang)
    boundary = t('指標の母数は別々です。同じ質問・原文組の保存済み回答を条件間で再利用しました。出典は4クラスターで、32の独立した会話ではありません。閲覧中にAIや検索エンジンは動きません。', 'Metrics have separate denominators. Conditions reuse the same saved answer for each query/source pair. Sources form four clusters, not 32 independent conversations. Browsing runs neither an AI nor the retrieval engine.', lang)
    return f'''<section class="latest-study" aria-labelledby="latest-study-title" data-source="{study.DATA_FILE}">
        <div class="latest-study-copy">
          <p class="latest-study-kicker">RECORDED STUDY <span aria-hidden="true">/</span> <time datetime="{d['date']}">{d['date']}</time></p>
          <h2 id="latest-study-title">{title}</h2>
          <p class="latest-study-summary">{description}</p>
          <a class="latest-study-link" href="{href}">{t('結果と、検証の範囲を読む', 'Read the results and evaluation limits', lang)} <span aria-hidden="true">↗</span></a>
        </div>
        <div class="latest-study-results">
          <p class="latest-study-order">{comparison}</p>
          <dl class="latest-study-metrics">{_metrics(d, lang, home=True)}</dl>
          <p class="latest-study-boundary">{boundary}</p>
          <a class="latest-study-source" href="{study.DATA_FILE}">{t('集計データ / JSON', 'Aggregate data / JSON', lang)}</a>
        </div>
      </section>'''


def integrate_home(html, lang, d):
    if d is None:
        return html
    if len(LATEST_SECTION.findall(html)) != 1:
        raise ValueError('Exactly one home latest-study section is required')
    return LATEST_SECTION.sub(lambda _: latest_home(d, lang), html, count=1)


def integrate_readme(text, d):
    if d is None:
        return text
    study.validate_summary(d)
    rows = {row['id']: row for row in d['conditions']}
    lines = ['| Normal retrieval condition | Correct supported / 16 | Correct abstention / 16 | Partial supported | Missed answer | Wrong / unsupported |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for arm in study.ARMS:
        row = rows[f'{arm}:normal']
        values = [row[key] for key in study.OUTCOMES]
        lines.append(f'| {study.label(f"{arm}:normal", "en")} | ' + ' | '.join(str(value) for value in values) + ' |')
    r, c = d['answer_reuse'], d['calls']
    section = f'''{README_START}
## Event answer adoption — {d['date']}

[日本語]({study.BASE + study.STUDY}) / [English]({study.BASE + study.STUDY}en.html)

Four archived conversations supplied all 95 retained messages and 32 frozen new queries: four literal, 12 paraphrase, eight confusable and eight absent. Answer correctness is separate from native source scene@1. The five exclusive answer outcomes sum to 32 per condition; supported answers and correct abstentions each use their own denominator of 16. Four source clusters are not 32 independent conversation episodes.

{chr(10).join(lines)}

All four retrieval arms report normal, `hops=0` and `convergence=false` variants. The additional designated-source ceiling supplies the author-associated source as a privileged diagnostic; it is not deployable retrieval, a mathematical upper bound or a guarantee of maximum accuracy. Full pages and JSON retain all 13 conditions, overlapping failure diagnostics, support-available denominators, query-kind strata and opaque C01–C04 source-cluster strata. Native retrieval diagnostics cover only the 12 retrieval conditions.

The actual answer pool contains {r['unique_query_source_answer_pool_items']} unique query/source answer items. Conditions use {r['unique_answer_items_used_in_condition_lookups']} unique items in {r['condition_answer_lookups']} lookups, including {r['reused_condition_answer_lookups']} reused lookups. These are saved actual AI answers, not fresh generations or independent repeated answer samples. The record separately reports {c['successful_reader_contexts']} successful reader contexts, {c['failed_collection_attempts']} retained failed collection attempts, actual distinct calls or unavailable call metadata, one primary assessor call and separate final-audit calls.

Source-only AI indexing and review retained 344 literal witness occurrences, 284 unique native feature entries and 230 canonical concepts. These are different units, not automatic learning. Roles were separated by instructions on the same host. Pre-score failures and the single repaired event review are disclosed in the dated pages. Public aggregates permit consistency checks, not source auditing or engine reruns. Fresh AI regeneration, natural daily recall, brain reproduction, AGI, Emotion and full Wake remain unverified. All four earlier study pairs and their data keep their original bytes.
{README_END}

'''
    if README_START in text or README_END in text:
        pattern = re.escape(README_START) + '.*?' + re.escape(README_END) + r'\n\n'
        text, count = re.subn(pattern, lambda _: section, text, count=1, flags=re.S)
        if count != 1:
            raise ValueError('README adoption block markers are inconsistent')
    else:
        anchor = '## Public and private scope\n'
        if text.count(anchor) != 1:
            raise ValueError('README public-scope anchor is missing')
        text = text.replace(anchor, section + anchor, 1)
    text = text.replace('The latest study also includes native route coverage and separate fresh/known ablation outcomes without scene IDs.', 'The event-compatibility study includes native route coverage and separate fresh/known ablation outcomes without scene IDs. The answer-adoption study separately reports answer outcomes, item-level failure flags, answer reuse and four opaque source clusters.')
    build = f'''## Build and verify the website

Python 3 standard library only:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_pages.py
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -B -m http.server 8769 --bind 127.0.0.1
```

The main builder reads only the five public summaries under `data/`, including `{study.DATA_FILE}`. It validates the optional event-adoption export before any publication update. When the export is absent, the four earlier studies remain the current public listing; no new study or placeholder numbers are generated. When present and audited, it adds the fifth dated JA/EN pair, updates the results listings and only the overview's latest-study panel, and updates this README and sitemap. Earlier dated studies, data and all four overview scroll illustrations remain unchanged.

`PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_event_adoption.py` rebuilds only the new dated pair and refuses missing or inconsistent data. The earlier standalone builders remain available. These commands rebuild and verify the **public website**, not the private SHIORI experiment. GitHub Pages serves `main` at the repository root; no dependencies or CI secrets are used.

'''
    text, count = re.subn(r'## Build and verify the website\n.*?(?=## Preservation\n)', lambda _: build, text, count=1, flags=re.S)
    if count != 1:
        raise ValueError('README build-instructions anchor is missing')
    return text


def integrate_sitemap(text, d):
    if d is None:
        return text
    study.validate_summary(d)
    urls = [study.BASE + study.STUDY, study.BASE + study.STUDY + 'en.html']
    if text.count('</urlset>') != 1:
        raise ValueError('Sitemap closing anchor is missing')
    for url in urls:
        if f'<loc>{url}</loc>' not in text:
            text = text.replace('</urlset>', f'  <url><loc>{escape(url)}</loc></url>\n</urlset>', 1)
    return text


def prepare_updates(root=ROOT, summary=None):
    """Return all optional writes; absence means an empty plan and no writes."""
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
