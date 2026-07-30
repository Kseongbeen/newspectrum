"""뉴스펙트럼 정적 시연 HTML 생성기.

네이버 검색 API로 이슈별 기사를 수집하고, 언론사 스펙트럼 좌표
(news_balance_app.py의 PRESS_LEANING_SCORES)에 배치한 자립형 HTML을 만든다.

실행:  python 시연_생성.py
입력:  .streamlit/secrets.toml (NAVER_CLIENT_ID / NAVER_CLIENT_SECRET)
출력:  뉴스펙트럼_시연.html  (더블클릭으로 열리는 단일 파일, 외부 의존 없음)

기사 좌표는 소속 언론사의 스펙트럼 좌표(『2025 언론수용자 조사』 재분석 기반)를
사용한다. 기사 단위 스탠스 판정(보고서 5장)은 파일럿 참조 — 데모 화면에도 명시.
"""

import ast
import json
import re
import sys
import html as html_mod
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests

sys.stdout.reconfigure(encoding='utf-8')
import os
BASE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(BASE, 'news_balance_app.py')
OUT = os.path.join(BASE, '뉴스펙트럼_시연.html')

# 후보 이슈 (앞에서부터 검사해 기사 12건 이상인 것 최대 5개 채택)
CANDIDATES = ['의대 증원', '최저임금', '반도체 특별법', '국민연금 개혁',
              '노란봉투법', '전세사기 대책']
MIN_ARTICLES = 12
MAX_ISSUES = 5

# ── news_balance_app.py에서 점수표·매핑·헬퍼 추출 (정의 중복 방지) ──
_wanted = {'PRESS_LEANING_SCORES', 'DOMAIN_TO_PRESS', '_press_from_link',
           '_clean_api_text'}
_ns = {'re': re, 'html': html_mod}
_tree = ast.parse(open(APP, encoding='utf-8').read())
for _node in _tree.body:
    _name = getattr(_node, 'name', None) or (
        _node.targets[0].id if isinstance(_node, ast.Assign)
        and hasattr(_node.targets[0], 'id') else None)
    if _name in _wanted:
        exec(compile(ast.Module([_node], []), APP, 'exec'), _ns)
PRESS_SCORES = _ns['PRESS_LEANING_SCORES']
press_from_link = _ns['_press_from_link']
clean_text = _ns['_clean_api_text']


def read_keys():
    txt = open(os.path.join(BASE, '.streamlit', 'secrets.toml'), encoding='utf-8').read()
    cid = re.search(r'NAVER_CLIENT_ID\s*=\s*"([^"]+)"', txt).group(1)
    csec = re.search(r'NAVER_CLIENT_SECRET\s*=\s*"([^"]+)"', txt).group(1)
    return cid, csec


def fetch_issue(query, keys):
    """API 호출 → 점수표 매칭 기사 목록 [{press,score,title,link,date}] (관련도순)."""
    cid, csec = keys
    if len(csec) > 20:
        url = 'https://naverapihub.apigw.ntruss.com/search/v1/news'
        headers = {'X-NCP-APIGW-API-KEY-ID': cid, 'X-NCP-APIGW-API-KEY': csec}
    else:
        url = 'https://openapi.naver.com/v1/search/news.json'
        headers = {'X-Naver-Client-Id': cid, 'X-Naver-Client-Secret': csec}
    res = requests.get(url, headers=headers,
                       params={'query': query, 'display': 100, 'sort': 'sim'},
                       timeout=8)
    res.raise_for_status()
    out, seen = [], set()
    for it in res.json().get('items', []):
        press = press_from_link(it.get('originallink', '') or it.get('link', ''))
        if not press or press not in PRESS_SCORES:
            continue
        title = clean_text(it.get('title', ''))
        norm = re.sub(r'\s+', '', title)
        if not title or norm in seen:
            continue
        seen.add(norm)
        try:
            d = parsedate_to_datetime(it['pubDate']).strftime('%m.%d %H:%M')
        except Exception:
            d = ''
        desc = clean_text(it.get('description', ''))
        desc = re.sub(r'[◀▶►▷◁]', ' ', desc)                 # 방송 스크립트 기호
        desc = re.sub(r'^\s*(앵커|리포트)\s*', '', desc)
        desc = re.sub(r'\s(앵커|리포트)\s', ' ', desc)
        desc = re.sub(r'[가-힣]{2,4}\s*기자입니다\.?', '', desc)
        desc = re.sub(r'\[[^\]]{0,20}\]\s*', '', desc)         # [세종=뉴시스] 등 발신지
        desc = re.sub(r'\([^)]{0,20}=[^)]{0,15}\)\s*', '', desc)  # (서울=뉴스1) 등
        desc = re.sub(r'[가-힣]{2,4}\s*(?:선임|수습|인턴)?기자\s*=?\s*', '', desc)  # 바이라인
        desc = re.sub(r'\s+', ' ', desc).strip()
        out.append({'press': press, 'score': PRESS_SCORES[press],
                    'title': title, 'link': it.get('originallink') or it.get('link', ''),
                    'date': d, 'desc': desc})
    return out


