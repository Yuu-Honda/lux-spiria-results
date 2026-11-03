"""Plan the optional thirteenth study without touching prior dated studies.

Every input and integration anchor is validated before callers perform writes.
No audited input creates no files, folders, placeholders or public conclusions.
"""
from hashlib import sha256
from html import escape
import importlib.util
import io
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('judgment_transfer_public_builder', ROOT / 'tools/build_judgment_transfer.py')
study = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(study)
t = study.t
LATEST = re.compile(r'<section class="latest-study"(?=\s).*?</section>', re.S)
CARD = re.compile(r'<article class="study-card" data-study="judgment-transfer">.*?</article>', re.S)
README_START = '<!-- JUDGMENT_TRANSFER_STUDY_START -->'
README_END = '<!-- JUDGMENT_TRANSFER_STUDY_END -->'
BUILD_START = '<!-- JUDGMENT_TRANSFER_BUILD_START -->'
BUILD_END = '<!-- JUDGMENT_TRANSFER_BUILD_END -->'


def optional_summary(root=ROOT, source=None):
    return study.optional_summary(root, source)


def metrics(d, lang, home=False):
    values = [(f"{study.aggregate(d, 'same_version', arm)['accepted']}/6", study.label(arm, lang)) for arm in study.ARMS]
    if home:
        return ''.join('<div class="latest-study-metric"><dt>' + label + '<span>' + t('同じversionでの受理', 'Same-version acceptance', lang) + '</span></dt><dd><span>' + value + '</span></dd></div>' for value, label in values)
    return ''.join('<span><strong>' + value + '</strong>' + label + '</span>' for value, label in values)


def latest_home(d, lang):
    href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    return f'''<section class="latest-study" aria-labelledby="latest-study-title" data-source="{study.DATA_FILE}"><div class="latest-study-copy"><p class="latest-study-kicker">JUDGMENT TRANSFER / <time datetime="2026-11-03">2026-11-03</time></p><h2 id="latest-study-title">{t('保存した判断は、<br>次の作業に役立つか。', 'Does a saved judgment<br>help with the next task?', lang)}</h2><p class="latest-study-summary">{t('AIが作業結果から書いた判断を、次の作業に渡すと何が変わるか。識別子をまとめる課題と、設計した途中状態からのSQLite取込で比べました。', 'What changes when an AI’s judgment about earlier work is passed to the next task? We compared identifier grouping and SQLite imports from engineered partial states.', lang)}</p><a class="latest-study-link" href="{href}">{t('6対応pairと全36選択を読む', 'Read six matched pairs and all 36 choices', lang)} ↗</a></div><div class="latest-study-results"><p class="latest-study-order">{t('主比較：同じversion、各条件6件', 'Primary comparison: same version, six per arm', lang)}</p><dl class="latest-study-metrics">{metrics(d, lang, True)}</dl><p class="latest-study-boundary">{study.finding(d, lang)} {t('全36件が現在の3操作を一度に見られる診断を使いました。', 'All 36 probes used a diagnostic showing all three current operations.', lang)}</p><a class="latest-study-source" href="{study.DATA_FILE}">{t('3条件・2phase・全36件 / JSON', 'Three arms, two phases, all 36 rows / JSON', lang)}</a></div></section>'''


def integrate_home(html, lang, d):
    study.validate_summary(d)
    if len(LATEST.findall(html)) != 1:
        raise ValueError('Exactly one existing overview latest panel required')
    return LATEST.sub(lambda _: latest_home(d, lang), html, count=1)


