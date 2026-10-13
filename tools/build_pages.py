"""Build public pages using only the public, allowlisted summary. Python 3 stdlib."""
from pathlib import Path
import json
from html import escape as E

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = 'data/shiori-pilot-2026-10-13.json'
D = json.loads((ROOT / DATA_FILE).read_text())
BASE = 'https://yuu-honda.github.io/lux-spiria-results/'
HUB = 'https://yuu-honda.github.io/lux-spiria/'
STUDY = 'studies/2026-10-13-shiori-pilot/'
CIDS = [c['id'] for c in D['conditions']]

def T(ja, en, lang): return ja if lang == 'ja' else en

def label(cid, lang):
    return {'direct_max': T('直接照合・最大値', 'Direct · best cue', lang),
            'direct_sum': T('直接照合・合流', 'Direct · cue aggregation', lang),
            'path_max': T('1段の経路・最大値', 'One hop · best cue', lang),
            'path_sum': T('1段の経路・合流', 'One hop · cue aggregation', lang)}[cid]

def category(cid, lang):
    return {'direct_source_question': T('直接', 'Direct', lang),
            'paraphrase_question': T('言い換え', 'Paraphrase', lang),
            'two_clue_question': T('二手掛かり', 'Two clues', lang),
            'no_answer_control': T('対象なし', 'No target', lang)}[cid]

def section(sid, eyebrow, title, desc='', content=''):
    return f'<section class="section" id="{sid}" aria-labelledby="{sid}-title"><div class="section-heading"><p class="eyebrow">{eyebrow}</p><h2 id="{sid}-title">{title}</h2>' + (f'<p>{desc}</p>' if desc else '') + f'</div>{content}</section>'

def table(caption, heads, rows, cls=''):
    return '<div class="table-wrap" role="region" aria-label="' + E(caption) + '" tabindex="0"><table class="' + cls + '"><caption>' + caption + '</caption><thead><tr>' + ''.join(f'<th scope="col">{h}</th>' for h in heads) + '</tr></thead><tbody>' + ''.join('<tr><th scope="row">'+str(r[0])+'</th>'+''.join(f'<td>{v}</td>' for v in r[1:])+'</tr>' for r in rows) + '</tbody></table></div>'

def cards(items):
    return '<div class="method-grid">'+''.join(f'<article><h3>{h}</h3><p>{p}</p></article>' for h,p in items)+'</div>'

def document(lang, study, title, description, body):
    prefix = '../../' if study else ''
    home = prefix + ('index.html' if lang == 'ja' else 'en.html')
    ja = BASE + (STUDY if study else '')
    en = ja + 'en.html'
    canonical = ja if lang == 'ja' else en
    alt = 'en.html' if lang == 'ja' else 'index.html'
    hub = HUB + ('' if lang == 'ja' else 'index.en.html')
    nav = f'<a href="{home}#studies">{T("研究結果", "Studies", lang)}</a><a href="{home}#scope">{T("公開範囲", "Public scope", lang)}</a><a href="{hub}">{T("研究の全体像", "Project overview", lang)} ↗</a>'
    languages = f'<span class="lang" aria-label="{T("表示言語", "Language", lang)}"><a href="index.html" lang="ja" hreflang="ja"'+(' aria-current="page"' if lang=='ja' else '')+'>日本語</a><span aria-hidden="true">/</span><a href="en.html" lang="en" hreflang="en"'+(' aria-current="page"' if lang=='en' else '')+'>EN</a></span>'
    return f'''<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — LUX SPIRIA Results</title><meta name="description" content="{E(description, quote=True)}">
<link rel="canonical" href="{canonical}"><link rel="alternate" hreflang="ja" href="{ja}"><link rel="alternate" hreflang="en" href="{en}"><link rel="alternate" hreflang="x-default" href="{ja}">
<meta name="theme-color" content="#090d12"><meta name="apple-mobile-web-app-title" content="LUX Results">
<meta property="og:type" content="website"><meta property="og:title" content="{E(title, quote=True)} — LUX SPIRIA Results"><meta property="og:description" content="{E(description, quote=True)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE}assets/lux-symbol.png">
<link rel="icon" type="image/png" sizes="32x32" href="{prefix}assets/favicon-32.png"><link rel="apple-touch-icon" sizes="180x180" href="{prefix}assets/apple-touch-icon.png"><link rel="manifest" href="{prefix}{'site' if lang=='ja' else 'site.en'}.webmanifest"><link rel="stylesheet" href="{prefix}site.css"><script src="{prefix}results.js" defer></script>
</head><body><a class="skip-link" href="#main">{T('本文へ', 'Skip to content', lang)}</a><div class="page">
<header class="masthead"><a class="brand" href="{home}" aria-label="LUX SPIRIA Results"><img src="{prefix}assets/lux-symbol.png" alt="" width="44" height="44"><span class="brand-wordmark">LUX SPIRIA<span class="brand-subtitle">RESEARCH RESULTS</span></span></a><nav aria-label="{T('主なページ', 'Main navigation', lang)}">{nav}{languages}</nav></header>
<main id="main">{body}</main>
<footer class="footer"><nav aria-label="{T('資料と規約','Resources and terms',lang)}"><a href="{hub}">LUX SPIRIA ↗</a><a href="{prefix}LICENSE">License / LSP-1.0</a><a href="https://github.com/Yuu-Honda/lux-spiria-results">GitHub ↗</a></nav><small>RESULT RECORD / {D['date']} · v1</small></footer>
</div></body></html>'''

