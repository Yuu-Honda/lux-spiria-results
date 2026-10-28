"""Plan the optional tenth public study without writing or reading native state."""
from html import escape
import importlib.util
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('tool_observation_public_builder', ROOT / 'tools/build_tool_observation_loop.py')
study = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(study)
t = study.t
LATEST = re.compile(r'<section class="latest-study"(?=\s).*?</section>', re.S)
CARD = re.compile(r'<article class="study-card" data-study="tool-observation-loop">.*?</article>', re.S)
README_START = '<!-- TOOL_OBSERVATION_LOOP_STUDY_START -->'
README_END = '<!-- TOOL_OBSERVATION_LOOP_STUDY_END -->'
BUILD_START = '<!-- TOOL_OBSERVATION_LOOP_BUILD_START -->'
BUILD_END = '<!-- TOOL_OBSERVATION_LOOP_BUILD_END -->'


def optional_summary(root=ROOT, source=None):
    return study.optional_summary(root, source)


def metrics(d, lang, home=False):
    exact, _ = study.achieved(d)
    rows = [(str(exact) + '/3', t('原記録と判断の返却・一致', 'Exact original evidence and judgment return', lang)),
        (d['counts']['operations'], t('記録した操作', 'Recorded operations', lang)),
        (d['source_counts']['independent_events'], t('意味索引の独立tool event', 'Independent tool events in the semantic index', lang))]
    if home:
        return ''.join(f'<div class="latest-study-metric"><dt>{label}</dt><dd><span>{value}</span></dd></div>' for value, label in rows)
    return ''.join(f'<span><strong>{value}</strong>{label}</span>' for value, label in rows)


def latest_home(d, lang):
    study.validate_summary(d); href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    exact, reads = study.achieved(d)
    return f'''<section class="latest-study" aria-labelledby="latest-study-title" data-source="{study.DATA_FILE}"><div class="latest-study-copy"><p class="latest-study-kicker">FUNCTIONAL PILOT / <time datetime="2026-10-28">2026-10-28</time></p><h2 id="latest-study-title">{t('実toolの記録を、<br>次の操作へつなぐ。', 'Connect actual tool evidence<br>to the next operation.', lang)}</h2><p class="latest-study-summary">{t(f'限定した3条件の{exact}/3で、手掛かり検索から過去の判断と元のtool input/outputを返し、一致を確認。次の実操作では現在のnative状態を読むlre_readが{reads}/3でexit 0でした。', f'Cued recall returned historical judgment and exact original tool input/output in {exact}/3 bounded checks. Subsequent lre_read calls to read current native state exited zero in {reads}/3.', lang)}</p><a class="latest-study-link" href="{href}">{t('実操作と機能接続の範囲を読む', 'Read actual operations and integration limits', lang)} ↗</a></div><div class="latest-study-results"><p class="latest-study-order">{t('保存済みの実記録 · 閲覧中のnative実行ではありません', 'Recorded evidence · no native execution while browsing', lang)}</p><dl class="latest-study-metrics">{metrics(d, lang, True)}</dl><p class="latest-study-boundary">{t('機能接続pilotであり、精度向上・心理的保持・脳の証明ではありません。private native code/stateとtool・判断本文は非公開。以前の24時間試験は別研究の未収集状態を保持します。', 'A functional pilot does not establish accuracy gains, psychological retention or brains. Private native code/state and tool/judgment bodies are excluded. The earlier 24-hour study keeps its separate pending state.', lang)}</p><a class="latest-study-source" href="{study.DATA_FILE}">{t('型・全操作・件数・hash / JSON', 'Types, all operations, counts and digests / JSON', lang)}</a></div></section>'''


def integrate_home(html, lang, d):
    if d is None:
        return html
    study.validate_summary(d)
    if len(LATEST.findall(html)) != 1:
        raise ValueError('Exactly one existing overview latest panel required')
    return LATEST.sub(lambda _: latest_home(d, lang), html, count=1)