def listing_card(d, lang):
    href = study.STUDY + ('index.html' if lang == 'ja' else 'en.html')
    return f'''<article class="study-card" data-study="judgment-transfer"><span class="study-status">STUDY / JUDGMENT TRANSFER / ENGINEERED HISTORIES</span><time datetime="2026-11-03">2026-11-03</time><h3><a href="{href}">{t('保存した判断は、次の作業に役立つか。', 'Does a saved judgment help with the next task?', lang)} ↗</a></h3><p>{t('識別子をまとめる課題と、設計した途中状態からのSQLite取込を各3history。教師役AIの36回の実行のあと、新しい36のAI contextで、原記録のみ／原記録＋AIが書いた判断／全原記録を最初に渡す3条件を比較。各phaseの18初期選択と18最終選択を、実操作前に固定しました。', 'Three histories each cover identifier grouping and SQLite imports from engineered partial states. After 36 teacher runs, 36 fresh AI contexts compare originals on request, originals + an AI-authored judgment, and all originals upfront. Each phase freezes 18 initial and 18 final choices before target effects.', lang)}</p><div class="study-stats">{metrics(d, lang)}</div><p>{study.finding(d, lang)}</p><p>{study.diagnostic_ceiling(d, lang)}</p><p>{study.boundary(lang)}</p></article>'''


