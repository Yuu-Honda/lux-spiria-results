"""Build the dated follow-up from the independently audited public export."""

from argparse import ArgumentParser
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://yuu-honda.github.io/lux-spiria-results/'
DATE = '2026-11-27'
STUDY = f'studies/{DATE}-no-diagnostic/'
DATA = f'data/no-diagnostic-{DATE}.json'
PRIOR = 'data/judgment-transfer-2026-11-03.json'
PRIOR_STUDY = 'studies/2026-11-03-judgment-transfer/'
PRIOR_ENGINE = 'experiments/judgment-transfer-2026-11-03/world_engine.py'
SCHEMA = 'lux-spiria-no-diagnostic.v1'
MECHANISMS = {'W01': 'A', 'W02': 'A', 'W04': 'B', 'W05': 'B'}
ARMS = ('raw_only', 'raw_plus_judgment')
PHASES = ('same_version', 'changed_version')
SITE_MARKER = re.compile(r'<aside class="finding-callout" id="no-diagnostic-followup"[^>]*>.*?</aside>\n', re.S)
README_START = '<!-- NO_DIAGNOSTIC_STUDY_START -->'
README_END = '<!-- NO_DIAGNOSTIC_STUDY_END -->'


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key {key!r}')
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f'Invalid JSON constant {value}')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def exact_fields(value, fields, label):
    require(type(value) is dict and value.keys() == set(fields.split()), f'Unexpected {label} fields')


