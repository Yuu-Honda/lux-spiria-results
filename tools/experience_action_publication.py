"""Plan the optional twelfth study from one audited public dataset only."""
from html import escape
import importlib.util
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('experience_action_public_builder', ROOT / 'tools/build_experience_action_loop.py')
study = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(study)
t = study.t
LATEST = re.compile(r'<section class="latest-study"(?=\s).*?</section>', re.S)
CARD = re.compile(r'<article class="study-card" data-study="experience-action-loop">.*?</article>', re.S)
README_START = '<!-- EXPERIENCE_ACTION_LOOP_STUDY_START -->'
README_END = '<!-- EXPERIENCE_ACTION_LOOP_STUDY_END -->'
BUILD_START = '<!-- EXPERIENCE_ACTION_LOOP_BUILD_START -->'
BUILD_END = '<!-- EXPERIENCE_ACTION_LOOP_BUILD_END -->'


def optional_summary(root=ROOT, source=None):
    return study.optional_summary(root, source)


def metrics(d, lang, home=False):
    rows = [(f"{study.aggregate(d, phase, 'full')['artifact_accepted']}/3", study.phase_label(phase, lang)) for phase in study.PHASES]
    if home:
        return ''.join(f'<div class="latest-study-metric"><dt>{name}<span>{t("全接続のartifact受理", "Full-loop artifact acceptance", lang)}</span></dt><dd><span>{count}</span></dd></div>' for count, name in rows)
    return ''.join(f'<span><strong>{count}</strong>{name} / {t("全接続の受理", "full-loop acceptance", lang)}</span>' for count, name in rows)


def latest_home(d, lang):
    study.validate_summary(d); href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    return f'''<section class="latest-study" aria-labelledby="latest-study-title" data-source="{study.DATA_FILE}"><div class="latest-study-copy"><p class="latest-study-kicker">EXPERIENCE–ACTION LOOP / <time datetime="2026-10-30">2026-10-30</time></p><h2 id="latest-study-title">{t('過去の経験から、<br>次の作業を選べるか。', 'Can past experience<br>guide the next task?', lang)}</h2><p class="latest-study-summary">{t('JSON・HTML・ZIPを実際に作る課題を用意し、36の新しいAIコンテキストで比較しました。変更後の条件、以前の条件、未経験の条件を区別して作業できるかを調べました。', 'We set up tasks that actually create JSON, HTML and ZIP files, then compared choices made in 36 fresh AI contexts. We tested whether they could distinguish changed conditions, earlier conditions and conditions they had never encountered.', lang)}</p><a class="latest-study-link" href="{href}">{t('全36選択と4条件を読む', 'Read all 36 choices and four arms', lang)} ↗</a></div><div class="latest-study-results"><p class="latest-study-order">{t('実結果：各条件3件・全接続の受理', 'Recorded results: full-loop acceptance, three per condition', lang)}</p><dl class="latest-study-metrics">{metrics(d, lang, True)}</dl><p class="latest-study-boundary">{study.hero_finding(d, lang)} {t('JSON・HTML・ZIPは同じordering-policy機構の形式反復です。', 'JSON, HTML and ZIP repeat one ordering-policy mechanism.', lang)}</p><a class="latest-study-source" href="{study.DATA_FILE}">{t('全4条件・36件・公開evidence / JSON', 'All four arms, 36 rows and public evidence / JSON', lang)}</a></div></section>'''


def integrate_home(html, lang, d):
    if d is None:
        return html
    study.validate_summary(d)
    if len(LATEST.findall(html)) != 1:
        raise ValueError('Exactly one existing overview latest panel required')
    return LATEST.sub(lambda _: latest_home(d, lang), html, count=1)


def listing_card(d, lang):
    study.validate_summary(d); href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    return f'''<article class="study-card" data-study="experience-action-loop"><span class="study-status">STUDY / EXPERIENCE–ACTION / ENGINEERED HISTORIES</span><time datetime="2026-10-30">2026-10-30</time><h3><a href="{href}">{t('経験と条件付き判断を、次の実操作へ。', 'Connect experience and conditional judgment to a real operation.', lang)} ↗</a></h3><p>{t('3つの人工history、6教師context、3意味reviewer、36新規probe。full / hops0 / no_writeback / no_historyを、変更後R・旧条件に戻るL・未観測opaque profile Nで比較します。各phaseの12選択を実行前に固定し、各1回だけ実操作しました。', 'Three engineered histories, six teacher contexts, three semantic reviewers and 36 fresh probes compare full / hops0 / no_writeback / no_history under changed R, legacy-return L and unobserved opaque-profile N conditions. Each phase freezes twelve choices before one real operation per item.', lang)}</p><div class="study-stats">{metrics(d, lang)}</div><p>{study.finding(d, lang)}</p><p>{study.boundary(lang)}</p><p><a href="{study.REPLAY}README.md">{t('公開evidenceの検算', 'Saved-evidence verification', lang)} ↗</a> · <a href="{study.ZIP_FILE}" download>Verifier ZIP ↓</a></p></article>'''


