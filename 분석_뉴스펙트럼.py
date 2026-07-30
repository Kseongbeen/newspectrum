"""
언론 이념 편향의 구조 분석과 관점 비교 서비스 「뉴스펙트럼」 제안

실행:  python 분석_뉴스펙트럼.py
입력:  한국언론진흥재단 제공 원자료 3종 (아래 PATHS 참조)
출력:  분석_결과/그림/*.png          (보고서 수록 그림)
       분석_결과/분석_통계_재현.json  (본문 인용 통계 재현 값)

- 언론수용자 조사는 인구비례 가중치(WT)를 적용해 집계한다 (보고서 3.2절).
- 언론인 조사(SAV)는 파일 내장 인코딩으로 읽는다 (encoding 지정 시 오류).
- 그림 5-2는 파일럿 산출물(분석_결과/파일럿/파일럿_결과.json)에서 재현한다.
  파일럿 원문 수집·전처리 절차는 보고서 부록 B 참조.
- 표 4-2(가장 영향력 있는 언론사·매체)는 공표 통계표(191쪽) 값을 사용하며,
  스크립트에는 해당 값을 상수로 두었다 (원자료 문항 비공개 항목).
"""
import json
import os
import sys

import numpy as np
import pandas as pd
import pyreadstat
from scipy import stats as sps

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ──────────────────────────────────────────────────────────────
# 0. 경로·스타일 상수
# ──────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
PATHS = {
    'journalist_sav': os.path.join(BASE, '[로데이터] 2025 언론인 조사 원본 데이터.SAV'),
    'audience_sav':   os.path.join(BASE, '3. 2025 언론수용자 조사_최종데이터.SAV'),
    'youth_xlsx':     os.path.join(BASE, '2025 10대 청소년 미디어 이용조사_데이터.xlsx'),
    'pilot_json':     os.path.join(BASE, '자료', '파일럿', '파일럿_결과.json'),
}
OUT_FIG = os.path.join(BASE, '분석_결과', '그림')
OUT_JSON = os.path.join(BASE, '분석_결과', '분석_통계_재현.json')
os.makedirs(OUT_FIG, exist_ok=True)

# 색: 검증된 팔레트 (진보/음(−)=파랑, 보수/양(+)=빨강, 중립·비강조=회색)
C_BLUE = '#2a78d6'      # 범주 1 / 강조
C_RED = '#e34948'       # 범주 2 / 보수측
C_BLUE_L = '#6da7ec'    # 파랑 밝은 단계 (덤벨 '개인'·'전체')
C_BLUE_D = '#184f95'    # 파랑 어두운 단계 (덤벨 '논조'·'19~29세')
C_GRAY = '#c3c2b7'      # 비강조 막대·중립
C_GRAY_SEG = '#d8d7d0'  # 스택 중립 구간
INK = '#0b0b0b'         # 본문 잉크
INK2 = '#52514e'        # 보조 잉크 (값 라벨)
MUTED = '#898781'       # 축 라벨
GRID = '#e1e0d9'        # 격자 헤어라인
AXIS = '#c3c2b7'        # 축선

for name in ('Malgun Gothic', 'NanumGothic'):
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        plt.rcParams['font.family'] = name
        break
plt.rcParams.update({
    'axes.unicode_minus': False,
    'figure.facecolor': 'white', 'axes.facecolor': 'white',
    'axes.edgecolor': AXIS, 'axes.linewidth': 0.8,
    'axes.grid': False, 'grid.color': GRID, 'grid.linewidth': 0.8,
    'xtick.color': MUTED, 'ytick.color': INK2,
    'xtick.labelsize': 9, 'ytick.labelsize': 9.5,
    'text.color': INK, 'axes.labelcolor': INK2,
    'font.size': 10, 'savefig.dpi': 200, 'savefig.bbox': 'tight',
    'savefig.facecolor': 'white',
})


def despine(ax, keep=('bottom',)):
    for side in ('top', 'right', 'left', 'bottom'):
        ax.spines[side].set_visible(side in keep)


def save(fig, fname):
    path = os.path.join(OUT_FIG, fname)
    fig.savefig(path)
    plt.close(fig)
    print('  그림 저장:', os.path.relpath(path, BASE))