def digest(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def valid_text(value):
    return isinstance(value, str) and bool(value.strip())


def validated_export(data, prior_bytes):
    exact_fields(data, 'schema date protocol_sha256 prior_public_sha256 independent_histories contexts case_pairs rows audit boundaries', 'export')
    require(data['schema'] == SCHEMA and data['date'] == DATE, 'Wrong follow-up schema or date')
    require(type(data['independent_histories']) is int and data['independent_histories'] == 4, 'Expected four matched histories')
    require(type(data['contexts']) is int and data['contexts'] == 16, 'Expected sixteen contexts')
    require(digest(data['protocol_sha256']), 'Invalid protocol digest')
    require(data['prior_public_sha256'] == sha256(prior_bytes).hexdigest(), 'Original public export digest differs')
    exact_fields(data['audit'], 'status sha256', 'audit')
    require(data['audit']['status'] == 'approved' and digest(data['audit']['sha256']), 'Audit is required')
    require(type(data['boundaries']) is list and data['boundaries'] and all(map(valid_text, data['boundaries'])), 'Expected study boundaries')

    prior = json.loads(prior_bytes)
    old_worlds = {world['world_id']: world for world in prior['worlds']}
    cases = {}
    require(type(data['case_pairs']) is list and len(data['case_pairs']) == 4, 'Expected four case pairs')
    for case in data['case_pairs']:
        exact_fields(case, 'world_id mechanism contract_text input v1_acceptable_operations v2_acceptable_operations', 'case pair')
        world = case['world_id']
        require(world in MECHANISMS and world not in cases and case['mechanism'] == MECHANISMS[world], 'Unexpected case history or mechanism')
        require(valid_text(case['contract_text']) and type(case['input']) is dict, 'Invalid case input')
        allowed = set(old_worlds[world]['operations'])
        for version in ('v1', 'v2'):
            acceptable = case[f'{version}_acceptable_operations']
            require(type(acceptable) is list and len(acceptable) == 1 and acceptable[0] in allowed, 'Expected one valid operation for each version')
        require(case['v1_acceptable_operations'] != case['v2_acceptable_operations'], 'Expected changed acceptable operation')
        cases[world] = case

    historical_ids = {}
    for row in prior['rows']:
        world = row['world_id']
        if world not in cases or row['phase'] != 'same_version' or row['arm'] != 'raw_plus_judgment':
            continue
        packet = row['task']
        original_ids = {entry['source_id'] for entry in packet['original_sources']}
        judgment = packet['initial_judgment']
        require(len(original_ids) == 6 and judgment['native_status'] == 'retained', 'Unexpected original evidence or judgment status')
        historical_ids[world] = (original_ids, judgment['source_id'])

    seen_cells = set()
    seen_ids = set()
    require(type(data['rows']) is list and len(data['rows']) == 16, 'Expected sixteen choice records')
    for row in data['rows']:
        exact_fields(row, 'id world_id mechanism phase arm final accepted state_valid process_completed status old_only_choice task_sha256 final_sha256 artifact_sha256', 'choice record')
        world, phase, arm = row['world_id'], row['phase'], row['arm']
        cell = world, phase, arm
        require(world in cases and row['mechanism'] == MECHANISMS[world] and phase in PHASES and arm in ARMS and cell not in seen_cells, 'Unexpected or repeated experiment cell')
        require(isinstance(row['id'], str) and re.fullmatch(r'[\w-]{1,64}', row['id'], re.ASCII) and row['id'] not in seen_ids, 'Unexpected or repeated choice identifier')
        seen_cells.add(cell)
        seen_ids.add(row['id'])
        require(digest(row['task_sha256']) and digest(row['final_sha256']), 'Invalid task or choice digest')

        final = row['final']
        exact_fields(final, 'decision operation reason historical_source_ids current_mapping', 'final choice')
        execute = final['decision'] == 'execute'
        require(execute or final['decision'] == 'abstain', 'Unrecognized choice')
        allowed = set(old_worlds[world]['operations'])
        require(final['operation'] in allowed if execute else final['operation'] is None, 'Choice is outside the action catalog')
        require(valid_text(final['reason']) and final['current_mapping'] in ('known', 'uncertain'), 'Invalid choice reason or mapping assessment')
        originals, judgment = historical_ids[world]
        allowed_sources = originals | ({judgment} if arm == 'raw_plus_judgment' else set())
        ids = final['historical_source_ids']
        require(type(ids) is list and len(ids) <= 3 and len(set(ids)) == len(ids) and set(ids) <= allowed_sources, 'Choice cites too many or unavailable sources')

        require(type(row['accepted']) is bool and type(row['old_only_choice']) is bool, 'Outcomes must be boolean')
        require(all(row[key] is None or type(row[key]) is bool for key in ('state_valid', 'process_completed')), 'Invalid work validation')
        require(row['artifact_sha256'] is None or digest(row['artifact_sha256']), 'Invalid artifact digest')
        if execute:
            require(row['status'] in (None, 'success', 'sql_error_rolled_back'), 'Unknown worker status')
            require(row['status'] is None or row['process_completed'] is not None, 'Missing worker validation')
        else:
            require(all(row[key] is None for key in ('state_valid', 'process_completed', 'status', 'artifact_sha256')), 'Abstention has a work result')
        completed = row['state_valid'] is True and row['process_completed'] is True
        require(row['accepted'] == (execute and completed), 'Acceptance does not match worker validation')
        require(not row['accepted'] or digest(row['artifact_sha256']), 'Accepted operation has no artifact digest')
        version = 'v1' if phase == 'same_version' else 'v2'
        current = set(cases[world][f'{version}_acceptable_operations'])
        old_only = set(cases[world]['v1_acceptable_operations']) - current
        require(row['old_only_choice'] == (execute and final['operation'] in old_only), 'Old-only operation flag differs')
        require(not row['accepted'] or final['operation'] in current, 'Accepted operation is outside the frozen acceptable set')
    return data


def choose(lang, ja, en):
    return ja if lang == 'ja' else en


def title(lang):
    return choose(lang, '動作を試せないとき、保存した判断は役立つか', 'Does saved judgment help when you cannot test the operations?')


def arm_label(lang, arm):
    if arm == 'raw_only':
        return choose(lang, '原記録のみ', 'Originals only')
    return choose(lang, '原記録＋保存判断', 'Originals + saved judgment')


def yes_no(lang, value):
    if value is None:
        return '—'
    if value:
        return choose(lang, 'はい', 'Yes')
    return choose(lang, 'いいえ', 'No')


def primary(data):
    return [sum(row['accepted'] for row in data['rows'] if row['phase'] == 'same_version' and row['arm'] == arm) for arm in ARMS]


def finding(data, lang):
    original, judgment = primary(data)
    diff = judgment - original
    signed = f'{diff:+d}' if diff else '0'
    return choose(lang,
        f'同じ版では、原記録のみで {original}/4 件、保存判断ありで {judgment}/4 件が受理されました。4履歴の比較で、受理数の差は {signed} 件です。',
        f'On the unchanged version, {original}/4 operations passed with originals alone and {judgment}/4 with the saved judgment. The difference across the four matched histories was {signed} accepted operations.')


def table(caption, headers, rows):
    columns = ''.join(f'<th scope="col">{escape(str(value))}</th>' for value in headers)
    body = ''.join('<tr><th scope="row">' + escape(str(row[0])) + '</th>' + ''.join(f'<td>{escape(str(value))}</td>' for value in row[1:]) + '</tr>' for row in rows)
    caption = escape(caption)
    return f'<div class="table-wrap" role="region" aria-label="{caption}" tabindex="0"><table><caption>{caption}</caption><thead><tr>{columns}</tr></thead><tbody>{body}</tbody></table></div>'


def detail(label, value):
    text = escape(json.dumps(value, ensure_ascii=False, indent=2))
    return f'<details><summary>{escape(label)}</summary><pre>{text}</pre></details>'


def section(slug, label, content):
    return f'<section class="section" id="{slug}" aria-labelledby="{slug}-title"><div class="section-heading"><h2 id="{slug}-title">{label}</h2></div>{content}</section>'


def installed_data(root=ROOT):
    export = read_export(root)
    return export[0] if export else None


def read_export(root, source=None):
    path = Path(source) if source else root / DATA
    if source is None and not path.exists() and not path.is_symlink():
        return None
    require(path.is_file() and not path.is_symlink(), 'Export must be a regular file')
    raw = path.read_bytes()
    parsed = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object, parse_constant=reject_constant)
    return validated_export(parsed, (root / PRIOR).read_bytes()), raw