def integrate_listing(html, lang, d):
    if d is None:
        return html
    study.validate_summary(d); html = CARD.sub('', html)
    hero = f'''<div class="status-strip"><span>{t('実tool経験から次の実操作までを収集', 'Recorded tool-experience-to-action loop', lang)}</span><small>UPDATED / 2026-10-30</small></div>
<div class="hero-metrics"><div class="metric"><strong>12</strong><span>{t('公開研究', 'Published studies', lang)}</span><small>2026-10-13 / 2026-10-30</small></div><div class="metric"><strong>3</strong><span>{t('人工history', 'Engineered histories', lang)}</span><small>{t('同じ機構の形式反復', 'Format repetitions of one mechanism', lang)}</small></div><div class="metric"><strong>36</strong><span>{t('新規probe context', 'Fresh probe contexts', lang)}</span><small>{t('4条件・3phase・各3件', 'Four arms × three phases × three items', lang)}</small></div></div>'''
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
        if count != 1 or text.count(start) != 1 or text.count(end) != 1:
            raise ValueError('README experience-action markers inconsistent')
        return text
    if text.count(anchor) != 1:
        raise ValueError('README experience-action anchor missing')
    return text.replace(anchor, block + anchor, 1)


def integrate_readme(text, d):
    if d is None:
        return text
    study.validate_summary(d); usage = study.schema.evidence_usage(d)
    rows = ['| Phase | Arm | Accepted | Builds | Abstentions | Rejected artifacts | Operation errors | Indirect returns | New-judgment returns |', '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for r in d['aggregates']:
        rows.append(f"| {r['phase']} | {r['arm']} | {r['artifact_accepted']}/{r['n']} | {r['builds']} | {r['abstentions']} | {r['rejected_artifacts']} | {r['operation_errors']} | {r['indirect_return_queries']} | {r['new_judgment_return_queries']} |")
    block = f'''{README_START}
## Experience to conditional judgment to another actual operation — 2026-10-30

[日本語]({study.BASE+study.STUDY}) / [English]({study.BASE+study.STUDY}en.html)

Actual tool experience is captured as condition-bound LRE judgments, indexed through native SHIORI, returned to fresh AI contexts, and followed by one actual operation. New judgments after a change are reindexed and checked for later return. Three independently engineered histories use JSON/HTML/ZIP as format repetitions of the same ordering-policy mechanism, not three distinct cognitive abilities. Six teacher contexts, three semantic-reviewer contexts and 36 fresh probe contexts remain separate units.

The four arms are full, hops0, no_writeback and no_history. R uses changed conditions; L returns to legacy conditions; N uses an unobserved opaque profile. All twelve choices within each phase freeze before one real operation per item. No probe repairs or outcome-driven reselection.

{chr(10).join(rows)}

{study.finding(d, 'en')} A returned judgment, a shared-feature path, accepted artifacts and appropriate abstention remain separate outcomes. The finite alias-to-shared-component network is engineered. `shared_feature_not_causal` denotes a shared-feature link, not a causal path. The dated pages retain all 36 actions, reasons, evidence, actual paths and outcomes, six teachers, and all 21 deduplicated public source messages. Empty-evidence abstention makes the empty-list quote check true; this is not evidence sufficiency. Independent audit separately assesses applicability, artifacts and protection.

{study.eligible_source_note(d, 'en')} The JSON field `all_quotes_exact` retains its original name and values; the public table labels it “Eligible original-source check” to make its narrow contract clear. False outcomes are retained without repair.

Evidence use, recalculated only from the 21 public sources and saved actions: {usage['eligible_nonempty_rows']} rows have nonempty eligible original-source evidence, {usage['empty_evidence_rows']} have empty evidence, and {usage['out_of_type_notice_rows']} cite out-of-type actual notices. There are {usage['eligible_tool_verbatim_quotes']} eligible original-tool verbatim quotations and {usage['eligible_native_judgment_verbatim_quotes']} eligible native-judgment quotations across {usage['native_judgment_citing_rows']} native-judgment-citing rows. Full returns the new judgment in {usage['full_new_judgment_return_rows']}/{usage['full_rows']} items. Return establishes availability; adoption/use of that judgment and its additional benefit are not established. Raw original-tool evidence has the same acceptance counts. The verifier treats raw `obs-*` / `tool:obs-*` and `cand-*` / `judgment:cand-*` as source lookup aliases only; it never rewrites original ACTION source IDs, bytes or hashes.

An author AI selected the vocabulary and an independent AI reviewed it. Full versus no_writeback compares incremental availability of new judgments; adding an episode can also change graph degree and scores. Native scores rank candidates, not confidence or probabilities of independent evidence. Automatic capture of all conversation, general Japanese understanding and production integration were not evaluated. Out-of-type notice quotations remain disclosed rather than being recoded as valid original tool/native-judgment evidence.

The 21 synthetic engineering checks are separate from the 36 actual probe choices. Provider/model/settings/tokens/compute metadata remains unverified and null. Roles use instruction-based read allowlists on a shared filesystem, not OS isolation. This evaluates isolated native components; full Wake, Emotion, biological brains, AGI, natural conversation, weight learning, psychological retention and unrestricted semantic understanding are not established. Tool receipts and judgments about the same event are not independent experiences.

[Public JSON]({study.BASE+study.DATA_FILE}) / [Saved-evidence verifier]({study.BASE+study.REPLAY}README.md) / [Verifier ZIP]({study.BASE+study.ZIP_FILE}). This public-data exception exposes only actual engineered-task tool outputs and AI judgments. It excludes private vendor source, native state, private repository source documents and conversations. The verifier checks disclosed schema, source hashes, quotation containment and arithmetic; it cannot rerun native execution, regenerate fresh AI choices, repeat the independent audit or independently prove every exported claim. Hashes identify local integrity, not external signatures or hardware attestation. All eleven earlier dated studies/data/replay/downloads and all four overview scroll stories retain their bytes.
{README_END}

'''
    text = _replace_block(text, README_START, README_END, block, '## Public and private scope\n')
    build = f'''{BUILD_START}
### Twelfth-study activation: audited experience-action public evidence

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_experience_action_loop.py --experience-action-loop /absolute/path/to/audited-public-export.json
```

The same `--experience-action-loop` flag is accepted by `tools/build_pages.py`; activate one new external study per command. Missing export creates no new publication, placeholder, numbers or conclusion. Before any publication write, the builder rejects extra schema keys, invalid context counts or profile bindings, source-text hash mismatches, misreported source-contract flags, graph/new-judgment flag mismatches, aggregate mismatches, unapproved audit, private absolute paths or changed protection boundaries. Actual source-contract deviations remain disclosed outcomes. It depends only on the audited public dataset and public builder/verifier code. The download has exactly evidence.json, verify.py, README.md and MANIFEST.json; its ZIP is deterministic. This is saved-evidence verification, not native replay. Repeat builds use the installed audited public JSON by default.
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


def prepare_updates(root=ROOT, source=None):
    export = study.read_export(root, source)
    if export is None:
        return {}
    d, raw = export; files, archive = study.public_bundle(d, raw)
    updates = {study.DATA_FILE: raw, study.STUDY + 'index.html': study.render('ja', d).encode('utf-8'),
        study.STUDY + 'en.html': study.render('en', d).encode('utf-8'),
        study.STUDY + 'experience-action-loop.css': study.CSS.encode('utf-8'), study.ZIP_FILE: archive}
    updates.update({study.REPLAY + name: value for name, value in files.items()})
    for name, lang in [('index.html', 'ja'), ('index.en.html', 'en')]:
        updates[name] = integrate_home((root / name).read_text(encoding='utf-8'), lang, d).encode('utf-8')
    for name, lang in [('results.html', 'ja'), ('results.en.html', 'en')]:
        updates[name] = integrate_listing((root / name).read_text(encoding='utf-8'), lang, d).encode('utf-8')
    updates['README.md'] = integrate_readme((root / 'README.md').read_text(encoding='utf-8'), d).encode('utf-8')
    updates['sitemap.xml'] = integrate_sitemap((root / 'sitemap.xml').read_text(encoding='utf-8'), d).encode('utf-8')
    return updates
