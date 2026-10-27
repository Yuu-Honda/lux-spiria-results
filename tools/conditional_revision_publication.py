"""Plan eighth-study publication only from validated audited public records."""
from html import escape
import importlib.util
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('conditional_revision_public_builder', ROOT / 'tools/build_conditional_revision.py')
study = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(study)
t = study.t
LATEST = re.compile(r'<section class="latest-study"(?=\s).*?</section>', re.S)
CARD = re.compile(r'<article class="study-card" data-study="conditional-revision">.*?</article>', re.S)
README_START = '<!-- CONDITIONAL_REVISION_STUDY_START -->'
README_END = '<!-- CONDITIONAL_REVISION_STUDY_END -->'


def optional_summary(root=ROOT):
    return study.optional_summary(root)


def _metrics(d, lang, home=False):
    parts = [(fmt, t('元形式の新規目的', 'New objectives: legacy', lang) if fmt == 'legacy_root' else
              t('包み替え形式の新規目的', 'New objectives: wrapped', lang)) for fmt in study.FORMATS]
    parts.append((None, t('後続全項目', 'All later items', lang)))
    values = [(study.aggregate_items(study.selected(d, study.ARMS[0], fmt))['accepted'],
               study.aggregate_items(study.selected(d, study.ARMS[1], fmt))['accepted'],
               3 if fmt else 6, label) for fmt, label in parts]
    if home:
        return ''.join(f'<div class="latest-study-metric"><dt>{label}<span>{t("3目的・各2形式", "Three objectives, two formats", lang)}</span></dt><dd><span>{a}<small>/{total}</small></span><span class="latest-study-arrow" aria-hidden="true">→</span><span>{b}<small>/{total}</small></span></dd></div>' for a, b, total, label in values)
    return ''.join(f'<span><strong>{a}/{total} → {b}/{total}</strong>{label}</span>' for a, b, total, label in values)


def latest_home(d, lang):
    study.validate_summary(d); href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    return f'''<section class="latest-study" aria-labelledby="latest-study-title" data-source="{study.DATA_FILE}"><div class="latest-study-copy"><p class="latest-study-kicker">RECORDED STUDY / <time datetime="2026-10-27">2026-10-27</time></p><h2 id="latest-study-title">{t('置き場所が変わったら、<br>読み方をどう変えるか。', 'When the location changes,<br>how does the reading method change?', lang)}</h2><p class="latest-study-summary">{t('同じ公開データをpayloadの下へ移し、保存操作を再実行。実際のAIが読み方を修正し、元形式では元の方法を保つ条件分岐を調べました。3つの新規目的を2形式、2条件で比べます。', 'The same public data was moved under payload and saved operations replayed. An actual AI chose compatible reads while retaining the legacy method. Three new objectives were compared across two formats and two arms.', lang)}</p><a class="latest-study-link" href="{href}">{t('実結果・分類・限界を読む', 'Read actual results, labels and limits', lang)} ↗</a></div><div class="latest-study-results"><p class="latest-study-order">{t('同じ観測記録 → 同じ記録＋条件付きレビュー', 'Same observations → same observations + conditional review', lang)}</p><dl class="latest-study-metrics">{_metrics(d,lang,True)}</dl><p class="latest-study-boundary">{t('意図した表層的なschema変更への適応です。完全な現在のJSONは渡さず、共通のschema観測＋handleを使います。旧操作の失敗を新しいAIの予測失敗にせず、信念改訂・概念学習・脳の実証へ広げません。', 'This is adaptation to a declared surface-schema change through shared schema observations and handles, without full current JSON. Old-action failures are not new-AI prediction errors and do not establish belief revision, concept learning or brains.',lang)}</p><a class="latest-study-source" href="{study.DATA_FILE}">{t('全21項目と集計 / JSON','All 21 items and aggregates / JSON',lang)}</a></div></section>'''


def integrate_home(html, lang, d):
    if d is None: return html
    study.validate_summary(d)
    if len(LATEST.findall(html)) != 1: raise ValueError('Exactly one overview latest-study panel required')
    return LATEST.sub(lambda _: latest_home(d,lang), html, count=1)