def phase_label(lang, phase):
    return choose(lang, '同じ版', 'Unchanged version') if phase == 'same_version' else choose(lang, '変更後', 'Changed version')


def operation_label(lang, final):
    return final['operation'] if final['decision'] == 'execute' else choose(lang, '棄権', 'Abstained')


def mapping_label(lang, final):
    return choose(lang, '十分', 'Sufficient') if final['current_mapping'] == 'known' else choose(lang, '不確か', 'Uncertain')


def changed_finding(data, lang):
    rows = [row for row in data['rows'] if row['phase'] == 'changed_version']
    abstained = sum(row['final']['decision'] == 'abstain' for row in rows)
    if abstained == len(rows):
        return choose(lang,
            '変更後の版では両条件とも4件すべてが棄権し、実行は0件でした。',
            'After the version change, all four contexts in each condition abstained. No operation ran.')
    return choose(lang,
        f'変更後の版では、8件のうち{abstained}件が棄権し、{len(rows) - abstained}件が操作を選びました。',
        f'After the version change, {abstained} of the eight contexts abstained and {len(rows) - abstained} selected an operation.')


def comparison(data, lang):
    rows = {(row['world_id'], row['phase'], row['arm']): row for row in data['rows']}
    pairs = []
    for world, mechanism in MECHANISMS.items():
        original = rows[world, 'same_version', 'raw_only']['accepted']
        judgment = rows[world, 'same_version', 'raw_plus_judgment']['accepted']
        label = choose(lang, 'キーのグループ化', 'Key grouping') if mechanism == 'A' else choose(lang, 'SQLite取り込み', 'SQLite import')
        pairs.append((world, label, yes_no(lang, original), yes_no(lang, judgment), f'{int(judgment) - int(original):+d}'))
    columns = (choose(lang, '履歴', 'History'), choose(lang, '課題の仕組み', 'Mechanism'), arm_label(lang, 'raw_only'), arm_label(lang, 'raw_plus_judgment'), choose(lang, '受理の差', 'Difference'))
    return table(choose(lang, '同じ版での成果物の受理', 'Artifact acceptance on the unchanged version'), columns, pairs)


def changed_results(data, lang):
    summaries = []
    for arm in ARMS:
        rows = [row for row in data['rows'] if row['phase'] == 'changed_version' and row['arm'] == arm]
        summaries.append((arm_label(lang, arm), sum(row['accepted'] for row in rows),
            sum(row['final']['decision'] == 'abstain' for row in rows), sum(row['old_only_choice'] for row in rows),
            sum(row['final']['current_mapping'] == 'uncertain' for row in rows)))
    columns = (choose(lang, '条件', 'Condition'), choose(lang, '受理', 'Accepted'), choose(lang, '棄権', 'Abstained'),
        choose(lang, '旧版でのみ正しい操作', 'Old-version-only choice'), choose(lang, '不確かと回答', 'Reported uncertainty'))
    paragraph = choose(lang,
        '変更後の対応を示す資料は渡していません。受理には偶然の一致が含まれ得ます。「不確か」はAI自身の申告です。両条件で、根拠が足りなければ棄権するよう明示しました。棄権の件数は、その明示的な指示がある条件での結果です。各列の件数は重なり得ます。',
        'The packets omitted evidence of the changed mapping. A successful choice could match by chance. Uncertainty is self-reported. Both conditions explicitly instructed the AI to abstain if the available evidence did not justify an operation. The abstentions reflect behavior under that instruction. Counts can overlap.')
    return f'<p>{paragraph}</p>' + table(choose(lang, '変更後の版・各条件4件', 'Changed version · four choices per condition'), columns, summaries)