def bucket_of(score):
    return 'p' if score < -0.10 else ('c' if score > 0.10 else 'n')


_TOKEN = re.compile(r'[가-힣]{2,}')
_STOP = {'기자', '뉴스', '사진', '영상', '오늘', '이날', '지난', '관련', '대한', '대해',
         '위해', '통해', '따르면', '밝혔다', '했다', '있다', '한다', '됐다', '이다',
         '있는', '하는', '하고', '으로', '에서', '까지', '부터', '종합', '단독', '속보',
         '앵커', '리포트', '올해', '내년', '내년도', '지난해', '이번', '가운데',
         '이후', '함께', '각각', '끝에', '이같이', '위한', '대비', '최근', '방안',
         '오전', '오후', '지적', '경우', '이상', '모두', '다시', '현재', '진행',
         '이같', '따라', '받는', '이전', '처음', '필요', '추가', '정부', '한국', '기준'}
# 토큰 끝의 흔한 조사·어미 제거 (2음절 이상 어근만 남김)
_SUFFIXES = ['에서는', '으로는', '에서', '에게', '으로', '까지', '부터', '라고', '이라',
             '하며', '면서', '했다', '한다', '된다', '들이', '들은', '들을', '들의',
             '는', '은', '이', '가', '을', '를', '의', '에', '도', '와', '과', '로', '만']


def _norm(token):
    for suf in _SUFFIXES:
        if token.endswith(suf) and len(token) - len(suf) >= 2:
            token = token[:-len(suf)]
            break
    return token[:-1] if token.endswith('으') else token   # '등으로'→'등으' 조각 방지


def synthesize(articles, query):
    """성향권별 특징 키워드(TF-IDF식 변별도)와 대표 문장(요약문 인용) 추출."""
    qwords = set(_TOKEN.findall(query))
    buckets = {'p': [], 'n': [], 'c': []}
    for a in articles:
        buckets[bucket_of(a['score'])].append(a)
    # 토큰 문서빈도 (기사당 1회, 검색어를 포함한 토큰은 제외)
    tf = {}
    for b, arts in buckets.items():
        c = {}
        for a in arts:
            for t in {_norm(t) for t in _TOKEN.findall(a['title'] + ' ' + a['desc'])}:
                if len(t) < 2 or t in _STOP or any(qw in t or t in qw for qw in qwords):
                    continue
                c[t] = c.get(t, 0) + 1
        tf[b] = c
    import math
    syn = {}
    for b, arts in buckets.items():
        if not arts:
            syn[b] = None
            continue
        other = {}
        for b2, c2 in tf.items():
            if b2 == b:
                continue
            for t, v in c2.items():
                other[t] = other.get(t, 0) + v
        n_in = len(arts)
        n_out = sum(len(buckets[b2]) for b2 in buckets if b2 != b) or 1
        # 출현율이 다른 성향권의 2배 이상인 토큰만 (변별 키워드)
        scored = []
        for t, v in tf[b].items():
            if v < 2 or t.endswith(('습니다', '입니다', '합니다', '하고', '하며',
                                    '등을', '등이', '대를')):
                continue
            lift = (v / n_in) / ((other.get(t, 0) + 0.5) / n_out)
            if lift >= 2:
                scored.append((t, v * math.log(lift + 1)))
        scored.sort(key=lambda x: -x[1])
        kws = [t for t, _ in scored[:4]]
        # 대표 문장: 관련도순 상위, 언론사 중복 없이 2건
        quotes, used = [], set()
        for a in arts:                      # arts는 API 관련도순 그대로
            if len(a['desc']) < 20 or a['press'] in used:
                continue
            used.add(a['press'])
            quotes.append({'press': a['press'],
                           'text': a['desc'][:110] + ('…' if len(a['desc']) > 110 else '')})
            if len(quotes) == 2:
                break
        # 성향권 내 언론사 상위 3곳
        pc = {}
        for a in arts:
            pc[a['press']] = pc.get(a['press'], 0) + 1
        tops = sorted(pc.items(), key=lambda kv: -kv[1])[:3]
        syn[b] = {'kws': kws, 'quotes': quotes,
                  'presses': [f'{p}({v})' for p, v in tops]}
    return syn


