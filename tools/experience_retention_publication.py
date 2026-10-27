"""Optional ninth-study publication plan; no output without audited records."""
from html import escape
import importlib.util
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('experience_retention_public_builder', ROOT / 'tools/build_experience_retention.py')
study = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(study)
t = study.t
LATEST = re.compile(r'<section class="latest-study"(?=\s).*?</section>', re.S)
CARD = re.compile(r'<article class="study-card" data-study="experience-retention">.*?</article>', re.S)
README_START = '<!-- EXPERIENCE_RETENTION_STUDY_START -->'
README_END = '<!-- EXPERIENCE_RETENTION_STUDY_END -->'


def optional_summary(root=ROOT): return study.optional_summary(root)


def _metrics(d, lang, home=False):
    rows = []
    for fmt in study.FORMATS:
        a, b = (d['counts']['immediate'][arm][fmt]['accepted'] for arm in study.ARMS)
        rows.append((a, b, 3, t('元形式の受理', 'Original-format acceptance', lang) if fmt == 'original' else t('包み替え形式の受理', 'Changed-format acceptance', lang)))
    a, b = (d['counts']['immediate'][arm]['all']['inspections'] for arm in study.ARMS)
    rows.append((a, b, 6, t('追加の構造確認', 'Additional schema inspections', lang)))
    if home:
        return ''.join(f'<div class="latest-study-metric"><dt>{label}<span>{t("同じ新規3目的×2形式", "Same three objectives × two formats", lang)}</span></dt><dd><span>{a}<small>/{total}</small></span><span class="latest-study-arrow" aria-hidden="true">→</span><span>{b}<small>/{total}</small></span></dd></div>' for a, b, total, label in rows)
    return ''.join(f'<span><strong>{a}/{total} → {b}/{total}</strong>{label}</span>' for a, b, total, label in rows)


def latest_home(d, lang):
    study.validate_summary(d); href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    return f'''<section class="latest-study" aria-labelledby="latest-study-title" data-source="{study.DATA_FILE}"><div class="latest-study-copy"><p class="latest-study-kicker">IMMEDIATE STUDY / <time datetime="2026-10-28">2026-10-28</time></p><h2 id="latest-study-title">{t('自分の実行経験を、<br>次の操作へ渡す。', 'Pass an execution record<br>to the next task.', lang)}</h2><p class="latest-study-summary">{t('自分で選んだ操作と実結果から凍結した経験記録を、条件×項目ごとの新しいAIへ渡すかどうかを比較。同じ3つの新規目的を2形式で実行し、受理と追加確認を分けて測ります。', 'Fresh AI contexts per arm/item receive a frozen record of own operations and actual outcomes, or no record. The same three held-out objectives in two formats compare artifact acceptance and optional inspection separately.', lang)}</p><a class="latest-study-link" href="{href}">{t('直後の実結果と限界を読む', 'Read immediate results and limits', lang)} ↗</a></div><div class="latest-study-results"><p class="latest-study-order">{t('経験記録なし → 同じ凍結記録あり', 'No experience record → same frozen record', lang)}</p><dl class="latest-study-metrics">{_metrics(d, lang, True)}</dl><p class="latest-study-boundary">{t('追加確認0は総source I/O0ではありません。実行器は両条件でファイルを読みます。24時間後は未収集で予約≠結果。外部記録の利用を、心理的保持・重み学習・脳の証明へ広げません。', 'Zero additional inspections is not zero total source I/O; both arms read files during execution. The ≥24-hour phase is uncollected: scheduling is not a result. External-record use does not establish psychological retention, weight learning or brains.', lang)}</p><a class="latest-study-source" href="{study.DATA_FILE}">{t('全実行記録・費用・未収集状態 / JSON', 'All attempts, costs and pending status / JSON', lang)}</a></div></section>'''


def integrate_home(html, lang, d):
    if d is None: return html
    study.validate_summary(d)
    if len(LATEST.findall(html)) != 1: raise ValueError('Exactly one overview latest panel required')
    return LATEST.sub(lambda _: latest_home(d, lang), html, count=1)