def scope(lang):
    return section('scope', 'PUBLIC SCOPE', T('公開するもの、保持するもの。','What is public, what is retained.',lang),
        T('概要・結果・歴史を、それぞれ追跡できる形に分けています。','Overview, results and history remain separately traceable.',lang), cards([
        (T('このResults','This Results site',lang),T('固定した手順、全条件の集計、匿名化した問別結果、実行確認と限界を公開します。画面は保存済み結果の表示です。閲覧中にSHIORIやAIを実行しません。','Publishes the frozen procedure, all condition aggregates, opaque per-query results, verification and limitations. These pages display stored results; they do not run SHIORI or an AI while you browse.',lang)),
        (T('非公開の研究一式','Private research bundle',lang),T('会話原文・質問本文・出典ID・特徴語・SQLite・実験用コードと詳細ログは非公開で保持します。公開集計は再計算できますが、第三者が公開ファイルだけで原文照合やエンジン再実行を行うことはできません。','Original conversations, question text, source IDs, feature terms, SQLite, experiment code and detailed logs remain private. Public aggregates can be recalculated; source auditing and engine reruns cannot be performed from public files alone.',lang)),
        (T('LUX SPIRIAの研究史','LUX SPIRIA history',lang),T('起点の問い、過去の観測、README、releaseは元のプロジェクトに保持します。新しい実験結果で過去を書き換えません。','The originating questions, past observations, README and releases remain in the original project. New experiments do not rewrite past records.',lang)),
        (T('今回まだ測っていないもの','Not evaluated in this study',lang),T('LREの全Wake、Emotionの効果、応答生成、日常会話での自然な想起、人格連続性は今回の評価対象に含みません。','Full LRE Wake, Emotion effects, response generation, natural everyday recall and personality continuity were not evaluated.',lang))]))

