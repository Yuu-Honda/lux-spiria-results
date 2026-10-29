"""Optional eleventh-study plan; prior dated publications remain immutable."""
from html import escape
import importlib.util
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('delayed_public_builder', ROOT / 'tools/build_experience_retention_delayed.py')
study = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(study)
t = study.t
LATEST = re.compile(r'<section class="latest-study"(?=\s).*?</section>', re.S)
CARD = re.compile(r'<article class="study-card" data-study="experience-retention-delayed">.*?</article>', re.S)
README_START = '<!-- EXPERIENCE_RETENTION_DELAYED_STUDY_START -->'
README_END = '<!-- EXPERIENCE_RETENTION_DELAYED_STUDY_END -->'
BUILD_START = '<!-- EXPERIENCE_RETENTION_DELAYED_BUILD_START -->'
BUILD_END = '<!-- EXPERIENCE_RETENTION_DELAYED_BUILD_END -->'


def optional_summary(root=ROOT, source=None):
    return study.optional_summary(root, source)


def metrics(d, lang, home=False):
    rows = []
    for fmt in study.FORMATS:
        a, b = (d['counts'][arm][fmt]['accepted'] for arm in study.ARMS)
        rows.append((a, b, 3, t('元形式の受理', 'Original-format acceptance', lang) if fmt == 'original' else t('変更形式の受理', 'Changed-format acceptance', lang)))
    a, b = (d['counts'][arm]['all']['inspections'] for arm in study.ARMS)
    rows.append((a, b, 6, t('追加の構造確認', 'Optional schema inspections', lang)))
    if home:
        return ''.join(f'<div class="latest-study-metric"><dt>{label}<span>{t("同じ遅延3目的×2形式", "Same three delayed objectives × two formats", lang)}</span></dt><dd><span>{a}<small>/{total}</small></span><span class="latest-study-arrow" aria-hidden="true">→</span><span>{b}<small>/{total}</small></span></dd></div>' for a, b, total, label in rows)
    return ''.join(f'<span><strong>{a}/{total} → {b}/{total}</strong>{label}</span>' for a, b, total, label in rows)


def latest_home(d, lang):
    study.validate_summary(d); href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    first = study.clock_ranges(d)['initial_authoring'][0] - d['clocks']['memory_freeze']['unix_seconds']
    return f'''<section class="latest-study" aria-labelledby="latest-study-title" data-source="{study.DATA_FILE}"><div class="latest-study-copy"><p class="latest-study-kicker">COLLECTED DELAYED STUDY / <time datetime="2026-10-29">2026-10-29</time></p><h2 id="latest-study-title">{t('同じ凍結記録を、<br>実際の遅延後に使う。', 'Use the same frozen record<br>after an actual delay.', lang)}</h2><p class="latest-study-summary">{t(f'記録凍結から最初の著述許可まで実際に約{study.elapsed_label(first)}。新しい項目コンテキストへ同じ外部記録を渡すかどうかで、3つの別目的×2形式の受理と追加確認を比べました。', f'Actual time from record freeze to first authoring authorization was about {study.elapsed_label(first)}. Fresh item contexts received the same external record or no record for three further objectives in two formats.', lang)}</p><a class="latest-study-link" href="{href}">{t('収集した実結果と時計を読む', 'Read collected outcomes and actual clocks', lang)} ↗</a></div><div class="latest-study-results"><p class="latest-study-order">{t('記録なし → 同じ凍結記録あり', 'No record → same frozen record', lang)}</p><dl class="latest-study-metrics">{metrics(d, lang, True)}</dl><p class="latest-study-boundary">{t('24時間ちょうどではなく、下限86400秒を超えた実試行です。追加確認は総source I/Oではありません。直後とは目的も時間も異なり、時間だけの効果や心理的保持へ広げません。直後公開物は当時の未収集状態を保持します。', 'Actual collection occurred later than the 86400-second minimum, not exactly at 24 hours. Optional inspection is not total source I/O. Different objectives and time prevent a time-only or psychological-retention claim. The immediate publication keeps its original pending state.', lang)}</p><a class="latest-study-source" href="{study.DATA_FILE}">{t('全12項目・費用・実時計 / JSON', 'All twelve items, costs and clocks / JSON', lang)}</a></div></section>'''


def integrate_home(html, lang, d):
    if d is None:
        return html
    study.validate_summary(d)
    if len(LATEST.findall(html)) != 1:
        raise ValueError('Exactly one existing overview latest panel required')
    return LATEST.sub(lambda _: latest_home(d, lang), html, count=1)


