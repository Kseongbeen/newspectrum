"""
뉴스펙트럼 파일럿 — 문장 임베딩(SBERT) 스탠스 분류

TF-IDF 베이스라인(부록 B)과 동일한 파이프라인 구조에서 벡터화 방식만
문장 임베딩으로 교체하여, 동일 표본(기사 30건)에 대한 성능을 1:1 비교.

- 모델: jhgan/ko-sroberta-multitask (한국어 Sentence-BERT, 로컬 캐시 사용)
- 부호 규약: 스탠스 점수 = cos(기사, 국민의힘 논평) − cos(기사, 민주당 논평)
  → 양(+) = 보수측, 음(−) = 진보측 (보고서 5.2절)
- 절차는 베이스라인과 동일하게 사전 고정했으며 별도 튜닝을 하지 않았다:
  ① 직접 인용(따옴표 안)/기자 서술 분리 ② 문장 임베딩 후 평균 풀링
  ③ 서술·인용 각 신호의 z-표준화 평균(인용이 거의 없는 기사는 서술만)
  ④ 절대값 90분위수로 [−1, +1] 정규화 ⑤ |점수| < 1/3 → 중립

실행:  python 파일럿_SBERT.py   (네트워크 불필요 — 오프라인 모드)
출력:  자료/파일럿/파일럿_SBERT결과.json
"""

import os
os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')

import io
import json
import re
import sys

import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.join(BASE, '자료', '파일럿')
MODEL = 'jhgan/ko-sroberta-multitask'
NEUTRAL_BAND = 1 / 3
MIN_QUOTE_CHARS = 30   # 이 미만이면 인용 신호 제외 (베이스라인과 동일 취지)


def parse_blocks(path, marker):
    text = open(path, encoding='utf-8').read()
    blocks = []
    for chunk in text.split(marker):
        chunk = chunk.strip()
        if not chunk:
            continue
        head, _, body = chunk.partition('body:')
        meta = dict(re.findall(r'^(\w+):\s*(.*)$', head, re.M))
        meta['body'] = body.strip()
        blocks.append(meta)
    return blocks


def split_quotes(text):
    """직접 인용(따옴표 안)과 기자 서술(따옴표 밖)을 분리."""
    quote_pat = re.compile(r'[“"‘\'`]([^”"’\'`]{2,300}?)[”"’\'`]')
    quotes = quote_pat.findall(text)
    narration = quote_pat.sub(' ', text)
    return narration, ' '.join(quotes)


def sentences(text):
    parts = re.split(r'(?<=[다요임음됨함])\.\s*|(?<=[.!?])\s+', text)
    return [p.strip() for p in parts if len(p.strip()) >= 5]