def observed_rows(data, lang):
    rows = []
    details = []
    for row in data['rows']:
        final = row['final']
        rows.append((f"{row['id']} / {row['world_id']}", phase_label(lang, row['phase']), arm_label(lang, row['arm']),
            operation_label(lang, final), yes_no(lang, row['process_completed']), yes_no(lang, row['state_valid']),
            yes_no(lang, row['accepted']), mapping_label(lang, final)))
        details.append(detail(f"{row['id']} · {row['world_id']} · {phase_label(lang, row['phase'])} · {arm_label(lang, row['arm'])}", row))
    columns = (choose(lang, '選択 / 履歴', 'Choice / history'), choose(lang, '版', 'Version'), choose(lang, '条件', 'Condition'),
        choose(lang, '操作', 'Operation'), choose(lang, '作業完了', 'Completed'), choose(lang, '状態適合', 'Valid state'),
        choose(lang, '受理', 'Accepted'), choose(lang, '根拠の自己評価', 'Self-rated evidence'))
    caption = choose(lang, '全16件の選択と実行結果', 'All sixteen choices and work results')
    note = choose(lang, '成果物の受理には作業完了と状態の適合が必要です。棄権した場合に実作業はありません。判定が得られなかった項目も「—」で示します。',
        'Acceptance requires a completed operation and a valid state. Abstention skips execution. A dash marks fields without an observed result.')
    return table(caption, columns, rows) + f'<p class="note">{note}</p>' + '\n'.join(details)


def render(data, lang):
    headline = title(lang)
    description = choose(lang,
        '現在の動作を試せない条件で、同じ原記録に保存判断を加えると成果物が変わるかを比べました。4履歴、16の新しいAIコンテキスト。',
        'Four matched histories and 16 fresh AI contexts compared the same originals with and without saved judgments, with current-operation tests unavailable.')
    filename = 'index.html' if lang == 'ja' else 'en.html'
    results = '../../results.html' if lang == 'ja' else '../../results.en.html'
    prior_page = '../../' + PRIOR_STUDY + filename
    ja_current = ' aria-current="page"' if lang == 'ja' else ''
    en_current = ' aria-current="page"' if lang == 'en' else ''
    canonical = BASE + STUDY + ('' if lang == 'ja' else 'en.html')
    manifest = 'site.webmanifest' if lang == 'ja' else 'site.en.webmanifest'
    design = choose(lang,
        '11月3日の実験では、全36件が現行の3操作を確認できる診断を使いました。今回は、キーのグループ化とSQLite取り込みから履歴ID順で先頭の2つずつを使い、現行の診断を用意しませんでした。両条件に同じ6件の過去の実行記録を最初から渡し、一方にはLREに保存されていた判断文とその保持状態も渡しました。各履歴で、新しい課題の入力と契約は版が変わっても同じです。AIが操作または棄権を選び、全16件を固定した後、選んだ操作を一度ずつ実行しました。',
        'In the November 3 study, all 36 contexts used a diagnostic that showed all three current operations. This follow-up used the first two histories by ID for key grouping and for SQLite import, with current-operation diagnostics unavailable. Both conditions received the same six original execution records upfront. One condition also received the saved LRE judgment and its retained status. Each history used the same new input and contract across versions. The experiment froze all 16 AI choices before executing each selected operation once.')
    limit = choose(lang,
        '差は再利用した4履歴における記述的な比較です。前回とは課題とAIコンテキストも異なるため、実験間の成績差を診断の有無だけに帰すことはできません。原記録は両条件に全件渡しており、原文取得の削減、速度、費用は計測していません。',
        'The result describes these four reused histories. The earlier study also differed in tasks and AI contexts, so any difference between studies has multiple possible causes. Both conditions received all original records. Retrieval savings, speed and cost were unmeasured.')
    methods = section('design', choose(lang, '同じ原記録を渡して比べる', 'Comparing the same original records'),
        f'<p>{design}</p><p><a href="{prior_page}">{choose(lang, "11月3日の実験記録", "Read the November 3 study")}</a></p>')
    pair_section = section('same-version', choose(lang, '同じ版での成果物', 'Artifacts on the unchanged version'), comparison(data, lang))
    changed_section = section('changed-version', choose(lang, '版が変わったときの選択', 'Choices after a version change'), changed_results(data, lang))
    records = section('choices', choose(lang, '実際の選択と根拠', 'Actual choices and reasons'), observed_rows(data, lang))
    for case in data['case_pairs']:
        records += detail(choose(lang, f"入力・受理される操作 / {case['world_id']}", f"Input and acceptable operations / {case['world_id']}"), case)
    evidence = f'''<p>{limit}</p>
<p><a href="../../{DATA}" download>{choose(lang, '公開データ（JSON）', 'Public data (JSON)')}</a> · <a href="../../{PRIOR}">{choose(lang, '過去の原記録IDと保存判断（JSON）', 'Historical source IDs and saved judgments (JSON)')}</a> · <a href="../../{PRIOR_ENGINE}">{choose(lang, '今回も使った公開エンジン', 'Archived engine reused in this study')}</a></p>
{detail(choose(lang, '手順と監査のハッシュ', 'Protocol and audit digests'), {'protocol_sha256': data['protocol_sha256'], 'prior_public_sha256': data['prior_public_sha256'], 'audit': data['audit']})}'''
    limits = section('evidence', choose(lang, 'この比較の範囲と公開データ', 'Scope and public data'), evidence)
    return f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(headline)} — LUX SPIRIA Results</title>