REPRO = {}  # 본문 인용 통계 재현 값

# ──────────────────────────────────────────────────────────────
# 1. 『2025 한국의 언론인』 (기자 2,020명)
# ──────────────────────────────────────────────────────────────
print('[1] 언론인 조사 로드·분석')
jr, jmeta = pyreadstat.read_sav(PATHS['journalist_sav'], encoding=None)
assert len(jr) == 2020
TYPE_LABELS = {int(k): v for k, v in jmeta.variable_value_labels['SQ4_1'].items()}

q27, q28 = jr['q27'], jr['q28']
t_all, p_all = sps.ttest_rel(q28, q27)
REPRO['언론인_q27평균'] = round(q27.mean(), 2)
REPRO['언론인_q28평균'] = round(q28.mean(), 2)
REPRO['언론인_격차'] = round((q28 - q27).mean(), 2)
REPRO['언론인_대응t'] = round(t_all, 2)

# 매체 유형별 (스포츠일간+외국어일간은 표본 소수로 원분석과 동일하게 개별 유지)
by_type = []
for code, label in TYPE_LABELS.items():
    sub = jr[jr['SQ4_1'] == code]
    if len(sub) < 20:      # 외국어일간(n=2)은 보고서 표 4-1과 동일하게 제외
        continue
    t, p = sps.ttest_rel(sub['q28'], sub['q27'])
    by_type.append({
        '유형': label, 'n': len(sub),
        '개인': sub['q27'].mean(), '논조': sub['q28'].mean(),
        '격차': (sub['q28'] - sub['q27']).mean(),
        '좌표': (sub['q28'].mean() - 5) / 5, 't': t, 'p': p,
    })
by_type.sort(key=lambda d: d['격차'], reverse=True)
REPRO['매체유형_수'] = len(by_type)
REPRO['유의한_격차_유형수'] = sum(1 for d in by_type if d['p'] < .05)

gap_abs = (q28 - q27).abs()
REPRO['격차2점이상_%'] = round((gap_abs >= 2).mean() * 100, 1)
REPRO['격차3점이상_%'] = round((gap_abs >= 3).mean() * 100, 1)
r_q11, p_q11 = sps.pearsonr(gap_abs, jr['q11'])
REPRO['격차x자유도_r'] = round(r_q11, 2)

# q12: 언론 자유 제한 요인 (1~3순위 합산)
Q12_LABELS = {int(k): v for k, v in jmeta.variable_value_labels['q12'].items()}
q12_cols = ['q12', 'q12_m2', 'q12_m3']
q12_sum = {}
for code, label in Q12_LABELS.items():
    hit = (jr[q12_cols] == code).any(axis=1)
    q12_sum[label] = round(hit.mean() * 100, 1)
REPRO['q12_광고주_%'] = q12_sum['광고주']

# ── 그림 4-1: 매체 유형별 개인 vs 논조 덤벨 ─────────────────────
fig, ax = plt.subplots(figsize=(7.6, 5.2))
rows = by_type  # 격차 내림차순
y = np.arange(len(rows))[::-1]
for yi, d in zip(y, rows):
    ax.plot([d['개인'], d['논조']], [yi, yi], color=AXIS, lw=1.2, zorder=1)
ax.scatter([d['개인'] for d in rows], y, s=58, color=C_BLUE_L, zorder=3,
           edgecolors='white', linewidths=1.5, label='기자 개인 이념 성향')
ax.scatter([d['논조'] for d in rows], y, s=58, color=C_BLUE_D, zorder=3,
           edgecolors='white', linewidths=1.5, label='소속사 논조 평가')
for yi, d in zip(y, rows):
    ax.annotate(f"+{d['격차']:.2f}" if d['격차'] > 0.005 else f"{d['격차']:.2f}",
                (max(d['개인'], d['논조']) + 0.13, yi), va='center', fontsize=8.5,
                color=INK2)
ax.axvline(5, color=GRID, lw=0.8, zorder=0)
ax.set_yticks(y)
ax.set_yticklabels([f"{d['유형']} (n={d['n']})" for d in rows])
ax.set_xlim(3.4, 7.6)
ax.set_xlabel('이념 성향 (0=매우 진보, 10=매우 보수)')
ax.legend(loc='lower right', frameon=False, fontsize=9)
despine(ax)
ax.xaxis.grid(True, color=GRID, lw=0.8)
ax.set_axisbelow(True)
save(fig, '그림4-1_매체유형별_이념격차_덤벨.png')