def listing_card(d, lang):
    study.validate_summary(d); href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    return f'''<article class="study-card" data-study="experience-retention"><span class="study-status">STUDY / OWN EXPERIENCE RECORD / IMMEDIATE</span><time datetime="2026-10-28">2026-10-28</time><h3><a href="{href}">{t('実行経験の記録を、次の操作へ使う。', 'Use an execution record on the next task.', lang)} ↗</a></h3><p>{t('本人が選んだ元形式・変更形式の初回6件と、失敗時だけの最大1修正から記録を凍結。別の新しいAIが同じ3新規目的×2形式を各条件6項目で実行します。プローブには予めschema・形式の答えや旧形式維持の直接指示を渡しません。経験記録のテンプレートは旧条件の適用範囲を尋ねます。', 'Freeze a record of six own initial operations across original/changed formats, with at most one repair per failure. Separate fresh AI contexts execute three held-out objectives × two formats, six items per arm, without pre-supplied schema/format answers or direct probe instructions to preserve legacy behavior. The record template asks about applicability of earlier conditions.', lang)}</p><p>{t('経験記録なし → 同じ凍結記録あり。追加確認は任意の実schema読取に限定し、総I/Oや速度・計算量の節約とは区別します。', 'No record → same frozen record. Optional actual schema inspections are distinct from total I/O, speed or compute savings.', lang)}</p><div class="study-stats">{_metrics(d, lang)}</div><p>{t('24時間後の別目的は事前固定済み・未収集。予約は結果ではありません。同じ外部記録の再利用は、心理的保持・重み学習・特定の記憶機構の実証ではありません。', 'Further objectives for ≥24 hours later are frozen but uncollected. Scheduling is not a result. Reuse of an external record does not establish psychological retention, weight learning or a particular memory mechanism.', lang)}</p><p><a href="{study.REPLAY}README.md">{t('公開リプレイ', 'Public replay', lang)} ↗</a> · <a href="{study.ZIP_FILE}" download>ZIP ↓</a></p></article>'''


def integrate_listing(html, lang, d):
    if d is None: return html
    study.validate_summary(d); html = CARD.sub('', html)
    attempts = 18 + sum(row['repair'] is not None for row in d['training'])
    hero = f'''<div class="status-strip"><span>{t('直後の実結果を公開 · 遅延は未収集', 'Immediate execution recorded · delayed uncollected', lang)}</span><small>UPDATED / 2026-10-28</small></div>
<div class="hero-metrics"><div class="metric"><strong>09</strong><span>{t('公開研究', 'Published studies', lang)}</span><small>2026-10-13 / 2026-10-28</small></div><div class="metric"><strong>3</strong><span>{t('直後の新規目的', 'Held-out immediate objectives', lang)}</span><small>{t('各2形式・2条件', 'Two formats and two arms each', lang)}</small></div><div class="metric"><strong>{attempts}</strong><span>{t('実際の実行項目', 'Actual execution items', lang)}</span><small>{t('学習初回6＋実修正＋直後12', 'Six training initials + repairs + 12 probes', lang)}</small></div></div>'''
    html, count = re.subn(r'<div class="status-strip">.*?</div>\n<div class="hero-metrics">.*?</div></div>', lambda _: hero, html, count=1, flags=re.S)
    if count != 1: raise ValueError('Listing latest metadata anchor missing')
    anchor = re.search(r'<section class="section" id="studies"[^>]*><div class="section-heading">.*?</div>', html, re.S)
    if anchor is None: raise ValueError('Listing card anchor missing')
    html = html[:anchor.end()] + listing_card(d, lang) + html[anchor.end():]
    old = t('実行結果・条件付き互換修正の公開データ作業台2研究は例外で', 'The action-feedback and conditional-compatibility public-data workbenches are exceptions:', lang)
    new = t('実行結果・条件付き互換修正・経験記録利用の公開データ作業台3研究は例外で', 'The action-feedback, conditional-compatibility and experience-record public-data workbenches are exceptions:', lang)
    return html.replace(old, new)