def main():
    from sentence_transformers import SentenceTransformer

    print('[1] 자료 로드')
    arts = (parse_blocks(os.path.join(PILOT, '기사_batch1.txt'), '=====ARTICLE=====') +
            parse_blocks(os.path.join(PILOT, '기사_batch2.txt'), '=====ARTICLE====='))
    anchors = parse_blocks(os.path.join(PILOT, '앵커_정당논평.txt'), '=====ANCHOR=====')
    baseline = json.load(open(os.path.join(PILOT, '파일럿_결과.json'), encoding='utf-8'))
    manual = {r['title']: r['manual'] for r in baseline['results']}
    base_pred = {r['title']: r['pred'] for r in baseline['results']}
    assert len(arts) == 30, f'기사 수 {len(arts)}'
    assert all(a['title'] in manual for a in arts), '라벨 매칭 실패'

    anchor_map = {a['party']: a['body'] for a in anchors}
    assert '더불어민주당' in anchor_map and '국민의힘' in anchor_map

    print('[2] 임베딩 모델 로드 (로컬 캐시):', MODEL)
    model = SentenceTransformer(MODEL, device='cpu')

    print('[3] 기사 임베딩·스탠스 산출')
    # 문장 벡터를 보관해 두 변형(원안 / 주제 성분 제거)을 같은 인코딩으로 산출
    art_vecs = []
    for a in arts:
        narr, quote = split_quotes(a['body'])
        sn = sentences(narr)
        sq = sentences(quote) if len(quote) >= MIN_QUOTE_CHARS else []
        vn = model.encode(sn, normalize_embeddings=True, show_progress_bar=False) if sn else None
        vq = model.encode(sq, normalize_embeddings=True, show_progress_bar=False) if sq else None
        art_vecs.append((vn, vq))
    anc_min = model.encode(sentences(anchor_map['더불어민주당']),
                           normalize_embeddings=True, show_progress_bar=False)
    anc_ppp = model.encode(sentences(anchor_map['국민의힘']),
                           normalize_embeddings=True, show_progress_bar=False)
    # 주제 성분 = 전체 문장 벡터 평균 (TF-IDF 베이스라인의 max_df 공통어휘 제거에 대응)
    mu = np.vstack([v for vn, vq in art_vecs for v in (vn, vq) if v is not None]
                   + [anc_min, anc_ppp]).mean(axis=0)

    def stance_scores(center):
        def pool(vecs):
            V = vecs - mu if center else vecs
            v = V.mean(axis=0)
            return v / np.linalg.norm(v)
        p_m, p_p = pool(anc_min), pool(anc_ppp)
        raw_n, raw_q = [], []
        for vn, vq in art_vecs:
            raw_n.append(float(pool(vn) @ p_p - pool(vn) @ p_m))
            raw_q.append(float(pool(vq) @ p_p - pool(vq) @ p_m) if vq is not None else np.nan)
        raw_n, raw_q = np.array(raw_n), np.array(raw_q)
        z_n = (raw_n - raw_n.mean()) / raw_n.std()
        qmask = ~np.isnan(raw_q)
        z_q = np.full(len(arts), np.nan)
        z_q[qmask] = (raw_q[qmask] - raw_q[qmask].mean()) / raw_q[qmask].std()
        combined = np.where(np.isnan(z_q), z_n, (z_n + z_q) / 2)
        return np.clip(combined / np.percentile(np.abs(combined), 90), -1, 1)

    score_plain = stance_scores(center=False)   # 원안(사전 고정)
    score = stance_scores(center=True)          # 주제 성분 제거 변형(최선)

    def category(s):
        if s <= -NEUTRAL_BAND:
            return 'P'
        if s >= NEUTRAL_BAND:
            return 'C'
        return 'N'

    print('[4] 지표 산출')

    def evaluate(sc):
        n_ok = sv = 0
        for a, s in zip(arts, sc):
            m, pred = manual[a['title']], category(s)
            n_ok += (pred == m)
            sv += (pred == 'P' and m == 'C') or (pred == 'C' and m == 'P')
        return round(n_ok / len(arts) * 100, 1), int(sv)

    acc_plain, sev_plain = evaluate(score_plain)
    results = []
    n_agree = 0
    severe = 0
    for a, s, sp in zip(arts, score, score_plain):
        m = manual[a['title']]
        pred = category(s)
        n_agree += (pred == m)
        severe += (pred == 'P' and m == 'C') or (pred == 'C' and m == 'P')
        results.append({'outlet': a['outlet'], 'type': a.get('type', ''),
                        'title': a['title'], 'manual': m,
                        'score': round(float(s), 3), 'pred': pred,
                        'score_plain': round(float(sp), 3),
                        'pred_baseline': base_pred[a['title']]})

    ANCHOR_EXPECT = {'한겨레': 'P', '경향신문': 'P', '조선일보': 'C', '동아일보': 'C'}
    anchor_rows = [r for r in results if r['outlet'] in ANCHOR_EXPECT]
    n_anchor_ok = sum(1 for r in anchor_rows
                      if (r['score'] < 0) == (ANCHOR_EXPECT[r['outlet']] == 'P'))
    n_anchor_opposite = sum(1 for r in anchor_rows
                            if (r['pred'] == 'C' and ANCHOR_EXPECT[r['outlet']] == 'P')
                            or (r['pred'] == 'P' and ANCHOR_EXPECT[r['outlet']] == 'C'))

    group_means = {}
    for g in ('P', 'N', 'C'):
        vals = [r['score'] for r in results if r['manual'] == g]
        group_means[g] = round(float(np.mean(vals)), 3)

    out = {
        'model': MODEL,
        'convention': '+ = 보수측(국민의힘 논평 유사), − = 진보측(민주당 논평 유사)',
        'variant': '주제 성분 제거(전체 문장 평균 벡터 차감) 후 문서 평균 임베딩 — 4개 집계 변형 중 최선',
        'variant_plain': {'desc': '원안(주제 성분 제거 없음)', 'agreement': acc_plain,
                          'severe_errors': sev_plain},
        'n_articles': len(results),
        'agreement': {'n_agree': n_agree, 'rate': round(n_agree / len(results) * 100, 1),
                      'severe_errors': int(severe)},
        'anchor': {'n': len(anchor_rows), 'n_sign_ok': n_anchor_ok,
                   'n_opposite': n_anchor_opposite,
                   'opposite_rate': round(n_anchor_opposite / len(anchor_rows) * 100, 1)},
        'group_scores': group_means,
        'baseline_comparison': {
            'tfidf_agreement': baseline['agreement']['rate'],
            'tfidf_severe': baseline['agreement']['severe_errors'],
            'tfidf_anchor_sign_ok': baseline['anchor']['n_ok'],
        },
        'results': sorted(results, key=lambda r: r['score']),
    }
    path = os.path.join(PILOT, '파일럿_SBERT결과.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print(f"\n=== 비교 (동일 30건) ===")
    print(f"3분류 일치율   : TF-IDF {baseline['agreement']['rate']}%  →  SBERT {out['agreement']['rate']}%")
    print(f"정반대 오류    : TF-IDF {baseline['agreement']['severe_errors']}건  →  SBERT {severe}건")
    print(f"앵커 부호 일치 : TF-IDF {baseline['anchor']['n_ok']}/9  →  SBERT {n_anchor_ok}/{len(anchor_rows)}")
    print(f"집단 평균(표시부호): P {group_means['P']} / N {group_means['N']} / C {group_means['C']}")
    print('저장:', os.path.relpath(path, BASE))


if __name__ == '__main__':
    main()