# ── 그림 4-2: 매체 유형별 논조 정규화 좌표 (다이버징 막대) ──────
fig, ax = plt.subplots(figsize=(7.6, 4.6))
rows2 = sorted(by_type, key=lambda d: d['좌표'])
y = np.arange(len(rows2))
vals = [d['좌표'] for d in rows2]
cols = [C_GRAY if abs(v) < 0.03 else (C_RED if v > 0 else C_BLUE) for v in vals]
ax.barh(y, vals, height=0.55, color=cols, zorder=3)
for yi, v in zip(y, vals):
    ax.annotate(f'{v:+.2f}' if abs(v) >= 0.005 else '0.00',
                (v + (0.008 if v >= 0 else -0.008), yi),
                ha='left' if v >= 0 else 'right', va='center',
                fontsize=8.5, color=INK2)
ax.axvline(0, color=AXIS, lw=0.8)
ax.set_yticks(y)
ax.set_yticklabels([d['유형'] for d in rows2])
ax.set_xlim(-0.28, 0.46)
ax.set_xlabel('소속사 논조 정규화 좌표  (-1 진보측 ← 0 → +1 보수측)')
despine(ax, keep=())
ax.xaxis.grid(True, color=GRID, lw=0.8)
ax.set_axisbelow(True)
save(fig, '그림4-2_매체유형별_논조좌표.png')

# ── 그림 4-3: 개인–소속사 격차 분포 (강조 히스토그램) ───────────
fig, ax = plt.subplots(figsize=(7.2, 3.4))
bins = np.arange(0, 11)
pct = [(gap_abs == b).mean() * 100 for b in bins]
cols = [C_BLUE if b >= 2 else C_GRAY for b in bins]
ax.bar(bins, pct, width=0.62, color=cols, zorder=3)
for b, v in zip(bins, pct):
    if v >= 0.5:
        ax.annotate(f'{v:.1f}', (b, v + 0.7), ha='center', fontsize=8.5, color=INK2)
share2 = (gap_abs >= 2).mean() * 100
ax.annotate(f'격차 2점 이상 {share2:.1f}%', xy=(5.6, max(pct) * 0.82),
            fontsize=10.5, color=C_BLUE, fontweight='bold')
ax.set_xticks(bins)
ax.set_xlabel('|소속사 논조 - 개인 성향| (점)')
ax.set_ylabel('기자 비율 (%)')
ax.set_ylim(0, max(pct) * 1.18)
despine(ax)
ax.yaxis.grid(True, color=GRID, lw=0.8)
ax.set_axisbelow(True)
save(fig, '그림4-3_개인조직_격차분포.png')

# ── 그림 4-4: 언론 자유 제한 요인 (1~3순위 합산) ────────────────
fig, ax = plt.subplots(figsize=(7.2, 3.6))
order = sorted(q12_sum.items(), key=lambda kv: kv[1], reverse=True)[:7]
names = [('편집·보도국 간부' if k.startswith('편집/보도국') else
          '언론 관련 법·제도' if k.startswith('언론 관련') else
          '독자·시청자·네티즌' if k.startswith('독자') else k) for k, v in order]
vals = [v for k, v in order]
internal = {'광고주', '편집·보도국 간부', '사주/사장'}
cols = [C_BLUE if n in internal else C_GRAY for n in names]
y = np.arange(len(names))[::-1]
ax.barh(y, vals, height=0.55, color=cols, zorder=3)
for yi, v in zip(y, vals):
    ax.annotate(f'{v:.1f}', (v + 0.8, yi), va='center', fontsize=8.5, color=INK2)
ax.set_yticks(y)
ax.set_yticklabels(names)
ax.set_xlim(0, 74)
ax.set_xlabel('응답 비율 (%, 1~3순위 합산, n=2,020)')
despine(ax, keep=())
ax.xaxis.grid(True, color=GRID, lw=0.8)
ax.set_axisbelow(True)
save(fig, '그림4-4_언론자유_제한요인.png')