<meta name="description" content="{escape(description)}">
<meta name="theme-color" content="#090d12">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="ja" href="{BASE + STUDY}">
<link rel="alternate" hreflang="en" href="{BASE + STUDY}en.html">
<link rel="alternate" hreflang="x-default" href="{BASE + STUDY}">
<link rel="icon" type="image/png" href="../../assets/favicon-32.png"><link rel="apple-touch-icon" href="../../assets/apple-touch-icon.png">
<link rel="manifest" href="../../{manifest}">
<link rel="stylesheet" href="../../site.css">
<style>
.study-detail details {{ margin-block: .7rem; padding: .8rem 1rem; border: 1px solid var(--line); background: var(--panel-soft) }}
.study-detail summary {{ cursor: pointer; overflow-wrap: anywhere }}
.study-detail pre {{ white-space: pre-wrap; overflow-wrap: anywhere; font: .8rem/1.6 var(--mono); color: var(--muted) }}
.study-detail p + p {{ margin-top: .7rem }}
</style>
</head>
<body><a class="skip-link" href="#main">{choose(lang, '本文へ', 'Skip to content')}</a><div class="page">
<header class="masthead">
<a class="brand" href="{results}" aria-label="LUX SPIRIA Results"><img src="../../assets/lux-symbol.png" alt="" width="44" height="44"><span class="brand-wordmark">LUX SPIRIA<span class="brand-subtitle">RESEARCH RESULTS</span></span></a>
<nav aria-label="{choose(lang, '主なページ', 'Main navigation')}"><a href="{results}#studies">{choose(lang, '研究結果', 'Studies')}</a><a href="#choices">{choose(lang, '全16件', 'All 16 choices')}</a><span class="lang"><a href="index.html" lang="ja" hreflang="ja"{ja_current}>日本語</a><span aria-hidden="true">/</span><a href="en.html" lang="en" hreflang="en"{en_current}>EN</a></span></nav>
</header>
<main id="main" class="study-detail">
<section class="study-hero"><time datetime="{DATE}">{DATE}</time><h1>{escape(headline)}</h1><p class="lead">{escape(description)}</p></section>
<div class="finding-callout"><p>{finding(data, lang)}</p><p>{changed_finding(data, lang)}</p></div>
{methods}
{pair_section}
{changed_section}
{records}
{limits}
</main>
<footer class="footer"><nav aria-label="{choose(lang, '資料と規約', 'Resources and terms')}"><a href="{results}">{choose(lang, '研究結果', 'Study archive')}</a><a href="../../LICENSE">License / LSP-1.0</a></nav></footer>
</div></body></html>
'''


def integrate_listing(html, lang, data):
    html = SITE_MARKER.sub('', html)
    anchor = re.search(r'<section class="section" id="studies"[^>]*><div class="section-heading">.*?</div>', html, re.S)
    require(anchor is not None, 'Study list anchor missing')
    number = html.count('<article class="study-card"') + 1
    link = STUDY + ('index.html' if lang == 'ja' else 'en.html')
    panel = f'''<aside class="finding-callout" id="no-diagnostic-followup" aria-labelledby="no-diagnostic-followup-title"><time datetime="{DATE}">{DATE}</time><h2 id="no-diagnostic-followup-title"><a href="{link}">{title(lang)} ↗</a></h2><p>{finding(data, lang)}</p></aside>