def integrate_listing(html, lang, d):
    study.validate_summary(d)
    html = CARD.sub('', html)
    hero = f'''<div class="status-strip"><span>{t('原記録に、保存判断を加える比較', 'Comparing originals with an added saved judgment', lang)}</span><small>UPDATED / 2026-11-03</small></div>
<div class="hero-metrics"><div class="metric"><strong>13</strong><span>{t('公開研究', 'Published studies', lang)}</span><small>2026-10-13 / 2026-11-03</small></div><div class="metric"><strong>6</strong><span>{t('人工history', 'Engineered histories', lang)}</span><small>{t('2機構・各3history', 'Two mechanisms, three histories each', lang)}</small></div><div class="metric"><strong>36</strong><span>{t('新規probe context', 'Fresh probe contexts', lang)}</span><small>{t('3条件・2phase・各6件', 'Three arms × two phases × six items', lang)}</small></div></div>'''
    html, count = re.subn(r'<div class="status-strip">.*?</div>\n<div class="hero-metrics">.*?</div></div>', lambda _: hero, html, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Listing metadata anchor missing')
    anchor = re.search(r'<section class="section" id="studies"[^>]*><div class="section-heading">.*?</div>', html, re.S)
    if anchor is None:
        raise ValueError('Listing card anchor missing')
    return html[:anchor.end()] + listing_card(d, lang) + html[anchor.end():]


def replace_block(text, start, end, block, anchor):
    if start in text or end in text:
        if text.count(start) != 1 or text.count(end) != 1:
            raise ValueError('Judgment-transfer README markers inconsistent')
        text, count = re.subn(re.escape(start) + '.*?' + re.escape(end) + r'\n\n', lambda _: block, text, count=1, flags=re.S)
        if count != 1:
            raise ValueError('Judgment-transfer README block incomplete')
        return text
    if text.count(anchor) != 1:
        raise ValueError('Judgment-transfer README anchor missing')
    return text.replace(anchor, block + anchor, 1)


def integrate_readme(text, d, replay=False):
    pairs = ['| History | Mechanism | Raw only | Raw + judgment | All raw upfront | Paired difference |', '| --- | --- | ---: | ---: | ---: | ---: |']
    for pair in d['matched_pairs']:
        if pair['phase'] == 'same_version':
            upfront = next(r['accepted'] for r in d['rows'] if r['world_id'] == pair['world_id'] and r['phase'] == 'same_version' and r['arm'] == 'all_raw_upfront')
            pairs.append(f"| {pair['world_id']} | {pair['mechanism']} | {int(pair['raw_only_accepted'])} | {int(pair['judgment_accepted'])} | {int(upfront)} | {pair['accepted_difference']} |")
    block = f'''{README_START}
## Does a saved judgment help with the next task? — 2026-11-03

[日本語]({study.BASE+study.STUDY}) / [English]({study.BASE+study.STUDY}en.html)

Six engineered histories cover two mechanisms, three each: grouping by identifier identity and SQLite imports from staged partial states. These partial states are engineered inputs, not observed process crashes. Six teacher contexts run three cases over two rounds (36 training calls), then their own judgments about work results undergo native LRE capture, review and readback. Both retained and deferred text + status pass through to the treatment. This isolates judgment-candidate/native-status availability; SHIORI ranking is not used. Saved text is transferred; model weights are not updated.

Thirty-six fresh probe contexts cover same_version/changed_version × raw_only/raw_plus_judgment/all_raw_upfront × six histories. Each phase freezes all 18 initial POLICY choices before feedback, offers identical six-original rights and one current toy diagnostic, then freezes all 18 FINAL choices in those same contexts before one target operation or abstention per item. Source order and rights match. All-originals-upfront is a diagnostic comparison, not a mathematical upper bound.

{chr(10).join(pairs)}

{study.finding(d, 'en')} The primary contrast is paired accepted real operations in the same version. Changed-version stale-only initial/final choices, diagnostic requests, final success and abstentions are separate outcomes. All 36 actual POLICY/FINAL reasons, predictions, typed quotations and false checks remain disclosed. Empty evidence remains citation status `none`, not a successful source check. A valid prior state after an SQL rollback is separate from operation completion; acceptance requires both.

{study.diagnostic_ceiling(d, 'en')}

{study.io_finding(d, 'en')} {study.io_exceptions(d, 'en')}

“Changed choice” counts only changes from a nonnull initial operation; initial null → selected final operation is excluded. Zero changes therefore does not imply no feedback-driven choice. Teacher practice acceptance is {sum(r['accepted'] for r in d['teacher_rounds'] if r['round'] == 1)}/18 → {sum(r['accepted'] for r in d['teacher_rounds'] if r['round'] == 2)}/18 on the same practice cases, rather than evidence of new-case transfer. Final evidence has {sum(r['exact_judgment_citations'] for r in d['rows'])} exact saved-judgment quotation(s); literal citation does not establish causal adoption or an accuracy gain.

Reads, diagnostics and initial + feedback packet bytes are secondary delivered-model I/O. They do not measure backend integrity disk reads, tokens, compute, speed or cost, and exclude judgment construction/training amortization. Provider/model/settings/tokens/compute are null. Six matched histories generated with one seed are not 36 independent experiences. A held-out cases replace numbers/IDs within the same eight-key relations, not new structures.

{study.boundary('en')} Roles use instruction-based allowlists on a shared filesystem, not OS isolation. Hashes identify local integrity, not external signatures or hardware attestation. The public verifier checks disclosed arithmetic, source-text hashes and typed quotation availability; it does not repeat the independent audit, private native execution or fresh AI choices. [Public JSON]({study.BASE+study.DATA_FILE}). Twelve prior studies/data/replay/ZIP publications and all four scroll stories retain their bytes.
{README_END}

'''
    text = replace_block(text, README_START, README_END, block, '## Public and private scope\n')
    build = f'''{BUILD_START}
### Thirteenth-study activation: audited judgment-transfer export

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/build_judgment_transfer.py --judgment-transfer /absolute/path/to/audited-public-export.json
```

The same flag is accepted by `tools/build_pages.py` through an isolated publication plan; do not combine it with another activation flag. No audited input means no new files, placeholders, numbers or conclusions. Before writes, strict validation checks all 36 records, 18 aggregates, 12 pairs, the six-pair primary contrast, typed quotation availability/exactness, disclosed source hashes, canonical packet I/O, native receipt bindings, audit approval and public protection boundaries. Only the overview latest panel, results listing, README and sitemap accompany the new dated study. Earlier dated study/data/replay/download bytes and scroll animation CSS/JS are preserved.
{BUILD_END}

'''
    return replace_block(text, BUILD_START, BUILD_END, build, '## Preservation\n')


def integrate_sitemap(text):
    if text.count('</urlset>') != 1:
        raise ValueError('Sitemap closing anchor missing')
    for url in (study.BASE + study.STUDY, study.BASE + study.STUDY + 'en.html'):
        if '<loc>' + url + '</loc>' not in text:
            text = text.replace('</urlset>', '  <url><loc>' + escape(url) + '</loc></url>\n</urlset>', 1)
    return text


def public_bundle(d, raw, replay=None):
    """Build a deterministic verifier package; code replay is separately audited."""
    files = {'evidence.json': raw, 'verify.py': (ROOT / 'tools/judgment_transfer_schema.py').read_bytes()}
    description = '''# Judgment transfer: saved public records, 2026-11-03

Python 3 standard library only. Run `python3 -B verify.py evidence.json`.
The verifier checks the strict public schema, all 36 POLICY/FINAL choices,
18 phase/arm/mechanism aggregates, 12 matched pairs, six-pair primary contrast,
source-text hashes, original availability, typed quotes and disclosed model I/O.
It checks package file hashes when MANIFEST.json is alongside evidence.json.
Optional quotations remain optional: empty evidence has citation status none;
false checks remain false. Exact quotation is not semantic validity.

This package has no private vendor source, native state, private repository
source documents or conversations, credentials, or fresh AI choices. It does
not rerun native LRE capture/review/readback or repeat the independent audit.
Native receipt hashes identify retained local provenance, not external signatures.
Both retained and deferred text + status reach treatment; SHIORI ranking is not
used. This is an engineered two-mechanism comparison of six matched histories
generated with one seed, not 36 independent experiences or new-structure
generalization. A held-out cases keep the same eight-key relations.

Read/diagnostic counts and packet bytes measure delivered model I/O, not total
backend integrity disk reads, tokens, compute, speed or cost. Judgment building,
training and amortization are excluded. Provider/model/settings/tokens/compute
remain null. Roles use instruction allowlists on a shared filesystem, not OS
isolation. Full Wake, Emotion, brains, AGI, natural conversation and weight
learning are not evaluated. Earlier published study results remain unchanged.

Read the Japanese/English dated study for all actual outcomes and boundaries.
The repository LICENSE applies; no license to private dependencies is granted.
'''
    if replay is not None:
        folder = Path(replay)
        expected = {'common.py', 'world_engine.py'}
        if folder.is_symlink() or not folder.is_dir() or {p.name for p in folder.iterdir()} != expected:
            raise ValueError('Audited replay code pack must contain exactly common.py and world_engine.py')
        for name, label in [('common.py', 'common_py_sha256'), ('world_engine.py', 'world_engine_py_sha256')]:
            path = folder / name
            if path.is_symlink() or not path.is_file():
                raise ValueError('Audited replay source must be a regular file')
            value = path.read_bytes()
            if d['hashes'].get(label) != sha256(value).hexdigest():
                raise ValueError('Audited own-authored replay code hash differs: ' + name)
            files[name] = value
        files['worlds.json'] = (study.schema.canonical({'schema': 'judgment-transfer-worlds.v1', 'worlds': d['worlds']}) + '\n').encode('utf-8')
        files['plans.json'] = (study.schema.canonical([{'assignment_id': r['assignment_id'], 'world_id': r['world_id'], 'phase': r['phase'], 'final': r['final'], 'target_artifact_sha256': r['target_artifact_sha256']} for r in d['rows']]) + '\n').encode('utf-8')
        files['replay.py'] = (ROOT / 'tools/judgment_transfer_replay.py').read_bytes()
        description += '''
## Public saved-work replay

Run `python3 -B replay.py evidence.json`. Only the disclosed saved FINAL choices
are executed, into fresh temporary directories which are removed afterwards.
Abstentions remain abstentions. The unchanged, own-authored common.py and
world_engine.py run actual grouping and actual transactional SQLite imports.
Semantic state validity, operation completion, acceptance, operation status and
artifact.json SHA256 are compared with saved actual target evaluations. Missing
original evaluations are reported separately rather than counted as matches.
SQLite binary SHA256 and timestamped result/manifest hashes are not compared.
The world configurations and all 36 frozen plans/artifact digests are also
provided as worlds.json and plans.json. This public replay is distinct from the
original trial: it makes no new AI choices and invokes no native memory code.

Trust the downloaded replay.py and publisher before running Python code. The
stdlib-only bootstrap checks every package file and evidence code pin before
loading the bundled schema verifier. That verifier validates the whole evidence
and manifest before captured, verified common/engine bytes execute. Hashes prove
internal consistency, not publisher identity, safety of arbitrary Python or an
external signature. This package is not a sandbox for untrusted code.
'''
    files['README.md'] = description.encode('utf-8')
    manifest = {'schema': 'judgment-transfer-public-package.v1', 'replay': replay is not None,
        'files': {name: {'bytes': len(value), 'sha256': sha256(value).hexdigest()} for name, value in sorted(files.items())}}
    files['MANIFEST.json'] = (study.schema.canonical(manifest) + '\n').encode('utf-8')
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, value in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, value, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return files, archive.getvalue()


def prepare_updates(root=ROOT, source=None, replay=None):
    export = study.read_export(root, source)
    if export is None:
        if replay is not None:
            raise ValueError('Replay requires an audited public export')
        return {}
    d, raw = export
    # Installed replay sources can be reused; new copies only enter through the
    # explicit two-file audit pack. Native/private dependencies never enter here.
    if replay is None and (root / study.REPLAY / 'replay.py').is_file():
        for name, label in [('common.py', 'common_py_sha256'), ('world_engine.py', 'world_engine_py_sha256')]:
            path = root / study.REPLAY / name
            if path.is_symlink() or not path.is_file() or sha256(path.read_bytes()).hexdigest() != d['hashes'].get(label):
                raise ValueError('Installed audited replay source hash differs: ' + name)
        # public_bundle expects only two source files, so source bytes are read
        # from an explicit audited pack on initial activation. Preserve installed
        # package bytes after that rather than copying from the research root.
        names = {'evidence.json', 'verify.py', 'README.md', 'MANIFEST.json', 'worlds.json', 'plans.json', 'common.py', 'world_engine.py', 'replay.py'}
        study.schema.verify_bundle(root / study.REPLAY)
        files = {name: (root / study.REPLAY / name).read_bytes() for name in names}
        if files['evidence.json'] != raw:
            raise ValueError('Installed replay evidence differs; activate an audited code pack again')
        archive = (root / study.ZIP_FILE).read_bytes()
        replay_enabled = True
    else:
        files, archive = public_bundle(d, raw, replay)
        replay_enabled = replay is not None
    updates = {study.DATA_FILE: raw, study.STUDY + 'index.html': study.render('ja', d, replay_enabled).encode('utf-8'),
        study.STUDY + 'en.html': study.render('en', d, replay_enabled).encode('utf-8'),
        study.STUDY + 'judgment-transfer.css': study.CSS.encode('utf-8'), study.ZIP_FILE: archive}
    updates.update({study.REPLAY + name: value for name, value in files.items()})
    for filename, lang in [('index.html', 'ja'), ('index.en.html', 'en')]:
        updates[filename] = integrate_home((root / filename).read_text(encoding='utf-8'), lang, d).encode('utf-8')
    for filename, lang in [('results.html', 'ja'), ('results.en.html', 'en')]:
        updates[filename] = integrate_listing((root / filename).read_text(encoding='utf-8'), lang, d).encode('utf-8')
    updates['README.md'] = integrate_readme((root / 'README.md').read_text(encoding='utf-8'), d, replay_enabled).encode('utf-8')
    updates['sitemap.xml'] = integrate_sitemap((root / 'sitemap.xml').read_text(encoding='utf-8')).encode('utf-8')
    return updates