# ──────────────────────────────────────────────────────────────
# 2. 『2025 언론수용자 조사』 (성인 6,000명, 가중치 WT)
# ──────────────────────────────────────────────────────────────
print('[2] 수용자 조사 로드·분석')
au, ameta = pyreadstat.read_sav(PATHS['audience_sav'], encoding='cp949')
assert len(au) == 6000
W = au['WT']


def wmean(mask, base=None):
    """가중 비율(%). base=None이면 전체."""
    b = W if base is None else W[base]
    return float(W[mask].sum() / b.sum() * 100)


# Q84 주 이용 경로 → 7개 그룹
Q84_LABELS = {int(k): v for k, v in ameta.variable_value_labels['Q84'].items()}


def q84_group(label):
    if '뉴스 모음' in label or '인공지능' in label or '뉴스레터' in label or '이용한 적 없음' in label:
        return '기타·이용 안 함'
    if '텔레비전' in label: return '텔레비전'
    if '포털' in label and '인터넷' in label: return '포털'
    if '동영상' in label or '숏폼' in label: return '동영상·숏폼'
    if 'SNS' in label or '커뮤니티' in label or '메신저' in label or '블로그' in label: return 'SNS·커뮤니티·메신저'
    if '홈페이지' in label or '앱(조선일보' in label: return '언론사 홈페이지·앱'
    if '종이신문' in label or '라디오' in label: return '전통매체(신문·라디오)'
    return '기타·이용 안 함'


au['Q84G'] = au['Q84'].map(lambda v: q84_group(Q84_LABELS[int(v)]))
q84g = {g: round(wmean(au['Q84G'] == g), 1) for g in au['Q84G'].unique()}
REPRO['Q84_언론사채널_%'] = q84g.get('언론사 홈페이지·앱')
REPRO['Q84_텔레비전_%'] = q84g.get('텔레비전')
REPRO['Q84_포털_%'] = q84g.get('포털')

# Q92 (모름/무응답=9999 제외, 응답자 기준) · Q93
b92_1 = au['Q92_1'].isin([1, 2])
b92_4 = au['Q92_4'].isin([1, 2])
REPRO['Q92_포털_언론인식_%'] = round(wmean(au['Q92_1'] == 1, base=b92_1), 1)
REPRO['Q92_동영상_언론인식_%'] = round(wmean(au['Q92_4'] == 1, base=b92_4), 1)
q93 = au['Q93'].dropna()
w93 = W[q93.index]
q93_dist = {
    '모른다(1~2점)': float(w93[q93 <= 2].sum() / w93.sum() * 100),
    '반반이다(3점)': float(w93[q93 == 3].sum() / w93.sum() * 100),
    '알고 있다(4~5점)': float(w93[q93 >= 4].sum() / w93.sum() * 100),
}
REPRO['Q93_안다_%'] = round(q93_dist['알고 있다(4~5점)'], 1)
REPRO['Q93_n'] = int(q93.notna().sum())

# Q56 온라인 동영상 플랫폼 뉴스 이용 방법 (이용자 기준; 3점(가끔) 이상·4점(자주) 이상)
b56 = au['Q56_3'].notna()
REPRO['Q56_n'] = int(b56.sum())
REPRO['Q56_추천영상_가끔이상_%'] = round(wmean(b56 & (au['Q56_3'] >= 3), base=b56), 1)
REPRO['Q56_추천영상_자주이상_%'] = round(wmean(b56 & (au['Q56_3'] >= 4), base=b56), 1)
REPRO['Q56_채널구독_가끔이상_%'] = round(wmean(b56 & (au['Q56_2'] >= 3), base=b56), 1)
REPRO['Q56_채널구독_자주이상_%'] = round(wmean(b56 & (au['Q56_2'] >= 4), base=b56), 1)

# Q91 뉴스 문제점 (심각=4~5점 비율)
Q91_NAMES = {'Q91_1': '무분별한 속보', 'Q91_2': '낚시성 기사', 'Q91_3': '어뷰징 기사',
             'Q91_4': '편파적 기사', 'Q91_5': '선정적 기사', 'Q91_6': '광고성 기사',
             'Q91_7': '받아쓰기 기사', 'Q91_8': '허위·조작정보(가짜뉴스)'}