'''
    html = html[:anchor.end()] + panel + html[anchor.end():]
    hero = f'''<div class="status-strip"><span>{choose(lang, '現行の操作を試せない条件での追試', 'Follow-up without current-operation tests')}</span><small>UPDATED / {DATE}</small></div>
<div class="hero-metrics"><div class="metric"><strong>{number}</strong><span>{choose(lang, '公開研究', 'Published studies')}</span><small>2026-10-13 / {DATE}</small></div><div class="metric"><strong>4</strong><span>{choose(lang, '比較した履歴', 'Matched histories')}</span><small>{choose(lang, '2機構・各2履歴', 'Two mechanisms, two histories each')}</small></div><div class="metric"><strong>16</strong><span>{choose(lang, '新規AIコンテキスト', 'Fresh AI contexts')}</span><small>{choose(lang, '2条件・2種類の版・各4件', 'Two conditions × two versions × four histories')}</small></div></div>'''
    html, changed = re.subn(r'<div class="status-strip">.*?</div>\n<div class="hero-metrics">.*?</div></div>', lambda _: hero, html, count=1, flags=re.S)
    require(changed == 1, 'Study count anchor missing')
    return html


def integrate_readme(text, data):
    block = f'''{README_START}
## Saved judgment without a current-operation diagnostic — {DATE}

[日本語]({BASE + STUDY}) / [English]({BASE + STUDY}en.html) / [Public JSON]({DATA})

Sixteen fresh AI contexts compared the same six original records, with or without an added LRE judgment, across four reused histories and two versions. The exercise withheld current-operation diagnostics and froze each choice before any target operation. {finding(data, 'en')} {changed_finding(data, 'en')}

The changed-version comparison documents choices, self-reported uncertainty and abstentions under an unknown mapping. Both conditions explicitly instructed the AI to abstain when evidence was insufficient. The study pages record all 16 choices and explain the limits of comparison with the November 3 study.

Rebuild the dated pages and catalog update after independent approval:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tools/no_diagnostic_publication.py --no-diagnostic /absolute/path/to/approved-public-export.json
```
{README_END}
'''
    pattern = re.compile(re.escape(README_START) + '.*?' + re.escape(README_END) + r'\n', re.S)
    if README_START in text or README_END in text:
        require(text.count(README_START) == text.count(README_END) == 1, 'Unexpected README markers')
        text, changed = pattern.subn(lambda _: block, text)
        require(changed == 1, 'Broken README section')
        return text
    return text + '\n' + block


def integrate_sitemap(text):
    locations = (BASE + STUDY, BASE + STUDY + 'en.html')
    require(text.count('</urlset>') == 1, 'Missing sitemap closure')
    for location in locations:
        entry = f'  <url><loc>{location}</loc></url>\n'
        require(text.count(entry) <= 1, 'Duplicate follow-up sitemap location')
        if entry not in text:
            text = text.replace('</urlset>', entry + '</urlset>', 1)
    return text


def prepare_updates(root=ROOT, source=None):
    loaded = read_export(root, source)
    if loaded is None:
        return {}
    data, raw = loaded
    updates = {DATA: raw, STUDY + 'index.html': render(data, 'ja').encode(), STUDY + 'en.html': render(data, 'en').encode()}
    for filename, lang in (('results.html', 'ja'), ('results.en.html', 'en')):
        updates[filename] = integrate_listing((root / filename).read_text(encoding='utf-8'), lang, data).encode()
    updates['README.md'] = integrate_readme((root / 'README.md').read_text(encoding='utf-8'), data).encode()
    updates['sitemap.xml'] = integrate_sitemap((root / 'sitemap.xml').read_text(encoding='utf-8')).encode()
    return updates


def apply_updates(updates, root=ROOT):
    for relative, raw in updates.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or target.read_bytes() != raw:
            target.write_bytes(raw)


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--no-diagnostic', type=Path, help='Independently approved public export')
    args = parser.parse_args()
    updates = prepare_updates(source=args.no_diagnostic)
    apply_updates(updates)
    print('Built the audited November 27 follow-up.' if updates else 'No audited follow-up export installed.')