def integrate_readme(text, d):
    if d is None: return text
    study.validate_summary(d); p = study.paired_counts(d)
    rows = ['| Arm / immediate | Accepted | Additional inspections | Inspection raw bytes | Returned projection chars |', '| --- | ---: | ---: | ---: | ---: |']
    for arm in study.ARMS:
        r = d['counts']['immediate'][arm]['all']; rows.append(f'| {study.label(arm, "en")} | {r["accepted"]}/6 | {r["inspections"]} | {r["source_bytes_read"]} | {r["returned_canonical_characters"]} |')
    m = d['memory']; delay = d['delay']
    block = f'''{README_START}
## Own experience-record use — immediate phase, 2026-10-28

[日本語]({study.BASE+study.STUDY}) / [English]({study.BASE+study.STUDY}en.html)

An actual AI chose six own initial operations on three known public numeric source families, first original then deliberately wrapped under `payload`. Only failed initials permitted at most one actual repair. The same fresh training context authored and froze three experience entries. Actual labels: {m['change_types'].count('conditional_update')} conditional_update, {m['change_types'].count('confirmation')} confirmation, {m['change_types'].count('deferred')} deferred; {m['canonical_characters']}/6000 canonical characters. Own errors or update labels were never guaranteed.

The primary comparison is availability of the whole frozen experience record versus no record, rather than review isolated from raw experience. Every arm/item uses a fresh context with the same current task, opaque source handle/family/raw hash and optional real schema inspection. No current schema or format answer is pre-supplied. Common probe instructions give no direct legacy-preservation instruction. The training-record template does request legacy_scope (applicability of earlier conditions); the AI chooses its contents. Three held-out objectives × two formats give six items per arm, not six independent objectives. All 12 policies freeze before any inspection output and all 12 actions before execution feedback. One action and at most one inspection per probe; no probe repairs or feedback updates.

{chr(10).join(rows)}

No record → record: paired corrected {p['corrected']}, regressed {p['regressed']}. The predeclared efficient-use criterion requires equal accepted counts, fewer actual additional schema inspections and no added execution errors, invalid actions or abstentions. Inspection raw bytes/projection characters concern additional structural reads only. Both arms' executor also reads the assigned source when computing each artifact, so zero inspections does not mean zero total source I/O. Latency, token, compute and spend savings are unmeasured; actual input lengths differ and provider metadata remains null.

**Delayed ≥24-hour phase: uncollected, no results.** Actual memory freeze: {delay['clock_start_utc']}; not before {delay['not_before_utc']} (86400 seconds). Further tasks/gold are frozen but only commitment hashes are public. Scheduling is not execution. A later real trial will append a separate dated page/data/root, preserving this phase-one at-publication pending state. Fresh contexts rereading the same external record tests persistence and portability, not psychological retention, continuous identity, weight learning, native Wake, SHIORI mechanism/speed, brains or a forgetting curve.

[Public replay]({study.BASE+study.REPLAY}README.md) / [Replay ZIP]({study.BASE+study.ZIP_FILE}). Saved-action replay does not regenerate fresh AI choices and excludes future tasks/gold. This is the third public-data workbench exception to the earlier six private-conversation studies; all eight earlier study/data/replay/download bytes and four overview stories remain unchanged.
{README_END}

'''
    if README_START in text or README_END in text:
        text, count = re.subn(re.escape(README_START) + '.*?' + re.escape(README_END) + r'\n\n', lambda _: block, text, count=1, flags=re.S)
        if count != 1: raise ValueError('README experience-record markers inconsistent')
    else:
        anchor = '## Public and private scope\n'
        if text.count(anchor) != 1: raise ValueError('README scope anchor missing')
        text = text.replace(anchor, block + anchor, 1)
    build = f'''## Build and verify the website

Python 3 standard library only:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_pages.py
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -B -m http.server 8769 --bind 127.0.0.1
```

Optional `{study.DATA_FILE}` activates the ninth JA/EN immediate study after exact schema/count/role/clock validation and matching original-source, replay manifest/README and external ZIP hashes. Missing export produces no new publication or placeholder results; invalid data/replay refuses writes. Only latest panels/listings, README and sitemap change alongside the new dated pair. Eight earlier dated studies/data/replay/downloads and four overview stories/assets remain unchanged. The delayed phase remains uncollected in this immutable immediate publication.

`PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_experience_retention.py` rebuilds only its dated pair after the same checks. Public replay executes saved choices without fresh AI generation. GitHub Pages serves `main` at the repository root.

'''
    text, count = re.subn(r'## Build and verify the website\n.*?(?=## Preservation\n)', lambda _: build, text, count=1, flags=re.S)
    if count != 1: raise ValueError('README build anchor missing')
    return text


def integrate_sitemap(text, d):
    if d is None: return text
    study.validate_summary(d)
    if text.count('</urlset>') != 1: raise ValueError('Sitemap closing anchor missing')
    for url in (study.BASE + study.STUDY, study.BASE + study.STUDY + 'en.html'):
        if f'<loc>{url}</loc>' not in text: text = text.replace('</urlset>', f'  <url><loc>{escape(url)}</loc></url>\n</urlset>', 1)
    return text


def prepare_updates(root=ROOT, summary=None):
    d = optional_summary(root) if summary is None else study.validate_summary(summary)
    if d is None: return {}
    study.require_public_inputs(root, d)
    updates = {study.STUDY + 'index.html': study.render('ja', d), study.STUDY + 'en.html': study.render('en', d)}
    for name, lang in [('index.html', 'ja'), ('index.en.html', 'en')]: updates[name] = integrate_home((root / name).read_text(encoding='utf-8'), lang, d)
    updates['README.md'] = integrate_readme((root / 'README.md').read_text(encoding='utf-8'), d)
    updates['sitemap.xml'] = integrate_sitemap((root / 'sitemap.xml').read_text(encoding='utf-8'), d)
    return updates