def build_data():
    keys = read_keys()
    issues = []
    for q in CANDIDATES:
        arts = fetch_issue(q, keys)
        if len(arts) < MIN_ARTICLES:
            print(f'  건너뜀 "{q}": {len(arts)}건 (<{MIN_ARTICLES})')
            continue
        mean = sum(a['score'] for a in arts) / len(arts)
        counts = {'p': sum(1 for a in arts if a['score'] < -0.10),
                  'n': sum(1 for a in arts if -0.10 <= a['score'] <= 0.10),
                  'c': sum(1 for a in arts if a['score'] > 0.10)}
        presses = len({a['press'] for a in arts})
        print(f'  채택 "{q}": {len(arts)}건, 언론사 {presses}곳, 좌표 {mean:+.2f}, '
              f'분포 {counts["p"]}/{counts["n"]}/{counts["c"]}')
        issues.append({'q': q, 'articles': arts, 'mean': round(mean, 3),
                       'counts': counts, 'presses': presses,
                       'syn': synthesize(arts, q)})
        if len(issues) >= MAX_ISSUES:
            break
    if not issues:
        sys.exit('수집된 이슈가 없습니다. API 키·네트워크를 확인하세요.')
    # 양쪽 성향이 모두 잡힌(균형 잡힌) 이슈를 기본 화면으로
    issues.sort(key=lambda i: (-min(i['counts']['p'], i['counts']['c']),
                               -len(i['articles'])))
    return {'generated': datetime.now().strftime('%Y-%m-%d %H:%M'), 'issues': issues}