def landing(lang):
    studyurl = STUDY + ('index.html' if lang=='ja' else 'en.html')
    body = f'''<section class="results-hero"><p class="eyebrow">LUX SPIRIA / RESEARCH RESULTS</p><h1>{T('問いと手順を固定し、<br>結果を残す。','Fix the question.<br>Keep the result.',lang)}</h1><p class="lead">{T('記憶・感情・変化・想起・連続性。その研究で実際に何を動かし、何が起き、どこまで確かめたかを残す場所です。','Memory, affect, change, recall and continuity. A record of what was actually run, what happened, and how far verification reaches.',lang)}</p></section>
<div class="status-strip"><span>{T('実行済み結果を公開 · 小規模な探索的試験','Recorded execution · small exploratory pilot',lang)}</span><small>UPDATED / {D['date']}</small></div>
<div class="hero-metrics"><div class="metric"><strong>01</strong><span>{T('公開研究','Published study',lang)}</span><small>SHIORI PILOT / v1</small></div><div class="metric"><strong>42</strong><span>{T('原文メッセージ','Source messages',lang)}</span><small>{T('1つの実会話セッション','One real conversation session',lang)}</small></div><div class="metric"><strong>24</strong><span>{T('作成した試験質問','Authored test queries',lang)}</span><small>{T('対象あり22・対象なし2','22 with targets · 2 controls',lang)}</small></div></div>'''
    card = f'''<article class="study-card"><span class="study-status">RUN 001 / EXPLORATORY PILOT</span><time datetime="{D['date']}">{D['date']}</time><h3><a href="{studyurl}">{T('SHIORI、手掛かりと経路の比較。','SHIORI: cues, paths and retrieval.',lang)} ↗</a></h3><p>{T('実会話を固定し、直接照合と1段の経路、最大値と手掛かりの合流を4条件で比較。索引のレビュー依存と、言い換えで入口が作れなかった失敗も記録しました。','A frozen real-dialogue sample compared direct versus one-hop retrieval and best-cue versus cue aggregation across four conditions. The record includes review-dependent indexing and failures to form cues for paraphrases.',lang)}</p><div class="study-stats"><span><strong>4</strong>{T('比較条件','conditions',lang)}</span><span><strong>0 → 203</strong>{T('標準解析 → レビュー後の延べ特徴数','default → reviewed feature occurrences',lang)}</span><span><strong>0 / 8</strong>{T('言い換えの対象到達','paraphrase target hits',lang)}</span></div></article>'''
    body += section('studies', '01 / STUDIES', T('実験の記録。','Study records.',lang), T('成功した条件だけでなく、失敗した入力と再現の範囲も残します。','Successes, failed inputs and the scope of reproduction are recorded together.',lang),card)
    body += section('method', '02 / METHOD', T('結果の手前に、手順を置く。','The procedure comes before the result.',lang), content=cards([
        (T('入力を固定する','Freeze the inputs',lang),T('原文、索引、質問、対象となる出典を検索実行前に固定。検索結果を見てから都合よく手掛かりや正解を変えません。','Freeze the source, index, questions and target sources before retrieval. Do not tune cues or targets after seeing the result.',lang)),
        (T('比較条件を全部出す','Show every condition',lang),T('4条件の全集計を公開。速度と到達率を分け、手掛かりの合流と経路探索の効果も分けて読みます。','Publish all four conditions. Read timing separately from target hits, and distinguish aggregation from path traversal.',lang))]))
    body += scope(lang)
    return document(lang,False,T('研究結果','Research results',lang),T('LUX SPIRIAの実行済み研究結果。方法、全条件比較、失敗、再現確認と限界。','Recorded LUX SPIRIA research: methods, all-condition comparisons, failures, verification and limitations.',lang),body)