q91 = {name: round(wmean(au[col] >= 4), 1) for col, name in Q91_NAMES.items()}
REPRO['Q91_편파_%'] = q91['편파적 기사']

# BQ7 성향 재범주화 + 교차
au['성향'] = pd.cut(au['BQ7'], [0, 2, 3, 5], labels=['진보', '중도', '보수'])
ct = pd.crosstab(au['성향'], au['Q84G'], au['WT'], aggfunc='sum', normalize='index') * 100
# 카이제곱 검정은 비가중 응답 빈도 기준 (가중 빈도 검정은 유효 표본 수를 왜곡)
chi2, chi_p, chi_df, _ = sps.chi2_contingency(pd.crosstab(au['성향'], au['Q84G']))
REPRO['BQ7xQ84_chi2'] = round(chi2, 1)
bias_by = {g: round(wmean((au['Q91_4'] >= 4) & (au['성향'] == g), base=(au['성향'] == g)), 1)
           for g in ['진보', '중도', '보수']}
REPRO['편파심각_성향별'] = bias_by

# ── 그림 4-5: 가장 영향력 있는 언론사·매체 — 전체 vs 19~29세 (덤벨) ──
# 공표 통계표(191쪽, 표 89) 값. 원자료 재계산 대상 아님(공개 문항 아님).
INFL = [('MBC', 28.4, 22.8), ('KBS', 27.7, 16.4), ('네이버(포털)', 10.0, 20.2),
         ('YTN', 7.5, 8.0), ('JTBC', 5.4, 9.3), ('SBS', 4.9, 4.5),
         ('유튜브', 2.6, 4.3), ('연합뉴스TV', 2.4, 1.9), ('TV조선', 2.3, 0.7),
         ('조선일보', 1.1, 0.1)]
fig, ax = plt.subplots(figsize=(7.2, 4.4))
y = np.arange(len(INFL))[::-1]
for yi, (nm, a, b) in zip(y, INFL):
    ax.plot([a, b], [yi, yi], color=AXIS, lw=1.2, zorder=1)
ax.scatter([a for _, a, _ in INFL], y, s=58, color=C_BLUE_L, zorder=3,
           edgecolors='white', linewidths=1.5, label='전체 (n=6,000)')
ax.scatter([b for _, _, b in INFL], y, s=58, color=C_BLUE_D, zorder=3,
           edgecolors='white', linewidths=1.5, label='19~29세 (n=885)')
for yi, (nm, a, b) in zip(y, INFL):
    if nm in ('네이버(포털)', '유튜브', 'KBS'):
        ax.annotate(f'{a:.1f} → {b:.1f}', (max(a, b) + 0.7, yi), va='center',
                    fontsize=8.5, color=INK2)
ax.set_yticks(y)
ax.set_yticklabels([nm for nm, _, _ in INFL])
ax.set_xlim(0, 33)
ax.set_xlabel('가장 영향력 있는 언론사·매체 응답 비율 (%)')
ax.legend(loc='lower right', frameon=False, fontsize=9)
despine(ax, keep=())
ax.xaxis.grid(True, color=GRID, lw=0.8)
ax.set_axisbelow(True)
save(fig, '그림4-5_영향력매체_전체vs2029.png')

# ── 그림 4-6: 뉴스 주 이용 경로 (언론사 채널 강조) ──────────────
fig, ax = plt.subplots(figsize=(7.2, 3.3))
order6 = sorted(q84g.items(), key=lambda kv: kv[1], reverse=True)
names = [k for k, v in order6]
vals = [v for k, v in order6]
cols = [C_BLUE if n == '언론사 홈페이지·앱' else C_GRAY for n in names]
y = np.arange(len(names))[::-1]
ax.barh(y, vals, height=0.55, color=cols, zorder=3)
for yi, v, n in zip(y, vals, names):
    lab = f'{v:.1f}'
    ax.annotate(lab, (v + 0.6, yi), va='center', fontsize=8.5,
                color=C_BLUE if n == '언론사 홈페이지·앱' else INK2,
                fontweight='bold' if n == '언론사 홈페이지·앱' else 'normal')
ax.set_yticks(y)
ax.set_yticklabels(names)
ax.set_xlim(0, 55)
ax.set_xlabel('뉴스·시사정보 주 이용 경로 (%, 가중, n=6,000)')
despine(ax, keep=())
ax.xaxis.grid(True, color=GRID, lw=0.8)
ax.set_axisbelow(True)
save(fig, '그림4-6_주이용경로.png')