def listing_card(d, lang):
    study.validate_summary(d); href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    return f'''<article class="study-card" data-study="tool-observation-loop"><span class="study-status">STUDY / TOOL OBSERVATION / FUNCTIONAL PILOT</span><time datetime="2026-10-28">2026-10-28</time><h3><a href="{href}">{t('実toolの原記録と判断を、次の操作へ。', 'From original tool evidence and judgment to another operation.', lang)} ↗</a></h3><p>{t('実tool観察とAI判断を分けてnative LRE/SHIORIへ接続。3つの限定context、変更条件と旧条件への戻り、全操作の終了状態を公開します。意味索引のtool原記録と同じeventの判断を独立した経験2件へ数えません。', 'Connect typed tool observations and separate AI judgments through native LRE/SHIORI. Report three bounded contexts, changed and legacy conditions, and every operation exit. A tool receipt and its interpretation of the same indexed event are not two independent experiences.', lang)}</p><div class="study-stats">{metrics(d, lang)}</div><p>{study.boundary(lang)}</p><p><a href="{study.REPLAY}README.md">{t('保存evidenceの検算', 'Saved-evidence verification', lang)} ↗</a> · <a href="{study.ZIP_FILE}" download>ZIP ↓</a></p></article>'''


def integrate_listing(html, lang, d):
    if d is None:
        return html
    study.validate_summary(d); html = CARD.sub('', html)
    hero = f'''<div class="status-strip"><span>{t('実tool記録とnative機能接続pilot', 'Actual tool evidence and native integration pilot', lang)}</span><small>UPDATED / 2026-10-28</small></div>
<div class="hero-metrics"><div class="metric"><strong>10</strong><span>{t('公開研究', 'Published studies', lang)}</span><small>2026-10-13 / 2026-10-28</small></div><div class="metric"><strong>{d['counts']['operations']}</strong><span>{t('記録した操作', 'Recorded operations', lang)}</span><small>{t('終了状態と意味判断を分離', 'Exit status and meaning remain separate', lang)}</small></div><div class="metric"><strong>3</strong><span>{t('限定context check', 'Bounded context checks', lang)}</span><small>{t('元・変更・旧条件へ戻る', 'Unchanged, changed, legacy return', lang)}</small></div></div>'''
    html, count = re.subn(r'<div class="status-strip">.*?</div>\n<div class="hero-metrics">.*?</div></div>', lambda _: hero, html, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Listing latest metadata anchor missing')
    anchor = re.search(r'<section class="section" id="studies"[^>]*><div class="section-heading">.*?</div>', html, re.S)
    if anchor is None:
        raise ValueError('Listing card anchor missing')
    return html[:anchor.end()] + listing_card(d, lang) + html[anchor.end():]


def integrate_readme(text, d):
    if d is None:
        return text
    study.validate_summary(d); c = d['counts']; s = d['source_counts']
    rows = ['| Context | First operation | Exit | Tool source returned | Judgment returned | Earlier retained |', '| --- | ---: | ---: | --- | --- | --- |']
    operations_by_id = {row['ordinal']: row for row in d['operations']}
    for row in d['contexts']:
        first = '—' if row['first_operation'] is None else 'O' + str(row['first_operation']).zfill(3) + ' ' + operations_by_id[row['first_operation']]['operation']
        rows.append('| ' + ' | '.join([row['id'], first, *[str(row[k]) for k in ['exit_code', 'tool_source_return', 'judgment_return', 'old_retained_preserved']]]) + ' |')
    block = f'''{README_START}
## Typed tool-observation integration pilot — 2026-10-28

[日本語]({study.BASE+study.STUDY}) / [English]({study.BASE+study.STUDY}en.html)

Actual subprocess observations and separate AI judgments were connected through isolated native LRE capture/review and native SHIORI cued recall. The pilot records {c['operations']} worker operations: {c['exit_zero']} exit zero and {c['exit_nonzero']} nonzero. Process exit is not semantic success, memory growth, or answer adequacy. The semantic index source set has {s['tool_observations']} tool observations and {s['actual_ai_judgments']} AI judgments about {s['independent_events']} independent tool events; a receipt and its interpretation of the same event are not two experiences.

{chr(10).join(rows)}

These are three bounded functional context checks, with an engineered change and legacy return, not an accuracy-benefit or psychological-retention trial. Continuations choose from a disclosed finite vocabulary of eight reviewed cue labels without source mappings, bodies or IDs; this does not demonstrate unconstrained language comprehension. Exact evidence return, native read-state equality, graph support paths, hops-zero and convergence-off diagnostics remain separate outcomes.

The changed copy saved a new condition-bound judgment in native LRE, but that new judgment was neither indexed nor subsequently recalled. Recurrent learning is not established.

Synthetic engineering rounds remain separate: round 01, 14 tests / 93 recorded workers; round 02, 15 tests / 102 workers. Initial initialize used revision 1. The reviewed revision 2 correction added original-input return before semantic indexing/continuation, without discarding or restarting the pilot. A pre-index diagnostic had a prospective plan but lacked a separate pre-call cue-span/review artifact and was not a scored continuation. The continuation choices use hash-bound pre-call span/review records; universal protocol compliance is not claimed.

No human/private conversation content was fetched or used. Tool input/stdout/stderr and AI judgment bodies, private vendor code, native state/databases, feature/cue/trace bodies, actor IDs and local paths are excluded. Provider/model metadata remains unverified and null. Earlier nine studies, including the experience-retention page's immutable pending delayed endpoint, and four overview animations retain their bytes. This pilot makes no full Wake, speed, biological brain, AGI, consciousness or psychological-identity claim.

[Saved-evidence verifier]({study.BASE+study.REPLAY}README.md) / [ZIP]({study.BASE+study.ZIP_FILE}). This verifies disclosed hashes, schema and arithmetic only. It cannot reconstruct undisclosed native operations or independently prove exported claims; it is not a complete native replay or fresh AI regeneration. Hashes are local integrity identifiers, not external signatures or hardware attestation.
{README_END}

'''
    if README_START in text or README_END in text:
        text, count = re.subn(re.escape(README_START) + '.*?' + re.escape(README_END) + r'\n\n', lambda _: block, text, count=1, flags=re.S)
        if count != 1:
            raise ValueError('README tool-observation markers inconsistent')
    else:
        anchor = '## Public and private scope\n'
        if text.count(anchor) != 1:
            raise ValueError('README scope anchor missing')
        text = text.replace(anchor, block + anchor, 1)
    build = f'''{BUILD_START}
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
{BUILD_END}

'''
    if BUILD_START in text or BUILD_END in text:
        text, count = re.subn(re.escape(BUILD_START) + '.*?' + re.escape(BUILD_END) + r'\n\n', '', text, count=1, flags=re.S)
        if count != 1:
            raise ValueError('README tool-observation build markers inconsistent')
    if text.count('## Build and verify the website\n') != 1 or text.count('## Preservation\n') != 1:
        raise ValueError('README build anchor missing')
    return text.replace('## Preservation\n', build + '## Preservation\n', 1)


def integrate_sitemap(text, d):
    if d is None:
        return text
    study.validate_summary(d)
    if text.count('</urlset>') != 1:
        raise ValueError('Sitemap closing anchor missing')
    for url in [study.BASE + study.STUDY, study.BASE + study.STUDY + 'en.html']:
        if f'<loc>{url}</loc>' not in text:
            text = text.replace('</urlset>', f'  <url><loc>{escape(url)}</loc></url>\n</urlset>', 1)
    return text


def prepare_updates(root=ROOT, source=None):
    export = study.read_export(root, source)
    if export is None:
        return {}
    d, raw = export
    bundle, archive = study.evidence_package(d, raw)
    updates = {study.DATA_FILE: raw, study.STUDY + 'index.html': study.render('ja', d).encode('utf-8'),
        study.STUDY + 'en.html': study.render('en', d).encode('utf-8'),
        study.STUDY + 'tool-observation-loop.css': study.CSS.encode('utf-8'), study.ZIP_FILE: archive}
    updates.update({study.REPLAY + name: value for name, value in bundle.items()})
    for name, lang in [('index.html', 'ja'), ('index.en.html', 'en')]:
        updates[name] = integrate_home((root / name).read_text(encoding='utf-8'), lang, d).encode('utf-8')
    for name, lang in [('results.html', 'ja'), ('results.en.html', 'en')]:
        updates[name] = integrate_listing((root / name).read_text(encoding='utf-8'), lang, d).encode('utf-8')
    updates['README.md'] = integrate_readme((root / 'README.md').read_text(encoding='utf-8'), d).encode('utf-8')
    updates['sitemap.xml'] = integrate_sitemap((root / 'sitemap.xml').read_text(encoding='utf-8'), d).encode('utf-8')
    return updates