def study(lang):
    body = f'''<section class="study-hero"><p class="kicker">RUN 001 / RETROSPECTIVE PILOT / v1</p><h1>{T('SHIORI、手掛かりと<br>経路の比較。','SHIORI: cues, paths<br>and retrieval.',lang)}</h1><p class="lead">{T('実会話42メッセージを保存し、レビュー済みの意味特徴を延べ203件で索引を作成。別工程で作った24問を固定し、4条件で検索しました。','42 real-dialogue messages were captured and indexed with 203 reviewed semantic-feature occurrences. 24 queries authored in a separate step were frozen and tested under four retrieval conditions.',lang)}</p><p class="note"><time datetime="{D['date']}">{D['date']}</time> · {T('保存済みの実行結果。閲覧中のエンジン実行ではありません。','Stored execution results; no engine runs while you browse.',lang)}</p></section>
<div class="finding-callout"><h2>{T('入口がないと、経路を辿れない。','Without a cue, there is no path to follow.',lang)}</h2><p>{T('言い換え8問は、全条件で手掛かり0・候補0でした。一方、手掛かりの合流は直接照合だけでも上位3件への対象到達を5問増やしました。1段の経路を加えた増分は、上位5件で1問でした。','All eight paraphrase queries produced zero cues and zero candidates in every condition. Cue aggregation added five top-three target hits even without hops. One-hop traversal added one top-five hit.',lang)}</p></div>'''
    chartrows=[]
    for c in D['conditions']:
        h=c['target_hits']
        chartrows.append(f'<li class="chart-row" data-condition="{c["id"]}" data-at-1="{h["at_1"]}" data-at-3="{h["at_3"]}" data-at-5="{h["at_5"]}"><div class="chart-label"><strong>{label(c["id"],lang)}</strong><small>{c["id"]}</small></div><span class="chart-track" aria-hidden="true"><span class="chart-fill" style="width:{h["at_5"]/22*100:.4f}%"></span></span><span class="chart-value">{h["at_5"]} / 22</span></li>')
    chart=f'''<figure class="summary-chart"><figcaption id="hit-caption">{T('上位5件に対象出典が入った質問数 / 対象あり22問','Queries with a target source in the top 5 / 22 target-bearing queries',lang)}</figcaption><label class="metric-control" for="hit-cutoff">{T('表示する集計','Display aggregate',lang)} <select id="hit-cutoff" data-chart-cutoff aria-controls="hit-bars"><option value="5" selected>Top 5</option><option value="3">Top 3</option><option value="1">Top 1</option></select></label><ol id="hit-bars" class="chart-rows">{''.join(chartrows)}</ol><p class="note" data-chart-announcement aria-live="polite"></p></figure>'''
    rows=[[label(c['id'],lang),str(c['target_hits']['at_1']),str(c['target_hits']['at_3']),str(c['target_hits']['at_5']),f'{c["mrr_at_5"]:.4f}'] for c in D['conditions']]
    chart+=table(T('全条件・対象あり22問の結果','All conditions · 22 target-bearing queries',lang),[T('条件','Condition',lang),'Top 1','Top 3','Top 5','MRR@5'],rows)
    chart+=f'<p class="note">{T("対象到達は、実行前に指定した出典のいずれかが返ったことです。会話理解や回答の正確さではありません。MRR@5は最初の対象順位の逆数の平均（上位5件になければ0）。同点はepisode root hash順で、上位5件の外に続く同点は測っていません。","A hit means retrieval of a predesignated target source. It does not measure comprehension or answer correctness. MRR@5 averages the reciprocal rank of the first target, assigning zero beyond five. Ties use episode-root-hash order; ties beyond the returned five were not measured.",lang)}</p>'
    chart+=cards([
        (T('合流の増分','Aggregation increment',lang),T('上位3件で5問増加、減少0。Q04・Q08・Q17・Q20・Q21。これは同じ試験内の記述的な差で、独立した証拠や統計的有意性の証明ではありません。','Five additional top-three hits, no losses: Q04, Q08, Q17, Q20 and Q21. This is a descriptive within-sample difference, not independent evidence or a claim of statistical significance.',lang)),
        (T('経路の増分','Hop increment',lang),T('上位3件の増加0。上位5件ではQ19だけが追加され、順位4でした。単一の手掛かりからの経路であり、複数手掛かりの合流による到達ではありません。','No additional top-three hits. Q19 alone was added at top five, at rank four. It followed a single-cue path, rather than multiple-cue convergence.',lang))])
    body+=section('results','01 / ALL CONDITIONS',T('何が届き、何が届かなかったか。','What was reached, what was missed.',lang),T('母数22。対象なしの2問は、到達率の母数に含めません。','Denominator: 22. The two no-target controls are excluded from target-hit rates.',lang),chart)
    catrows=[]
    for cat in ('direct_source_question','paraphrase_question','two_clue_question'):
        qs=[q for q in D['per_query'] if q['category']==cat]
        hits=lambda k:sum(q['conditions']['path_sum']['target_rank_at_5'] is not None and q['conditions']['path_sum']['target_rank_at_5']<=k for q in qs)
        catrows.append([category(cat,lang),len(qs),hits(3),hits(5)])
    content=table(T('1段の経路＋合流：質問種別ごとの対象到達','One hop + aggregation: target hits by query category',lang),[T('種別','Category',lang),T('問数','Queries',lang),'Top 3','Top 5'],catrows)
    content+=f'<div class="boundary-box"><ul><li>{T("標準解析で意味特徴は0件。延べ203件は、原文だけを読むAIによるレビューで作りました。検索を繰り返して自動学習した結果ではありません。","Default preparation produced zero semantic features. The 203 feature occurrences came from source-only AI-assisted review, not automatic learning through repeated retrieval.",lang)}</li><li>{T("Q09〜Q16は手掛かりも候補も0。unknownの出力も0でしたが、理解済みを意味しません。解析器は未知表現を網羅して列挙しません。","Q09–Q16 had zero cues and candidates. A zero unknown count does not mean comprehension; the parser does not enumerate every unrecognized expression.",lang)}</li><li>{T("対象なし2問も2問とも候補を返しました。検索候補が出たことと、回答可能であることは別です。今回はAIの回答を生成していません。","Both no-target controls returned candidates. Candidate retrieval does not establish answerability. No model answers were generated.",lang)}</li></ul></div>'
    body+=section('failures','02 / FAILURE ANALYSIS',T('索引と解析の限界が見えた。','Indexing and parsing limits became visible.',lang),content=content)
    method=cards([
        (T('01 原文を選ぶ','01 Select source',lang),T('2025-02-27の保存済み会話1セッション。exportの47レコードからsystem 2件と空のAI発話3件を除き、ユーザー21件・AI21件を保存。途中で切れたAI発話1件は補完せず保持しました。','One archived conversation dated 2025-02-27. Of 47 export records, two system records and three empty AI messages were excluded, leaving 21 user and 21 AI messages. One truncated AI message was retained without completion.',lang)),
        (T('02 索引を固定する','02 Freeze indexing',lang),T('1メッセージを1episodeとして原文を保存。原文だけから特徴をレビューし、質問作成前に索引を固定しました。質問を索引作成者には渡していません。','Each message became one episode. Features were reviewed from source alone and frozen before query authoring. The indexer was not given the queries.',lang)),
        (T('03 質問と対象を固定する','03 Freeze queries and targets',lang),T('別工程で直接8・言い換え8・二手掛かり6・対象なし2問を作成。対象出典を検索前に照合しました。ローカルの手順固定であり、外部機関への事前登録ではありません。','A separate step authored eight direct, eight paraphrase, six two-clue and two no-target queries. Target sources were audited before retrieval. This was a local protocol freeze, not external preregistration.',lang)),
        (T('04 全条件を実行する','04 Run all conditions',lang),T('経路0段/1段 × 手掛かり最大値/合流の2×2比較。各手掛かりの最良寄与を足す合流方式を使用。bitmap、上位5件、hub_limit 32、literal補助検索なしで固定しました。','A 2×2 comparison: zero/one hop × best cue/cue aggregation. Aggregation sums the best contribution per cue. Main runs fixed bitmap, limit five, hub_limit 32, and no lexical fallback.',lang))])
    method+=f'<p class="note">{T("保存候補の絞り込みと、2問の対象・表現の修正は初回検索前に記録し、旧版も保持しました。結果を見た後の索引・質問調整はしていません。既存13抜粋との非重複は原文hashと場面で確認しました。日時による独立照合ではありません。","Source selection and two query/target corrections were recorded before the first retrieval; earlier versions were retained. No index or query tuning followed results. Non-overlap with an earlier 13-excerpt sample was checked using text hashes and scenes, not an independent timestamp comparison.",lang)}</p>'
    method+=f'<p class="note">{T("保存と検索は同じcue parser関数を使います。ただし検索時の語彙はレビュー済み特徴で拡張され、標準保存解析時とは異なります。作業分担は同じチーム内のAI補助であり、外部研究者による独立した盲検評価ではありません。","Preparation and recall use the same cue-parser function, but the recall lexicon is expanded by reviewed features and differs from default preparation. Role separation used AI assistance within the same team; it was not independent external blind review.",lang)}</p>'
    body+=section('method','03 / FROZEN METHOD',T('何を固定して、比較したか。','What was fixed for comparison.',lang),content=method)
    rows=[]
    for q in D['per_query']:
        values=[]
        for cid in CIDS:
            rank=q['conditions'][cid]['target_rank_at_5']
            values.append(f'<span class="rank-value">{rank}</span>' if rank else f'<span class="rank-miss">{T("対象なし" if q["category"]=="no_answer_control" else "未到達", "No target" if q["category"]=="no_answer_control" else "Miss",lang)}</span>')
        rows.append([q['id'],category(q['category'],lang)]+values)
    content=table(T('24問の匿名順位：上位5件内の最初の対象','Opaque ranks for 24 queries: first target within top five',lang),['ID',T('種別','Category',lang)]+[label(c,lang) for c in CIDS],rows,'run-table')
    content+=f'<p class="note">{T("Q01〜Q24は今回専用の公開ラベルです。問い本文、原文、出典ID、特徴語は公開しません。全条件の候補数・手掛かり数・同点有無は公開JSONにあります。対象指定は十分な出典を選ぶ方式で、関連する全出典の網羅ではありません。","Q01–Q24 are public labels created for this study. Question text, source text, source IDs and feature terms remain private. Candidate counts, cue counts and within-top-five ties for every condition are in the public JSON. Targets identify sufficient sources, not an exhaustive set of relevant records.",lang)}</p>'
    body+=section('queries','04 / PER-QUERY RESULTS',T('集計の内訳も残す。','Keep the individual outcomes.',lang),content=content)
    timingrows=[[label(r['condition'],lang),r['method'],f'{r["median_ms"]:.4f}',f'{r["p95_ms"]:.4f}',r['n']] for r in D['timing']['samples']]
    timing=table(T('初回実行のwarm recall計時 / ms','Warm recall timing from the first run / ms',lang),[T('条件','Condition',lang),T('方式','Method',lang),T('中央値 ms','Median ms',lang),'p95 ms','n'],timingrows)
    timing+=f'<p class="note">{T("24問×21反復、条件・方式ごとに504サンプル。手掛かり0の質問も含みます。条件と方式の順序を回転して計時。query解析を含み、原文取得・JSON化・DB構築・モデル実行・レビュー時間を含みません。Memory読み込みでは全方式の索引を構築します。","24 queries × 21 repetitions gives 504 samples per condition and method, including zero-cue queries. Timing order was rotated across conditions and methods. Timing includes query parsing, excludes raw-source lookup, serialization, DB construction, model execution and review. Memory loading builds all indexes.",lang)}</p>'
    timing+=f'<div class="boundary-box"><p>{T("42メッセージのこの試験では、二進数・tag・bitmap間の大きな速度優位は示せません。従来の全文検索や旧保存系との速度比較でもありません。別プロセスで確認したのは結果の一致で、計時値の一致ではありません。","This 42-message test does not establish a large speed advantage between binary, tag and bitmap retrieval, or a speedup over full-text search or older storage systems. Cross-process checks reproduced retrieval results, not timing values.",lang)}</p></div>'
    body+=section('timing','05 / MEASURED RUNTIME',T('速度は、測った範囲で読む。','Read timing within its measured scope.',lang),content=timing)
    checks=[T('保存した42件を原文と完全照合','All 42 captured messages matched source rereads',lang),T('24問×4条件の96組で、binary / tags / bitmapの結果・score・evidence一致','Results, scores and evidence matched across binary / tags / bitmap in all 96 query-condition cases',lang),T('検索前後でDB hashが変わらない','Database hash unchanged by retrieval',lang),T('同じDBを再度開いて同じ結果','Reopening the same database returned the same results',lang),T('別Pythonプロセス・新DB・hash seed 0/17で結果と集計が一致','Fresh Python processes and databases with hash seeds 0/17 reproduced results and metrics',lang),T('別検算でhit数とMRRを再計算して一致','Separate recalculation matched hit counts and MRR',lang),T('再実行wrapperで再構築と参照結果一致を確認','A reproduction wrapper verified rebuilding and equality with reference results',lang)]
    verify='<div class="boundary-box"><ul>'+''.join(f'<li>{s}</li>' for s in checks)+'</ul></div>'
    verify+=f'<p class="note">{T("ここでの再実行確認は、非公開の同じ固定入力を用いた内部確認です。公開JSONで集計は追跡できますが、第三者が原文や意味索引の妥当性を独立検証できる公開データセットではありません。","These are internal reproduction checks using the same private frozen inputs. Aggregates are traceable from public JSON; this is not a public dataset enabling independent source or semantic-index validation.",lang)}</p>'
    verify+=f'<details><summary>{T("実装と入力固定の識別子","Implementation and freeze identifiers",lang)}</summary><div class="source-note"><p>{T("実験版SHIORI v0.2の固定snapshotを使用。LRE mainの正本機構とは分離されたdraft prototypeです。","A pinned experimental SHIORI v0.2 snapshot was used, separate from canonical LRE main, as a draft prototype.",lang)}</p><p>Engine commit: <code>{D["provenance"]["engine_commit"]}</code></p><p>Frozen manifest SHA-256: <code>{D["provenance"]["freeze_sha256"]}</code></p><p>Experiment manifest SHA-256: <code>{D["provenance"]["experiment_manifest_sha256"]}</code></p><p>{T("hashは保持した一式の識別子です。それ自体で科学的妥当性や公開再現性を証明しません。","Hashes identify retained bundles; they do not by themselves establish scientific validity or public reproducibility.",lang)}</p></div></details>'
    body+=section('verification','06 / VERIFICATION',T('何を再実行して確かめたか。','What reruns actually verified.',lang),content=verify)
    limits=[T('選択した実会話1件・研究者が作った24問の探索試験。日常会話全体の精度や統計的有意性へ一般化しません。','An exploratory test on one selected conversation and 24 researcher-authored queries. It does not estimate everyday conversation accuracy or statistical significance.',lang),T('原文は「何が語られたか」の記録です。そこで語られた製品や外部事実の正しさを独立に検証したものではありません。','The transcript records what was said; it does not independently establish the truth of product claims or external facts in that conversation.',lang),T('レビュー依存の索引、限定的なparser、上位5件の同点が残ります。人格連続性・主観的感情・自然な想起の因果効果はこの結果から導きません。','Review-dependent indexing, bounded parsing and top-five ties remain. These results do not establish personality continuity, subjective affect or a causal effect on natural recall.',lang),T('LREの全Wake、Emotion、SHIORIとの自動統合、AIの応答生成は実行していません。','Full LRE Wake, Emotion, automatic SHIORI integration and AI response generation were not run.',lang)]
    content='<div class="boundary-box"><ul>'+''.join(f'<li>{l}</li>' for l in limits)+'</ul></div>'
    content+=f'<div class="download-links"><a href="../../{DATA_FILE}" download>{T("公開集計JSONを取得","Download public summary JSON",lang)}</a><a href="../../{ "index.html" if lang=="ja" else "en.html"}#scope">{T("公開範囲を確認","Read public scope",lang)} →</a></div>'
    body+=section('limits','07 / LIMITATIONS',T('示したことと、まだ示していないこと。','What is shown, and what remains untested.',lang),content=content)
    return document(lang,True,T('SHIORI実会話パイロット','SHIORI real-record pilot',lang),T('実会話42件・24問・4条件。手掛かりの合流、経路探索、失敗、速度、内部再実行確認の記録。','42 real messages, 24 queries, four conditions: cue aggregation, path traversal, failures, timing and internal reproduction checks.',lang),body)

if __name__ == '__main__':
    for lang, filename in [('ja','index.html'),('en','en.html')]:
        (ROOT/filename).write_text(landing(lang)+'\n')
        (ROOT/STUDY/filename).write_text(study(lang)+'\n')
    print('Built 4 public pages from the public summary.')