TEMPLATE = r'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>뉴스펙트럼 — 실데이터 시연</title>
<style>
  :root{
    --surface:#fcfcfb; --page:#f3f3f0; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
    --grid:#e1e0d9; --base:#c3c2b7; --border:rgba(11,11,11,.10);
    --prog:#2a78d6; --cons:#d03b3b; --neutral:#9b9a93; --neutral-bg:#f0efec;
    --prog-bg:#eaf2fc; --prog-ink:#1c5cab; --cons-bg:#fbeaea; --cons-ink:#a02c2c;
  }
  *{margin:0;padding:0;box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{background:var(--page);font-family:"Malgun Gothic",system-ui,-apple-system,"Segoe UI",sans-serif;
       color:var(--ink);padding:26px 18px;}
  .frame{max-width:1180px;margin:0 auto;background:var(--surface);border:1px solid var(--border);
         border-radius:14px;overflow:hidden;box-shadow:0 2px 14px rgba(11,11,11,.06);}
  /* ── 상단 바 ── */
  .topbar{display:flex;align-items:center;gap:16px;padding:14px 24px;border-bottom:1px solid var(--grid);}
  .logo{font-size:17px;font-weight:800;letter-spacing:-.3px;}
  .logo .sp{background:linear-gradient(90deg,var(--prog),var(--neutral),var(--cons));
            -webkit-background-clip:text;background-clip:text;color:transparent;}
  .live{font-size:11px;font-weight:700;color:var(--prog-ink);background:var(--prog-bg);
        border-radius:999px;padding:3px 10px;}
  .gen{margin-left:auto;font-size:12px;color:var(--muted);}
  /* ── 이슈 선택 칩 ── */
  .issues{display:flex;gap:8px;flex-wrap:wrap;padding:14px 24px 4px;}
  .chip{border:1px solid var(--grid);border-radius:10px;background:#fff;padding:9px 13px;cursor:pointer;
        display:flex;flex-direction:column;gap:6px;min-width:150px;transition:border-color .15s, box-shadow .15s;}
  .chip:hover{border-color:var(--base);}
  .chip.on{border-color:var(--ink);box-shadow:0 0 0 1px var(--ink);}
  .chip .t{font-size:12.5px;font-weight:700;letter-spacing:-.2px;}
  .chip .c{font-size:10.5px;color:var(--muted);}
  .mini{position:relative;width:100%;height:5px;border-radius:3px;
        background:linear-gradient(90deg,var(--prog) 0%,#b7d3f6 38%,var(--neutral-bg) 50%,#f3c1c1 62%,var(--cons) 100%);}
  .mini i{position:absolute;top:-2.5px;width:10px;height:10px;border-radius:50%;background:#fff;
          border:2.5px solid var(--ink);transform:translateX(-50%);}
  /* ── 이슈 헤더 + KPI ── */
  .issue{padding:16px 24px 0;}
  .issue h1{font-size:20px;letter-spacing:-.3px;}
  .kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:14px 24px 4px;}
  .kpi{border:1px solid var(--grid);border-radius:12px;padding:12px 14px;}
  .kpi .l{font-size:11px;color:var(--muted);margin-bottom:5px;}
  .kpi .v{font-size:20px;font-weight:800;letter-spacing:-.4px;}
  .kpi .v small{font-size:11.5px;font-weight:400;color:var(--ink2);margin-left:4px;}
  /* ── 스펙트럼 (비스웜) ── */
  .spectrum{margin:14px 24px 8px;padding:16px 20px 12px;border:1px solid var(--grid);border-radius:12px;}
  .spectrum .caphead{display:flex;align-items:baseline;gap:14px;margin-bottom:6px;flex-wrap:wrap;}
  .spectrum .cap{font-size:12.5px;color:var(--ink);font-weight:700;}
  .legend{display:flex;gap:12px;font-size:11px;color:var(--ink2);margin-left:auto;}
  .legend b{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:4px;vertical-align:-1px;}
  .swarm{position:relative;margin:6px 8px 0;}
  .axis{position:relative;height:8px;border-radius:4px;
        background:linear-gradient(90deg,var(--prog) 0%,#b7d3f6 38%,var(--neutral-bg) 50%,#f3c1c1 62%,var(--cons) 100%);}
  .zero{position:absolute;top:-4px;bottom:-4px;width:2px;background:var(--surface);
        outline:1px solid var(--base);left:50%;}
  .ticks{position:relative;height:18px;font-size:10.5px;color:var(--muted);}
  .ticks span{position:absolute;transform:translateX(-50%);top:4px;}
  .dots{position:relative;}
  .adot{position:absolute;border-radius:50%;border:2px solid var(--surface);
        transform:translate(-50%,0);cursor:pointer;transition:transform .1s;}
  .adot:hover{transform:translate(-50%,0) scale(1.18);z-index:3;}
  .adot.p{background:var(--prog)} .adot.n{background:var(--neutral)} .adot.c{background:var(--cons)}
  .plab{position:absolute;transform:translateX(-50%);font-size:10px;color:var(--muted);
        white-space:nowrap;pointer-events:none;}
  .meanpin{position:absolute;transform:translateX(-50%);text-align:center;z-index:2;pointer-events:none;}
  .meanpin .flag{font-size:10.5px;font-weight:700;color:var(--ink);background:#fff;border:1px solid var(--base);
                 border-radius:6px;padding:2px 7px;white-space:nowrap;}
  .meanpin .stem{width:2px;height:12px;background:var(--ink);margin:0 auto;}
  .tip{position:fixed;display:none;z-index:9;background:#fff;border:1px solid var(--base);border-radius:8px;
       padding:8px 11px;font-size:11.5px;line-height:1.5;color:var(--ink2);
       box-shadow:0 4px 14px rgba(11,11,11,.12);max-width:280px;pointer-events:none;}
  .tip b{color:var(--ink);}
  /* ── 3열 관점 ── */
  .cols{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;padding:12px 24px 8px;}
  .col h2{font-size:13px;padding:8px 12px;border-radius:8px;margin-bottom:10px;
          display:flex;justify-content:space-between;align-items:center;}
  .col.pro h2{background:var(--prog-bg);color:var(--prog-ink);}
  .col.neu h2{background:var(--neutral-bg);color:var(--ink2);}
  .col.con h2{background:var(--cons-bg);color:var(--cons-ink);}
  .card{display:block;border:1px solid var(--grid);border-radius:10px;padding:11px 13px;margin-bottom:9px;
        background:#fff;text-decoration:none;color:inherit;transition:border-color .15s;}
  .card:hover{border-color:var(--base);}
  .card.hl{border-color:var(--ink);box-shadow:0 0 0 1px var(--ink);}
  .card .src{font-size:11.5px;color:var(--muted);display:flex;justify-content:space-between;align-items:center;gap:8px;}
  .badge{font-size:10.5px;font-weight:700;border-radius:6px;padding:2px 7px;white-space:nowrap;}
  .badge.p{background:var(--prog-bg);color:var(--prog-ink);}
  .badge.n{background:var(--neutral-bg);color:var(--ink2);}
  .badge.c{background:var(--cons-bg);color:var(--cons-ink);}
  .card .tit{font-size:13px;font-weight:700;line-height:1.45;margin-top:7px;letter-spacing:-.2px;}
  .more{font-size:11.5px;color:var(--muted);text-align:center;padding:4px 0 2px;}
  /* 관점 종합 (추출 요약) */
  .syn{border:1px solid var(--grid);border-left:3px solid var(--base);border-radius:10px;
       padding:11px 13px;margin-bottom:10px;font-size:11.8px;color:var(--ink2);line-height:1.65;background:#fff;}
  .col.pro .syn{border-left-color:var(--prog);}
  .col.neu .syn{border-left-color:var(--neutral);}
  .col.con .syn{border-left-color:var(--cons);}
  .syn .hd{font-size:11px;font-weight:800;color:var(--muted);margin-bottom:5px;letter-spacing:.2px;}
  .syn .kw{display:inline-block;background:var(--neutral-bg);border-radius:6px;padding:1px 7px;
           font-size:11px;font-weight:700;color:var(--ink);margin:0 3px 3px 0;}
  .syn .q{display:block;margin-top:6px;color:var(--ink);}
  .syn .q small{color:var(--muted);font-size:10.5px;}
  /* ── 하단 패널 ── */
  .dash{display:grid;grid-template-columns:1.15fr 1fr 1.25fr;gap:14px;padding:6px 24px 22px;}
  .panel{border:1px solid var(--grid);border-radius:12px;padding:14px 16px;}
  .panel .h{font-size:12.5px;font-weight:800;margin-bottom:12px;}
  .hbars .row{display:flex;align-items:center;gap:10px;margin-bottom:9px;font-size:11.5px;color:var(--ink2);}
  .hbars .lab{width:34px;flex:none;}
  .hbars .track{flex:1;height:14px;border-radius:4px;background:var(--neutral-bg);position:relative;overflow:hidden;}
  .hbars .fill{position:absolute;inset:0 auto 0 0;border-radius:4px 3px 3px 4px;}
  .hbars .fill.p{background:var(--prog)} .hbars .fill.n{background:var(--base)} .hbars .fill.c{background:var(--cons)}
  .hbars .val{width:56px;flex:none;text-align:right;font-weight:700;color:var(--ink);}
  .gauge{position:relative;height:8px;border-radius:4px;margin:34px 6px 6px;
         background:linear-gradient(90deg,var(--prog) 0%,#b7d3f6 38%,var(--neutral-bg) 50%,#f3c1c1 62%,var(--cons) 100%);}
  .gpin{position:absolute;top:-28px;transform:translateX(-50%);text-align:center;}
  .gpin .v{font-size:15px;font-weight:800;}
  .gpin .stem{width:2px;height:14px;background:var(--ink);margin:2px auto 0;}
  .glab{display:flex;justify-content:space-between;font-size:10.5px;color:var(--muted);padding:0 6px;margin-top:6px;}
  .diag{font-size:12px;color:var(--ink2);line-height:1.75;}
  .diag b{color:var(--ink);}
  .method{font-size:11.8px;color:var(--ink2);line-height:1.7;}
  .method b{color:var(--ink);}
  .note{max-width:1180px;margin:10px auto 0;font-size:11.5px;color:var(--muted);line-height:1.6;}
  @media (max-width:900px){
    .kpis{grid-template-columns:repeat(2,1fr);}
    .cols,.dash{grid-template-columns:1fr;}
  }
</style>
</head>
<body>
<div class="frame">
  <div class="topbar">
    <div class="logo">뉴스<span class="sp">펙트럼</span></div>
    <span class="live">실데이터 시연 · 네이버 검색 API</span>
    <div class="gen">수집 __GENERATED__</div>
  </div>
  <div class="issues" id="issues"></div>
  <div class="issue"><h1 id="issueTitle"></h1></div>
  <div class="kpis" id="kpis"></div>
  <div class="spectrum">
    <div class="caphead">
      <div class="cap">이슈 스펙트럼 — 보도 언론사를 좌표에 배치, 원 면적은 기사 수 (−1 진보측 ← 0 중립 → +1 보수측)</div>
      <div class="legend">
        <span><b style="background:var(--prog)"></b>진보측</span>
        <span><b style="background:var(--neutral)"></b>중립</span>
        <span><b style="background:var(--cons)"></b>보수측</span>
      </div>
    </div>
    <div class="swarm">
      <div class="dots" id="dots"></div>
      <div class="axis"><div class="zero"></div></div>
      <div class="ticks">
        <span style="left:0%">−1.0</span><span style="left:25%">−0.5</span>
        <span style="left:50%">0</span><span style="left:75%">+0.5</span>
        <span style="left:100%">+1.0</span>
      </div>
    </div>
  </div>
  <div class="cols" id="cols"></div>
  <div class="dash">
    <div class="panel">
      <div class="h">보도 분포 — 성향권별 기사 수</div>
      <div class="hbars" id="hbars"></div>
    </div>
    <div class="panel">
      <div class="h">커버리지 좌표 — 기사 좌표 평균</div>
      <div class="gauge" id="gauge"></div>
      <div class="glab"><span>−1 진보측</span><span>0</span><span>+1 보수측</span></div>
    </div>
    <div class="panel">
      <div class="h">균형 진단</div>
      <div class="diag" id="diag"></div>
    </div>
  </div>
  <div class="dash" style="grid-template-columns:1fr;padding-top:0;">
    <div class="panel method">
      <b>방법 주기</b> — 기사 좌표는 소속 언론사의 스펙트럼 좌표를 사용했다.
      언론사 좌표는 『2025 언론수용자 조사』의 정치성향별 신뢰·열독 교차 재분석으로 산출한 값이며(보고서 부록 A-2 방법),
      기사 단위 스탠스 판정(TF-IDF·문장 임베딩, 보고서 5장 파일럿)은 이 데모에 적용하지 않았다.
      각 열 상단의 &ldquo;관점 종합&rdquo;은 해당 성향권 기사들의 제목·요약문에서 변별도(TF-IDF식) 상위 키워드와
      대표 문장을 추출해 그대로 인용한 것으로, 생성형 요약이 아니다.
      기사는 네이버 검색 API 관련도순 상위 100건 중 좌표 산출 대상 언론사(20곳)의 기사만 표시한다.
    </div>
  </div>
</div>
<div class="note">뉴스펙트럼 시연 페이지 — 언론 이념 편향의 구조 분석과 관점 비교 서비스 제안(보고서 5장) 부속 데모.
기사 제목·링크 출처: 네이버 뉴스 검색 API (수집 __GENERATED__). 이 파일은 단일 HTML로, 열람 시 네트워크 연결이 필요 없다.</div>
<div class="tip" id="tip"></div>
<script>
const DATA = __DATA__;
const $ = (s) => document.querySelector(s);
const esc = (s) => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
const bucket = (s) => s < -0.10 ? 'p' : (s > 0.10 ? 'c' : 'n');
const fmt = (v) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(2);
const pos = (s) => (s + 1) / 2 * 100;
let cur = 0;

function renderChips(){
  $('#issues').innerHTML = DATA.issues.map((it, i) => `
    <div class="chip ${i===cur?'on':''}" onclick="show(${i})">
      <span class="t">${esc(it.q)}</span>
      <span class="mini"><i style="left:${pos(it.mean)}%"></i></span>
      <span class="c">기사 ${it.articles.length}건 · 언론사 ${it.presses}곳 · 좌표 ${fmt(it.mean)}</span>
    </div>`).join('');
}

function show(i){
  cur = i;
  renderChips();
  const it = DATA.issues[i];
  $('#issueTitle').textContent = it.q;
  const n = it.articles.length;
  $('#kpis').innerHTML = `
    <div class="kpi"><div class="l">분석 기사</div><div class="v">${n}<small>건</small></div></div>
    <div class="kpi"><div class="l">보도 언론사</div><div class="v">${it.presses}<small>곳</small></div></div>
    <div class="kpi"><div class="l">커버리지 좌표 (평균)</div><div class="v">${fmt(it.mean)}</div></div>
    <div class="kpi"><div class="l">진보측 / 중립 / 보수측</div>
      <div class="v">${it.counts.p}<small>/</small>${it.counts.n}<small>/</small>${it.counts.c}<small>건</small></div></div>`;

  // 언론사 버블: 같은 언론사 기사를 원 하나로 집계 (면적 ∝ 기사 수)
  const arts = it.articles.map((a, k) => ({...a, id: 'a' + k}));
  const byPress = {};
  arts.forEach(a => {
    const g = byPress[a.press] = byPress[a.press] ||
      {press: a.press, score: a.score, count: 0, first: a.id, sample: []};
    g.count++;
    if (g.sample.length < 2) g.sample.push(a.title);
  });
  const groups = Object.values(byPress).sort((x, y) => x.score - y.score);
  const W = $('#dots').clientWidth || 1100;
  const dia = (c) => Math.min(26, 10 + 4 * Math.sqrt(c - 1));
  const ROWH = 30;
  const placed = [];
  groups.forEach(g => {
    const x = pos(g.score) / 100 * W, r = dia(g.count) / 2;
    let row = 0;
    while (placed.some(p => p.row === row && Math.abs(p.x - x) < p.r + r + 4)) row++;
    Object.assign(g, {x, r, row});
    placed.push(g);
  });
  const maxRow = Math.max(...groups.map(g => g.row));
  const topCounts = [...groups].sort((x, y) => y.count - x.count)
                               .slice(0, 3).map(g => g.press);
  const H = (maxRow + 1) * ROWH + 44;
  $('#dots').style.height = H + 'px';
  $('#dots').innerHTML = groups.map(g => {
    const d = dia(g.count);
    const extra = g.count - g.sample.length;
    const tipTitles = g.sample.map(esc).join('<br>· ') +
                      (extra > 0 ? `<br>외 ${extra}건` : '');
    return `
    <span class="adot ${bucket(g.score)}"
      style="left:${pos(g.score)}%;bottom:${g.row * ROWH + (ROWH - d) / 2}px;width:${d}px;height:${d}px"
      data-tip="<b>${esc(g.press)}</b> · ${fmt(g.score)} · 기사 ${g.count}건<br>· ${tipTitles}"
      onclick="focusPress('${esc(g.press)}','${g.first}')"></span>` +
    (topCounts.includes(g.press) ? `
    <span class="plab" style="left:${pos(g.score)}%;bottom:${g.row * ROWH + (ROWH + d) / 2 + 2}px">${esc(g.press)} ${g.count}</span>` : '');
  }).join('')
    + `<div class="meanpin" style="left:${pos(it.mean)}%;bottom:${H - 36}px">
         <span class="flag">평균 ${fmt(it.mean)}</span><div class="stem"></div></div>`;

  // 3열 카드
  const CAP = 8;
  const colDef = [
    ['pro', 'p', '진보측 보도', (a,b)=>a.score-b.score],
    ['neu', 'n', '중립 보도',   (a,b)=>Math.abs(a.score)-Math.abs(b.score)],
    ['con', 'c', '보수측 보도', (a,b)=>b.score-a.score]];
  $('#cols').innerHTML = colDef.map(([cls, bk, label, cmp]) => {
    const list = arts.filter(a => bucket(a.score) === bk).sort(cmp);
    const shown = list.slice(0, CAP);
    const sy = it.syn[bk];
    const pressNames = list.length ? [...new Set(list.map(a => a.press))] : [];
    const lead = sy ? `${label.replace(' 보도','측')} 시각은 ${sy.presses.slice(0,2).map(p => esc(p.replace(/\(\d+\)/,''))).join('·')} 등 ${pressNames.length}개 언론사 ${list.length}건에서 나타난다.` : '';
    const kwSent = (sy && sy.kws.length >= 2)
      ? ` 다른 성향권 대비 ${sy.kws.slice(0,3).map(k => `<span class="kw">${esc(k)}</span>`).join('')} 언급이 상대적으로 잦다.`
      : '';
    return `<div class="col ${cls}"><h2><span>${label}</span><span>${list.length}건</span></h2>
      ${sy ? `<div class="syn">
        <div class="hd">관점 종합 · 추출 요약</div>
        <div>${lead}${kwSent}</div>
        ${sy.quotes.map(q => `<span class="q">&ldquo;${esc(q.text)}&rdquo; <small>— ${esc(q.press)}</small></span>`).join('')}
      </div>` : ''}
      ${shown.map(a => `
        <a class="card" id="card-${a.id}" href="${esc(a.link)}" target="_blank" rel="noopener">
          <span class="src"><span>${esc(a.press)} · ${a.date}</span>
            <span class="badge ${bucket(a.score)}">${fmt(a.score)}</span></span>
          <div class="tit">${esc(a.title)}</div>
        </a>`).join('')}
      ${list.length > CAP ? `<div class="more">외 ${list.length - CAP}건 — 스펙트럼 원에서 확인</div>` : ''}
      ${list.length === 0 ? `<div class="more">이 수집분에는 해당 성향권 기사가 없습니다 — 그 자체가 커버리지 신호입니다.</div>` : ''}
    </div>`;
  }).join('');

  // 분포 바
  const mx = Math.max(it.counts.p, it.counts.n, it.counts.c, 1);
  $('#hbars').innerHTML = [['진보측','p',it.counts.p],['중립','n',it.counts.n],['보수측','c',it.counts.c]]
    .map(([l, k, v]) => `<div class="row"><span class="lab">${l}</span>
      <span class="track"><span class="fill ${k}" style="width:${v / mx * 100}%"></span></span>
      <span class="val">${v}건 (${Math.round(v / n * 100)}%)</span></div>`).join('');

  // 게이지 + 진단
  $('#gauge').innerHTML = `<div class="gpin" style="left:${pos(it.mean)}%">
      <div class="v">${fmt(it.mean)}</div><div class="stem"></div></div>`;
  const domi = it.counts.p > it.counts.c ? ['진보측', it.counts.p] :
               it.counts.c > it.counts.p ? ['보수측', it.counts.c] : null;
  const share = domi ? Math.round(domi[1] / n * 100) : 0;
  const kwP = it.syn.p && it.syn.p.kws.length ? it.syn.p.kws[0] : null;
  const kwC = it.syn.c && it.syn.c.kws.length ? it.syn.c.kws[0] : null;
  $('#diag').innerHTML =
    (Math.abs(it.mean) <= 0.05
      ? `현재 수집분 기준 커버리지 좌표는 <b>${fmt(it.mean)}</b>로 중립권입니다.`
      : `현재 수집분 기준 커버리지 좌표는 <b>${fmt(it.mean)}</b>로 ${it.mean < 0 ? '진보측' : '보수측'}에 기울어 있습니다.`)
    + (domi ? ` 방향성 있는 보도 중에는 <b>${domi[0]}</b> 기사가 ${domi[1]}건(${share}%)으로 더 많습니다.` : '')
    + (kwP && kwC ? ` 같은 사안을 진보측은 &lsquo;<b>${esc(kwP)}</b>&rsquo;, 보수측은 &lsquo;<b>${esc(kwC)}</b>&rsquo; 중심의 어휘로 다룹니다.` : '')
    + ` 한쪽 관점만 소비하고 있지 않은지, 반대편 열의 기사 제목과 비교해 보세요.`;
}

function focusPress(press, firstId){
  document.querySelectorAll('.card.hl').forEach(c => c.classList.remove('hl'));
  let first = null;
  document.querySelectorAll('.card').forEach(c => {
    if (c.querySelector('.src span').textContent.startsWith(press)){
      c.classList.add('hl');
      first = first || c;
    }
  });
  if (first) first.scrollIntoView({block: 'center'});
}

// 툴팁
const tip = $('#tip');
document.addEventListener('mousemove', (e) => {
  const t = e.target.closest('[data-tip]');
  if (t){
    tip.innerHTML = t.dataset.tip;
    tip.style.display = 'block';
    const w = tip.offsetWidth, x = Math.min(e.clientX + 14, innerWidth - w - 10);
    tip.style.left = x + 'px';
    tip.style.top = (e.clientY + 16) + 'px';
  } else tip.style.display = 'none';
});

renderChips();
show(0);
</script>
</body>
</html>
'''


def main():
    print('[뉴스펙트럼 시연 생성]')
    data = build_data()
    page = (TEMPLATE
            .replace('__DATA__', json.dumps(data, ensure_ascii=False))
            .replace('__GENERATED__', data['generated']))
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(page)
    total = sum(len(i['articles']) for i in data['issues'])
    print(f'완료: {os.path.basename(OUT)} — 이슈 {len(data["issues"])}개, 기사 {total}건')


if __name__ == '__main__':
    main()