def listing_card(d, lang):
    study.validate_summary(d); href = study.STUDY + ('index.html' if lang=='ja' else 'en.html')
    return f'''<article class="study-card" data-study="conditional-revision"><span class="study-status">STUDY / CONTROLLED CONDITIONAL REVISION</span><time datetime="2026-10-27">2026-10-27</time><h3><a href="{href}">{t('置き場所の変更に、読み方を合わせる。', 'Adapt the reading method to a changed location.',lang)} ↗</a></h3><p>{t('保存操作6再実行＋実際のAI修正3＋後続12の計21項目。データの値を保ってpayloadの下へ移し、新しい読み方と元形式の方法保持を調べます。', '21 execution items: six saved replays, three actual AI repairs and 12 later actions. Data values stay the same under payload while new reads and legacy preservation are checked.',lang)}</p><p>{t('以下は同じ観測記録 → レビュー追加。後続6項目は3目的×2形式で、6つの独立した目的ではありません。', 'Below: identical observations → added review. Six later items are three objectives × two formats, not six independent objectives.',lang)}</p><div class="study-stats">{_metrics(d,lang)}</div><p>{t('形式変更は意図した操作です。完全な現在のJSONを与えない人工interfaceで、元形式保持の指示があります。本人の誤判断後の改訂、概念学習、自然な記憶や脳を実証する結果とは扱いません。', 'The migration is engineered. This artificial interface withholds full current JSON and explicitly instructs legacy preservation. It does not demonstrate revision after one’s own mistaken judgment, concept learning, natural memory or brains.',lang)}</p><p><a href="{study.REPLAY}README.md">{t('公開リプレイ','Public replay',lang)} ↗</a> · <a href="{study.ZIP_FILE}" download>ZIP ↓</a></p></article>'''


def integrate_listing(html, lang, d):
    if d is None: return html
    study.validate_summary(d); html = CARD.sub('',html)
    hero = f'''<div class="status-strip"><span>{t('実行済み結果を公開 · 制御した互換性課題','Recorded execution · controlled compatibility task',lang)}</span><small>UPDATED / 2026-10-27</small></div>
<div class="hero-metrics"><div class="metric"><strong>08</strong><span>{t('公開研究','Published studies',lang)}</span><small>2026-10-13 / 2026-10-27</small></div><div class="metric"><strong>3</strong><span>{t('最新研究の新規目的','New objectives in latest study',lang)}</span><small>{t('各2形式・2条件','Two formats and two arms each',lang)}</small></div><div class="metric"><strong>21</strong><span>{t('実際の実行項目','Actual execution items',lang)}</span><small>{t('保存再実行6＋修正3＋後続12','Six replays + three repairs + 12 later actions',lang)}</small></div></div>'''
    html,count = re.subn(r'<div class="status-strip">.*?</div>\n<div class="hero-metrics">.*?</div></div>',lambda _:hero,html,count=1,flags=re.S)
    if count!=1: raise ValueError('Listing latest metadata anchor missing')
    anchor=re.search(r'<section class="section" id="studies"[^>]*><div class="section-heading">.*?</div>',html,re.S)
    if anchor is None: raise ValueError('Listing study-card anchor missing')
    html=html[:anchor.end()]+listing_card(d,lang)+html[anchor.end():]
    html=html.replace(t('今回の公開データ作業台は例外で','The present public-data workbench is an exception:',lang),
                      t('実行結果・条件付き互換修正の公開データ作業台2研究は例外で','The action-feedback and conditional-compatibility public-data workbenches are exceptions:',lang))
    return html