# ── 그림 4-7: 온라인 뉴스 출처 인지 (다이버징 스택) ─────────────
fig, ax = plt.subplots(figsize=(7.2, 1.9))
segs = [('모른다(1~2점)', C_RED), ('반반이다(3점)', C_GRAY_SEG), ('알고 있다(4~5점)', C_BLUE)]
left = 0.0
for name, color in segs:
    v = q93_dist[name]
    ax.barh([0], [v], left=left, height=0.5, color=color, zorder=3,
            edgecolor='white', linewidth=2)
    txt_c = 'white' if color in (C_RED, C_BLUE) else INK
    ax.annotate(f"{name.split('(')[0]}\n{v:.1f}%", (left + v / 2, 0), ha='center',
                va='center', fontsize=9.5, color=txt_c, linespacing=1.4)
    left += v
ax.set_xlim(0, 100)
ax.set_ylim(-0.55, 0.55)
ax.set_yticks([])
ax.set_xlabel('내가 보는 온라인 뉴스의 작성 언론사 인지 여부 (%, 온라인 뉴스 이용자 n=4,194)')
despine(ax, keep=())
ax.set_xticks([0, 25, 50, 75, 100])
save(fig, '그림4-7_출처인지.png')

# ──────────────────────────────────────────────────────────────
# 3. 『2025 10대 청소년 미디어 이용조사』 (초·중·고 2,674명)
# ──────────────────────────────────────────────────────────────
print('[3] 청소년 조사 로드·분석')
yo = pd.read_excel(PATHS['youth_xlsx'], sheet_name='DATA')
assert len(yo) == 2674
P1 = {'P1_1': '텔레비전', 'P1_2': '종이신문', 'P1_12': '인터넷 포털',
      'P1_9': '온라인 동영상 플랫폼', 'P1_10': '메신저', 'P1_11': 'SNS',
      'P1_13': '온라인 카페·커뮤니티', 'P1_14': '인터넷 뉴스 사이트',
      'P1_15': '언론사 홈페이지 직접 접속'}
youth = {name: round((yo[col] == 1).mean() * 100, 1) for col, name in P1.items()}
REPRO['청소년_TV_%'] = youth['텔레비전']
REPRO['청소년_언론사직접_%'] = youth['언론사 홈페이지 직접 접속']
direct_by_school = {
    {1: '초등학생', 2: '중학생', 3: '고등학생'}[int(k)]:
        round((yo.loc[yo['학교급_CD'] == k, 'P1_15'] == 1).mean() * 100, 1)
    for k in (1, 2, 3)
}
REPRO['청소년_언론사직접_학교급'] = direct_by_school

# ── 그림 4-8: 청소년 뉴스 이용 경로 (언론사 직접 강조) ──────────
fig, ax = plt.subplots(figsize=(7.2, 3.6))
order8 = sorted(youth.items(), key=lambda kv: kv[1], reverse=True)
names = [k for k, v in order8]
vals = [v for k, v in order8]
cols = [C_BLUE if n == '언론사 홈페이지 직접 접속' else C_GRAY for n in names]
y = np.arange(len(names))[::-1]
ax.barh(y, vals, height=0.55, color=cols, zorder=3)
for yi, v, n in zip(y, vals, names):
    ax.annotate(f'{v:.1f}', (v + 1.0, yi), va='center', fontsize=8.5,
                color=C_BLUE if n == '언론사 홈페이지 직접 접속' else INK2,
                fontweight='bold' if n == '언론사 홈페이지 직접 접속' else 'normal')
ax.set_yticks(y)
ax.set_yticklabels(names)
ax.set_xlim(0, 84)
ax.set_xlabel('뉴스·시사정보 이용 경로 (%, 복수응답, n=2,674)')
despine(ax, keep=())
ax.xaxis.grid(True, color=GRID, lw=0.8)
ax.set_axisbelow(True)
save(fig, '그림4-8_청소년_뉴스이용경로.png')