def listing_card(d, lang):
    study.validate_summary(d); href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    return f'''<article class="study-card" data-study="experience-retention-delayed"><span class="study-status">STUDY / FROZEN RECORD / DELAYED COLLECTED</span><time datetime="2026-10-29">2026-10-29</time><h3><a href="{href}">{t('同じ経験記録を、実際の遅延後に再利用する。', 'Reuse the same experience record after actual elapsed time.', lang)} ↗</a></h3><p>{t('事前に凍結した別の3目的×2形式を、条件ごとに6項目で実行。12の新しい項目コンテキストが記録なし／同じ5627文字の記録ありを比較し、元形式と変更形式の受理・追加確認・実時計を残します。', 'Three further objectives frozen in advance × two formats produce six items per arm. Twelve fresh item contexts compare no record with the same 5627-character record, retaining original/changed acceptance, optional inspection and actual clocks.', lang)}</p><div class="study-stats">{metrics(d, lang)}</div><p>{t('実際の著述許可・確認・native実行時計を区別します。24時間ちょうどの測定ではなく、心理的保持・重み学習・時間だけの因果効果の証明でもありません。直後ページの未収集状態を変更せず、別の実結果として追加しました。', 'Authoring authorization, inspection and native execution clocks remain distinct. Collection was not exactly at 24 hours and does not establish psychological retention, weight learning or a time-only causal effect. This appends collected outcomes without altering the immediate page’s pending state.', lang)}</p><p><a href="{study.REPLAY}README.md">{t('保存ACTIONリプレイ', 'Saved-action replay', lang)} ↗</a> · <a href="{study.ZIP_FILE}" download>ZIP ↓</a></p></article>'''