def integrate_readme(text,d):
    if d is None:return text
    study.validate_summary(d);pairs=study.paired_counts(d)
    rows=['| Condition | Accepted | Execution errors | Written artifacts |','| --- | ---: | ---: | ---: |']
    for condition in study.CONDITIONS:
        row=d['counts'][condition];rows.append(f'| {study.label(condition,"en")} | {row["accepted"]}/{row["items"]} | {row["execution_errors"]} | {row["artifacts_written"]} |')
    types=d['review']['change_types']
    section=f'''{README_START}
## Controlled conditional compatibility — 2026-10-27

[日本語]({study.BASE+study.STUDY}) / [English]({study.BASE+study.STUDY}en.html)

The same three known public sources were deliberately moved under `payload` in an `artifact-container.v2` wrapper. Parsed original types/values and original raw bytes were preserved. Saved operations were replayed, an actual AI chose compatible new reads, and the original method remained applicable to legacy files. This is an engineered surface-schema change, not a natural outage, belief revision, spontaneous concept learning or brain reproduction.

{chr(10).join(rows)}

The 21 execution items comprise six saved replays, three new AI repairs and 12 later actions. Saved predictions belong to an earlier v1 context and are excluded from current prediction scores in both diagnostic replays. Current repair choice and post-outcome review reuse the same fresh context over two turns; the two later arms are fresh contexts. The primary comparison is identical raw observations versus those same observations plus conditional review, not feedback versus no feedback. All 12 later actions are frozen before feedback.

The later six items per arm are three new objectives in two formats, not six independent objectives. Raw → review corrected {pairs['corrected']} items and regressed {pairs['regressed']}. Actual review classifications are {types.count('conditional_update')} conditional_update, {types.count('confirmation')} confirmation and {types.count('deferred')} deferred. Repairing saved external operations is distinct from revising one's own mistaken judgment; actual confirmation labels are not recoded as updates.

Actors receive shared actual schema observations and handles, not full current JSON. Observations retain keys/array order and condition-id strings, replace other scalars by type markers, and explicitly omit per_query/provenance. The contract explains formats and instructs legacy preservation, so appropriate conditional branching is not spontaneous discovery. Task order and dispatch are fixed; provider/time effects and equal compute are unverified. Review grounding and retained legacy scope are independently assessed. Canonical input/output characters, actual errors and all retained items remain distinct from model learning or psychological accuracy.

[Public replay instructions]({study.BASE+study.REPLAY}README.md) / [Replay ZIP]({study.BASE+study.ZIP_FILE}). Replay executes saved operations without regenerating fresh AI decisions. All seven earlier dated studies/data/replay and four overview stories/assets retain their bytes and publication boundaries.
{README_END}

'''
    if README_START in text or README_END in text:
        text,count=re.subn(re.escape(README_START)+'.*?'+re.escape(README_END)+r'\n\n',lambda _:section,text,count=1,flags=re.S)
        if count!=1:raise ValueError('README conditional-revision markers inconsistent')
    else:
        anchor='## Public and private scope\n'
        if text.count(anchor)!=1:raise ValueError('README public-scope anchor missing')
        text=text.replace(anchor,section+anchor,1)
    build=f'''## Build and verify the website

Python 3 standard library only:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_pages.py
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python3 -B -m http.server 8769 --bind 127.0.0.1
```

Optional `{study.DATA_FILE}` activates the eighth JA/EN study only after strict validation and matching original-source, public manifest/README and external ZIP hashes. Missing export makes no new publication changes or placeholder results. Invalid data or missing replay files fails before writes. The builder updates only listings, the overview latest-study panel, README and sitemap, and adds the new dated pair. Seven older studies/data/replay and four overview stories/assets remain unchanged.

`PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_conditional_revision.py` rebuilds only its dated pair after the same checks. Public workbench replay has separate instructions and does not regenerate fresh AI. GitHub Pages serves `main` at the repository root.

'''
    text,count=re.subn(r'## Build and verify the website\n.*?(?=## Preservation\n)',lambda _:build,text,count=1,flags=re.S)
    if count!=1:raise ValueError('README build section anchor missing')
    return text


def integrate_sitemap(text,d):
    if d is None:return text
    study.validate_summary(d)
    if text.count('</urlset>')!=1:raise ValueError('Sitemap closing anchor missing')
    for url in (study.BASE+study.STUDY,study.BASE+study.STUDY+'en.html'):
        if f'<loc>{url}</loc>' not in text:text=text.replace('</urlset>',f'  <url><loc>{escape(url)}</loc></url>\n</urlset>',1)
    return text


def prepare_updates(root=ROOT,summary=None):
    d=optional_summary(root) if summary is None else study.validate_summary(summary)
    if d is None:return {}
    study.require_public_inputs(root,d)
    updates={study.STUDY+'index.html':study.render('ja',d),study.STUDY+'en.html':study.render('en',d)}
    for name,lang in [('index.html','ja'),('index.en.html','en')]:updates[name]=integrate_home((root/name).read_text(encoding='utf-8'),lang,d)
    updates['README.md']=integrate_readme((root/'README.md').read_text(encoding='utf-8'),d)
    updates['sitemap.xml']=integrate_sitemap((root/'sitemap.xml').read_text(encoding='utf-8'),d)
    return updates