# ── 그림 4-9: 정치성향별 주 이용 경로 (그룹 막대) ───────────────
fig, ax = plt.subplots(figsize=(7.4, 3.6))
groups = ['텔레비전', '포털', '동영상·숏폼', 'SNS·커뮤니티·메신저']
x = np.arange(len(groups))
w = 0.24
series = [('진보', C_BLUE), ('중도', C_GRAY), ('보수', C_RED)]
for i, (nm, color) in enumerate(series):
    vals = [ct.loc[nm, g] for g in groups]
    bars = ax.bar(x + (i - 1) * (w + 0.02), vals, width=w, color=color,
                  zorder=3, label=nm)
    for b, v in zip(bars, vals):
        ax.annotate(f'{v:.1f}', (b.get_x() + b.get_width() / 2, v + 1.1),
                    ha='center', fontsize=8, color=INK2)
ax.set_xticks(x)
ax.set_xticklabels(groups)
ax.set_ylabel('주 이용 경로 비율 (%, 가중)')
ax.set_ylim(0, 76)
ax.legend(loc='upper right', frameon=False, fontsize=9, ncols=3)
despine(ax)
ax.yaxis.grid(True, color=GRID, lw=0.8)
ax.set_axisbelow(True)
save(fig, '그림4-9_성향별_이용경로.png')

# ── 그림 4-10: 뉴스 문제점 인식 (편파 강조 + 성향별 공통) ───────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.4, 3.5),
                               gridspec_kw={'width_ratios': [1.55, 1]})
order10 = sorted(q91.items(), key=lambda kv: kv[1], reverse=True)
names = [k for k, v in order10]
vals = [v for k, v in order10]
cols = [C_BLUE if n == '편파적 기사' else C_GRAY for n in names]
y = np.arange(len(names))[::-1]
ax1.barh(y, vals, height=0.55, color=cols, zorder=3)
for yi, v, n in zip(y, vals, names):
    ax1.annotate(f'{v:.1f}', (v + 0.7, yi), va='center', fontsize=8.5,
                 color=C_BLUE if n == '편파적 기사' else INK2,
                 fontweight='bold' if n == '편파적 기사' else 'normal')
ax1.set_yticks(y)
ax1.set_yticklabels(names, fontsize=9)
ax1.set_xlim(0, 70)
ax1.set_xlabel('“심각하다”(4~5점) 응답 (%)')
ax1.set_title('뉴스 관련 문제점 인식', fontsize=10.5, color=INK, pad=10)
despine(ax1, keep=())
ax1.xaxis.grid(True, color=GRID, lw=0.8)
ax1.set_axisbelow(True)

names2 = ['진보', '중도', '보수']
cols2 = [C_BLUE, C_GRAY, C_RED]
vals2 = [bias_by[n] for n in names2]
bars = ax2.bar(np.arange(3), vals2, width=0.5, color=cols2, zorder=3)
for b, v in zip(bars, vals2):
    ax2.annotate(f'{v:.1f}', (b.get_x() + b.get_width() / 2, v + 2.2),
                 ha='center', fontsize=9, color=INK2)
ax2.set_xticks(np.arange(3))
ax2.set_xticklabels(names2)
ax2.set_ylim(0, 100)
ax2.set_ylabel('“편파적 기사 심각” 응답 (%)')
ax2.set_title('정치성향별 편파성 인식', fontsize=10.5, color=INK, pad=10)
despine(ax2)
ax2.yaxis.grid(True, color=GRID, lw=0.8)
ax2.set_axisbelow(True)
fig.tight_layout(w_pad=2.5)
save(fig, '그림4-10_뉴스문제점_편파인식.png')

# ──────────────────────────────────────────────────────────────
# 4. 파일럿 재현 그림 (분석_결과/파일럿/파일럿_결과.json)
# ──────────────────────────────────────────────────────────────
print('[4] 파일럿 그림 재현')
with open(PATHS['pilot_json'], encoding='utf-8') as f:
    pilot = json.load(f)
arts = pilot['results']
REPRO['파일럿_일치율_%'] = pilot['agreement']['rate']
REPRO['파일럿_정반대오류'] = pilot['agreement']['severe_errors']
REPRO['파일럿_집단평균_표시부호'] = {k: round(-v['mean'], 3) for k, v in pilot['group_scores'].items()}