def integrate_listing(html, lang, d):
    if d is None:
        return html
    study.validate_summary(d); html = CARD.sub('', html)
    hero = f'''<div class="status-strip"><span>{t('実際の遅延後の試行を収集', 'Actual delayed trial collected', lang)}</span><small>UPDATED / 2026-10-29</small></div>
<div class="hero-metrics"><div class="metric"><strong>11</strong><span>{t('公開研究', 'Published studies', lang)}</span><small>2026-10-13 / 2026-10-29</small></div><div class="metric"><strong>3</strong><span>{t('遅延した別目的', 'Further delayed objectives', lang)}</span><small>{t('各2形式・2条件', 'Two formats and two arms each', lang)}</small></div><div class="metric"><strong>12</strong><span>{t('実際の遅延項目', 'Actual delayed items', lang)}</span><small>{t('著述許可と実行の時計を分離', 'Authorization and execution clocks separate', lang)}</small></div></div>'''
    html, count = re.subn(r'<div class="status-strip">.*?</div>\n<div class="hero-metrics">.*?</div></div>', lambda _: hero, html, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Listing latest metadata anchor missing')
    anchor = re.search(r'<section class="section" id="studies"[^>]*><div class="section-heading">.*?</div>', html, re.S)
    if anchor is None:
        raise ValueError('Listing card anchor missing')
    return html[:anchor.end()] + listing_card(d, lang) + html[anchor.end():]


def _replace_block(text, start, end, block, anchor):
    if start in text or end in text:
        text, count = re.subn(re.escape(start) + '.*?' + re.escape(end) + r'\n\n', lambda _: block, text, count=1, flags=re.S)
        if count != 1:
            raise ValueError('README delayed markers inconsistent')
        return text
    if text.count(anchor) != 1:
        raise ValueError('README delayed anchor missing')
    return text.replace(anchor, block + anchor, 1)


def integrate_readme(text, d):
    if d is None:
        return text
    study.validate_summary(d); frozen = d['clocks']['memory_freeze']['unix_seconds']; ranges = study.clock_ranges(d)
    rows = ['| Delayed arm | Format | Accepted | Optional inspections | Inspection bytes | Projection chars |', '| --- | --- | ---: | ---: | ---: | ---: |']
    for arm in study.ARMS:
        for fmt in ('all', *study.FORMATS):
            c = d['counts'][arm][fmt]; rows.append(f'| {arm} | {fmt} | {c["accepted"]}/{c["attempts"]} | {c["inspections"]} | {c["source_bytes_read"]} | {c["returned_canonical_characters"]} |')
    pairs = study.paired_counts(d)
    finding = 'The predeclared equal-acceptance/fewer-inspections/no-added-errors criterion was met.' if study.efficient_record_use(d) else 'The predeclared equal-acceptance/fewer-inspections/no-added-errors criterion was not met; no accuracy or optional-inspection benefit is established.'
    block = f'''{README_START}
## Same frozen experience record — collected delayed trial, 2026-10-29

[日本語]({study.BASE+study.STUDY}) / [English]({study.BASE+study.STUDY}en.html)

Three further objectives frozen before training × two formats give six items per arm, not six independent objectives or experiences. Twelve fresh arm/item contexts received the same unchanged 5627-character external record or no record. Both arms received the same current evidence and optional inspection opportunity. All twelve policies froze before inspection outputs; all twelve actions froze before execution outcomes. One action and at most one inspection per item; no probe repairs or feedback-driven record updates.

{chr(10).join(rows)}

Paired outcomes: corrected {pairs['corrected']}, regressed {pairs['regressed']}, both correct {pairs['both_correct']}, both wrong {pairs['both_wrong']}. {finding} Optional-inspection bytes and projection characters are not total source I/O: both arms' executor reads the assigned source for every actual artifact. Speed, token, compute and spending savings are unmeasured.

Actual first/last initial authoring authorization elapsed: {ranges['initial_authoring'][0] - frozen:.6f}–{ranges['initial_authoring'][1] - frozen:.6f} seconds after memory freeze, later than the 86400-second minimum, not exactly 24 hours. Memory freeze UTC: {d['clocks']['memory_freeze']['utc']}; preparation UTC: {d['clocks']['collection_prepared']['utc']}. Native item execution starts elapsed: {ranges['execution'][0] - frozen:.6f}–{ranges['execution'][1] - frozen:.6f} seconds. Initial/final authoring clocks are actual pre-call authorization receipts, not exposed provider sampling timestamps. Inspection and native execution clocks are recorded separately in the JSON and dated pages; direct submission has no second authoring call.

The three stage-record local modification times use original state-file local filesystem mtimes (`stage_freeze_clock_basis=local_filesystem_mtime`). All three raw policy/inspection/action phase-entry authorization guards are separately recorded; phase-entry is not completion and may follow the last output. The clock-projection audit digest binds this reporting projection. These are not instrumented exact completion timestamps. Local metadata is not a provider timestamp, external signature or attestation; original trial records and times are unchanged.

The immediate and delayed blocks use different objectives as well as different times. Differences between them do not identify a time-only retention effect or forgetting. Fresh contexts rereading an external record test persistence/portability, not one subject's psychological retention, continuous identity, weight learning, natural conversation memory or a forgetting curve. Provider/model/settings/token/compute metadata is unverified and null; roles use read allowlists on a shared host, not OS isolation. No private native LRE, SHIORI mechanism/speed, native Wake, Emotion, biological brain, AGI or consciousness claim is made.

The training review template explicitly requested `legacy_scope`; this is not unprompted conceptual learning.

The {d['engineering']['tests_run']} synthetic transport-preparation checks are engineering evidence, separate from twelve actual delayed items. The 2026-10-28 immediate data/page retains its immutable at-publication pending state. This dated study/data/replay appends actual collected outcomes without changing any of the ten earlier studies, downloads or four overview animations.

[Saved-action replay]({study.BASE+study.REPLAY}README.md) / [External ZIP]({study.BASE+study.ZIP_FILE}). Exact public numeric sources, frozen record, saved policies/actions/gold and the unchanged executor support mechanical replay. This does not regenerate fresh AI judgment or repeat delayed actor collection. Only the newly collected delayed tasks/gold are included; private actor envelopes, receipts and local runtime paths are excluded.
{README_END}

'''
    text = _replace_block(text, README_START, README_END, block, '## Public and private scope\n')
    build = f'''{BUILD_START}
### Eleventh-study activation: actual delayed saved-action results

Existing study/build instructions above remain applicable. To activate the independently audited delayed export and separately audited replay:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_pages.py --experience-retention-delayed /absolute/path/to/reports/public-export-v1.json --experience-retention-delayed-replay /absolute/path/to/reports/public-replay --experience-retention-delayed-zip /absolute/path/to/reports/public-replay.zip
```

The same flags are accepted by `tools/build_experience_retention_delayed.py`. Missing export produces no new publication or placeholder results. Invalid schema/counts/clocks, original source changes, MANIFEST case/hash/inventory changes or an external ZIP mismatch refuse publication writes. Repeat builds use the installed audited data/replay by default. The immediate phase-one page and its pending state are never rewritten as collected.
{BUILD_END}

'''
    return _replace_block(text, BUILD_START, BUILD_END, build, '## Preservation\n')


def integrate_sitemap(text, d):
    if d is None:
        return text
    study.validate_summary(d)
    if text.count('</urlset>') != 1:
        raise ValueError('Sitemap closing anchor missing')
    for url in (study.BASE + study.STUDY, study.BASE + study.STUDY + 'en.html'):
        if f'<loc>{url}</loc>' not in text:
            text = text.replace('</urlset>', f'  <url><loc>{escape(url)}</loc></url>\n</urlset>', 1)
    return text


def prepare_updates(root=ROOT, source=None, bundle=None, zip_path=None):
    export = study.read_export(root, source)
    if export is None:
        return {}
    d, raw = export; files, archive = study.require_public_inputs(root, d, bundle, zip_path)
    updates = {study.DATA_FILE: raw, study.STUDY + 'index.html': study.render('ja', d).encode('utf-8'),
        study.STUDY + 'en.html': study.render('en', d).encode('utf-8'),
        study.STUDY + 'experience-retention-delayed.css': study.CSS.encode('utf-8'), study.ZIP_FILE: archive}
    updates.update({study.REPLAY + name: value for name, value in files.items()})
    for name, lang in [('index.html', 'ja'), ('index.en.html', 'en')]:
        updates[name] = integrate_home((root / name).read_text(encoding='utf-8'), lang, d).encode('utf-8')
    for name, lang in [('results.html', 'ja'), ('results.en.html', 'en')]:
        updates[name] = integrate_listing((root / name).read_text(encoding='utf-8'), lang, d).encode('utf-8')
    updates['README.md'] = integrate_readme((root / 'README.md').read_text(encoding='utf-8'), d).encode('utf-8')
    updates['sitemap.xml'] = integrate_sitemap((root / 'sitemap.xml').read_text(encoding='utf-8'), d).encode('utf-8')
    return updates
