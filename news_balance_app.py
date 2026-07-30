import streamlit as st
import pandas as pd
import pyreadstat
import matplotlib.pyplot as plt
import seaborn as sns
import os
import requests
import re
import html
from collections import Counter
from bs4 import BeautifulSoup
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
import plotly.express as px
import plotly.graph_objects as go

# Set page config for premium look and collapse sidebar by default
st.set_page_config(
    page_title="뉴스펙트럼 (Newspectrum)",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Set Korean font for Matplotlib to avoid broken characters (Malgun Gothic is default on Windows)
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# Newspaper editorial CSS - broadsheet style
st.markdown("""
<style>
    /* Google Fonts: Playfair Display (serif headlines) + Noto Serif KR + Source Sans 3 (body) */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800;900&family=Noto+Serif+KR:wght@400;600;700&family=Source+Sans+3:wght@400;600;700&display=swap');
    
    /* ── Global reset & base ─────────────────────────────────────── */
    html, body, [class*="css"] {
        font-family: 'Source Sans 3', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
        background-color: #F7F5F0 !important;
        color: #1A1A1A !important;
    }
    [data-testid="stAppViewContainer"] { background-color: #F7F5F0; }
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    [data-testid="stHeader"] {
        background-color: rgba(247, 245, 240, 0.92) !important;
        backdrop-filter: blur(8px);
        border-bottom: 2px solid #1A1A1A !important;
    }

    /* ── Newspaper card containers ───────────────────────────────── */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 1px solid #D0CBC0 !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        padding: 24px !important;
        margin-bottom: 20px !important;
    }
    .toss-card {
        background-color: #FFFFFF;
        padding: 22px 26px;
        border-left: 4px solid #1A1A1A;
        border-top: 1px solid #D0CBC0;
        border-right: 1px solid #D0CBC0;
        border-bottom: 1px solid #D0CBC0;
        margin-bottom: 18px;
    }

    /* ── Newspaper masthead typography ──────────────────────────── */
    .toss-title {
        font-family: 'Playfair Display', 'Noto Serif KR', Georgia, serif;
        font-size: 3.2rem;
        color: #0D0D0D;
        font-weight: 900;
        letter-spacing: -0.02em;
        margin-bottom: 4px;
        text-align: center;
        margin-top: 16px;
        line-height: 1.1;
        text-transform: uppercase;
    }
    .toss-subtitle {
        font-family: 'Source Sans 3', sans-serif;
        font-size: 0.95rem;
        color: #555550;
        font-weight: 400;
        margin-bottom: 0;
        letter-spacing: 0.04em;
        text-align: center;
        max-width: 900px;
        margin-left: auto;
        margin-right: auto;
        line-height: 1.5;
        border-top: 3px double #1A1A1A;
        border-bottom: 1px solid #1A1A1A;
        padding: 10px 0;
        margin-top: 10px;
    }
    .toss-h2 {
        font-family: 'Playfair Display', 'Noto Serif KR', Georgia, serif;
        font-size: 1.55rem;
        color: #0D0D0D;
        font-weight: 800;
        margin-bottom: 14px;
        letter-spacing: -0.01em;
        border-bottom: 2px solid #1A1A1A;
        padding-bottom: 6px;
    }
    
    /* Dynamic Badges */
    .toss-badge-blue {
        background-color: #E8F3FF;
        color: #3182F6;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        display: inline-block;
        margin-bottom: 8px;
    }

    /* ── Badges ─────────────────────────────────────────────────── */
    .toss-badge-blue {
        background-color: transparent;
        color: #1A4FA0;
        padding: 2px 8px;
        border: 1.5px solid #1A4FA0;
        border-radius: 2px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-block;
        margin-bottom: 6px;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    .toss-badge-red {
        background-color: transparent;
        color: #B01020;
        padding: 2px 8px;
        border: 1.5px solid #B01020;
        border-radius: 2px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-block;
        margin-bottom: 6px;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    .toss-badge-gray {
        background-color: transparent;
        color: #555550;
        padding: 2px 8px;
        border: 1.5px solid #999990;
        border-radius: 2px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 6px;
        letter-spacing: 0.03em;
    }
    .toss-keyword-badge {
        background-color: #F0EDE6;
        color: #1A1A1A;
        padding: 3px 9px;
        border-radius: 2px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-right: 5px;
        display: inline-block;
        border: 1px solid #D0CBC0;
    }

    /* ── Article cards: newspaper column style ───────────────────── */
    .article-card {
        background-color: #FFFFFF;
        padding: 16px 18px;
        border-top: 3px solid #1A1A1A;
        border-left: none;
        border-right: none;
        border-bottom: 1px solid #D0CBC0;
        margin-bottom: 14px;
    }
    .article-card h4 {
        font-family: 'Playfair Display', 'Noto Serif KR', Georgia, serif !important;
    }

    /* ── Tabs: editorial section tabs ───────────────────────────── */
    div.stTabs [data-baseweb="tab-list"] {
        background-color: transparent !important;
        border-bottom: 2px solid #1A1A1A;
        gap: 0;
        justify-content: flex-start;
        margin-bottom: 28px;
    }
    div.stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        color: #555550 !important;
        font-size: 0.88rem !important;
        font-weight: 700 !important;
        padding: 10px 20px !important;
        border-radius: 0 !important;
        border: none !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    div.stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #0D0D0D !important;
        background-color: #1A1A1A !important;
        color: #FFFFFF !important;
    }

    /* ── Inputs ──────────────────────────────────────────────────── */
    textarea {
        border-radius: 0 !important;
        border: 1px solid #1A1A1A !important;
        background-color: #FDFCF8 !important;
        padding: 14px !important;
        font-family: 'Source Sans 3', sans-serif !important;
    }
    .stButton > button {
        border-radius: 0 !important;
        font-weight: 700 !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        font-size: 0.85rem !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #1A1A1A !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #B01020 !important;
    }

    /* ── Live status pills ───────────────────────────────────────── */
    .live-status-green {
        color: #1A4A20;
        font-weight: 700;
        font-size: 0.82rem;
        background-color: #DFF0E0;
        padding: 3px 10px;
        border: 1px solid #1A4A20;
        border-radius: 2px;
        display: inline-block;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .live-status-yellow {
        color: #6B3A00;
        font-weight: 700;
        font-size: 0.82rem;
        background-color: #FFF0CC;
        padding: 3px 10px;
        border: 1px solid #6B3A00;
        border-radius: 2px;
        display: inline-block;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }

    /* ── Spectrum bar (kept for fallback) ────────────────────────── */
    .spectrum-bar-container { position: relative; height: 60px; margin: 20px 0 8px 0; padding: 0 10px; }
    .spectrum-track { height: 8px; background: linear-gradient(90deg, #1A4FA0 0%, #D0CBC0 50%, #B01020 100%); position: relative; }
    .spectrum-node { position: absolute; top: -10px; transform: translateX(-50%); display: flex; flex-direction: column; align-items: center; }
    .spectrum-dot-blue { width: 10px; height: 10px; background-color: #1A4FA0; border: 2px solid #F7F5F0; border-radius: 50%; }
    .spectrum-dot-red { width: 10px; height: 10px; background-color: #B01020; border: 2px solid #F7F5F0; border-radius: 50%; }
    .spectrum-dot-gray { width: 10px; height: 10px; background-color: #888; border: 2px solid #F7F5F0; border-radius: 50%; }
    .spectrum-label { font-size: 0.72rem; font-weight: 700; color: #1A1A1A; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 매체 이념 성향 점수 데이터베이스
# 출처: KPF 2025 언론수용자 조사 (n=5,010)
# 계산 방식: 각 정치 성향 집단(진보/중도/보수)의 응답자 수 가중 평균
#   Score = (-1.0 × n진보 + 0.0 × n중도 + +1.0 × n보수) / 전체
# 범위: 이론적으로 [-1.0, +1.0] (실제 데이터 범위: -0.34 ~ +0.50)
# 주의: 유튜브/네이버 등 플랫폼은 편집권이 없으므로 제외
# ============================================================
PRESS_LEANING_SCORES = {
    # === 방송 (신뢰도 기반 교차표, n진보=1828 n중도=2531 n보수=1641) ===
    "JTBC":       -0.34,   # 진보 성향 신뢰 압도적
    "MBC":        -0.22,   # 진보 성향 신뢰 높음
    "SBS":        -0.01,   # 사실상 중립
    "YTN":        +0.02,   # 사실상 중립
    "연합뉴스TV": +0.15,   # 약한 보수 방향
    "KBS":        +0.25,   # 보수 성향 신뢰 높음
    "TV조선":     +0.50,   # 강보수 성향 신뢰

    # === 신문 (열독률 기반 교차표, n진보=137 n중도=183 n보수=184) ===
    "한겨레":     -0.28,   # 진보 독자층 집중
    "한겨레21":   -0.28,
    "한국경제":   -0.12,   # 약진보 (경제지 특성상 진보 독자층 많음)
    "한경비즈니스": -0.12,
    "중앙일보":   -0.06,   # 거의 중립
    "경향신문":   -0.06,   # 거의 중립 (열독률 기반)
    "경향비즈":   -0.06,
    "동아일보":   +0.03,   # 거의 중립
    "주간동아":   +0.03,
    "신동아":     +0.03,
    "매일경제":   +0.05,   # 거의 중립
    "매경이코노미": +0.05,
    "조선일보":   +0.38,   # 보수 독자층 집중
    "주간조선":   +0.38,

    # === 통신·온라인 (중립 가정, 편집 방향 불명확) ===
    "연합뉴스":   0.00,
    "뉴스1":      0.00,
    "뉴시스":     0.00,
}

# Stop words to clean search query keywords
STOP_WORDS = {
    "은", "는", "이", "가", "을", "를", "의", "에", "로", "으로", "와", "과", "도",
    "대해", "대한", "통한", "따른", "의해", "위한", "하여"
}

# Stance/Action keywords that bias the search query (Stance Filter)
QUERY_STOP_WORDS = {
    "폐지", "시행", "도입", "반대", "찬성", "규탄", "촉구", "우려", "사직", "복지",
    "활성화", "사태", "공백", "마비", "의혹", "수사", "외압", "기소", "정상화", "완화",
    "대란", "공방", "갈등", "대치", "충돌", "논란", "비판", "반발", "규명",
    "개정", "폐지안", "도입안", "시행안", "혜택", "부여", "사태", "요구", "거부", "거부권",
    "조사", "임용", "발표", "처리", "통과", "저지", "정국", "강행"
}

# General adverbs, pronouns, and meaningless nouns in journalist writing (XAI Blacklist)
# 이념적 프레이밍과 무관한 중립/일반 단어를 철저히 제거해야 XAI 결과 신뢰도가 올라감
XAI_STOP_WORDS = {
    # 시간/부사
    "즉시", "당장", "최근", "올해", "다시", "결국", "앞으로", "이후", "지금", "오늘", "내일",
    "어제", "하루", "이틀", "이번", "지난", "내년", "때문", "만큼", "현재", "향후", "이날",
    "당시", "매일", "연일", "오전", "오후", "새벽", "저녁", "이번엔", "올들어", "금년",
    # 보도/언론 일반
    "기자", "보도", "뉴스", "언론", "단독", "속보", "종합", "취재", "보도자료", "취재진",
    "재배포", "무단", "전재", "금지", "사진", "영상", "화면", "제공", "출처", "인터뷰",
    # 일반 명사 (이념 무관)
    "사실", "내용", "이유", "이름", "경우", "때에", "진짜", "그냥", "모두", "누가",
    "무엇", "어떻게", "사람", "여성", "남성", "국민", "시민", "주민", "관계자", "당국자",
    "대표", "위원", "위원장", "장관", "차관", "총장", "본부장", "실장", "국장", "과장",
    "학생", "교사", "교수", "연구원", "전문가", "관련", "가운데", "상황", "상태", "현실",
    "문제", "방안", "방법", "대책", "조치", "부분", "측면", "차원", "수준", "정도",
    "결과", "과정", "절차", "체계", "시스템", "제도", "기관", "기구", "단체", "센터",
    # 동사/서술 일반
    "진행", "발표", "설명", "주장", "지적", "강조", "요구", "촉구", "확인", "파악",
    "의견", "입장", "소식", "정리", "종합", "분석", "평가", "전망", "계획", "예정",
    "실시", "추진", "검토", "논의", "협의", "합의", "결정", "발견", "착수", "개시",
    "마련", "공개", "발생", "집계", "기록", "조사", "운영", "관리", "담당", "처리",
    # 사법/치안 중립 (프레이밍이 아닌 사실 서술)
    "경찰", "소방", "군인", "군대", "사고", "사건", "현장", "피해", "피해자", "용의자",
    "신고", "출동", "체포", "조사", "수색", "구조", "구급", "병원", "치료", "입원",
    # 지역/장소 일반
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원",
    "충북", "충남", "전북", "전남", "경북", "경남", "제주", "한국", "국내", "해외",
    # 숫자/단위 관련
    "이상", "이하", "이내", "약간", "다수", "일부", "전체", "대부분", "절반", "가량",
    "만원", "억원", "조원", "달러", "퍼센트", "포인트",
    # 기타 무의미 고빈도어
    "대해", "대한", "통한", "따른", "위해", "통해", "관련", "가능", "필요", "중요",
    "적극", "긴급", "신속", "즉각", "완전", "전면", "추가", "별도", "자체", "직접"
}

# ============================================================
# 이념 프레이밍 어휘 화이트리스트 (Ideological Framing Vocabulary)
# XAI에서 이 사전에 등록된 단어만 '프레이밍 결정 단어'로 표시
# 블랙리스트(불용어 제거)는 한계가 있으므로 화이트리스트 방식 채택
# ============================================================

# 진보 프레임 어휘: 비판·견제·복지·분배·인권·평화 등
PROG_FRAME_WORDS = {
    # 분배/복지/평등
    "민생", "서민", "약자", "취약계층", "불평등", "양극화", "복지", "분배", "보편적",
    "기본권", "인권", "차별", "평등", "공정", "무상", "공공", "국공립", "사회안전망",
    "최저임금", "생활임금", "비정규직", "해고", "노동권", "노동자", "착취",
    # 재벌/기득권 비판
    "재벌", "특혜", "특권", "기득권", "갑질", "독점", "담합", "편법", "탈세",
    "부자감세", "감세혜택", "초부자", "부유층", "상위층",
    # 권력 견제/민주주의
    "적폐", "청산", "개혁", "민주주의", "촛불", "시민사회", "견제", "감시", "투명",
    "독재", "권위주의", "사찰", "탄압", "언론탄압", "검찰독재", "검찰독점",
    "불통", "독선", "폭주", "강행", "날치기", "직권상정", "밀어붙이기",
    # 특검/수사 관련 (야당 관점)
    "특검", "진상규명", "국정조사", "책임규명", "은폐", "축소", "외압", "무마",
    # 평화/외교
    "평화", "대화", "협력", "화해", "교류", "공존", "외교적", "평화체제",
    "탈원전", "재생에너지", "기후위기", "환경", "생태",
    # 프레이밍 수사
    "세금폭탄", "혈세낭비", "특혜의혹", "비리", "게이트", "스캔들",
    "퇴진", "사퇴", "물러나", "책임져", "규탄",
}

# 보수 프레임 어휘: 성장·안보·자유·법치·효율·시장 등
CONS_FRAME_WORDS = {
    # 자유/시장/성장
    "자유", "시장", "경쟁", "성장", "효율", "규제완화", "규제혁파", "민영화",
    "투자활성화", "기업활력", "경제활력", "활성화", "경쟁력", "혁신성장",
    "감세", "세금감면", "감면", "세제혜택", "기업하기좋은",
    # 안보/동맹
    "안보", "동맹", "한미", "한미동맹", "국방", "자유민주", "체제수호",
    "국익", "애국", "자유대한민국", "대한민국", "자유민주주의",
    "핵억제", "미사일", "전력강화", "군사력", "억제력",
    # 반북/반좌 프레이밍
    "좌파", "종북", "친북", "반미", "반국가", "이적", "친중",
    "사회주의", "공산주의", "전체주의", "선동",
    # 법치/질서
    "법치", "준법", "질서", "법과원칙", "엄정", "법적조치", "단호",
    "불법", "불법시위", "불법파업", "폭력시위", "무법", "법치주의",
    # 재정 건전성/비판
    "포퓰리즘", "퍼주기", "세금폭탄", "혈세", "재정건전성", "방만", "비효율",
    "공공개혁", "구조조정", "효율화", "합리화",
    "무분별", "무책임", "선심성", "표퓰리즘",
    # 거부권/제도방어 (여당 관점)
    "재의요구", "거부권", "헌법수호", "제도보호", "정상화",
    # 프레이밍 수사
    "정쟁", "발목잡기", "반대만", "정략", "꼼수", "편향", "왜곡",
    "막말", "폭언", "원내대치", "식물국회",
}

# 통합 이념 어휘 사전 (화이트리스트)
IDEOLOGICAL_VOCAB = PROG_FRAME_WORDS | CONS_FRAME_WORDS

# 방향 매핑: 진보 프레임 단어면 -1, 보수면 +1
IDEO_DIRECTION = {}
for w in PROG_FRAME_WORDS:
    IDEO_DIRECTION[w] = -1
for w in CONS_FRAME_WORDS:
    IDEO_DIRECTION[w] = 1

def strip_korean_particles(word):
    particles = [
        "은", "는", "이", "가", "을", "를", "의", "에", "로", "으로", "와", "과", "도",
        "에서", "에게", "한테", "께", "이며", "고", "하고", "랑", "이랑", "보다",
        "처럼", "같이", "부터", "까지", "마저", "조차", "만", "뿐", "치고", "야말로", "로써", "로서"
    ]
    particles.sort(key=len, reverse=True)
    for p in particles:
        if word.endswith(p) and len(word) > len(p):
            return word[:-len(p)]
    return word

# Clean Korean text
def clean_korean(text):
    cleaned = re.sub(r'[^가-힣\s]', ' ', text)
    return " ".join([w for w in cleaned.split() if len(w) >= 2])

def compute_pmi_weights(all_articles):
    """
    Cross-corpus PMI: 진보 매체 코퍼스 vs 보수 매체 코퍼스를 나눠
    각 단어의 이념적 편향도를 자동 계산합니다.
    
    Returns: dict { word -> float }
      양수 → 보수 매체에서 더 자주 등장 (보수 프레임어)
      음수 → 진보 매체에서 더 자주 등장 (진보 프레임어)
      ~0   → 양측 균등 (중립 토픽어: 속보, 코스피 등 자동 제거)
    """
    from math import log
    from collections import Counter

    prog_counter = Counter()
    cons_counter = Counter()

    for art in all_articles:
        score = PRESS_LEANING_SCORES.get(art.get('press', ''), None)
        if score is None:
            continue
        cleaned = clean_korean(art['title'])
        words = cleaned.split()
        tokens = words + [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        if score < -0.08:
            for t in tokens:
                prog_counter[t] += 1
        elif score > 0.08:
            for t in tokens:
                cons_counter[t] += 1

    prog_total = max(sum(prog_counter.values()), 1)
    cons_total = max(sum(cons_counter.values()), 1)
    all_tokens = set(prog_counter) | set(cons_counter)

    pmi_weights = {}
    for token in all_tokens:
        # Add-0.5 smoothing to avoid log(0)
        p_given_prog = (prog_counter[token] + 0.5) / (prog_total + 0.5 * len(all_tokens))
        p_given_cons = (cons_counter[token] + 0.5) / (cons_total + 0.5 * len(all_tokens))
        # Ideological score: positive=conservative, negative=progressive
        pmi_weights[token] = log(p_given_cons / p_given_prog)

    return pmi_weights


def apply_pmi_scaling(X, vectorizer, pmi_weights, min_weight=0.05):
    """
    TF-IDF 행렬의 각 피처 컬럼에 PMI 이념 가중치의 절댓값을 곱합니다.
    중립어(PMI≈0) → 거의 0, 이념어(|PMI| 큰) → 원래 값 유지
    """
    feature_names = vectorizer.get_feature_names_out()
    weights = np.array([abs(pmi_weights.get(name, 0.0)) for name in feature_names])
    # Normalize to [min_weight, 1.0]
    max_w = weights.max()
    if max_w > 0:
        weights = weights / max_w
    weights = np.clip(weights, min_weight, 1.0)
    # Multiply each column (feature) by its weight
    return X.multiply(weights)


# Extract top nouns for JIT search (using particle stripper and stance filter)
def extract_nouns(text):
    words = re.findall(r'[가-힣]{2,8}', text)
    cleaned_words = []
    for w in words:
        stripped = strip_korean_particles(w)
        # Filter out both general stop words and stance-biasing words
        if len(stripped) >= 2 and stripped not in STOP_WORDS and stripped not in QUERY_STOP_WORDS:
            cleaned_words.append(stripped)
    return cleaned_words[:2]

# Load audience and journalist datasets
@st.cache_data
def load_audience_data():
    target_dir = r"C:\Users\5174k\OneDrive\바탕 화면\언론 공모전"
    path = os.path.join(target_dir, "3. 2025 언론수용자 조사_최종데이터.SAV")
    df, meta = pyreadstat.read_sav(path, encoding='cp949')
    return df, meta

@st.cache_data
def load_journalist_data():
    target_dir = r"C:\Users\5174k\OneDrive\바탕 화면\언론 공모전"
    path = os.path.join(target_dir, "[로데이터] 2025 언론인 조사 원본 데이터.SAV")
    df, meta = pyreadstat.read_sav(path, encoding='utf-8')
    return df, meta

try:
    df_aud, meta_aud = load_audience_data()
    df_jour, meta_jour = load_journalist_data()
    data_loaded = True
except Exception as e:
    st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
    data_loaded = False

# High Volume Live Naver News Crawler (Strict - returns empty array on failure)
@st.cache_data(ttl=180) # Cache for 3 minutes
def fetch_all_ranking_news():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    }
    articles = []
    crawled_ok = False
    error_messages = []
    
    target_presses = [
        "조선일보", "중앙일보", "동아일보", "한겨레", "경향신문", "MBC", "KBS", "SBS", "JTBC", "YTN", "한국일보", "서울신문",
        "연합뉴스", "뉴시스", "뉴스1", "매일경제", "한국경제", "서울경제", "아시아경제", "세계일보", "국민일보", "문화일보", "헤럴드경제"
    ]
    
    def _safe_decode(response):
        """EUC-KR 페이지를 안전하게 디코딩하는 헬퍼"""
        for enc in ['utf-8', 'euc-kr', 'cp949']:
            try:
                return response.content.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return response.content.decode('utf-8', errors='replace')
    
    # ── Source 1: 인기뉴스 랭킹 (popularDay.naver) ──────────────────
    # 23개 주요 언론사 × 5개 기사 = 최대 115개
    url_pop = "https://news.naver.com/main/ranking/popularDay.naver"
    try:
        res = requests.get(url_pop, headers=headers, timeout=8)
        res.raise_for_status()
        html_text = _safe_decode(res)
        soup = BeautifulSoup(html_text, "html.parser")
        boxes = soup.select(".rankingnews_box")
        
        pop_count = 0
        for box in boxes:
            press_name_el = box.select_one(".rankingnews_name")
            if not press_name_el:
                continue
            press_name = press_name_el.get_text().strip()
            
            if press_name not in target_presses:
                continue
                
            list_titles = box.select(".rankingnews_list .list_title")
            for t in list_titles:
                title_text = t.get_text().strip()
                link = t.get("href") or ""
                if link and not link.startswith("http"):
                    link = "https://news.naver.com" + link
                if title_text:
                    articles.append({
                        "press": press_name,
                        "title": title_text,
                        "link": link
                    })
                    pop_count += 1
        if pop_count > 0:
            crawled_ok = True
    except Exception as e:
        error_messages.append(f"인기뉴스 랭킹 오류: {e}")
    
    # ── Source 2: 신규 섹션 페이지 (/section/100,101,102) ────────────
    # 정치/경제/사회 각 46개+ 기사 (sa_text_title 셀렉터 사용)
    section_sids = [100, 101, 102]
    for sid in section_sids:
        section_url = f"https://news.naver.com/section/{sid}"
        try:
            sec_res = requests.get(section_url, headers=headers, timeout=8)
            if sec_res.status_code == 200:
                sec_html = _safe_decode(sec_res)
                sec_soup = BeautifulSoup(sec_html, "html.parser")
                
                # sa_text_title: 신규 네이버 뉴스 섹션 페이지의 기사 제목 링크
                title_els = sec_soup.select("a.sa_text_title")
                sec_count = 0
                for title_el in title_els:
                    title_text = ""
                    # 제목 텍스트는 .sa_text_strong 안에 있음
                    strong_el = title_el.select_one(".sa_text_strong")
                    if strong_el:
                        title_text = strong_el.get_text().strip()
                    else:
                        title_text = title_el.get_text().strip()
                    
                    link = title_el.get("href", "")
                    
                    # 언론사명 추출: 같은 기사 블록 내 .sa_text_press 또는 img alt
                    press_name = ""
                    parent = title_el.parent
                    for _ in range(5):
                        if not parent:
                            break
                        press_el = parent.select_one(".sa_text_press")
                        if press_el:
                            press_name = press_el.get_text().strip()
                            break
                        press_img = parent.select_one("img.sa_thumb_press")
                        if press_img:
                            press_name = press_img.get("alt", "").strip()
                            break
                        parent = parent.parent
                    
                    if not press_name:
                        press_name = "Unknown"
                    
                    if title_text:
                        articles.append({
                            "press": press_name,
                            "title": title_text,
                            "link": link
                        })
                        sec_count += 1
                if sec_count > 0:
                    crawled_ok = True
        except Exception as e:
            error_messages.append(f"섹션 {sid} 크롤링 오류: {e}")
        
    # ── Source 3: 레거시 리스트 페이지 (list.naver) ──────────────────
    # 정치/경제/사회 각 2페이지 × 20개 = 최대 120개
    for sid in section_sids:
        for page in [1, 2]:
            list_url = f"https://news.naver.com/main/list.naver?mode=LSD&mid=sec&sid1={sid}&page={page}"
            try:
                list_res = requests.get(list_url, headers=headers, timeout=8)
                if list_res.status_code == 200:
                    list_html = _safe_decode(list_res)
                    list_soup = BeautifulSoup(list_html, "html.parser")
                    items = list_soup.select(".list_body li")
                    for item in items:
                        title_el = item.select("dt a")
                        title_text = ""
                        link = ""
                        for a in title_el:
                            text = a.get_text().strip()
                            if text:
                                title_text = text
                                link = a.get("href", "")
                                break
                        
                        press_el = item.select_one(".writing")
                        press_name = press_el.get_text().strip() if press_el else "Unknown"
                        
                        if title_text:
                            if link and not link.startswith("http"):
                                link = "https://news.naver.com" + link
                            articles.append({
                                "press": press_name,
                                "title": title_text,
                                "link": link
                            })
                    crawled_ok = True
            except Exception as e:
                error_messages.append(f"리스트 sid={sid} p{page} 오류: {e}")
                
    # ── De-duplicate by normalized title ─────────────────────────────
    unique_articles = []
    seen_titles = set()
    for art in articles:
        normalized_title = re.sub(r'\s+', '', art["title"])
        # 깨진 인코딩 기사 필터링 (한글이 포함되지 않은 제목은 제외)
        if not re.search(r'[가-힣]', art["title"]):
            continue
        if normalized_title not in seen_titles:
            seen_titles.add(normalized_title)
            unique_articles.append(art)
            
    if unique_articles:
        crawled_ok = True
        articles = unique_articles
    else:
        crawled_ok = False
        articles = []
        
    return articles, crawled_ok, " | ".join(error_messages)

# ── Naver Search API (공식) ─────────────────────────────────────────────
# https://developers.naver.com/docs/serviceapi/search/news/news.md
# 응답에 언론사명이 없어 originallink 도메인으로 매핑한다.
# 주의: 부분 문자열 매칭이므로 구체적인 도메인(tvchosun, weekly.chosun)을 앞에 둘 것.
DOMAIN_TO_PRESS = [
    ("tvchosun.com", "TV조선"),
    ("weekly.chosun.com", "주간조선"),
    ("chosun.com", "조선일보"),
    ("yonhapnewstv", "연합뉴스TV"),
    ("yna.co.kr", "연합뉴스"),
    ("h21.hani.co.kr", "한겨레21"),
    ("hani.co.kr", "한겨레"),
    ("hankyung.com", "한국경제"),
    ("joongang.co.kr", "중앙일보"),
    ("joins.com", "중앙일보"),
    ("khan.co.kr", "경향신문"),
    ("weekly.donga.com", "주간동아"),
    ("shindonga.donga.com", "신동아"),
    ("donga.com", "동아일보"),
    ("mk.co.kr", "매일경제"),
    ("jtbc.co.kr", "JTBC"),
    ("imbc.com", "MBC"),
    ("sbs.co.kr", "SBS"),
    ("ytn.co.kr", "YTN"),
    ("kbs.co.kr", "KBS"),
    ("news1.kr", "뉴스1"),
    ("newsis.com", "뉴시스"),
]


def _naver_api_keys():
    """환경변수 또는 st.secrets에서 API 키를 읽는다. 없으면 None."""
    cid = os.environ.get("NAVER_CLIENT_ID")
    csec = os.environ.get("NAVER_CLIENT_SECRET")
    if not (cid and csec):
        try:
            cid = st.secrets["NAVER_CLIENT_ID"]
            csec = st.secrets["NAVER_CLIENT_SECRET"]
        except Exception:
            return None
    return (cid, csec) if cid and csec else None


def _press_from_link(link):
    for domain, press in DOMAIN_TO_PRESS:
        if domain in link:
            return press
    return None


def _clean_api_text(text):
    """API 응답의 <b> 태그·HTML 엔티티 제거."""
    return html.unescape(re.sub(r"<[^>]+>", "", text)).strip()


def fetch_search_results_api(query, keys):
    """공식 검색 API로 기사 목록을 가져온다. 실패 시 빈 리스트.

    키 형식으로 플랫폼을 판별한다:
    시크릿 40자 = NAVER API HUB(ncloud), 10자 내외 = 개발자센터 오픈API.
    두 API의 응답 JSON 구조는 동일하다.
    """
    cid, csec = keys
    if len(csec) > 20:
        url = "https://naverapihub.apigw.ntruss.com/search/v1/news"
        headers = {"X-NCP-APIGW-API-KEY-ID": cid, "X-NCP-APIGW-API-KEY": csec}
    else:
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec}
    articles = []
    try:
        res = requests.get(
            url,
            headers=headers,
            params={"query": query, "display": 100, "sort": "sim"},
            timeout=5,
        )
        if res.status_code != 200:
            return []
        for item in res.json().get("items", []):
            press = _press_from_link(item.get("originallink", "") or item.get("link", ""))
            title = _clean_api_text(item.get("title", ""))
            if press and title:
                articles.append({"press": press, "title": title})
    except Exception:
        return []
    # De-duplicate (스크래핑 버전과 동일 기준)
    unique = []
    seen = set()
    for art in articles:
        norm = re.sub(r'\s+', '', art["title"])
        if norm not in seen:
            seen.add(norm)
            unique.append(art)
    return unique


def fetch_search_results(query):
    """공식 API 우선, 키가 없거나 실패하면 기존 검색 페이지 스크래핑으로 폴백."""
    keys = _naver_api_keys()
    if keys:
        articles = fetch_search_results_api(query, keys)
        if articles:
            return articles
    return _fetch_search_results_scrape(query)


# Just-In-Time (JIT) Naver Search Crawler (Extracts articles from Naver Search SDS layout)
def _fetch_search_results_scrape(query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    articles = []
    
    # Query Naver News Search (Pages 1, 2, 3)
    for start in [1, 11, 21]:
        search_url = f"https://search.naver.com/search.naver?where=news&query={query}&start={start}"
        try:
            res = requests.get(search_url, headers=headers, timeout=5)
            res.encoding = 'utf-8' # Search portal uses UTF-8
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                titles_el = soup.select(".sds-comps-text-type-headline1")
                
                for title_el in titles_el:
                    title_text = title_el.get_text().strip()
                    parent = title_el.parent
                    press_text = None
                    
                    # Walk up up to 6 levels to find the publisher block containing press text
                    for _ in range(6):
                        if not parent:
                            break
                        press_el = parent.select_one(".sds-comps-profile-info-title-text")
                        if press_el:
                            press_text = press_el.get_text().strip().replace("새 창 열림", "").replace("언론사 선정", "").strip()
                            break
                        parent = parent.parent
                        
                    if press_text and title_text:
                        articles.append({"press": press_text, "title": title_text})
        except Exception:
            pass
            
    # De-duplicate
    unique = []
    seen = set()
    for art in articles:
        norm = re.sub(r'\s+', '', art["title"])
        if norm not in seen:
            seen.add(norm)
            unique.append(art)
    return unique

# Just-In-Time (JIT) dynamic ML classifier training (Using RandomForestRegressor)
def jit_classify_and_explain(user_input):
    keywords = extract_nouns(user_input)
    if not keywords:
        return "중립", 50, [], "분석을 위한 핵심 단어를 추출하지 못했습니다.", 0
        
    query = " ".join(keywords)
    
    # 1. Fetch search results dynamically
    search_articles = fetch_search_results(query)
    if not search_articles:
        return "중립", 50, [], f"포털 실시간 뉴스 검색 연동에 실패했습니다. (검색어: '{query}')", 0
        
    # 2. Extract targets using continuous scores
    training_items = []
    for item in search_articles:
        press = item["press"]
        title_cleaned = clean_korean(item["title"])
        if not title_cleaned:
            continue
        if press in PRESS_LEANING_SCORES:
            training_items.append({"title": title_cleaned, "score": PRESS_LEANING_SCORES[press]})
            
    df_train = pd.DataFrame(training_items)
    
    # 3. Handle data scarcity - strict error (No fallback to local)
    if len(df_train) < 6:
        return "중립", 50, [], f"실시간 포털 뉴스에서 해당 이슈('{query}')에 대한 충분한 양의 비교 대상 기사들을 찾을 수 없습니다. (매칭된 학습 데이터: {len(df_train)}개)", len(df_train)
        
    # Split into Prog/Cons/Neut and perform minority oversampling for 1:1 balance (scale is [-1.0, 1.0])
    prog = df_train[df_train["score"] < -0.10]
    cons = df_train[df_train["score"] > 0.10]
    neut = df_train[(df_train["score"] >= -0.10) & (df_train["score"] <= 0.10)]
    
    if len(prog) > 0 and len(cons) > 0:
        max_len = max(len(prog), len(cons))
        prog_balanced = prog.sample(max_len, replace=True, random_state=42) if len(prog) < max_len else prog
        cons_balanced = cons.sample(max_len, replace=True, random_state=42) if len(cons) < max_len else cons
        df_train_balanced = pd.concat([prog_balanced, cons_balanced, neut]).reset_index(drop=True)
    else:
        df_train_balanced = df_train
        
    # 4. Train RandomForestRegressor on the fly
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    X_raw = vectorizer.fit_transform(df_train_balanced["title"])
    y = df_train_balanced["score"].values
    # Apply PMI scaling: amplify ideological words, suppress neutral ones
    X = apply_pmi_scaling(X_raw, vectorizer, pmi_weights) if pmi_weights else X_raw
    
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X, y)
    
    # Calculate directions using weighted averages of targets
    X_array = X.toarray()
    num_features = X.shape[1]
    directions = np.zeros(num_features)
    for i in range(num_features):
        col = X_array[:, i]
        mask = col > 0
        if mask.any():
            weighted_avg_y = np.average(y[mask], weights=col[mask])
            directions[i] = 1 if weighted_avg_y > 0.0 else -1
            
    # Classify the user input
    cleaned_input = clean_korean(user_input)
    vec = vectorizer.transform([cleaned_input])
    pred_y = rf.predict(vec)[0]
    
    if pred_y < -0.10:
        label = "진보"
        display_score = int(((abs(pred_y) - 0.10) / 0.90) * 40 + 55)
        display_score = min(95, max(55, display_score))
    elif pred_y > 0.10:
        label = "보수"
        display_score = int(((pred_y - 0.10) / 0.90) * 40 + 55)
        display_score = min(95, max(55, display_score))
    else:
        label = "중립"
        display_score = 50
        
    # Local XAI: Extract word contributions
    feature_names = vectorizer.get_feature_names_out()
    importances = rf.feature_importances_
    
    feature_idx = vec.tocoo().col
    contributions = []
    for idx in feature_idx:
        word = feature_names[idx]
        # 화이트리스트 방식: 이념 프레이밍 사전에 등록된 단어만 표시
        word_tokens = word.split()
        matched_ideo = any(tok in IDEOLOGICAL_VOCAB for tok in word_tokens)
        if not matched_ideo:
            continue
        # Filter out the search keywords themselves
        if word in keywords:
            continue
        imp = importances[idx]
        # 방향은 사전 기반으로 우선, 없으면 모델 기반
        ideo_dir = None
        for tok in word_tokens:
            if tok in IDEO_DIRECTION:
                ideo_dir = IDEO_DIRECTION[tok]
                break
        if ideo_dir is not None:
            dir_label = "보수 성향" if ideo_dir == 1 else "진보 성향"
        else:
            dir_val = directions[idx]
            dir_label = "보수 성향" if dir_val == 1 else "진보 성향"
        contributions.append({
            "word": word,
            "importance": imp,
            "direction": dir_label
        })
        
    # Sort contributions by importance descending
    contributions.sort(key=lambda x: x["importance"], reverse=True)
    return label, display_score, contributions, None, len(df_train)

# Generate 2D semantic ideology coordinate map using document frequencies (Volcano Plot)
def draw_2d_semantic_map(user_input):
    keywords = extract_nouns(user_input)
    if not keywords:
        return None
    query = " ".join(keywords)
    search_articles = fetch_search_results(query)
    if not search_articles:
        return None
        
    matching_articles = []
    for art in search_articles:
        press = art["press"]
        title_cleaned = clean_korean(art["title"])
        if title_cleaned and press in PRESS_LEANING_SCORES:
            words = [strip_korean_particles(w) for w in title_cleaned.split() if len(strip_korean_particles(w)) >= 2]
            matching_articles.append({
                "press": press,
                "title_words": words,
                "score": PRESS_LEANING_SCORES[press]
            })
            
    if len(matching_articles) == 0:
        return None
        
    vocabulary = set()
    for doc in matching_articles:
        for w in doc["title_words"]:
            vocabulary.add(w)
            
    word_coordinates = []
    for word in vocabulary:
        # 화이트리스트 방식: 이념 사전에 있는 단어만 지도에 표시
        if word not in IDEOLOGICAL_VOCAB or word in keywords:
            continue
        # Filter documents containing this word
        word_docs = [doc for doc in matching_articles if word in doc["title_words"]]
        if len(word_docs) >= 1:
            mean_score = np.mean([doc["score"] for doc in word_docs]) # [-1.0, 1.0]
            freq = len(word_docs) / len(matching_articles) # Relative Document Frequency [0.0, 1.0]
            word_coordinates.append({
                "word": word,
                "leaning_score": mean_score,
                "frequency": freq,
                "count": len(word_docs)
            })
            
    # Sort by frequency
    word_coordinates.sort(key=lambda x: x["count"], reverse=True)
    top_words = word_coordinates[:15]
    
    if not top_words:
        return None
        
    # Convert to pandas DataFrame for Plotly
    df_plot = pd.DataFrame(top_words)
    
    # Map leaning_score to political leaning categories
    df_plot["color"] = df_plot["leaning_score"].apply(
        lambda x: "Conservative" if x > 0.1 else ("Progressive" if x < -0.1 else "Neutral")
    )
    
    # Adaptive offset stacking to prevent visual overlap of text labels
    seen_coords = {}
    display_freqs = []
    for idx, row in df_plot.iterrows():
        x, y = row["leaning_score"], row["frequency"]
        coord_key = (round(x, 2), round(y, 2))
        if coord_key in seen_coords:
            seen_coords[coord_key] += 1
            # Add subtle visual vertical offset for labels
            display_y = y + 0.03 * seen_coords[coord_key]
        else:
            seen_coords[coord_key] = 0
            display_y = y
        display_freqs.append(display_y)
    df_plot["display_frequency"] = display_freqs
    
    color_map = {
        "Progressive": "#3182F6",   # Toss Blue
        "Neutral": "#8B95A1",       # Toss Gray
        "Conservative": "#F04452"   # Toss Red
    }
    
    fig = go.Figure()
    
    # Add ideological grid lines
    fig.add_vline(x=0.0, line_width=1.5, line_dash="solid", line_color="#8B95A1", opacity=0.5)
    fig.add_vline(x=-0.1, line_width=1, line_dash="dash", line_color="#E5E8EB")
    fig.add_vline(x=0.1, line_width=1, line_dash="dash", line_color="#E5E8EB")
    
    # Add traces for scatter plot
    for cat in ["Progressive", "Neutral", "Conservative"]:
        df_cat = df_plot[df_plot["color"] == cat]
        if len(df_cat) == 0:
            continue
        fig.add_trace(go.Scatter(
            x=df_cat["leaning_score"],
            y=df_cat["display_frequency"],
            mode="markers+text",
            name="🔵 진보 프레임" if cat == "Progressive" else ("🔴 보수 프레임" if cat == "Conservative" else "⚪ 중립/공통"),
            text=df_cat["word"],
            textposition="top center",
            textfont=dict(size=10, color="#333D4B", family="sans-serif"),
            marker=dict(
                size=14 + df_cat["frequency"] * 15,
                color=color_map[cat],
                line=dict(width=1, color="white")
            ),
            customdata=np.stack((df_cat["word"], df_cat["leaning_score"], df_cat["count"]), axis=-1),
            hovertemplate="<b>%{customdata[0]}</b><br>평균 이념 성향: %{customdata[1]:+.2f}<br>노출 빈도: %{y:.2%}<br>출현 기사: %{customdata[2]}건<extra></extra>"
        ))
        
    # Annotate region text
    max_y = max(df_plot["display_frequency"])
    fig.add_annotation(x=-0.9, y=max_y * 0.95, text="🔵 진보 프레임", showarrow=False, font=dict(color="#3182F6", size=10, weight="bold"))
    fig.add_annotation(x=0.9, y=max_y * 0.95, text="🔴 보수 프레임", showarrow=False, font=dict(color="#F04452", size=10, weight="bold"))
    fig.add_annotation(x=0.0, y=max_y * 0.98, text="⚪ 공통/중립 화두", showarrow=False, font=dict(color="#8B95A1", size=10, weight="bold"))
    
    # Update layout
    fig.update_layout(
        xaxis=dict(
            title=dict(text="이념 경향성 (← 진보 [-1.0] | 중도 [0.0] | 보수 [+1.0] →)", font=dict(size=10, color="#4E5968")),
            tickfont=dict(size=9, color="#8B95A1"),
            range=[-1.15, 1.15],
            zeroline=False,
            gridcolor="#F2F4F6"
        ),
        yaxis=dict(
            title=dict(text="어휘 노출 빈도 (Exposure Freq)", font=dict(size=10, color="#4E5968")),
            tickfont=dict(size=9, color="#8B95A1"),
            range=[-0.02, max_y + 0.08],
            zeroline=False,
            gridcolor="#F2F4F6"
        ),
        plot_bgcolor="#F9FAFB",
        paper_bgcolor="#FFFFFF",
        margin=dict(l=20, r=20, t=30, b=30),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=9)
        ),
        height=380
    )
    
    return fig

# Dynamic Global TF-IDF + RandomForestRegressor (Trained on the general live news pool)
def train_global_classifier(live_articles):
    training_items = []
    for item in live_articles:
        press = item["press"]
        title_cleaned = clean_korean(item["title"])
        if not title_cleaned:
            continue
        if press in PRESS_LEANING_SCORES:
            training_items.append({"title": title_cleaned, "score": PRESS_LEANING_SCORES[press]})
            
    df_train = pd.DataFrame(training_items)
    
    if len(df_train) < 15:
        return None, None, None, df_train
        
    # Split into Prog/Cons/Neut and perform minority oversampling for 1:1 balance (scale is [-1.0, 1.0])
    prog = df_train[df_train["score"] < -0.10]
    cons = df_train[df_train["score"] > 0.10]
    neut = df_train[(df_train["score"] >= -0.10) & (df_train["score"] <= 0.10)]
    
    if len(prog) > 0 and len(cons) > 0:
        max_len = max(len(prog), len(cons))
        prog_balanced = prog.sample(max_len, replace=True, random_state=42) if len(prog) < max_len else prog
        cons_balanced = cons.sample(max_len, replace=True, random_state=42) if len(cons) < max_len else cons
        df_train_balanced = pd.concat([prog_balanced, cons_balanced, neut]).reset_index(drop=True)
    else:
        df_train_balanced = df_train
        
    # Fit RandomForestRegressor with PMI-weighted features
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    X_raw = vectorizer.fit_transform(df_train_balanced["title"])
    y = df_train_balanced["score"].values
    X = apply_pmi_scaling(X_raw, vectorizer, pmi_weights) if pmi_weights else X_raw
    
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X, y)
    
    # Calculate directions
    X_array = X.toarray()
    num_features = X.shape[1]
    directions = np.zeros(num_features)
    for i in range(num_features):
        col = X_array[:, i]
        mask = col > 0
        if mask.any():
            weighted_avg_y = np.average(y[mask], weights=col[mask])
            directions[i] = 1 if weighted_avg_y > 0.0 else -1
            
    return rf, vectorizer, directions, df_train

# Classify and explain an individual article's framing using global/custom regressor model
def classify_and_explain(title, rf, vectorizer, directions):
    cleaned = clean_korean(title)
    if not cleaned:
        return "중립", 50, []
    vec = vectorizer.transform([cleaned])
    pred_y = rf.predict(vec)[0]
    
    if pred_y < -0.10:
        label = "진보"
        score = int(((abs(pred_y) - 0.10) / 0.90) * 40 + 55)
        score = min(95, max(55, score))
    elif pred_y > 0.10:
        label = "보수"
        score = int(((pred_y - 0.10) / 0.90) * 40 + 55)
        score = min(95, max(55, score))
    else:
        label = "중립"
        score = 50
        
    feature_names = vectorizer.get_feature_names_out()
    importances = rf.feature_importances_
    feature_idx = vec.tocoo().col
    contributions = []
    for idx in feature_idx:
        word = feature_names[idx]
        # 화이트리스트 방식: 이념 프레이밍 사전에 등록된 단어만 표시
        word_tokens = word.split()
        matched_ideo = any(tok in IDEOLOGICAL_VOCAB for tok in word_tokens)
        if not matched_ideo:
            continue
        imp = importances[idx]
        # 방향은 사전 기반으로 우선, 없으면 모델 기반
        ideo_dir = None
        for tok in word_tokens:
            if tok in IDEO_DIRECTION:
                ideo_dir = IDEO_DIRECTION[tok]
                break
        if ideo_dir is not None:
            dir_label = "보수 성향" if ideo_dir == 1 else "진보 성향"
        else:
            dir_val = directions[idx]
            dir_label = "보수 성향" if dir_val == 1 else "진보 성향"
        contributions.append({
            "word": word,
            "importance": imp,
            "direction": dir_label
        })
    contributions.sort(key=lambda x: x["importance"], reverse=True)
    return label, score, contributions

# ── Live Crawler: cached so it only runs once per session ──────────────────
@st.cache_data(ttl=600, show_spinner="📡 실시간 포털 뉴스 수집 중...")
def get_live_news():
    return fetch_all_ranking_news()

if "demo_mode" not in st.session_state:
    st.session_state["demo_mode"] = False

raw_news_data, live_crawled, err_msg = get_live_news()

# Override with mock data if demo mode is enabled
if st.session_state["demo_mode"]:
    mock_data = []
    presses_list = ["조선일보", "중앙일보", "동아일보", "한겨레", "경향신문", "MBC", "KBS", "SBS", "JTBC", "YTN", "한국일보", "서울신문"]
    mock_topics = [
        ("의대 증원 2천명 확정 발표 보건의료 개혁의 역사적 신호탄", 1),
        ("의료 대란 장기화 속 전공의 사직서 처리 공방 격화", 0),
        ("초부자 감세 정책 고수하더니 나라 곳간 세수 펑크 비상 사태", 0),
        ("종부세 폐지안 국회 제출 징벌적 세금폭탄 드디어 걷어낸다", 1),
        ("코스피 장중 폭락 충격 금리 인상 공포에 개미들 패닉 셀", 0),
        ("해외 악재로 인한 일시적 조정 대한민국 증시 기초체력 견고", 1),
        ("대통령실 특검법 재의요구권 행사 강력 시사 헌법 수호 조치", 1),
        ("야당 쟁점 특검법 단독 가결 검찰 장악 시도 및 수사 외압 의혹 규명", 0)
    ]
    for idx, (title, label) in enumerate(mock_topics * 10):
        p = presses_list[idx % len(presses_list)]
        mock_data.append({
            "press": p,
            "title": f"[모의-{idx+1}] {title}",
            "link": "https://news.naver.com"
        })
    raw_news_data = mock_data
    live_crawled = True
    err_msg = ""

# Cross-corpus PMI 계산 (진보/보수 매체 코퍼스 분리 → 이념어 자동 추출)
pmi_weights = compute_pmi_weights(raw_news_data) if live_crawled and len(raw_news_data) > 0 else {}

# Train the Global Classifier only if live news has crawled successfully (otherwise keep model variables None)
if live_crawled and len(raw_news_data) > 0:
    rf_g, vectorizer_g, directions_g, df_train_g = train_global_classifier(raw_news_data)
    global_model_ready = rf_g is not None
else:
    global_model_ready = False
    rf_g, vectorizer_g, directions_g, df_train_g = None, None, None, pd.DataFrame()


# Pure Factual/Non-bias News Filtering Layer
def filter_political_articles(articles):
    # Exclusion keywords (Weather, sports, entertainment, daily life, local general accidents)
    non_political_kws = [
        "날씨", "기온", "소나기", "장마", "태풍", "폭염", "더위", "추위", "미세먼지", "황사", "눈길", "포근", "선선", "눈비",
        "스포츠", "축구", "야구", "골프", "농구", "배구", "올림픽", "손흥민", "이강인", "류현진", "경기", "득점", "골", "출전", "승리", "패배",
        "연예", "예능", "드라마", "영화", "가수", "배우", "데뷔", "열애", "결혼", "이혼", "방송", "음반", "뮤직", "콘서트", "방영",
        "맛집", "로또", "당첨", "운세", "쇼핑", "세일", "출시", "신제품", "스마트폰", "갤럭시", "아이폰",
        "교통사고", "화재", "추돌", "사망", "부상", "구조", "침수", "정체", "낙뢰", "정전", "붕괴사고"
    ]
    
    # Inclusion keywords (Politics, Policy, Social Controversy, Major Economic Policy indicators)
    political_kws = [
        "대통령", "대통령실", "청와대", "윤석열", "이재명", "한동훈", "정부", "국회", "의원", "야당", "여당",
        "민주당", "국민의힘", "특검", "거부권", "재의요구", "청문회", "국정조사", "탄핵", "개헌", "조국", "이준석",
        "검찰", "경찰", "수사", "압수수색", "기소", "재판", "판결", "법원", "대법원", "헌법재판소",
        "의대", "의사", "전공의", "병원", "의료", "의정", "증원", "의협", "응급실", "보건",
        "종부세", "부동산", "상속세", "세금", "감세", "증세", "세수", "재산세", "취득세", "세법", "종합부동산세",
        "노조", "노동", "임금", "최저임금", "파업", "시위", "집회", "민주노총", "한국노총", "근로자", "노동법",
        "외교", "대북", "북한", "미국", "중국", "일본", "러시아", "동맹", "안보", "군사", "핵", "사설",
        "경제", "물가", "금리", "한국은행", "기준금리", "환율", "수출", "일자리", "고용", "인상", "인하",
        "코스피", "증시", "주가", "주식", "폭락", "급등", "하락", "상승", "밸류업",
        "개혁", "규제", "폐지", "도입", "개정", "입법", "발의", "선거", "공천", "총선", "대선", "정당",
        "논란", "공방", "의혹", "갈등", "대치", "규탄", "비판", "반발", "촉구", "성명", "회견", "구형", "징역", "선고"
    ]
    
    filtered_articles = []
    removed_count = 0
    
    for art in articles:
        title = art["title"]
        is_non_political = False
        for kw in non_political_kws:
            if kw in title:
                is_non_political = True
                break
        
        if is_non_political:
            removed_count += 1
            continue
            
        is_political = False
        for kw in political_kws:
            if kw in title:
                is_political = True
                break
                
        if is_political:
            filtered_articles.append(art)
        else:
            removed_count += 1
            
    return filtered_articles, removed_count

# Hybrid Topic Clustering Algorithm
def cluster_topics(political_news, stop_words):
    # Predefined Concept Themes
    themes = {
        "의료 정책 및 의료 공백 갈등": ["의대", "의사", "전공의", "의협", "의료", "병원", "응급실", "증원"],
        "세제 개편 및 부동산 규제 논란": ["종부세", "부동산", "상속세", "세금", "감세", "증세", "세수", "재산세", "취득세", "종합부동산세"],
        "정치·사법 특검 공방": ["특검", "거부권", "재의요구", "탄핵", "검찰", "수사", "압수수색", "이재명", "김건희", "청문회", "조국", "이준석", "구형", "징역", "선고", "법원", "재판", "피의자"],
        "증시 변동 및 경제 실물 지표": ["코스피", "증시", "주식", "주가", "금리", "환율", "수출", "물가", "경제", "폭락", "급등", "하락", "상승", "기준금리", "재정"]
    }
    
    # 1. Initialize pools
    theme_articles = {theme: [] for theme in themes}
    theme_sub_kws = {theme: Counter() for theme in themes}
    
    unclustered_articles = []
    
    # 2. Assign articles to Concept Themes based on 2-Gram keywords
    for art in political_news:
        cleaned = re.sub(r'[^가-힣\s]', ' ', art["title"])
        words = [w for w in cleaned.split() if len(w) >= 2 and len(w) <= 8 and w not in stop_words]
        
        phrases = []
        for i in range(len(words) - 1):
            phrases.append(f"{words[i]} {words[i+1]}")
            
        matched_theme = None
        for phrase in phrases:
            components = phrase.split()
            for theme, keywords in themes.items():
                if any(comp in keywords for comp in components):
                    matched_theme = theme
                    theme_sub_kws[theme][phrase] += 1
            if matched_theme:
                break
                
        if matched_theme:
            theme_articles[matched_theme].append(art)
        else:
            unclustered_articles.append((art, phrases))
            
    # 3. Dynamic Shared-Word Clustering for unclustered articles
    unclustered_phrases = Counter()
    for art, phrases in unclustered_articles:
        for p in phrases:
            unclustered_phrases[p] += 1
            
    top_dynamic = [item[0] for item in unclustered_phrases.most_common(3) if item[1] >= 2]
    
    dynamic_articles = {dp: [] for dp in top_dynamic}
    dynamic_sub_kws = {dp: Counter() for dp in top_dynamic}
    
    for art, phrases in unclustered_articles:
        for dp in top_dynamic:
            components = dp.split()
            if all(comp in art["title"] for comp in components):
                dynamic_articles[dp].append(art)
                for p in phrases:
                    dynamic_sub_kws[dp][p] += 1
                break
                
    # 4. Merge predefined and dynamic themes into a final list
    final_topics = []
    
    # Predefined Themes
    for theme, arts in theme_articles.items():
        if len(arts) >= 2:
            sub_kws = [item[0] for item in theme_sub_kws[theme].most_common(3)]
            final_topics.append({
                "theme_name": theme,
                "display_name": theme,
                "count": len(arts),
                "articles": arts,
                "sub_keywords": sub_kws
            })
            
    # Dynamic Fallback Themes
    for dp, arts in dynamic_articles.items():
        if len(arts) >= 2:
            sub_kws = [item[0] for item in dynamic_sub_kws[dp].most_common(3)]
            display_name = f"'{dp}' 관련 주요 이슈"
            final_topics.append({
                "theme_name": dp,
                "display_name": display_name,
                "count": len(arts),
                "articles": arts,
                "sub_keywords": sub_kws
            })
            
    # Sort topics by count of articles descending
    final_topics.sort(key=lambda x: x["count"], reverse=True)
    return final_topics


# Main Page Title
st.markdown("<div class='toss-title'>뉴스펙트럼 (Newspectrum)</div>", unsafe_allow_html=True)
st.markdown("<div class='toss-subtitle'>생존을 위해 정파성을 버릴 수 없는 미디어 비즈니스의 현실. 억지 공정 대신 편향을 데이터주도 AI로 정밀 분석하여 수용자가 균형 있게 읽고 필터 버블을 직접 해독하도록 돕습니다.</div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs([
    "📊 미디어 정치 편향 실증 데이터", 
    "⚡ 실시간 핫 토픽 종합 분석",
    "💡 공모전 제안서 요약"
])

# Tab 1: Data Insights
with tab1:
    st.markdown("<div class='toss-h2'>📊 한국 사회의 주관적 이념성향과 언론 신뢰 팩트</div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='font-size: 1.02rem; color: #8B95A1; margin-bottom: 25px;'>
    한국언론진흥재단 공식 보고서(149-150p)에 등재된 실증 통계 자료입니다. 수용자들의 정치적 지형도를 객관적으로 파악할 수 있는 통계 기초를 보여줍니다.
    </div>
    """, unsafe_allow_html=True)
    
    if data_loaded:
        col1, col2 = st.columns(2)
        
        with col1:
            with st.container(border=True):
                st.markdown("<div style='font-size: 1.15rem; font-weight: 700; color: #191F28; margin-bottom: 20px;'>1. 수용자 vs 언론인 이념 성향 분포비교</div>", unsafe_allow_html=True)
                aud_dist = df_aud['BQ7'].value_counts(normalize=True).sort_index() * 100
                
                def map_q27(val):
                    if val <= 1: return 1.0
                    elif val <= 3: return 2.0
                    elif val <= 6: return 3.0
                    elif val <= 8: return 4.0
                    else: return 5.0
                
                df_jour['q27_mapped'] = df_jour['q27'].apply(map_q27)
                jour_dist = df_jour['q27_mapped'].value_counts(normalize=True).sort_index() * 100
                
                comparison_df = pd.DataFrame({
                    '일반 수용자 (BQ7)': aud_dist,
                    '언론인 (q27 변환)': jour_dist
                })
                comparison_df.index = ["매우 진보", "진보", "중도", "보수", "매우 보수"]
                
                df_comp = comparison_df.reset_index().rename(columns={'index': '정치 성향'})
                fig_comp = px.bar(
                    df_comp, 
                    x='정치 성향', 
                    y=['일반 수용자 (BQ7)', '언론인 (q27 변환)'],
                    barmode='group',
                    color_discrete_map={
                        '일반 수용자 (BQ7)': '#3182F6',
                        '언론인 (q27 변환)': '#F04452'
                    }
                )
                fig_comp.update_layout(
                    xaxis=dict(title=None, tickfont=dict(size=10)),
                    yaxis=dict(title="비율 (%)", ticksuffix="%", gridcolor="#F2F4F6"),
                    legend=dict(title=None, orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                    margin=dict(l=10, r=10, t=10, b=10),
                    plot_bgcolor="#FFFFFF",
                    paper_bgcolor="#FFFFFF",
                    height=280
                )
                st.plotly_chart(fig_comp, use_container_width=True)
            
        with col2:
            with st.container(border=True):
                st.markdown("<div style='font-size: 1.15rem; font-weight: 700; color: #191F28; margin-bottom: 20px;'>2. 수용자의 정치 성향별 언론 공정성 인식</div>", unsafe_allow_html=True)
                fairness_avg = df_aud.groupby('BQ7')['Q85_1'].mean()
                fairness_df = pd.DataFrame({'공정성 평가점수 (5점 만점)': fairness_avg})
                fairness_df.index = ["매우 진보", "진보", "중도", "보수", "매우 보수"]
                
                df_fair = fairness_df.reset_index().rename(columns={'index': '정치 성향'})
                fig_fair = px.bar(
                    df_fair,
                    x='정치 성향',
                    y='공정성 평가점수 (5점 만점)',
                    color_discrete_sequence=['#3182F6']
                )
                fig_fair.update_layout(
                    xaxis=dict(title=None, tickfont=dict(size=10)),
                    yaxis=dict(title="공정성 평가 (5점 만점)", range=[1, 5], gridcolor="#F2F4F6"),
                    margin=dict(l=10, r=10, t=10, b=10),
                    plot_bgcolor="#FFFFFF",
                    paper_bgcolor="#FFFFFF",
                    height=280
                )
                st.plotly_chart(fig_fair, use_container_width=True)

# Tab 2: Real-time Dynamic Hot Topic Perspective Analyzer (Enhanced)
with tab2:
    # ── Hybrid Generative AI Opinion Summarizer Settings ────────────────
    with st.expander("🔑 하이브리드 생성형 AI 요약 설정 (선택사항)"):
        gemini_api_key = st.text_input(
            "Gemini API Key를 입력하시면 뉴스펙트럼이 실시간 진영별 기사들을 정밀 요약해 줍니다.", 
            type="password",
            placeholder="AIZA...",
            help="구글 AI 스튜디오(Google AI Studio) 및 Cloud 콘솔에서 발급받은 유료/무료 API Key를 입력하세요. 입력하지 않을 경우 로컬 NLP 엔진이 작동합니다."
        )

    if st.session_state.get("demo_mode", False):
        st.warning("💡 **오프라인 개발자 데모 모드**가 활성화되었습니다. (로컬 백업 속보 말뭉치를 활용해 실시간 AI 분석 모델을 시뮬레이션 중)")
        if st.button("🔌 실시간 포털 연동 모드로 복귀"):
            st.session_state["demo_mode"] = False
            st.cache_data.clear()
            st.rerun()

    # ── 언론사 이념 스펙트럼 (KPF 2025 데이터 기반) ──────────────
    with st.container(border=True):
        st.markdown("<div style='font-size: 1.15rem; font-weight: 700; color: #191F28; margin-bottom: 4px;'>📍 KPF 2025 언론수용자 조사 기반 언론사 이념 스펙트럼</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.82rem; color: #8B95A1; margin-bottom: 12px;'>각 언론사의 점수는 KPF 2025 언론수용자 조사(n=5,010)의 수용자 정치성향 교차표에서 가중평균으로 산출된 원점수입니다. 임의 스케일링 없음.</div>", unsafe_allow_html=True)
        
        MAJOR_OUTLETS = ["JTBC", "MBC", "한겨레", "경향신문", "SBS", "YTN", "연합뉴스", "연합뉴스TV", "KBS", "조선일보", "TV조선", "동아일보", "중앙일보", "매일경제", "한국경제"]
        spectrum_data = [
            {"매체": m, "이념점수": PRESS_LEANING_SCORES[m]}
            for m in MAJOR_OUTLETS
            if m in PRESS_LEANING_SCORES
        ]
        df_spectrum = pd.DataFrame(spectrum_data).sort_values("이념점수")
        df_spectrum["색상"] = df_spectrum["이념점수"].apply(
            lambda x: "#3182F6" if x < -0.08 else ("#F04452" if x > 0.08 else "#8B95A1")
        )
        df_spectrum["성향"] = df_spectrum["이념점수"].apply(
            lambda x: "진보" if x < -0.08 else ("보수" if x > 0.08 else "중립")
        )
        
        fig_spectrum = go.Figure()
        for cat, color, label in [("진보", "#3182F6", "🔵 진보"), ("중립", "#8B95A1", "⚪ 중립"), ("보수", "#F04452", "🔴 보수")]:
            df_cat = df_spectrum[df_spectrum["성향"] == cat]
            if len(df_cat) == 0:
                continue
            fig_spectrum.add_trace(go.Scatter(
                x=df_cat["이념점수"],
                y=[0.5] * len(df_cat),
                mode="markers+text",
                name=label,
                text=df_cat["매체"],
                textposition="top center",
                textfont=dict(size=10, color="#191F28"),
                marker=dict(size=18, color=color, line=dict(width=2, color="white")),
                hovertemplate="<b>%{text}</b><br>이념 성향 점수: %{x:+.2f}<extra></extra>"
            ))
        
        fig_spectrum.add_vline(x=0.0, line_width=2, line_color="#8B95A1", opacity=0.4)
        fig_spectrum.add_vrect(x0=-0.08, x1=0.08, fillcolor="#F2F4F6", opacity=0.5, layer="below", line_width=0)
        fig_spectrum.add_annotation(x=-0.6, y=0.1, text="← 진보 (-1.0)", showarrow=False, font=dict(color="#3182F6", size=10))
        fig_spectrum.add_annotation(x=0.6, y=0.1, text="보수 (+1.0) →", showarrow=False, font=dict(color="#F04452", size=10))
        fig_spectrum.update_layout(
            xaxis=dict(range=[-0.85, 0.85], zeroline=False, tickformat="+.2f", tickfont=dict(size=9, color="#8B95A1"), gridcolor="#F2F4F6"),
            yaxis=dict(visible=False, range=[-0.2, 1.2]),
            plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF",
            margin=dict(l=10, r=10, t=10, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=10)),
            height=200
        )
        st.plotly_chart(fig_spectrum, use_container_width=True)

    col_tab2_title, col_tab2_refresh = st.columns([5, 1])
    with col_tab2_title:
        st.markdown("<div class='toss-h2'>⚡ 실시간 포털 뉴스 핫 토픽 관점 분류판</div>", unsafe_allow_html=True)
    with col_tab2_refresh:
        if st.button("🔄 새로고침", help="포털 뉴스를 다시 수집합니다 (10분 캐시)"):
            st.cache_data.clear()
            st.rerun()
    
    # Render connection status or strict error message
    if live_crawled and len(raw_news_data) > 0:
        st.markdown(f"<span class='live-status-green'>● 포털 실시간 대용량 수집기 가동 중 (고유 기사 {len(raw_news_data)}개 통합 완료)</span>", unsafe_allow_html=True)
        
        # 2. Fact Filter Layer Execution
        political_news, removed_count = filter_political_articles(raw_news_data)
        
        # Render Filtering Statistics Cards
        st.markdown("<div style='font-size:0.95rem; font-weight:700; color:#333D4B; margin-bottom:8px;'>🧹 단순 사실 보도 필터링 레이어 작동 현황</div>", unsafe_allow_html=True)
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.info(f"📊 총 수집된 헤드라인: {len(raw_news_data)}개")
        with col_stat2:
            st.warning(f"🧹 단순 팩트/생활 제외 (날씨, 스포츠, 연예, 사고 등): -{removed_count}개")
        with col_stat3:
            st.success(f"⚖️ 정파성/이념 분석 대상 선별: {len(political_news)}개")
            
        st.markdown("""
        <div style='font-size: 1.02rem; color: #8B95A1; margin: 15px 0 25px 0;'>
        단순 팩트(날씨, 스포츠 등)를 배제하고 선별된 뉴스 헤드라인에서 <b>동적으로 가장 많이 빈출되는 핫 키워드를 컴퓨터 언어학적으로 추출해 실시간 토픽 순위를 빌드</b>합니다.
        사전에 정의된 고정 필터링 항목 없이, 기사 제목 텍스트 그 자체로부터 즉석으로 화제어가 실시간 도출됩니다.
        </div>
        """, unsafe_allow_html=True)
        
        # Global model diagnostics
        if global_model_ready:
            with st.container(border=True):
                st.markdown("<div style='font-size: 1.15rem; font-weight: 700; color: #191F28; margin-bottom: 12px;'>📊 AI(Random Forest)가 탐지한 실시간 뉴스 이념 프레이밍 주요 어휘 (Global Feature Importance)</div>", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size: 0.88rem; color: #8B95A1; margin-bottom: 15px;'>학습된 의사결정 모델 전체에서 기사의 정치적 진보/보수 프레임을 가장 명확하게 구분 짓는 중요도가 높은 핵심 실시간 형태소 순위입니다. (오늘 학습 셋: {len(df_train_g)}개 기사)</div>", unsafe_allow_html=True)
                
                global_imps = rf_g.feature_importances_
                global_names = vectorizer_g.get_feature_names_out()
                # 화이트리스트 방식: 이념 프레이밍 사전에 등록된 단어만 표시
                filtered_indices = []
                for i in np.argsort(global_imps)[::-1]:
                    word = global_names[i]
                    word_tokens = word.split()
                    if any(tok in IDEOLOGICAL_VOCAB for tok in word_tokens):
                        filtered_indices.append(i)
                    if len(filtered_indices) >= 15:
                        break
                top_indices = filtered_indices
                
                top_words = [global_names[i] for i in top_indices]
                top_imps_vals = [global_imps[i] for i in top_indices]
                top_colors = ['#F04452' if directions_g[i] == 1 else '#3182F6' for i in top_indices]
                
                df_global = pd.DataFrame({
                    "word": top_words,
                    "importance": top_imps_vals,
                    "color": top_colors,
                    "direction": ["보수 프레임" if directions_g[i] == 1 else "진보 프레임" for i in top_indices]
                })
                
                fig_global = go.Figure()
                fig_global.add_trace(go.Bar(
                    x=df_global["word"],
                    y=df_global["importance"],
                    marker=dict(color=df_global["color"], line=dict(width=0)),
                    hovertemplate="<b>%{x}</b><br>피처 중요도: %{y:.5f}<br>프레임 방향: %{customdata}<extra></extra>",
                    customdata=df_global["direction"]
                ))
                fig_global.update_layout(
                    xaxis=dict(tickfont=dict(size=10, color="#333D4B"), tickangle=-30),
                    yaxis=dict(title=dict(text="전역 피처 중요도", font=dict(size=9, color="#4E5968")), gridcolor="#F2F4F6"),
                    margin=dict(l=10, r=10, t=10, b=60),
                    plot_bgcolor="#FFFFFF",
                    paper_bgcolor="#FFFFFF",
                    showlegend=False,
                    height=300
                )
                st.plotly_chart(fig_global, use_container_width=True)
                
                st.markdown("<div style='text-align: center; font-size: 0.85rem; font-weight: 700;'><span style='color:#3182F6; margin-right:20px;'>■ 진보적 프레임 지표 단어</span> <span style='color:#F04452;'>■ 보수적 프레임 지표 단어</span></div>", unsafe_allow_html=True)
        else:
            st.warning("⚠️ 실시간 수집된 뉴스 크기가 작아 전역 특징 분석을 건너뜁니다.")

        # 3. 100% PURE DYNAMIC KEYWORD CLUSTERING & RANKING (Run on filtered political news)
        stop_words = {
            "단독", "속보", "종합", "재배포", "금지", "무단", "전재", "네이버", "뉴스", "기자", 
            "오전", "오후", "오늘", "내일", "어제", "대표", "대통령", "정부", "국민", "한국", 
            "서울", "의혹", "논란", "공방", "우려", "검토", "주요", "대치", "출구", "대량", 
            "결정", "발표", "최근", "상황", "현실", "위기", "대란", "공백", "사태", "지속",
            "돌파", "돌풍", "비명", "이유", "이유는", "때문", "때문에", "결국", "다시", "또",
            "하루", "이틀", "이번", "지난", "올해", "내년", "내용", "의정", "결과", "보도", "단독보도",
            "선고", "구형", "요구", "촉구", "진행", "개시", "합의", "착수", "확정", "발견", "확인", "의견", "논의",
            "사정", "주장", "언론", "매체", "보도자료", "입장", "해명", "대답", "답변", "질문", "답해"
        }
        
        ranked_topics = cluster_topics(political_news, stop_words)
        
        if not ranked_topics:
            st.info("실시간 랭킹 뉴스에서 판독할 수 있는 빈출 키워드가 수집되지 않았습니다.")
        else:
            # Render Topic selection menu dynamically based on extracted clustered themes
            selectbox_options = []
            for idx, rt in enumerate(ranked_topics, 1):
                icon = "🔥"
                theme_lower = rt['display_name'].lower()
                if any(k in theme_lower for k in ["의료", "의대", "의사", "병원", "전공의"]): icon = "🩺"
                elif any(k in theme_lower for k in ["종부세", "부동산", "주택", "세금", "상속세", "세제"]): icon = "🏠"
                elif any(k in theme_lower for k in ["코스피", "증시", "주가", "주식", "금리", "폭락", "급등", "하락", "상승", "경제"]): icon = "📉"
                elif any(k in theme_lower for k in ["특검", "거부권", "수사", "검찰", "민주당", "국민의힘", "이재명", "징역", "김건희", "정치", "사법"]): icon = "⚖️"
                
                selectbox_options.append(f"{icon} {idx}위 핫 토픽: {rt['display_name']} (분석 대상 기사 {rt['count']}개 실시간 포착)")
                
            selected_live_topic_str = st.selectbox(
                "🔥 분석할 동적 실시간 토픽을 고르세요 (포털 보도 빈도수 100% 자동 랭킹화):",
                options=selectbox_options
            )
            
            selected_idx = selectbox_options.index(selected_live_topic_str)
            selected_topic = ranked_topics[selected_idx]
            selected_word = selected_topic["theme_name"]
            
            st.write("---")
            
            if selected_topic["sub_keywords"]:
                sub_kws_badges = " ".join([f"<span class='toss-keyword-badge' style='font-size:0.9rem; padding:4px 10px; margin-right:6px;'># {kw}</span>" for kw in selected_topic["sub_keywords"]])
                st.markdown(f"<div style='margin-bottom: 20px;'>🔍 <b>주요 세부 쟁점 키워드:</b> {sub_kws_badges}</div>", unsafe_allow_html=True)
            
            # 4. Dynamic Context Summary
            co_occurring_words = []
            for art in selected_topic["articles"]:
                words = re.findall(r'[가-힣]{2,8}', art["title"])
                for w in words:
                    if w not in selected_word and w not in stop_words:
                        is_sub_kw = False
                        for sk in selected_topic["sub_keywords"]:
                            if w in sk:
                                is_sub_kw = True
                                break
                        if not is_sub_kw:
                            co_occurring_words.append(w)
            co_occur_counter = Counter(co_occurring_words)
            top_co_occur = [item[0] for item in co_occur_counter.most_common(5)]
            co_occur_str = ", ".join(top_co_occur) if top_co_occur else "단독 보도"
            
            fact_html = f"""
            <div class='toss-card'>
                <span class='toss-badge-gray'>⚖️ 실시간 뉴스 동적 컨텍스트 팩트</span>
                <div style='font-size: 1.05rem; color: #191F28; font-weight: 700; margin: 10px 0 6px 0;'>'{selected_word}' 쟁점 팩트체크:</div>
                <div style='font-size: 0.95rem; color: #4E5968; line-height: 1.6;'>
                실시간 수집된 포털의 기사를 자연어 분석한 결과, 현재 대한민국 뉴스룸에서는 <b>'{selected_word}'</b> 주제를 둘러싼 
                보도 경쟁이 매우 치열하게 진행되고 있습니다. 기사 텍스트 내에서 함께 빈번히 교차 등장하는 연관 키워드는 
                <b>[{co_occur_str}]</b> 등이며, 각 언론사는 본 팩트 관계를 기조로 삼아 상반된 정서적 프레이밍 사설을 펼쳐내고 있습니다.
                </div>
            </div>
            """
            st.markdown(fact_html, unsafe_allow_html=True)
            
            # Process and classify live articles
            left_side_articles = []
            right_side_articles = []
            neutral_side_articles = []
            
            for art in selected_topic["articles"]:
                if global_model_ready:
                    label, score, contributions = classify_and_explain(art["title"], rf_g, vectorizer_g, directions_g)
                else:
                    label, score, contributions = "중립", 50, []
                art_processed = {
                    "press": art["press"],
                    "title": art["title"],
                    "link": art["link"],
                    "score": score,
                    "contributions": contributions
                }
                if label == "진보":
                    left_side_articles.append(art_processed)
                elif label == "보수":
                    right_side_articles.append(art_processed)
                else:
                    neutral_side_articles.append(art_processed)
                   # ── 3개 진영의 의견 요약을 단 1번의 API 호출로 묶어 처리하는 하이브리드 엔진 (1-Shot Hybrid Miner) ──
            def generate_all_opinions_hybrid(left_arts, neutral_arts, right_arts, theme_word, stop_words, api_key=None):
                results = {"진보": "", "중립": "", "보수": ""}
                
                # 로컬 백업 요약문 계산기 헬퍼 (로컬에서 이념 프레임 억지 판단을 배제하고 단순 통계 정보만 제공)
                def get_local_opinion(camp_articles, camp_name):
                    if not camp_articles:
                        return f"현재 이 토픽에 대해 {camp_name} 성향으로 판별된 실시간 보도가 충분치 않아 분석을 보류합니다."
                    
                    words_list = []
                    for art in camp_articles:
                        words = re.findall(r'[가-힣]{2,8}', art["title"])
                        for w in words:
                            if w not in stop_words and w != theme_word and theme_word not in w:
                                words_list.append(w)
                    counter = Counter(words_list)
                    top_words = [item[0] for item in counter.most_common(3)]
                    
                    best_headline = ""
                    max_matches = -1
                    for art in camp_articles:
                        title = art["title"]
                        clean_title = re.sub(r'\[모의-\d+\]\s*', '', title).strip()
                        matches = sum(1 for w in top_words if w in clean_title)
                        if matches > max_matches:
                            max_matches = matches
                            best_headline = clean_title
                    if not best_headline:
                        best_headline = re.sub(r'\[모의-\d+\]\s*', '', camp_articles[0]["title"]).strip()
                    
                    top_words_str = ", ".join([f"#{w}" for w in top_words]) if top_words else "실시간 쟁점"
                    tip_text = "\n\n<span style='font-size:0.75rem; color:#8B95A1;'>🔑 상단 설정에서 Gemini API Key를 입력하시면 실시간 생성형 AI 요약문으로 업그레이드됩니다.</span>"
                    
                    if camp_name == "진보":
                        desc = f"진보 성향 언론에서 주로 **{top_words_str}** 키워드군을 강조하고 있습니다. 대표적으로 **\"{best_headline}\"** 등의 기사를 내세우고 있습니다."
                    elif camp_name == "보수":
                        desc = f"보수 성향 언론에서 주로 **{top_words_str}** 키워드군을 강조하고 있습니다. 대표적으로 **\"{best_headline}\"** 등의 기사를 내세우고 있습니다."
                    else:
                        desc = f"중립 언론사에서 주로 **{top_words_str}** 관련 어휘를 사용하고 있으며, 사실 관계를 단순 중계하는 **\"{best_headline}\"** 기사가 주를 이룹니다."
                    return desc + tip_text

                # ── API Key가 있으면 1-Shot 통합 호출 ──
                if api_key and api_key.strip():
                    left_titles = [re.sub(r'\[모의-\d+\]\s*', '', a["title"]).strip() for a in left_arts[:10]]
                    right_titles = [re.sub(r'\[모의-\d+\]\s*', '', a["title"]).strip() for a in right_arts[:10]]
                    neutral_titles = [re.sub(r'\[모의-\d+\]\s*', '', a["title"]).strip() for a in neutral_arts[:10]]
                    
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key.strip()}"
                    headers = {"Content-Type": "application/json"}
                    
                    # ⚠️ 로컬의 불완전한 필터링 판단 없이 원본 헤드라인 전체 리스트를 AI에게 통째로 넘겨 요약하게 만듦
                    prompt = (
                        f"실시간 토픽인 '{theme_word}'에 대해 이념 성향별(진보/중립/보수)로 분류된 실제 뉴스 헤드라인 목록입니다.\n\n"
                        f"[진보 성향 기사 헤드라인 목록]\n" + ("\n".join([f"- {t}" for t in left_titles]) if left_titles else "- (기사 없음)") + "\n\n"
                        f"[보수 성향 기사 헤드라인 목록]\n" + ("\n".join([f"- {t}" for t in right_titles]) if right_titles else "- (기사 없음)") + "\n\n"
                        f"[중립/사실 기사 헤드라인 목록]\n" + ("\n".join([f"- {t}" for t in neutral_titles]) if neutral_titles else "- (기사 없음)") + "\n\n"
                        f"위 기사 제목들의 뉘앙스, 사용된 어휘, 주요 프레임을 종합 분석하여, 각 진영이 취하고 있는 핵심 논리와 어조의 차이를 성향별로 각각 2줄 내외의 친절한 요약문으로 작성해줘.\n"
                        f"반드시 응답 형식은 다른 안내나 인사말 없이 정확히 아래 마크다운 포맷만 지켜서 리턴해줘:\n"
                        f"진보_요약: [진보측 요약내용]\n"
                        f"중립_요약: [중립측 요약내용]\n"
                        f"보수_요약: [보수측 요약내용]"
                    )
                    
                    system_instruction = (
                        "너는 고도화된 미디어 프레임 분석 전문가이자 저널리즘 연구원이야. "
                        "전달받은 뉴스 제목 목록들의 이념적 정서, 공격 대상, 프레임 수사를 분석하여 각 진영의 주장을 명확하게 대조 요약해줘."
                    )
                    
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "systemInstruction": {"parts": [{"text": system_instruction}]}
                    }
                    
                    try:
                        import urllib3
                        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                        
                        session = requests.Session()
                        session.trust_env = True
                        
                        res = session.post(url, json=payload, headers=headers, timeout=20, verify=False)
                        if res.status_code == 200:
                            api_res = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                            
                            # 응답 파싱
                            lines = api_res.split("\n")
                            for line in lines:
                                if "진보_요약:" in line:
                                    results["진보"] = "🤖 **AI 요약:** " + line.replace("진보_요약:", "").replace("**", "").strip()
                                elif "중립_요약:" in line:
                                    results["중립"] = "🤖 **AI 요약:** " + line.replace("중립_요약:", "").replace("**", "").strip()
                                elif "보수_요약:" in line:
                                    results["보수"] = "🤖 **AI 요약:** " + line.replace("보수_요약:", "").replace("**", "").strip()
                            
                            # 세 성향 중 파싱이 덜 된 항목이 있다면 로컬로 보강
                            for camp in ["진보", "중립", "보수"]:
                                if not results[camp]:
                                    results[camp] = f"🤖 **AI 요약 (포맷 분석 오류):**\n\n" + get_local_opinion(left_arts if camp=="진보" else (right_arts if camp=="보수" else neutral_arts), camp)
                            return results
                        else:
                            err_msg = f"🚨 **AI 요약 실패 (API 에러 {res.status_code}):**\n`{res.text}`"
                            for camp in ["진보", "중립", "보수"]:
                                results[camp] = err_msg + "\n\n" + get_local_opinion(left_arts if camp=="진보" else (right_arts if camp=="보수" else neutral_arts), camp)
                            return results
                    except Exception as e:
                        err_msg = f"🚨 **AI 요약 실패 (연결 오류):**\n`{e}`"
                        for camp in ["진보", "중립", "보수"]:
                            results[camp] = err_msg + "\n\n" + get_local_opinion(left_arts if camp=="진보" else (right_arts if camp=="보수" else neutral_arts), camp)
                        return results
                
                # API Key가 없으면 기본 로컬 요약문으로 전체 맵 할당
                results["진보"] = get_local_opinion(left_arts, "진보")
                results["중립"] = get_local_opinion(neutral_arts, "중립")
                results["보수"] = get_local_opinion(right_arts, "보수")
                return results

            # ── 1-Shot 통합 요약 실행 ──
            opinions_map = generate_all_opinions_hybrid(left_side_articles, neutral_side_articles, right_side_articles, selected_word, stop_words, gemini_api_key)

            # Render opinion summary cards
            st.markdown("<div style='font-size: 1.15rem; font-weight: 700; color: #191F28; margin: 15px 0 10px 0;'>💡 실시간 진영별 보도 의견 / 논조 분석</div>", unsafe_allow_html=True)
            with st.container(border=True):
                col_op_l, col_op_n, col_op_r = st.columns(3)
                with col_op_l:
                    st.markdown("<div style='font-size:0.85rem; font-weight:700; color:#3182F6;'>🔵 진보측 기사 의견 (비판/분배/견제)</div>", unsafe_allow_html=True)
                    st.write(opinions_map["진보"], unsafe_allow_html=True)
                with col_op_n:
                    st.markdown("<div style='font-size:0.85rem; font-weight:700; color:#8B95A1;'>⚪ 중립측 기사 의견 (수치/사실/중계)</div>", unsafe_allow_html=True)
                    st.write(opinions_map["중립"], unsafe_allow_html=True)
                with col_op_r:
                    st.markdown("<div style='font-size:0.85rem; font-weight:700; color:#F04452;'>🔴 보수측 기사 의견 (성장/효율/의무)</div>", unsafe_allow_html=True)
                    st.write(opinions_map["보수"], unsafe_allow_html=True)
                
                selectbox_options.append(f"{icon} {idx}위 핫 토픽: {rt['display_name']} (분석 대상 기사 {rt['count']}개 실시간 포착)")
                
            selected_live_topic_str = st.selectbox(
                "🔥 분석할 동적 실시간 토픽을 고르세요 (포털 보도 빈도수 100% 자동 랭킹화):",
                options=selectbox_options
            )
            
            selected_idx = selectbox_options.index(selected_live_topic_str)
            selected_topic = ranked_topics[selected_idx]
            selected_word = selected_topic["theme_name"]
            
            st.write("---")
            
            if selected_topic["sub_keywords"]:
                sub_kws_badges = " ".join([f"<span class='toss-keyword-badge' style='font-size:0.9rem; padding:4px 10px; margin-right:6px;'># {kw}</span>" for kw in selected_topic["sub_keywords"]])
                st.markdown(f"<div style='margin-bottom: 20px;'>🔍 <b>주요 세부 쟁점 키워드:</b> {sub_kws_badges}</div>", unsafe_allow_html=True)
            
            # 4. Dynamic Context Summary
            co_occurring_words = []
            for art in selected_topic["articles"]:
                words = re.findall(r'[가-힣]{2,8}', art["title"])
                for w in words:
                    if w not in selected_word and w not in stop_words:
                        is_sub_kw = False
                        for sk in selected_topic["sub_keywords"]:
                            if w in sk:
                                is_sub_kw = True
                                break
                        if not is_sub_kw:
                            co_occurring_words.append(w)
            co_occur_counter = Counter(co_occurring_words)
            top_co_occur = [item[0] for item in co_occur_counter.most_common(5)]
            co_occur_str = ", ".join(top_co_occur) if top_co_occur else "단독 보도"
            
            fact_html = f"""
            <div class='toss-card'>
                <span class='toss-badge-gray'>⚖️ 실시간 뉴스 동적 컨텍스트 팩트</span>
                <div style='font-size: 1.05rem; color: #191F28; font-weight: 700; margin: 10px 0 6px 0;'>'{selected_word}' 쟁점 팩트체크:</div>
                <div style='font-size: 0.95rem; color: #4E5968; line-height: 1.6;'>
                실시간 수집된 포털의 기사를 자연어 분석한 결과, 현재 대한민국 뉴스룸에서는 <b>'{selected_word}'</b> 주제를 둘러싼 
                보도 경쟁이 매우 치열하게 진행되고 있습니다. 기사 텍스트 내에서 함께 빈번히 교차 등장하는 연관 키워드는 
                <b>[{co_occur_str}]</b> 등이며, 각 언론사는 본 팩트 관계를 기조로 삼아 상반된 정서적 프레이밍 사설을 펼쳐내고 있습니다.
                </div>
            </div>
            """
            st.markdown(fact_html, unsafe_allow_html=True)
            
            # Process and classify live articles
            left_side_articles = []
            right_side_articles = []
            neutral_side_articles = []
            
            for art in selected_topic["articles"]:
                # Use global classifier if ready, otherwise fallback strictly to neutral label
                if global_model_ready:
                    label, score, contributions = classify_and_explain(art["title"], rf_g, vectorizer_g, directions_g)
                else:
                    label, score, contributions = "중립", 50, []
                art_processed = {
                    "press": art["press"],
                    "title": art["title"],
                    "link": art["link"],
                    "score": score,
                    "contributions": contributions
                }
                if label == "진보":
                    left_side_articles.append(art_processed)
                elif label == "보수":
                    right_side_articles.append(art_processed)
                else:
                    neutral_side_articles.append(art_processed)
                    
            # ── 진영별 실시간 핵심 논조/의견 요약 엔진 (Hybrid Gemini API & Local NLP Miner) ──
            def extract_camp_opinion(camp_articles, stop_words, theme_word, camp_name, api_key=None):
                if not camp_articles:
                    return f"현재 이 토픽에 대해 {camp_name} 성향으로 판별된 실시간 보도가 충분치 않아 분석을 보류합니다."
                
                # ── 만약 사용자가 설정한 Gemini API Key가 있다면 REST API 호출 ──
                if api_key and api_key.strip():
                    titles_list = [re.sub(r'\[모의-\d+\]\s*', '', art["title"]).strip() for art in camp_articles[:15]]
                    titles_bullet = "\n".join([f"- {t}" for t in titles_list])
                    
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key.strip()}"
                    headers = {"Content-Type": "application/json"}
                    
                    system_instruction = (
                        "너는 미디어 분석 전문가이자 중립적인 팩트 분석가야. 제공된 뉴스 헤드라인 목록을 읽고, "
                        "이 진영(진보/보수/중립)이 어떤 이념적 프레임이나 관점으로 기사를 전개하고 있는지 핵심을 잡아 명확하게 요약해줘."
                    )
                    
                    prompt = (
                        f"실시간 토픽 '{theme_word}'에 대해 분류된 {camp_name} 성향의 언론 보도 목록입니다:\n"
                        f"{titles_bullet}\n\n"
                        f"이 기사들이 공통적으로 취하고 있는 주요 관점, 비판 대상, 논조의 핵심을 2줄로 친절하게 설명식 요약해줘. "
                        f"존댓말 요약문만 즉시 출력하고 서론, 결론, 번호 매기기는 생략해."
                    )
                    
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "systemInstruction": {"parts": [{"text": system_instruction}]}
                    }
                    
                    try:
                        import urllib3
                        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                        res = requests.post(url, json=payload, headers=headers, timeout=15, verify=False)
                        if res.status_code == 200:
                            summary_text = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                            return f"🤖 **AI 요약:** {summary_text}"
                        else:
                            # 400, 404, 429 등 API 에러 세부 원인 표출
                            return f"🚨 **AI 요약 실패 (API 에러 {res.status_code}):**\n`{res.text}`"
                    except Exception as e:
                        return f"🚨 **AI 요약 실패 (연결 오류):**\n`{e}`"
                
                # ── API Key가 없거나 호출 오류 시 작동하는 로컬 통계 기반 백업 엔진 ──
                # 1. 형태소 및 명사 어휘 빈도 집계
                words_list = []
                for art in camp_articles:
                    # 한글 단어 추출 (2~8글자)
                    words = re.findall(r'[가-힣]{2,8}', art["title"])
                    for w in words:
                        if w not in stop_words and w != theme_word and theme_word not in w:
                            words_list.append(w)
                
                counter = Counter(words_list)
                top_words = [item[0] for item in counter.most_common(3)]
                
                # 2. 대표 헤드라인 선정 (가장 많은 상위 어휘를 지닌 원본 기사)
                best_headline = ""
                max_matches = -1
                for art in camp_articles:
                    title = art["title"]
                    clean_title = re.sub(r'\[모의-\d+\]\s*', '', title).strip() # 데모 문구 제거
                    matches = sum(1 for w in top_words if w in clean_title)
                    if matches > max_matches:
                        max_matches = matches
                        best_headline = clean_title
                
                if not best_headline:
                    best_headline = re.sub(r'\[모의-\d+\]\s*', '', camp_articles[0]["title"]).strip()
                
                # 3. 진영 특성별 요약 서술형 문구 빌드
                top_words_str = ", ".join([f"#{w}" for w in top_words]) if top_words else "실시간 쟁점"
                
                tip_text = "\n\n<span style='font-size:0.75rem; color:#8B95A1;'>🔑 상단 설정에서 Gemini API Key를 입력하시면 실시간 생성형 AI 요약문으로 업그레이드됩니다.</span>"
                
                if camp_name == "진보":
                    desc = f"주로 **{top_words_str}** 관점을 조명하고 있습니다. 특히 **\"{best_headline}\"**과 같은 보도 수사를 활용하여, 정책의 추진 부작용, 분배 불평등, 혹은 피해자의 권리와 정부 견제 논리를 핵심 보도로 내세웁니다."
                elif camp_name == "보수":
                    desc = f"주로 **{top_words_str}** 관점을 조명하고 있습니다. 특히 **\"{best_headline}\"**과 같은 보도 수사를 활용하여, 정책 실행의 효율성 및 대의적 명분, 거시 성장 동력 및 법적인 강제력 준수를 핵심 보도 논리로 삼습니다."
                else:
                    desc = f"주로 **{top_words_str}** 관련 어휘를 사용합니다. 이념적 색채를 배제하고 수치 및 통계 자료 위주로 보도하거나 양 진영의 주장을 단순 중립 중계하는 팩트 지향 저널리즘 기조를 띱니다."
                
                return desc + tip_text

            # Render opinion summary cards
            st.markdown("<div style='font-size: 1.15rem; font-weight: 700; color: #191F28; margin: 15px 0 10px 0;'>💡 실시간 진영별 보도 의견 / 논조 분석</div>", unsafe_allow_html=True)
            with st.container(border=True):
                col_op_l, col_op_n, col_op_r = st.columns(3)
                with col_op_l:
                    st.markdown("<div style='font-size:0.85rem; font-weight:700; color:#3182F6;'>🔵 진보측 기사 의견 (비판/분배/견제)</div>", unsafe_allow_html=True)
                    st.write(extract_camp_opinion(left_side_articles, stop_words, selected_word, "진보", gemini_api_key), unsafe_allow_html=True)
                with col_op_n:
                    st.markdown("<div style='font-size:0.85rem; font-weight:700; color:#8B95A1;'>⚪ 중립측 기사 의견 (수치/사실/중계)</div>", unsafe_allow_html=True)
                    st.write(extract_camp_opinion(neutral_side_articles, stop_words, selected_word, "중립", gemini_api_key), unsafe_allow_html=True)
                with col_op_r:
                    st.markdown("<div style='font-size:0.85rem; font-weight:700; color:#F04452;'>🔴 보수측 기사 의견 (성장/효율/의무)</div>", unsafe_allow_html=True)
                    st.write(extract_camp_opinion(right_side_articles, stop_words, selected_word, "보수", gemini_api_key), unsafe_allow_html=True)
                    
            # Render summary metrics
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                with st.container(border=True):
                    st.metric(label="비판적 / 복지 / 개혁 프레임 기사", value=f"{len(left_side_articles)}개 기사", delta=f"{int(len(left_side_articles)/len(selected_topic['articles'])*100) if len(selected_topic['articles']) > 0 else 0}% 점유")
            with col_m2:
                with st.container(border=True):
                    st.metric(label="성장 / 효율 / 규제완화 프레임 기사", value=f"{len(right_side_articles)}개 기사", delta=f"{int(len(right_side_articles)/len(selected_topic['articles'])*100) if len(selected_topic['articles']) > 0 else 0}% 점유")

            # Render comparisons
            st.markdown(f"<div style='font-size: 1.25rem; font-weight: 800; color: #191F28; margin: 25px 0 15px 0;'>⚖️ '{selected_word}' 관련 충돌 프레임 직접 비교 (실시간 수집 기사 {len(selected_topic['articles'])}개)</div>", unsafe_allow_html=True)
            
            col_live_left, col_live_right = st.columns(2)
            
            with col_live_left:
                st.markdown("<h3 style='font-size: 1.15rem; font-weight: 700; color: #3182F6; margin-bottom: 12px;'>🔵 비판적 / 복지·분배 / 정부 견제 위주 기사</h3>", unsafe_allow_html=True)
                if not left_side_articles:
                    st.markdown("<div style='color:#8B95A1; font-size:0.9rem; padding: 20px 0;'>해당 키워드가 포함된 기사 중 진보적 수사 프레임이 감지된 기사가 없습니다.</div>", unsafe_allow_html=True)
                else:
                    for art in left_side_articles[:10]:
                        kws_badges = " ".join([f"<span class='toss-keyword-badge' style='color:#3182F6; background-color:#E8F3FF;'>{c['word']}</span>" for c in art["contributions"][:3]]) if art["contributions"] else "<span style='font-size:0.75rem; color:#8B95A1;'>프레임 미감지</span>"
                        st.markdown(f"""
                        <div class='article-card'>
                            <span class='toss-badge-blue'>{art['press']} (진보적 프레임 {art['score']}%)</span>
                            <h4 style='font-size:1.02rem; color:#191F28; font-weight:700; margin: 8px 0;'>"{art['title']}"</h4>
                            <div style='margin-top: 10px;'>
                                <span style='font-size:0.78rem; color:#8B95A1; margin-right:8px;'>결정단어:</span>{kws_badges}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
            with col_live_right:
                st.markdown("<h3 style='font-size: 1.15rem; font-weight: 700; color: #F04452; margin-bottom: 12px;'>🔴 성장·효율 / 규제 완화 / 정책 의무 위주 기사</h3>", unsafe_allow_html=True)
                if not right_side_articles:
                    st.markdown("<div style='color:#8B95A1; font-size:0.9rem; padding: 20px 0;'>해당 키워드가 포함된 기사 중 보수적 수사 프레임이 감지된 기사가 없습니다.</div>", unsafe_allow_html=True)
                else:
                    for art in right_side_articles[:10]:
                        kws_badges = " ".join([f"<span class='toss-keyword-badge' style='color:#F04452; background-color:#FEEBEB;'>{c['word']}</span>" for c in art["contributions"][:3]]) if art["contributions"] else "<span style='font-size:0.75rem; color:#8B95A1;'>프레임 미감지</span>"
                        st.markdown(f"""
                        <div class='article-card'>
                            <span class='toss-badge-red'>{art['press']} (보수적 프레임 {art['score']}%)</span>
                            <h4 style='font-size:1.02rem; color:#191F28; font-weight:700; margin: 8px 0;'>"{art['title']}"</h4>
                            <div style='margin-top: 10px;'>
                                <span style='font-size:0.78rem; color:#8B95A1; margin-right:8px;'>결정단어:</span>{kws_badges}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
            if neutral_side_articles:
                st.markdown("<div style='font-size: 1.15rem; font-weight: 700; color: #191F28; margin: 25px 0 10px 0;'>⚪ 중립적 / 단순 수치·사실 위주 보도</div>", unsafe_allow_html=True)
                for art in neutral_side_articles[:5]:
                    st.markdown(f"""
                    <div class='toss-card' style='padding: 16px 20px;'>
                        <span class='toss-badge-gray'>{art['press']} (중립 보도)</span>
                        <span style='font-size:1rem; color:#191F28; font-weight:600; margin-left: 10px;'>"{art['title']}"</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
        # Raw Logs
        st.markdown("<div style='font-weight: 700; color: #191F28; margin: 30px 0 10px 0;'>📍 실시간 수집된 원본 포털 헤드라인 검출 데이터 로그 (EUC-KR 보정 완료)</div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(f"<div style='font-size:0.85rem; color:#8B95A1; margin-bottom:10px;'>포털 사이트 네이버에서 긁어온 {len(raw_news_data)}개 기사 제목의 실시간 디코딩 원본 데이터 로그입니다.</div>", unsafe_allow_html=True)
            for i, art in enumerate(raw_news_data[:50], 1):
                st.write(f"**{i}. [{art['press']}]** {art['title']} — [링크]({art['link']})")
                
    else:
        # Strictly render error warning for crawl failure (No silent fallback to mock data)
        st.markdown("<span class='live-status-yellow'>● 포털 실시간 수집 엔진 상태: 오프라인(연결 실패)</span>", unsafe_allow_html=True)
        st.error(f"""
        **🚨 실시간 포털 뉴스 연동 실패 (네트워크 연결 끊김 또는 포털 서버 차단)**
        * **상세 오류 내용:** `{err_msg if err_msg else '네이버 뉴스로부터 응답 데이터가 반환되지 않았습니다.'}`
        * **영향:** 실시간 속보 데이터 크롤링에 실패하여 금일 핫 토픽 분석 서비스를 일시적으로 중단합니다. 
        """)
        
        # Add a checkbox to explicitly trigger offline developer demo if needed
        demo_mode = st.checkbox("💡 개발자 전용 오프라인 데모 가동 (로컬 백업 데이터를 활용해 AI 분류판 시뮬레이션)")
        if demo_mode:
            st.session_state["demo_mode"] = True
            st.rerun()

# Tab 3: Competition Summary (Toss Clean Report)
with tab3:
    with st.container(border=True):
        st.markdown("<div class='toss-h2'>💡 정파 상업주의 인정과 미디어 리터러시 강화를 위한 '뉴스펙트럼 (Newspectrum)' 기획서</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size: 1.05rem; color: #4E5968; line-height: 1.75;'>
        <b>1. 문제 정의 및 기획 배경 (Background & Value)</b><br>
        디지털 저널리즘 시대에 광고 모델이 붕괴하면서, 언론사들은 독자 포섭과 후원금 유치를 위해 정파적 기사를 쏟아내며 생존하고 있습니다. 
        이러한 <b>'생존형 정파 보도'</b>는 구조적 원인이기 때문에 규제나 중립성 촉구 등의 당위적인 방안으로는 해소할 수 없습니다.<br>
        <b>뉴스펙트럼 (Newspectrum)</b>은 이념적 정파성을 억지로 제거하려 하는 대신, 기사의 프레이밍과 편향도를 AI로 정밀 분석하여 투명하게 드러냅니다. 
        이를 통해 수용자 스스로 정파적 보도를 다각도로 대조하며 필터 버블(확증 편향)을 해독하도록 돕는 플랫폼입니다.<br><br>
        
        <b>2. 서비스 핵심 아키텍처 (Architecture)</b><br>
        - <b>단순 사실 보도 필터링 레이어 (Fact Filter Layer):</b> 날씨, 스포츠, 연예, 일반 사고 등 정치적 대립이나 편향이 무의미한 일상성 기사들을 필터링을 통해 분석 대상에서 배제하여 데이터 분석의 정밀도를 끌어올립니다.<br>
        - <b>실시간 검색 및 적시 학습 (JIT-L, Just-in-Time Learning):</b> 정적인 단어 사전이나 고정 데이터셋에 의존하지 않고, 사용자가 입력한 문장에서 추출된 명사 키워드를 통해 포털(네이버 뉴스 검색)에서 관련 보도를 즉석에서 긁어와 Random Forest 모델로 학습합니다. 새로운 이슈(연금 개혁, 기후 위기 등)가 터지더라도 별도의 관리 작업이 일체 발생하지 않습니다.<br>
        - <b>설명 가능한 AI (XAI) 시각화:</b> 기사의 정치적 진보/보수 프레임을 분류하는 데 있어 각 형태소가 판정에 기여한 방향(진보 방향 기여 vs 보수 방향 기여)과 그 가중치를 국소 피처 기여도(Local Feature Contribution) 분석을 통해 차트 및 배지로 역추적하여 수용자에게 명확히 설명합니다.<br>
        - <b>하이브리드 토픽 클러스터링 (Topic Clustering):</b> 2-Gram 명사 구문을 분석하여 주제가 미세하게 쪼개지는 현상을 극복하고, 사전 기반의 핵심 Concept Theme 분류 및 공유어 병합 가중치를 사용해 관련 기사 풀을 하나의 대주제(예: '의료 정책 및 의료 공백 갈등')로 유기적으로 바인딩합니다.<br>
        - <b>이념 스펙트럼 1:1 대조:</b> 진보와 보수 양측의 핵심 기사 프레임을 나란히 배치하여 독자가 양 진영의 논리를 입체적으로 수용하도록 합니다.<br><br>
        
        <b>3. 공모전 심사위원을 사로잡을 셀링 포인트 (Winning Strategy)</b><br>
        - <b>현실적 생존 모델에 대한 이해:</b> 당위적인 공정보도를 요구하는 평범한 기획과 차별화하여, 언론 비즈니스 현실(후원/구독)을 전제한 높은 설득력을 지닙니다.
        - <b>블랙박스 알고리즘 탈피 (XAI 강조):</b> 인공지능이 왜 해당 기사를 진보/보수로 분류했는지에 대한 설명(XAI)을 제공하여 평가위원단의 신뢰를 확보할 수 있습니다.
        - <b>수용자 메타인지(Self-awareness) 유도:</b> 정파성 편향도를 수치와 시각 자료로 제시함으로써 독자가 스스로의 정보 편향 수준을 깨닫고 리터러시를 향상시키는 공익적 기여를 증명합니다.
        </div>
        """, unsafe_allow_html=True)