# 표시 부호: 보고서 5.2절 정의(+ = 보수측/국민의힘 논평 유사)에 맞추어
# 파일럿 산출물의 점수(+ = 민주당 유사)를 반전해 표시한다.
LBL = {'P': ('진보측', C_BLUE), 'N': ('중립', C_GRAY), 'C': ('보수측', C_RED)}
fig, ax = plt.subplots(figsize=(7.6, 3.4))
rng = np.random.default_rng(42)
row_y = {'P': 2, 'N': 1, 'C': 0}
for a in arts:
    nm, color = LBL[a['manual']]
    yv = row_y[a['manual']] + rng.uniform(-0.16, 0.16)
    ax.scatter(-a['score'], yv, s=64, color=color, zorder=3,
               edgecolors='white', linewidths=1.5)
for key, (nm, color) in LBL.items():
    m = -pilot['group_scores'][key]['mean']
    yv = row_y[key]
    ax.plot([m, m], [yv - 0.26, yv + 0.26], color=color, lw=2, zorder=4)
    ax.annotate(f'평균 {m:+.2f}', (m, yv + 0.33), ha='center', fontsize=8.5,
                color=INK2)
extremes = {'한겨레': (-1.0, 2), '프레시안': (-0.669, 2), '헤럴드경제': (1.0, 0)}
for nm, (xv, yv) in extremes.items():
    ax.annotate(nm, (xv, yv - 0.30), ha='center', fontsize=8, color=MUTED)
ax.axvline(0, color=AXIS, lw=0.8)
ax.axvspan(-1 / 3, 1 / 3, color=GRID, alpha=0.35, zorder=0)
ax.annotate('중립 밴드 |점수|<1/3', (0, 2.72), ha='center', fontsize=8, color=MUTED)
ax.set_yticks([2, 1, 0])
ax.set_yticklabels(['진보측 (수작업 라벨)', '중립 (수작업 라벨)', '보수측 (수작업 라벨)'])
ax.set_xlim(-1.15, 1.15)
ax.set_ylim(-0.6, 2.95)
ax.set_xlabel('스탠스 점수  (-1 진보측·민주당 논평 유사 ← 0 → +1 보수측·국민의힘 논평 유사)')
despine(ax, keep=())
ax.xaxis.grid(True, color=GRID, lw=0.8)
ax.set_axisbelow(True)
save(fig, '그림5-2_스탠스분포.png')

# ──────────────────────────────────────────────────────────────
# 5. 재현 통계 저장·본문 대조 출력
# ──────────────────────────────────────────────────────────────
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(REPRO, f, ensure_ascii=False, indent=1)
print('\n[재현 통계 → 보고서 본문 대조]')
EXPECT = {
    '언론인_q27평균': 4.64, '언론인_q28평균': 5.70, '언론인_격차': 1.05,
    '언론인_대응t': 17.49, '격차2점이상_%': 55.9, '격차3점이상_%': 35.4,
    '격차x자유도_r': -0.17, 'q12_광고주_%': 64.5, 'Q84_언론사채널_%': 0.8,
    'Q84_텔레비전_%': 48.0, 'Q84_포털_%': 33.0, 'Q92_포털_언론인식_%': 88.6,
    'Q92_동영상_언론인식_%': 46.6, 'Q93_안다_%': 30.0, 'Q91_편파_%': 59.3,
    'Q56_추천영상_가끔이상_%': 80.3, 'Q56_추천영상_자주이상_%': 40.3,
    'Q56_채널구독_가끔이상_%': 58.3, 'Q56_채널구독_자주이상_%': 25.8,
    'BQ7xQ84_chi2': 340.5, '청소년_TV_%': 72.3, '청소년_언론사직접_%': 18.1,
    '파일럿_일치율_%': 46.7, '파일럿_정반대오류': 0,
}
n_bad = 0
for k, exp in EXPECT.items():
    got = REPRO.get(k)
    ok = got is not None and abs(float(got) - exp) < 0.15
    n_bad += (not ok)
    print(f"  {'OK ' if ok else 'XX '} {k}: 재현={got}  본문={exp}")
print(f'\n완료: 그림 11개 → {os.path.relpath(OUT_FIG, BASE)}\\, 불일치 {n_bad}건')
sys.exit(1 if n_bad else 0)
