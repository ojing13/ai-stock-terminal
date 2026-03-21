import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from google import genai
from datetime import datetime, timedelta
import requests
import FinanceDataReader as fdr
import xml.etree.ElementTree as ET
import pandas as pd
from bs4 import BeautifulSoup
import math
import re
import urllib.parse
import copy
import pytz
import hashlib


def md_to_html(text):
    """마크다운 → HTML 변환"""
    # XSS 방어: script 태그 제거
    text = re.sub(r'<script[\s\S]*?</script>', '', text, flags=re.IGNORECASE)
    # **텍스트** → <strong> 변환
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # * 단독 제거
    text = re.sub(r'(?<![\w\d])\*(?![\*])', '', text)
    # 숫자-단위 사이 하이픈 보호 (예: 5-일 → 5일, 13-주 → 13주, 9-월 → 9월)
    text = re.sub(r'(\d+)-(일|주|월|년|개월)', r'\1\2', text)

    lines = text.split('\n')
    html_parts = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        # 헤딩
        if line.startswith('#### '):
            html_parts.append(f'<p style="font-size:16px;font-weight:800;color:#111827;margin:20px 0 4px 0;padding:0;border:none;">{line[5:].strip()}</p>')
        elif line.startswith('### '):
            html_parts.append(f'<h3 style="font-size:19px;font-weight:800;color:#111827;margin:24px 0 8px;padding-bottom:6px;border-bottom:1px solid #d1d5db;">{line[4:].strip()}</h3>')
        elif line.startswith('## '):
            html_parts.append(f'<h2 style="font-size:20px;font-weight:800;color:#111827;margin:26px 0 8px;padding-bottom:6px;border-bottom:1px solid #d1d5db;">{line[3:].strip()}</h2>')
        elif line.startswith('# '):
            html_parts.append(f'<h2 style="font-size:20px;font-weight:800;color:#111827;margin:26px 0 8px;padding-bottom:6px;border-bottom:1px solid #d1d5db;">{line[2:].strip()}</h2>')
        # 빈 줄 → 단락 간격
        elif line.strip() == '':
            html_parts.append('<div style="height:10px;"></div>')
        # 일반 텍스트
        else:
            html_parts.append(f'<p style="margin:0 0 10px 0;line-height:1.85;color:#374151;font-size:16px;">{line}</p>')
        i += 1
    return '\n'.join(html_parts)

# 전체 화면 넓게 쓰기 및 기본 설정
st.set_page_config(layout="wide", page_title="AI 주식 분석 터미널", menu_items={})

# 라이트 테마 기반 세련된 디자인 (탭4 투자의견 바 스타일에 맞춤)
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
  
    * { font-family: 'Pretendard', 'Noto Sans KR', sans-serif !important; }

    /* ===== 전체 배경 ===== */
    .stApp { background-color: #f0f2f5 !important; }
    .block-container {
        background-color: #f0f2f5 !important;
        padding-top: 3.5rem !important;
    }
    @media (max-width: 768px) {
        .block-container { padding-top: 2.8rem !important; }
        h1 { font-size: 1.35rem !important; word-break: keep-all; }
    }

    /* ===== 타이틀 ===== */
    h1 { font-weight: 800 !important; font-size: 2rem !important; color: #1a1a2e !important; letter-spacing: -0.5px; }
    h2, h3 { font-weight: 700 !important; color: #1a1a2e !important; letter-spacing: -0.3px; }

    /* ===== 구분선 ===== */
    hr { border-color: #e0e3e8 !important; margin: 1.5rem 0 !important; }

    /* ===== 탭 ===== */
    .stTabs [data-baseweb="tab-list"] { gap: 0px; border-bottom: 2px solid #e0e3e8; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        height: 48px; font-size: 15px; font-weight: 600; color: #9ca3af;
        background-color: transparent; border-bottom: 3px solid transparent !important;
        padding: 0 24px; transition: color 0.2s;
    }
    .stTabs [aria-selected="true"] {
        color: #1a1a2e !important; border-bottom: 3px solid #1a1a2e !important;
        box-shadow: none !important; background-color: transparent !important;
    }
    .stTabs [data-baseweb="tab"]:hover { color: #374151 !important; }
    /* 종합 리포트 탭 (4번째) 강조 */
    .stTabs [data-baseweb="tab-list"] button:nth-child(4) {
        color: #e8490f !important;
        background-color: #fff4f0 !important;
        border-radius: 8px 8px 0 0 !important;
        border: 1.5px solid #f5c4b2 !important;
        border-bottom: 3px solid transparent !important;
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(4)[aria-selected="true"] {
        color: #e8490f !important;
        background-color: #fff4f0 !important;
        border: 1.5px solid #f5c4b2 !important;
        border-bottom: 3px solid #e8490f !important;
    }
    .stTabs [data-baseweb="tab-list"] button:nth-child(4):hover {
        color: #c73d0a !important;
        background-color: #ffe8df !important;
    }

    /* ===== 버튼 ===== */
    .stButton > button {
        border-radius: 8px; font-weight: 700; font-size: 14px;
        border: 1.5px solid #dde1e7; background-color: #ffffff; color: #1a1a2e;
        width: 100%; padding: 10px 16px; transition: all 0.2s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .stButton > button:hover {
        border-color: #3b82f6; color: #3b82f6; background-color: #f0f6ff;
        box-shadow: 0 2px 8px rgba(59,130,246,0.15);
    }
    .stButton > button:active { transform: scale(0.98); }

    /* ===== 텍스트 입력창 ===== */
    .stTextInput div[data-baseweb="input"] {
        background-color: #ffffff !important; border-radius: 10px !important;
        border: 1.5px solid #dde1e7 !important; box-shadow: 0 1px 4px rgba(0,0,0,0.07) !important;
        height: 48px !important;
    }
    .stTextInput div[data-baseweb="input"]:focus-within {
        border-color: #3b82f6 !important; box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important;
    }
    .stTextInput input { color: #1a1a2e !important; font-weight: 500 !important; font-size: 15px !important; }
    .stTextInput label { font-size: 13px !important; font-weight: 600 !important; color: #6b7280 !important; }

    /* ===== Selectbox ===== */
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important; border-radius: 8px !important;
        border: 1.5px solid #dde1e7 !important; box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
    }
    div[data-baseweb="select"] > div:hover, div[data-baseweb="select"] > div:focus-within {
        border-color: #3b82f6 !important; box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important;
    }
    div[data-baseweb="select"] input { caret-color: transparent !important; user-select: none !important; }

    /* ===== 슬라이더 ===== */
    div[data-testid="stSlider"] div[role="slider"] {
        background-color: #ef4444 !important; border-color: #ef4444 !important;
        box-shadow: 0 0 0 3px rgba(239,68,68,0.2) !important;
    }
    div[data-testid="stSlider"] div[style*="background-color: rgb(255, 75, 75)"],
    div[data-testid="stSlider"] div[style*="background-color: #ff4b4b"] { background-color: #ef4444 !important; }
    [data-testid="stTickBarMin"], [data-testid="stTickBarMax"], [data-testid="stThumbValue"] {
        color: #ef4444 !important; font-weight: 700 !important;
    }

    /* ===== Metric 카드 ===== */
    div[data-testid="metric-container"] {
        background-color: #ffffff; border: 1px solid #e8ebf0; border-radius: 10px;
        padding: 14px 16px !important; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 10px;
    }
    div[data-testid="stMetricLabel"] {
        color: #6b7280 !important; font-size: 12px !important; font-weight: 600 !important;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    div[data-testid="stMetricValue"] {
        white-space: normal !important; word-break: break-all !important;
        font-size: 1.3rem !important; line-height: 1.2 !important;
        font-weight: 800 !important; color: #1a1a2e !important;
    }

    /* ===== 재무제표 표 ===== */
    .fin-table {
        width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px;
        table-layout: fixed; background-color: #ffffff; border-radius: 10px;
        overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .fin-table th {
        text-align: left; border-bottom: 2px solid #e8ebf0; padding: 10px 12px;
        color: #6b7280; font-size: 12px; text-transform: uppercase;
        letter-spacing: 0.5px; background-color: #f8f9fc;
    }
    .fin-table td { border-bottom: 1px solid #f0f2f5; padding: 9px 12px; text-align: right; vertical-align: middle; color: #374151; }
    .fin-table td:first-child { text-align: left; font-weight: 600; color: #1a1a2e; width: 45%; }
    .fin-table tr:last-child td { border-bottom: none; }
    .fin-table tr:hover td { background-color: #f8f9fc; }

    /* ===== AI 분석 결과 카드 ===== */
    .ai-result-card {
        background-color: #e8eaed;
        border-radius: 14px;
        padding: 28px 32px;
        margin-top: 8px;
    }
    .ai-result-card p,
    .ai-result-card li {
        color: #374151;
        line-height: 1.9;
        font-size: 14.5px;
    }
    .ai-result-card h1,
    .ai-result-card h2,
    .ai-result-card h3 {
        color: #111827;
        font-weight: 800;
        font-size: 15.5px;
        margin-top: 28px;
        margin-bottom: 10px;
        padding-bottom: 8px;
        border-bottom: 1px solid #d1d5db;
        letter-spacing: -0.2px;
    }
    .ai-result-card strong {
        color: #111827;
        font-weight: 700;
    }
    /* stAlert 완전 숨기기 (혹시 남아있을 경우 대비) */
    div[data-testid="stAlert"] {
        display: none !important;
    }

    /* ===== 섹션 헤더 ===== */
    .section-header {
        font-size: 15px; font-weight: 800; color: #1a1a2e;
        margin-bottom: 16px; padding-bottom: 10px; border-bottom: 2px solid #e8ebf0;
        display: flex; align-items: center; gap: 8px;
    }
    .section-badge {
        display: inline-block; background-color: #1a1a2e; color: white;
        font-size: 10px; font-weight: 700; padding: 2px 9px;
        border-radius: 20px; letter-spacing: 0.8px;
    }

    /* ===== 종목명 가격 헤더 ===== */
    .price-header {
        background-color: #ffffff; border: 1px solid #e8ebf0; border-radius: 12px;
        padding: 18px 24px; margin-bottom: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
    }
    .price-ticker {
        font-size: 12px; font-weight: 600; color: #6b7280;
        background-color: #f0f2f5; padding: 3px 10px; border-radius: 6px;
    }
    .price-name { font-size: 20px; font-weight: 800; color: #1a1a2e; }
    .price-value { font-size: 22px; font-weight: 800; color: #ef4444; margin-left: auto; }

    /* ===== 뉴스 링크 ===== */
    a { color: #3b82f6 !important; text-decoration: none !important; }
    a:hover { text-decoration: underline !important; }

    /* ===== 타이틀 클릭을 위한 전용 클래스 (기본 디자인 유지) ===== */
    .title-link { color: #1a1a2e !important; text-decoration: none !important; }
    .title-link:hover { text-decoration: none !important; color: #1a1a2e !important; cursor: pointer; }

    /* ===== 상단 흰색 헤더 바 완전 제거 ===== */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    /* 헤더 제거 후 생기는 상단 여백 보정 */
    .block-container {
        padding-top: 2.5rem !important;
    }
    @media (max-width: 768px) {
        .block-container { padding-top: 2rem !important; }
    }

    /* ===== 불필요한 UI 숨기기 ===== */
    .stDeployButton { display: none !important; }
    [data-testid="stStatusWidget"] * { display: none !important; }
    [data-testid="stStatusWidget"]::after {
        content: "분석 중..."; font-size: 13px; font-weight: 600; color: #6b7280;
        display: flex; align-items: center; padding: 5px 15px;
    }

    /* ===== 모바일 우하단 Streamlit 툴바 완전 숨기기 ===== */
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stMainMenu"] { display: none !important; }
    .stActionButton { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    [class*="toolbar"] { display: none !important; }
    [class*="Toolbar"] { display: none !important; }
    div[class*="viewerBadge"] { display: none !important; }
    #stDecoration { display: none !important; }

    /* ===== 재무 섹션 제목 ===== */
    .fin-section-title {
        font-size: 13px; font-weight: 700; color: #374151;
        margin-bottom: 8px; padding: 7px 12px; background-color: #f8f9fc;
        border-radius: 7px; border-left: 3px solid #1a1a2e; letter-spacing: 0.2px;
    }

</style>
""", unsafe_allow_html=True)

try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("API 키를 찾을 수 없습니다. Streamlit Cloud의 Settings -> Secrets에 'GEMINI_API_KEY'를 등록해주세요.")
    st.stop()
    
client = genai.Client(api_key=MY_API_KEY)

@st.cache_data(ttl=3600)
def load_krx_data():
    try:
        return fdr.StockListing('KRX')
    except Exception:
        try:
            kospi = fdr.StockListing('KOSPI')
            kosdaq = fdr.StockListing('KOSDAQ')
            return pd.concat([kospi, kosdaq], ignore_index=True)
        except Exception:
            return pd.DataFrame(columns=['Code', 'Name', 'Market'])

krx_df = load_krx_data()

@st.cache_data(ttl=3600*24)
def get_korean_display_name(ticker, english_name):
    try:
        clean_ticker = ticker.split('.')[0]
        ac_url = f"https://ac.finance.naver.com/ac?q={clean_ticker}&q_enc=utf-8&st=111&r_format=json&r_enc=utf-8"
        headers = {'User-Agent': 'Mozilla/5.0'}
        ac_res = requests.get(ac_url, headers=headers, timeout=3)
        ac_data = ac_res.json()

        if ac_data.get('items') and len(ac_data['items']) > 0 and len(ac_data['items'][0]) > 0:
            for item in ac_data['items'][0]:
                if item[0].upper() == clean_ticker.upper():
                    korean_name = item[1]
                    if korean_name and korean_name.upper() != clean_ticker.upper():
                        return korean_name
            first_name = ac_data['items'][0][0][1]
            if first_name and first_name.upper() != clean_ticker.upper():
                return first_name
    except:
        pass
    return english_name

def get_ticker_symbol(search_term):
    """외부 진입점. strip() 정규화 후 캐시된 내부 함수로 위임."""
    return _get_ticker_symbol_cached(search_term.strip())

@st.cache_data(ttl=3600)
def _get_ticker_symbol_cached(search_term):
    search_clean = search_term.replace(" ", "").upper()
    
    custom_mapping = {
        "TSMC": "TSM",
        "티에스엠씨": "TSM",
        "APPLE": "AAPL",
        "애플": "AAPL",
        "NVIDIA": "NVDA",
        "엔비디아": "NVDA",
        "TESLA": "TSLA",
        "테슬라": "TSLA",
        "MICROSOFT": "MSFT",
        "마이크로소프트": "MSFT",
        "마소": "MSFT",
        "GOOGLE": "GOOGL",
        "구글": "GOOGL",
        "ALPHABET": "GOOGL",
        "AMAZON": "AMZN",
        "아마존": "AMZN",
        "META": "META",
        "메타": "META",
        "NETFLIX": "NFLX",
        "넷플릭스": "NFLX",
        "AMD": "AMD",
        "INTEL": "INTC",
        "인텔": "INTC",
        "SCHD": "SCHD",
        "큐큐큐": "QQQ",
        "QQQ": "QQQ",
        "스파이": "SPY",
        "SPY": "SPY",
        "디어유": "376300.KQ",
        "비트마인": "BMNR",
        "BITMAIN": "BMNR",
        "BMNR": "BMNR",
        "써클": "CRCL",
        "서클": "CRCL",
        "CIRCLE": "CRCL",
        "CRCL": "CRCL",
        "리게티": "RGTI",
        "RIGETTI": "RGTI",
        "RGTI": "RGTI",
        "버크셔": "BRK-B",
        "버크셔해서웨이": "BRK-B",
        "BERKSHIRE": "BRK-B",
        "BERKSHIREHATHAWAY": "BRK-B",
        "BRK-B": "BRK-B",
        "BRKB": "BRK-B",
        "BRK-A": "BRK-A",
        "BRKA": "BRK-A",
        "팔란티어": "PLTR",
        "PALANTIR": "PLTR",
        "PLTR": "PLTR",
    }
    
    if search_clean in custom_mapping:
        return custom_mapping[search_clean]

    if not krx_df.empty:
        df_temp = krx_df.copy()
        df_temp['Name_clean'] = df_temp['Name'].astype(str).str.replace(" ", "").str.upper()
        # 완전일치
        match = df_temp[df_temp['Name_clean'] == search_clean]
        if not match.empty:
            code = match.iloc[0]['Code']
            market = match.iloc[0]['Market']
            if market == 'KOSPI': return f"{code}.KS"
            else: return f"{code}.KQ"
        # 부분일치 (검색어가 종목명에 포함)
        partial = df_temp[df_temp['Name_clean'].str.contains(search_clean, na=False)]
        if not partial.empty:
            code = partial.iloc[0]['Code']
            market = partial.iloc[0]['Market']
            if market == 'KOSPI': return f"{code}.KS"
            else: return f"{code}.KQ"
        # 역방향 부분일치 (종목명이 검색어에 포함)
        partial2 = df_temp[df_temp['Name_clean'].apply(lambda n: n in search_clean and len(n) >= 3)]
        if not partial2.empty:
            code = partial2.iloc[0]['Code']
            market = partial2.iloc[0]['Market']
            if market == 'KOSPI': return f"{code}.KS"
            else: return f"{code}.KQ"
            
    try:
        encoded_term = urllib.parse.quote(search_term)
        ac_url = f"https://ac.finance.naver.com/ac?q={encoded_term}&q_enc=utf-8&st=111&r_format=json&r_enc=utf-8"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer': 'https://finance.naver.com/'
        }
        ac_res = requests.get(ac_url, headers=headers, timeout=5)
        ac_data = ac_res.json()
        
        if ac_data.get('items') and len(ac_data['items']) > 0 and len(ac_data['items'][0]) > 0:
            item = ac_data['items'][0][0]
            code = item[0]
            market_str = item[2] if len(item) > 2 else ""
            if '코스피' in market_str:
                return f"{code}.KS"
            elif '코스닥' in market_str:
                return f"{code}.KQ"
            elif any(x in market_str for x in ['나스닥', 'NASDAQ', 'NYSE', '뉴욕', 'NMS', 'NYQ']):
                return code
    except:
        pass
            
    try:
        encoded_term_euc = urllib.parse.quote(search_term.encode('euc-kr'))
        html_url = f"https://finance.naver.com/search/searchList.naver?query={encoded_term_euc}"
        html_res = requests.get(html_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        soup = BeautifulSoup(html_res.text, 'html.parser')
        a_tag = soup.select_one('td.tit a')
        if a_tag and 'code=' in a_tag['href']:
            code = a_tag['href'].split('code=')[1]
            tr = a_tag.find_parent('tr')
            tds = tr.find_all('td')
            if len(tds) > 2:
                market_str = tds[2].text.strip()
                if '코스피' in market_str: return f"{code}.KS"
                elif '코스닥' in market_str: return f"{code}.KQ"
                else: return code
    except:
        pass

    # ====================== [버그 수정] Yahoo Finance Search API ======================
    # 수정 1: quote.get('type') → quote.get('quoteType')
    #         Yahoo Finance API 실제 응답 키 이름은 'quoteType'이지 'type'이 아님.
    #         기존 코드는 항상 None을 반환해 1st/2nd 루프가 동작하지 않았음.
    # 수정 2: exchange 코드 확장
    #         NGM(Nasdaq Global Market), NCM(Nasdaq Capital Market), PCX(NYSE Arca) 등 누락된 코드 추가.
    # 수정 3: exchDisp 보조 판별 추가
    #         exchange 값이 예상 밖이어도 exchDisp='NASDAQ'/'NYSE' 등으로 미국 거래소 판별 가능.
    # 수정 4: isYahooFinance 우선 선택
    #         정식 Yahoo Finance 등록 종목을 커뮤니티 데이터보다 우선 반환.
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(search_term)}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        data = res.json()
        if 'quotes' in data and len(data['quotes']) > 0:
            # 미국 거래소 exchange 코드 (확장)
            us_exchanges = {
                'NYQ',   # NYSE
                'NMS',   # Nasdaq Global Select Market
                'NGM',   # Nasdaq Global Market (기존 누락)
                'NCM',   # Nasdaq Capital Market (기존 누락)
                'PCX',   # NYSE Arca (ETF 주요 상장, 기존 누락)
                'ASE',   # NYSE American (구 AMEX, 기존 누락)
                'NYSE',
                'NASDAQ',
                'NAS',
                'BATS',  # CBOE/BATS Exchange
                'BTS',
            }
            # exchDisp 기반 보조 판별 (exchange 코드가 예상 밖일 때 대비)
            us_disps = {'NASDAQ', 'NYSE', 'NYSE ARCA', 'NYSE MKT', 'NYSE AMERICAN', 'BATS'}
            # 유효한 quoteType
            equity_types = {'EQUITY', 'ETF', 'MUTUALFUND'}

            def _is_us_quote(q):
                """미국 거래소 상장 주식/ETF 여부 판별"""
                qt = q.get('quoteType', '').upper()
                ex = q.get('exchange', '').upper()
                exd = q.get('exchDisp', '').upper()
                return qt in equity_types and (ex in us_exchanges or exd in us_disps)

            # 1순위: quoteType 정확 + 미국 거래소 + isYahooFinance
            for quote in data['quotes']:
                if _is_us_quote(quote) and quote.get('isYahooFinance'):
                    return quote['symbol']
            # 2순위: quoteType 정확 + 미국 거래소
            for quote in data['quotes']:
                if _is_us_quote(quote):
                    return quote['symbol']
            # 3순위: quoteType만 (비미국 거래소 포함) + isYahooFinance
            for quote in data['quotes']:
                qt = quote.get('quoteType', '').upper()
                if qt in equity_types and quote.get('isYahooFinance'):
                    return quote['symbol']
            # 4순위: quoteType만
            for quote in data['quotes']:
                qt = quote.get('quoteType', '').upper()
                if qt in equity_types:
                    return quote['symbol']
            # 최후 fallback
            return data['quotes'][0]['symbol']
    except:
        pass
        
    try:
        ticker_prompt = f"""당신은 금융 데이터 전문가입니다. 사용자의 검색어('{search_term}')를 바탕으로 정확한 야후 파이낸스 주식 티커 딱 1개만 출력하세요.
        [엄격한 규칙]
        1. 미국 주식: 영문 티커 (예: AAPL, HIMS, TSLA)
        2. 한국 주식: 6자리숫자.KS 또는 6자리숫자.KQ (예: 005930.KS)
        3. 확신할 수 없다면 절대 임의의 숫자를 지어내지 마세요.
        4. 사고 과정 추가 설명 없이 오직 '티커 기호' 하나만 출력하세요."""
        trans_response = client.models.generate_content(model='gemini-2.5-flash', contents=ticker_prompt)
        eng_ticker = trans_response.text.strip().upper()
        
        lines = [line.strip() for line in eng_ticker.split('\n') if line.strip() and not line.startswith('THOUGHT')]
        if lines:
            match = re.search(r'[A-Z0-9]+\.[A-Z]+|[A-Z0-9]+', lines[-1])
            if match:
                return match.group(0)
    except:
        pass
       
    return search_term.upper()

def safe_get_fin(df, keys, default='N/A'):
    if df is None or df.empty: return default
    for k in keys:
        if k in df.index:
            val = df.loc[k].iloc[0]
            if pd.notna(val):
                return f"{val:,.0f}"
    return default

def format_large_number(num, currency):
    return f"{num:,.0f} {currency}"

def get_52w_high_low(stock, info_high, info_low):
    try: high = float(info_high) if info_high else 0
    except: high = 0
    try: low = float(info_low) if info_low else 0
    except: low = 0
    
    if low <= 0 or high <= 0:
        try:
            hist = stock.history(period="1y")
            hist = hist[hist['Low'] > 0] 
            if not hist.empty:
                high = hist['High'].max()
                low = hist['Low'].min()
        except:
            pass
    return high, low

def safe_info(info, keys, default='N/A'):
    for k in keys:
        v = info.get(k)
        if v is not None and v != '' and v != 0 and str(v).upper() != 'N/A':
            return v
    return default

@st.cache_data(ttl=600)
def _fetch_korean_augment(ticker):
    """네이버 크롤링 결과를 ticker 키로 캐시. 업데이트할 키-값 dict 반환."""
    result = {}
    try:
        code = ticker.split('.')[0]
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')

        def get_val_by_id(eid):
            el = soup.find(id=eid)
            if el:
                try: return float(el.text.replace(',', '').replace('%', '').strip())
                except: return None
            return None

        per = get_val_by_id('_per')
        pbr = get_val_by_id('_pbr')
        div = get_val_by_id('_dvr')

        if per is not None: result['trailingPE'] = per
        if pbr is not None: result['priceToBook'] = pbr
        if div is not None:
            result['dividendYield'] = div / 100.0
            result['naver_div_yield'] = div / 100.0

        table = soup.find('table', {'class': 'tb_type1 tb_num tb_type1_ifrs'})
        if table:
            tbody = table.find('tbody')
            if tbody:
                for row in tbody.find_all('tr'):
                    th = row.find('th')
                    if not th: continue
                    title = th.text.strip()
                    valid_vals = []
                    for td in row.find_all('td'):
                        txt = td.text.strip().replace(',', '')
                        try: valid_vals.append(float(txt))
                        except: pass
                    if not valid_vals: continue
                    recent_val = valid_vals[-1]
                    if 'ROE' in title:           result['returnOnEquity']   = recent_val / 100.0
                    elif '영업이익률' in title:   result['operatingMargins'] = recent_val / 100.0
                    elif '순이익률' in title:     result['profitMargins']    = recent_val / 100.0
                    elif '부채비율' in title:     result['debtToEquity']     = recent_val
                    elif '당좌비율' in title:     result['quickRatio']       = recent_val / 100.0
                    elif '유동비율' in title:     result['currentRatio']     = recent_val / 100.0
    except:
        pass
    return result

def augment_korean_fundamentals(ticker, info):
    if not (ticker.endswith('.KS') or ticker.endswith('.KQ')):
        return info
    info.update(_fetch_korean_augment(ticker))
    return info

@st.cache_data(ttl=600)
def _fetch_us_augment(ticker):
    """Finviz 크롤링 결과를 ticker 키로 캐시. 업데이트할 키-값 dict 반환."""
    result = {}
    try:
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'text/html',
            'Upgrade-Insecure-Requests': '1'
        }
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')

        table = soup.find('table', class_='snapshot-table2')
        if table:
            data_dict = {}
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                for i in range(0, len(cols), 2):
                    data_dict[cols[i].text.strip()] = cols[i+1].text.strip()

            def parse_finviz_val(val_str, is_pct=False):
                if val_str == '-' or val_str == '': return None
                val_str = val_str.replace(',', '').replace('%', '')
                try:
                    num = float(val_str)
                    return num / 100.0 if is_pct else num
                except:
                    return None

            if (v := parse_finviz_val(data_dict.get('P/E', '-'))) is not None:             result['trailingPE'] = v
            if (v := parse_finviz_val(data_dict.get('Forward P/E', '-'))) is not None:     result['forwardPE'] = v
            if (v := parse_finviz_val(data_dict.get('P/B', '-'))) is not None:             result['priceToBook'] = v
            if (v := parse_finviz_val(data_dict.get('P/S', '-'))) is not None:             result['priceToSalesTrailing12Months'] = v
            if (v := parse_finviz_val(data_dict.get('PEG', '-'))) is not None:             result['pegRatio'] = v
            if (v := parse_finviz_val(data_dict.get('ROE', '-'), True)) is not None:       result['returnOnEquity'] = v
            if (v := parse_finviz_val(data_dict.get('ROA', '-'), True)) is not None:       result['returnOnAssets'] = v
            if (v := parse_finviz_val(data_dict.get('ROI', '-'), True)) is not None:       result['returnOnCapitalEmployed'] = v
            if (v := parse_finviz_val(data_dict.get('Gross Margin', '-'), True)) is not None:  result['grossMargins'] = v
            if (v := parse_finviz_val(data_dict.get('Oper. Margin', '-'), True)) is not None:  result['operatingMargins'] = v
            if (v := parse_finviz_val(data_dict.get('Profit Margin', '-'), True)) is not None: result['profitMargins'] = v
            if (v := parse_finviz_val(data_dict.get('Dividend %', '-'), True)) is not None:
                result['dividendYield'] = v
                result['finviz_div_yield'] = v
            if (v_debt := parse_finviz_val(data_dict.get('Debt/Eq', '-'))) is not None:   result['debtToEquity'] = v_debt * 100
            if (v := parse_finviz_val(data_dict.get('Current Ratio', '-'))) is not None:  result['currentRatio'] = v
            if (v := parse_finviz_val(data_dict.get('Quick Ratio', '-'))) is not None:    result['quickRatio'] = v
    except:
        pass
    return result

def augment_us_fundamentals(ticker, info):
    if ticker.endswith('.KS') or ticker.endswith('.KQ'):
        return info
    info.update(_fetch_us_augment(ticker))
    return info

def get_article_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=2, allow_redirects=True)
        soup = BeautifulSoup(res.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text().strip() for p in paragraphs if p.get_text()])
        return text[:800] if text else ""
    except:
        return ""

@st.cache_data(ttl=600)
def fetch_yf_data(ticker):
    stock = yf.Ticker(ticker)
    try: hist_basic = stock.history(period="5d")   # '1d'는 주말·공휴일 후 빈 DataFrame 가능 → '5d'로 안전 확보
    except: hist_basic = pd.DataFrame()
    try: info = stock.info
    except: info = {}
    try: fin_df = stock.financials
    except: fin_df = pd.DataFrame()
    try: bs_df = stock.balance_sheet
    except: bs_df = pd.DataFrame()
    try: cf_df = stock.cashflow
    except: cf_df = pd.DataFrame()
    try: div_series = stock.dividends
    except: div_series = pd.Series()
    return hist_basic, info, fin_df, bs_df, cf_df, div_series

@st.cache_data(ttl=600)
def fetch_chart_history(ticker, interval):
    try:
        return yf.Ticker(ticker).history(period="max", interval=interval)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def fetch_news_data(ticker, official_name, search_korean_news):
    news_list = []
    try:
        if search_korean_news:
            rss_url = f"https://news.google.com/rss/search?q={official_name}+주식&hl=ko-KR&gl=KR&ceid=KR:ko"
        else:
            rss_url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
        response = requests.get(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        root = ET.fromstring(response.content)
        for item in root.findall('.//item')[:100]:
            title = item.find('title').text if item.find('title') is not None else "No title"
            link = item.find('link').text if item.find('link') is not None else "#"
            desc = item.find('description').text if item.find('description') is not None else ""
            content = BeautifulSoup(desc, "html.parser").get_text() if desc else get_article_text(link)
            news_list.append({"title": title, "link": link, "content": content[:800].replace('\n', ' ')})
    except: pass
      
    if not news_list:
        try:
            stock = yf.Ticker(ticker)
            raw_news = stock.news
            for n in raw_news[:100]:
                if isinstance(n, dict) and 'title' in n:
                    _link = n.get('link') or n.get('url', '#')
                    content = n.get('summary', '') or get_article_text(_link)
                    news_list.append({"title": n['title'], "link": _link, "content": content[:800].replace('\n', ' ')})
        except: pass
    return news_list

# ====================== 메인 ======================
st.markdown("""
<div style="margin-bottom: 6px;">
    <span style="font-size: 10px; font-weight: 700; letter-spacing: 2.5px; color: #9ca3af; text-transform: uppercase; background:#eef0f4; padding:3px 10px; border-radius:20px;">AI Stock Analysis Terminal</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="font-size: 1.75rem; font-weight: 900; letter-spacing: -0.8px; line-height: 1.2; margin-bottom: 6px;">
    <a href="?" target="_self" class="title-link">웅이의 AI 주식 분석 터미널</a>
</div>
<div style="color: #9ca3af; font-size: 13.5px; font-weight: 400; margin-bottom: 22px; letter-spacing: 0.1px;">
    
</div>
""", unsafe_allow_html=True)

col_search, _ = st.columns([1, 2])
with col_search:
    user_input = st.text_input("분석할 종목명 또는 티커", placeholder="예: 삼성전자, AAPL, NVDA", key="main_search_input")

if user_input:
    ticker = get_ticker_symbol(user_input)
    stock = yf.Ticker(ticker)
    
    hist_basic, cached_info, fin_df, bs_df, cf_df, div_series = fetch_yf_data(ticker)
    info = copy.deepcopy(cached_info) if isinstance(cached_info, dict) else {}
  
    if not hist_basic.empty:
        current_price = hist_basic['Close'].iloc[-1]
        display_name = user_input

        if ticker.endswith('.KS') or ticker.endswith('.KQ'):
            code_only = ticker.split('.')[0]
            name_found = False
            if not krx_df.empty:
                match_name = krx_df[krx_df['Code'] == code_only]
                if not match_name.empty:
                    display_name = match_name.iloc[0]['Name']
                    name_found = True

            if not name_found:
                try:
                    basic_url = f"https://m.stock.naver.com/api/stock/{code_only}/basic"
                    basic_res = requests.get(basic_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
                    if basic_res.status_code == 200:
                        fetched_name = basic_res.json().get('stockName')
                        if fetched_name:
                            display_name = fetched_name
                            name_found = True
                except: pass
                
                if not name_found and info and 'shortName' in info:
                    display_name = info['shortName']

        else:
            yf_official_name = None
            try:
                _yf_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(ticker)}&quotesCount=1&newsCount=0"
                _yf_res = requests.get(_yf_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=4)
                _yf_data = _yf_res.json()
                for _q in _yf_data.get('quotes', []):
                    if _q.get('symbol', '').upper() == ticker.upper():
                        _name = _q.get('longname') or _q.get('shortname') or ''
                        if _name and _name.upper() != ticker.upper():
                            yf_official_name = _name
                            break
            except:
                pass

            if yf_official_name:
                english_name = yf_official_name
            else:
                _ln = info.get('longName', '')
                _sn = info.get('shortName', '')
                if _ln and _ln.upper() != ticker.upper():
                    english_name = _ln
                elif _sn and _sn.upper() != ticker.upper():
                    english_name = _sn
                else:
                    english_name = ticker

            display_name = get_korean_display_name(ticker, english_name)
        
        info = augment_korean_fundamentals(ticker, info)
        info = augment_us_fundamentals(ticker, info) 
        
        today_date = datetime.now(pytz.timezone('Asia/Seoul')).strftime("%Y년 %m월 %d일")
        
        is_korean_stock = ticker.endswith('.KS') or ticker.endswith('.KQ')
        is_japanese_stock = ticker.endswith('.T')

        # _quote_type: 탭2 프롬프트와 탭4 종목 유형 판별에서 공통 사용 → 탭 생성 전에 미리 정의
        _quote_type = info.get('quoteType', '').upper()
        
        if is_korean_stock: currency, price_fmt = "원", ",.0f"
        elif is_japanese_stock: currency, price_fmt = "엔", ",.0f"
        else: currency, price_fmt = "달러", ",.2f"
        
        search_korean_news = is_korean_stock or is_japanese_stock
        news_list = fetch_news_data(ticker, display_name, search_korean_news)
                
        news_context_list = []
        for idx, item in enumerate(news_list[:25]):  # 최대 25개로 제한 (100개 전부 넘기면 토큰 낭비)
            news_context_list.append(f"[{idx+1}] 제목: {item['title']}\n본문: {item.get('content', '본문 없음')}")
        news_context = "\n\n".join(news_context_list) if news_context_list else "수집된 실시간 데이터가 없습니다."
        
        def fmt_pct(v):
            if v == 'N/A' or v is None: return 'N/A'
            try: return f"{float(v)*100:.2f}%"
            except: return 'N/A'
            
        def fmt_flt(v, is_per=False):
            if v is None or pd.isna(v) or str(v).strip() == '' or str(v).upper() == 'N/A': return 'N/A'
            try: 
                f = float(v)
                if math.isnan(f) or math.isinf(f): return 'N/A'
                if is_per and f > 1000: return 'N/A'
                return f"{f:,.2f}"
            except: return 'N/A'
            
        market_cap = info.get('marketCap', 0)
        high_52 = info.get('fiftyTwoWeekHigh')
        low_52 = info.get('fiftyTwoWeekLow')
        high_52, low_52 = get_52w_high_low(stock, high_52, low_52)
        
        trailing_pe = safe_info(info, ['trailingPE', 'trailingPe', 'PE'])
        forward_pe = safe_info(info, ['forwardPE', 'forwardPe'])
        pb = safe_info(info, ['priceToBook', 'pbr', 'priceBook'])
        psr = safe_info(info, ['priceToSalesTrailing12Months', 'priceToSales', 'psr'])
        peg = safe_info(info, ['pegRatio', 'peg'])
        ev_ebitda = safe_info(info, ['enterpriseToEbitda', 'evToEbitda'])
        
        roe = safe_info(info, ['returnOnEquity', 'roe'])
        roa = safe_info(info, ['returnOnAssets', 'roa'])
        roic = safe_info(info, ['returnOnCapitalEmployed', 'roic'])

        if roic == 'N/A' or roic is None:
            try:
                op_inc = None
                if not fin_df.empty:
                    if 'Operating Income' in fin_df.index: op_inc = fin_df.loc['Operating Income'].iloc[0]
                    elif 'EBIT' in fin_df.index: op_inc = fin_df.loc['EBIT'].iloc[0]
                
                tot_assets = None
                cur_liab = 0
                if not bs_df.empty:
                    if 'Total Assets' in bs_df.index: tot_assets = bs_df.loc['Total Assets'].iloc[0]
                    if 'Current Liabilities' in bs_df.index: cur_liab = bs_df.loc['Current Liabilities'].iloc[0]
                
                if pd.notna(op_inc) and pd.notna(tot_assets) and float(tot_assets) > 0:
                    nopat = float(op_inc) * 0.75
                    invested_capital = float(tot_assets) - float(cur_liab if pd.notna(cur_liab) else 0)
                    if invested_capital > 0: roic = nopat / invested_capital
            except: pass

        gross_margin = safe_info(info, ['grossMargins', 'grossMargin'])
        net_margin = safe_info(info, ['profitMargins', 'netMargin'])
        op_margin = safe_info(info, ['operatingMargins', 'operatingMargin'])
        rev_growth = safe_info(info, ['revenueGrowth'])
        
        def get_robust_dividend_yield(info_dict, div_data, current_p):
            for key in ['finviz_div_yield', 'naver_div_yield']:
                val = info_dict.get(key)
                if val is not None and str(val).strip() != '' and str(val).upper() != 'N/A':
                    try:
                        v = float(val)
                        if 0 < v < 0.50: return v
                    except: pass
                    
            try:
                if not div_data.empty and current_p > 0:
                    one_year_ago = div_data.index[-1] - pd.Timedelta(days=365)
                    recent_divs = div_data[div_data.index > one_year_ago]
                    if not recent_divs.empty:
                        history_yield = float(recent_divs.sum()) / float(current_p)
                        if 0 < history_yield < 0.50: 
                            return history_yield
            except: pass
                
            for key in ['dividendRate', 'trailingAnnualDividendRate']:
                r = info_dict.get(key)
                if r is not None and str(r).strip() != '' and str(r).upper() != 'N/A':
                    try:
                        r_val = float(r)
                        if r_val > 0 and current_p > 0:
                            rate_yield = r_val / float(current_p)
                            if 0 < rate_yield < 0.50: return rate_yield
                    except: pass
            
            for key in ['dividendYield', 'trailingAnnualDividendYield', 'yield']:
                y = info_dict.get(key)
                if y is not None and str(y).strip() != '' and str(y).upper() != 'N/A':
                    try:
                        y_val = float(y)
                        curr = info_dict.get('currency', 'USD')
                        f_curr = info_dict.get('financialCurrency', 'USD')
                        if curr != f_curr and y_val > 0.05: continue
                        
                        if 0 < y_val < 0.50:
                            if y_val > 0.15: 
                                assumed_yield = y_val / current_p
                                if 0 < assumed_yield < 0.15: return assumed_yield
                            return y_val
                    except: pass
            
            return 'N/A'

        div_yield = get_robust_dividend_yield(info, div_series, current_price)
        
        debt = safe_info(info, ['debtToEquity'])
        current_ratio = safe_info(info, ['currentRatio'])
        quick_ratio = safe_info(info, ['quickRatio'])
        
        try:
            op_inc_val = fin_df.loc['Operating Income'].iloc[0]
            int_exp_val = fin_df.loc['Interest Expense'].iloc[0]
            if pd.isna(op_inc_val) or pd.isna(int_exp_val) or int_exp_val == 0:
                interest_cov = 'N/A'
            else:
                # abs()는 분모(이자비용)에만 적용: yfinance가 음수/양수 둘 다 반환하므로 부호 통일
                # 분자(영업이익)는 부호 유지: 적자 기업은 이자보상배율이 음수로 표시되어야 함
                interest_cov = fmt_flt(op_inc_val / abs(int_exp_val))
        except:
            interest_cov = 'N/A'
        
        v_rev = safe_get_fin(fin_df, ['Total Revenue'])
        v_cogs = safe_get_fin(fin_df, ['Cost Of Revenue'])
        v_gp = safe_get_fin(fin_df, ['Gross Profit'])
        v_sga = safe_get_fin(fin_df, ['Selling General And Administration'])
        v_op = safe_get_fin(fin_df, ['Operating Income'])
        v_pretax = safe_get_fin(fin_df, ['Pretax Income'])
        v_net = safe_get_fin(fin_df, ['Net Income'])
        v_oci = safe_get_fin(fin_df, ['Other Comprehensive Income'])
        
        v_tot_assets = safe_get_fin(bs_df, ['Total Assets'])
        v_cur_assets = safe_get_fin(bs_df, ['Current Assets'])
        v_ncur_assets = safe_get_fin(bs_df, ['Total Non Current Assets'])
        v_tot_liab = safe_get_fin(bs_df, ['Total Liabilities Net Minority Interest', 'Total Liabilities'])
        v_cur_liab = safe_get_fin(bs_df, ['Current Liabilities'])
        v_ncur_liab = safe_get_fin(bs_df, ['Total Non Current Liabilities Net Minority Interest'])
        v_tot_eq = safe_get_fin(bs_df, ['Stockholders Equity', 'Total Equity Gross Minority Interest'])
        
        v_cash = safe_get_fin(bs_df, ['Cash And Cash Equivalents', 'Cash'])
        v_receiv = safe_get_fin(bs_df, ['Accounts Receivable', 'Net Receivables'])
        v_inv = safe_get_fin(bs_df, ['Inventory'])
        v_tangible = safe_get_fin(bs_df, ['Net PPE'])
        v_intangible = safe_get_fin(bs_df, ['Total Intangible Assets', 'Goodwill And Other Intangible Assets'])
        
        v_s_debt = safe_get_fin(bs_df, ['Current Debt', 'Current Debt And Capital Lease Obligation'])
        v_l_debt = safe_get_fin(bs_df, ['Long Term Debt', 'Long Term Debt And Capital Lease Obligation'])
        v_cap_stock = safe_get_fin(bs_df, ['Capital Stock', 'Common Stock'])
        v_cap_surplus = safe_get_fin(bs_df, ['Additional Paid In Capital'])
        v_retained = safe_get_fin(bs_df, ['Retained Earnings'])
        
        v_cf_op = safe_get_fin(cf_df, ['Operating Cash Flow'])
        v_cf_inv = safe_get_fin(cf_df, ['Investing Cash Flow'])
        v_cf_fin = safe_get_fin(cf_df, ['Financing Cash Flow'])
        v_cf_beg = safe_get_fin(cf_df, ['Beginning Cash Position'])
        v_cf_end = safe_get_fin(cf_df, ['End Cash Position'])
        v_dividend = safe_get_fin(cf_df, ['Cash Dividends Paid', 'Dividends Paid'])

        # ma_context_str: 슬라이더 선택과 무관하게 일봉 전체 데이터 최근값 기준으로 계산
        # (탭4 종합 리포트에서 사용 - 슬라이더가 짧은 기간이면 120일MA가 '데이터 부족'이 되는 문제 방지)
        try:
            _daily_full = fetch_chart_history(ticker, "1d")
            _daily_full = _daily_full[_daily_full['Close'] > 0].copy()
            for _w in [5, 20, 60, 120]:
                _daily_full[f'MA_{_w}'] = _daily_full['Close'].rolling(window=_w).mean()
            _last_row = _daily_full.iloc[-1]
            ma_context_str = " / ".join([
                f"MA{_w}일: {_last_row[f'MA_{_w}']:{price_fmt}} {currency}" if pd.notna(_last_row[f'MA_{_w}']) else f"MA{_w}일: 데이터 부족"
                for _w in [5, 20, 60, 120]
            ])
        except:
            ma_context_str = "차트 데이터 부족"

        tab1, tab2, tab3, tab4 = st.tabs(["차트 분석", "상세 재무", "최신 동향", "종합 리포트"])
        
        # --- [탭 1: 차트 분석] ---
        with tab1:
            st.markdown(f"""
            <div class="price-header">
                <span class="price-name">{display_name}</span>
                <span class="price-ticker">{ticker}</span>
                <span class="price-value">{current_price:{price_fmt}} {currency}</span>
            </div>
            """, unsafe_allow_html=True)

            col_interval_only = st.columns([3, 1])
            with col_interval_only[1]:
                interval_option = st.selectbox("차트 주기", ("일봉", "주봉", "월봉"), index=0)
            
            interval = "1d" if interval_option == "일봉" else "1wk" if interval_option == "주봉" else "1mo"
            
            history = fetch_chart_history(ticker, interval)
            
            if not history.empty:
                history = history[(history['Low'] > 0) & (history['High'] > 0) & (history['Close'] > 0)]
                
                raw_min_date = history.index.min().to_pydatetime().date()
                min_date = raw_min_date.replace(day=1) 
                max_date = datetime.now().date()       
                
                ideal_start_date = max_date - timedelta(days=365*10)
                default_start = ideal_start_date if ideal_start_date > min_date else min_date
                
                selected_start, selected_end = st.slider(
                    "조회 기간 설정",
                    min_value=min_date,
                    max_value=max_date,
                    value=(default_start, max_date),
                    format="YYYY-MM-DD",
                    label_visibility="collapsed",
                    key=f"slider_{ticker}" 
                )
                
                mask = (history.index.date >= selected_start) & (history.index.date <= selected_end)
                
                if interval_option == "일봉":
                    ma_settings = [(5, "MA1(5일)", "#00b0ff"), (20, "MA2(20일)", "#ff9100"), (60, "MA3(60일)", "#ff4081"), (120, "MA4(120일)", "#aa00ff")]
                elif interval_option == "주봉":
                    ma_settings = [(13, "MA1(13주)", "#00b0ff"), (26, "MA2(26주)", "#ff9100"), (52, "MA3(52주)", "#ff4081")]
                else:
                    ma_settings = [(9, "MA1(9개월)", "#00b0ff"), (24, "MA2(24개월)", "#ff9100"), (60, "MA3(60개월)", "#ff4081")]
                    
                for w, name, color in ma_settings:
                    history[f'MA_{w}'] = history['Close'].rolling(window=w).mean()

                filtered_history = history.loc[mask].copy()

                if not filtered_history.empty:
                    xaxis_config = dict(
                        rangeslider=dict(visible=False), 
                        type="date", 
                        hoverformat="%Y-%m-%d", 
                        fixedrange=True
                    )
                    
                    if interval_option == "일봉":
                        dt_all = pd.date_range(start=filtered_history.index.min(), end=filtered_history.index.max(), freq='D')
                        dt_obs = filtered_history.index.normalize()
                        dt_breaks = [d.strftime('%Y-%m-%d') for d in dt_all if d not in dt_obs]
                        xaxis_config['rangebreaks'] = [dict(values=dt_breaks)]

                    price_min = filtered_history['Low'].min()
                    price_max = filtered_history['High'].max()
                    min_idx = filtered_history['Low'].idxmin()
                    max_idx = filtered_history['High'].idxmax()
                    
                    ma_last_vals_str = []
                    for w, name, color in ma_settings:
                        val = filtered_history[f'MA_{w}'].iloc[-1]
                        val_str = f"{val:{price_fmt}} {currency}" if pd.notna(val) else "데이터 부족"
                        ma_last_vals_str.append(f"{name}: {val_str}")
                    # ma_last_vals_str은 차트 범례/호버 표시용으로만 사용 (ma_context_str 덮어쓰지 않음)
                    
                    padding = (price_max - price_min) * 0.1 if price_max != price_min else price_max * 0.1
                    min_y = price_min - padding
                    max_y = price_max + padding
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Candlestick(
                        x=filtered_history.index, open=filtered_history['Open'], high=filtered_history['High'],
                        low=filtered_history['Low'], close=filtered_history['Close'],
                        increasing_line_color='#ff2d55', decreasing_line_color='#007bff',
                        name="가격"
                    ))

                    for w, name, color in ma_settings:
                        fig.add_trace(go.Scatter(
                            x=filtered_history.index, 
                            y=filtered_history[f'MA_{w}'], 
                            name=name,
                            line=dict(color=color, width=1.2),
                            hovertemplate=f'%{{y:{price_fmt}}}' 
                        ))
                    
                    fig.add_annotation(
                        x=max_idx, y=price_max,
                        text=f"최고: {price_max:{price_fmt}} {currency}",
                        showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#ff2d55",
                        ax=0, ay=-35,
                        font=dict(color="white", size=13, family="Pretendard"),
                        bgcolor="#ff2d55", bordercolor="#ff2d55", borderwidth=1, borderpad=4, opacity=0.9
                    )
                    fig.add_annotation(
                        x=min_idx, y=price_min,
                        text=f"최저: {price_min:{price_fmt}} {currency}",
                        showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#00b0ff",
                        ax=0, ay=35,
                        font=dict(color="white", size=13, family="Pretendard"),
                        bgcolor="#00b0ff", bordercolor="#00b0ff", borderwidth=1, borderpad=4, opacity=0.9
                    )
                    
                    fig.update_layout(
                        template="plotly_dark",
                        dragmode=False,
                        xaxis=dict(**xaxis_config, gridcolor="#dde1e7", tickfont=dict(color="#6b7280", size=12), linecolor="#dde1e7"),
                        yaxis=dict(range=[min_y, max_y], gridcolor="#dde1e7", autorange=False, fixedrange=True, tickformat=price_fmt, hoverformat=price_fmt, tickfont=dict(color="#6b7280", size=12), linecolor="#dde1e7"),
                        height=520,
                        margin=dict(l=0, r=10, t=48, b=0),
                        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(240,242,245,0.92)", font=dict(color="#374151", size=12), bordercolor="#dde1e7", borderwidth=1),
                        hovermode="x unified",
                        clickmode="none",
                        hoverlabel=dict(font_family="Pretendard", bgcolor="#1a1a2e", bordercolor="#374151", font_color="white"),
                        paper_bgcolor="#f0f2f5",
                        plot_bgcolor="#f0f2f5",
                    )
                    
                    st.plotly_chart(fig, use_container_width=True, config={
                        'displayModeBar': False,
                        'scrollZoom': False,
                        'showAxisDragHandles': False,
                        'doubleClick': False
                    })
                else:
                    st.warning("선택하신 기간에는 표시할 데이터가 없어요. 슬라이더 조절해 주세요!")
            else:
                pass  # ma_context_str은 탭 외부에서 이미 계산됨
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("AI 차트 추세 분석 실행"):
                with st.spinner("순수 기술적 관점에서 차트를 분석하는 중입니다..."):
                    def get_formatted_history(interval_str, ma_config):
                        try:
                            temp_hist = fetch_chart_history(ticker, interval_str)
                            if temp_hist.empty: return ""
                            temp_hist = temp_hist[(temp_hist['Low'] > 0) & (temp_hist['High'] > 0) & (temp_hist['Close'] > 0)].copy()
                            for w, _, _ in ma_config:
                                temp_hist[f'MA_{w}'] = temp_hist['Close'].rolling(window=w).mean()
                            
                            temp_mask = (temp_hist.index.date >= selected_start) & (temp_hist.index.date <= selected_end)
                            temp_filtered = temp_hist.loc[temp_mask].copy()
                            
                            cols_to_export = ['Open', 'High', 'Low', 'Close', 'Volume'] + [f'MA_{w}' for w, _, _ in ma_config]
                            df_export = temp_filtered[cols_to_export].copy()
                            df_export.index = df_export.index.strftime('%Y-%m-%d')
                            return df_export.tail(150).round(2).to_csv(header=True)
                        except: return ""

                    daily_csv = get_formatted_history("1d", [(5, "", ""), (20, "", ""), (60, "", ""), (120, "", "")])
                    weekly_csv = get_formatted_history("1wk", [(13, "", ""), (26, "", ""), (52, "", "")])
                    monthly_csv = get_formatted_history("1mo", [(9, "", ""), (24, "", ""), (60, "", "")])

                    prompt = f"""당신은 기술적 분석 전문가입니다. SMC(스마트 머니 컨셉), 프라이스 액션, 이동평균, 거래량 분석 등 다양한 기법을 통합적으로 활용하여 {display_name}({ticker})의 심층 기술적 분석 리포트를 작성해주세요.

                    [일봉 데이터 (Open, High, Low, Close, Volume + MAs)]
                    {daily_csv}

                    [주봉 데이터]
                    {weekly_csv}

                    [월봉 데이터]
                    {monthly_csv}

                    ─────────────────────────────────────────
                    [분석에 사용할 핵심 개념 정의]
                    ─────────────────────────────────────────
                    • 유동성 풀(Liquidity Pool): 스윙 고점/저점 직상단·직하단에 쌓인 스탑 주문 군집. 가격은 이 구간을 건드린 뒤 반전하거나, 돌파 후 가속하는 경향이 있다.
                    • 오더블록(Order Block, OB): 큰 추세 전환이 시작되기 직전 마지막 상승(매수 OB) 또는 하락(매도 OB) 캔들 구간. 기관/세력의 미체결 주문이 잠재해 있어 재방문 시 강한 반응이 나타난다. 데이터로 추정할 수 있는 경우에만 언급하고, 반드시 '추정 구간'임을 명시할 것.
                    • FVG(Fair Value Gap, 공정가치갭): 연속 3캔들에서 1번 캔들 고가 < 3번 캔들 저가(상승 FVG), 또는 1번 캔들 저가 > 3번 캔들 고가(하락 FVG)인 미충전 갭. 최근 20캔들 내 아직 가격이 되돌아오지 않은 유효 FVG만 언급할 것.
                    • 거짓 돌파(Fake out): 주요 지지/저항을 일시적으로 돌파한 뒤 즉시 내부로 회귀하는 움직임. 세력이 스탑을 털어낸 직후 역방향으로 강하게 움직이는 신호.
                    • 함정(Trap): Bull Trap(저항 돌파 후 급락) / Bear Trap(지지 붕괴 후 급등). 거짓 돌파의 결과로 발생하며, 반대 방향 포지션 청산을 유도한다.
                    • 피보나치 되돌림: 데이터 구간 내 주요 스윙 고점과 저점을 기준으로 0.382, 0.500, 0.618 구간을 산출하여 지지/저항 가능성을 판단한다.
                    ─────────────────────────────────────────

                    아래 5개 항목 순서로 리포트를 작성하세요.
                    ★ 핵심 원칙: 각 항목은 현재 차트에서 실제로 유의미한 내용이 있을 때만 서술하세요. 억지로 채우는 것은 오분석입니다. 항목당 최대 4~5문장으로 간결하게.

                    ### 1. 추세 구조
                    월봉(빅픽처) → 주봉 → 일봉 순서로 큰 그림부터 작은 그림으로 좁혀가며 서술하세요(멀티타임프레임 탑다운 분석).
                    - 각 타임프레임의 추세 방향(상승/하락/횡보)과 추세선·채널 구조를 파악하세요.
                    - 타임프레임 간 추세가 상충될 경우 '타임프레임 충돌' 상황으로 명시하세요.
                    - 주요 스윙 고점/저점의 유동성 풀 위치(가격대)를 구체적으로 짚으세요.

                    ### 2. 핵심 가격 구조
                    - 강력 수평 지지/저항선을 먼저 파악하세요.
                    - 데이터 구간의 주요 스윙 고저점 기준 피보나치 되돌림 0.382 / 0.500 / 0.618 구간을 계산하여 현재 가격과의 관계를 설명하세요.
                    - 추세 전환점으로 추정되는 오더블록(OB) 구간이 있다면 가격대와 함께 서술하되, 반드시 '추정'임을 명시하세요.
                    - 최근 20캔들(일봉 기준) 내 아직 미충전 상태인 FVG가 있다면 위치와 방향(상승/하락 FVG)을 언급하세요. 없으면 이 항목은 생략하세요.

                    ### 3. 차트 패턴
                    현재 차트에서 실제로 식별되는 패턴만 서술하세요. 아래 패턴 중 해당하는 것을 확인하세요:
                    컵앤핸들 / 다이아몬드 / 아담앤이브(이중바닥 변형) / 헤드앤숄더·역헤드앤숄더 / 이중천장(M자)·이중바닥(W자) / 거짓 돌파(Fake out) / 함정(Bull·Bear Trap) / 변동성 수축 후 확장(VCP)
                    → 뚜렷한 패턴이 없다면: "현재 뚜렷한 차트 패턴은 형성 중이지 않습니다."라고 한 줄로 쓰고 이 항목을 마무리하세요.

                    ### 4. 모멘텀 & 거래량
                    - 이동평균선 배열(정배열/역배열) 및 골든크로스·데드크로스 발생 여부를 서술하세요.
                    - 가격의 고점/저점 시퀀스를 분석하여 추세 강도 변화(고점이 낮아지거나 저점이 높아지는 등)를 파악하세요.
                    - 거래량 흐름을 반드시 분석하세요: 돌파 시 거래량 수반 여부, 상승(하락) 시 거래량 증감 패턴, 거래량 이상 급증/급감 구간. 거래량은 절댓값보다 전일/전주 대비 상대적 변화로 해석하세요.
                    - 가격 고저점 시퀀스 기반의 강세 또는 약세 다이버전스 징후가 있다면 언급하세요(오실레이터 없이 가격·거래량 흐름만으로 판단).
                    - 캔들 크기와 거래량의 수축·확장 국면을 함께 언급하세요.

                    ### 5. 종합 시나리오
                    단기(일봉 기준)와 중장기(주봉·월봉 기준)로 나누어 유력한 시나리오를 서술하세요.
                    반드시 핵심 변수(Key Level)를 명시하세요: "X {currency} 돌파 시 → Y 방향 전개 예상 / Z {currency} 붕괴 시 → W 방향 전개 예상"

                    ─────────────────────────────────────────
                    [공통 작성 규칙]
                    ─────────────────────────────────────────
                    - 어조: 정중체. 전문가 톤. 이모티콘·과장 표현 금지.
                    - 소제목은 반드시 위에 명시한 ### 헤딩 그대로 사용.
                    - 핵심 문장·가격대·전환 신호는 **굵은 글씨**로 강조. 단순 수치 나열에는 굵은 글씨 쓰지 말 것.
                    - 달러 기호 금지. 모든 금액은 '{currency}' 단위 사용.
                    - 출처 표기 절대 금지: (1), (2) 등 기사 번호 괄호 표기 완전 금지.
                    - 뉴스 헤드라인 직접 인용 절대 금지.
                    - 전문 용어 첫 등장 시 괄호로 간략 설명 포함. 예: 오더블록(OB, 기관 매수/매도 시작 구간)

                    [최신 시장 동향 - 차트 해석의 배경 맥락으로만 참고. 기술적 분석의 주재료가 되어선 안 됨]
                    {news_context}
                    """
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.0}
                        )
                        _html = md_to_html(response.text)
                        st.markdown(f'<div class="ai-result-card">{_html}</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"⚠️ 에러가 발생했습니다. 잠시 후 다시 시도해주세요. ({e})")
          
        # --- [탭 2: 상세 재무] ---
        with tab2:
            st.markdown('<div class="section-header"><span class="section-badge">01</span> 가치 및 안정성 지표</div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            
            c1.metric("시가총액", format_large_number(market_cap, currency) if market_cap else 'N/A')
            c1.metric("Trailing PER", fmt_flt(trailing_pe, is_per=True))
            c1.metric("Forward PER", fmt_flt(forward_pe, is_per=True))
            c1.metric("PBR", fmt_flt(pb))
            c1.metric("PSR", fmt_flt(psr))
            
            c2.metric("PEG", fmt_flt(peg))
            c2.metric("EV/EBITDA", fmt_flt(ev_ebitda))
            c2.metric("ROE", fmt_pct(roe))
            c2.metric("ROA", fmt_pct(roa))
            c2.metric("ROIC", fmt_pct(roic))
            
            c3.metric("매출총이익률", fmt_pct(gross_margin))
            c3.metric("영업이익률", fmt_pct(op_margin))
            c3.metric("순이익률", fmt_pct(net_margin))
            c3.metric("매출 성장률", fmt_pct(rev_growth))
            c3.metric("배당 수익률", fmt_pct(div_yield)) 
            
            try:
                debt_val = float(debt)
                debt_str = f"{debt_val:.2f}%"
            except:
                debt_str = f"{debt}%" if debt != 'N/A' else 'N/A'
                
            c4.metric("부채비율", debt_str)
            c4.metric("유동비율", fmt_flt(current_ratio))
            c4.metric("당좌비율", fmt_flt(quick_ratio))
            c4.metric("이자보상배율", interest_cov)
            c4.metric("52주 최고/최저", f"{high_52:{price_fmt}} / {low_52:{price_fmt}}")
            
            st.markdown("---")
            st.markdown('<div class="section-header"><span class="section-badge">02</span> 재무제표 요약 (최근 결산)</div>', unsafe_allow_html=True)
            fc1, fc2, fc3 = st.columns(3)
            
            with fc1:
                st.markdown('<div class="fin-section-title">손익계산서</div>', unsafe_allow_html=True)
                st.markdown(f"""
                <table class="fin-table">
                    <tr><td>매출액</td><td>{v_rev}</td></tr>
                    <tr><td>매출원가</td><td>{v_cogs}</td></tr>
                    <tr><td>매출총이익</td><td>{v_gp}</td></tr>
                    <tr><td>판매관리비</td><td>{v_sga}</td></tr>
                    <tr><td>영업이익</td><td>{v_op}</td></tr>
                    <tr><td>법인세차감전순이익</td><td>{v_pretax}</td></tr>
                    <tr><td>당기순이익</td><td>{v_net}</td></tr>
                    <tr><td>기타포괄손익</td><td>{v_oci}</td></tr>
                </table>
                """, unsafe_allow_html=True)
                
            with fc2:
                st.markdown('<div class="fin-section-title">재무상태표</div>', unsafe_allow_html=True)
                st.markdown(f"""
                <table class="fin-table">
                    <tr><td>자산총계</td><td>{v_tot_assets}</td></tr>
                    <tr><td>유동자산</td><td>{v_cur_assets}</td></tr>
                    <tr><td>현금및현금성자산</td><td>{v_cash}</td></tr>
                    <tr><td>매출채권</td><td>{v_receiv}</td></tr>
                    <tr><td>재고자산</td><td>{v_inv}</td></tr>
                    <tr><td>비유동자산</td><td>{v_ncur_assets}</td></tr>
                    <tr><td>유형자산</td><td>{v_tangible}</td></tr>
                    <tr><td>무형자산</td><td>{v_intangible}</td></tr>
                    <tr><td>부채총계</td><td>{v_tot_liab}</td></tr>
                    <tr><td>유동부채</td><td>{v_cur_liab}</td></tr>
                    <tr><td>단기차입금</td><td>{v_s_debt}</td></tr>
                    <tr><td>비유동부채</td><td>{v_ncur_liab}</td></tr>
                    <tr><td>장기차입금</td><td>{v_l_debt}</td></tr>
                    <tr><td>자본총계</td><td>{v_tot_eq}</td></tr>
                    <tr><td>자본금</td><td>{v_cap_stock}</td></tr>
                    <tr><td>자본잉여금</td><td>{v_cap_surplus}</td></tr>
                    <tr><td>이익잉여금</td><td>{v_retained}</td></tr>
                </table>
                """, unsafe_allow_html=True)
            with fc3:
                st.markdown('<div class="fin-section-title">현금흐름표</div>', unsafe_allow_html=True)
                st.markdown(f"""
                <table class="fin-table">
                    <tr><td>기초현금</td><td>{v_cf_beg}</td></tr>
                    <tr><td>영업활동현금흐름</td><td>{v_cf_op}</td></tr>
                    <tr><td>투자활동현금흐름</td><td>{v_cf_inv}</td></tr>
                    <tr><td>재무활동현금흐름</td><td>{v_cf_fin}</td></tr>
                    <tr><td>배당금 지급</td><td>{v_dividend}</td></tr>
                    <tr><td>기말현금</td><td>{v_cf_end}</td></tr>
                </table>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("AI 재무 건전성 평가 실행"):
                with st.spinner("재무 데이터를 분석하는 중입니다..."):
                    prompt = f"""종목 {display_name}({ticker})의 상세 재무 데이터를 분석하여 재무 건전성을 평가해주세요.
{'[종목 유형 참고] 이 종목은 ETF/펀드입니다. PER·PBR 등 기업가치 지표가 N/A인 경우, 운용보수·NAV 괴리율·추적 지수의 장기 성과 관점으로 평가하세요.' if _quote_type == 'ETF' else ''}

[가치 및 수익성 지표]
※ 아래 모든 재무 수치는 {currency} 단위(절댓값)입니다.
시가총액: {format_large_number(market_cap, currency) if market_cap else 'N/A'}, Trailing PER: {fmt_flt(trailing_pe, is_per=True)}, Forward PER: {fmt_flt(forward_pe, is_per=True)}, PBR: {fmt_flt(pb)}, PSR: {fmt_flt(psr)}, PEG: {fmt_flt(peg)}, EV/EBITDA: {fmt_flt(ev_ebitda)}
ROE: {fmt_pct(roe)}, ROA: {fmt_pct(roa)}, ROIC: {fmt_pct(roic)}, 매출 성장률: {fmt_pct(rev_growth)}, 배당 수익률: {fmt_pct(div_yield)}
매출총이익률: {fmt_pct(gross_margin)}, 영업이익률: {fmt_pct(op_margin)}, 순이익률: {fmt_pct(net_margin)}
[안정성 지표]
부채비율: {debt_str}, 유동비율: {fmt_flt(current_ratio)}, 당좌비율: {fmt_flt(quick_ratio)}, 이자보상배율: {interest_cov}
[손익계산서]
매출액: {v_rev}, 매출원가: {v_cogs}, 매출총이익: {v_gp}, 판매관리비: {v_sga}, 영업이익: {v_op}, 법인세차감전순이익: {v_pretax}, 당기순이익: {v_net}, 기타포괄손익: {v_oci}
[재무상태표]
자산총계: {v_tot_assets}, 유동자산: {v_cur_assets}, 현금및현금성자산: {v_cash}
부채총계: {v_tot_liab}, 유동부채: {v_cur_liab}, 단기차입금: {v_s_debt}, 장기차입금: {v_l_debt}
자본총계: {v_tot_eq}
[현금흐름표]
기초현금: {v_cf_beg}, 영업활동현금흐름: {v_cf_op}, 투자활동현금흐름: {v_cf_inv}, 재무활동현금흐름: {v_cf_fin}, 배당금지급: {v_dividend}, 기말현금: {v_cf_end}

이 모든 세부 재무 수치들을 종합적으로 분석하여 다음을 객관적으로 평가해주세요:
1. 현재 기업 가치의 고평가 또는 저평가 여부
2. 기업의 재무적 안전성 및 리스크 판단
3. 기업의 수익성 및 미래 성장 가능성

[분석 지침]
- 정중체 사용. 깔끔한 전문가 톤 유지.
- 각 평가 항목은 마크다운 헤딩(###)으로 작성.
- 분석 내용 중 핵심 문장은 반드시 **굵은 글씨(**)**로 강조해서 한눈에 들어오게 하세요. 단, 폰트 크기나 색상은 임의로 변경하지 마세요.
- [기사 번호 괄호 표기 절대 금지]: (예: 1, 12, 50), (60) 등 문장 끝이나 중간에 기사 번호를 괄호로 넣는 짓을 절대 하지 마세요. 출처 번호는 완전히 생략하고 자연스러운 문장으로만 작성하세요.
- 뉴스 헤드라인 직접 인용 절대 금지: 기사 제목이나 헤드라인을 따옴표로 그대로 쓰지 마세요.
- 달러 기호 금지. (금액은 '{currency}'으로 표기할 것).

[최신 동향 — 재무 수치 배경 설명에만 제한적 활용. 재무와 무관한 뉴스(신제품·파트너십·인사 등)는 언급 금지]
{news_context}
"""
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.0}
                        )
                        _html = md_to_html(response.text)
                        st.markdown(f'<div class="ai-result-card">{_html}</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"⚠️ 에러가 발생했습니다. 잠시 후 다시 시도해주세요. ({e})")
                    
        # --- [탭 3: 최신 동향] ---
        with tab3:
            st.markdown('<div class="section-header"><span class="section-badge">LIVE</span> 실시간 동향 및 투심 분석</div>', unsafe_allow_html=True)
            st.write(f"기준일: **{today_date}**")
          
            col_news1, col_news2 = st.columns(2)
            with col_news1:
                if st.button("AI 최신 동향 브리핑"):
                    with st.spinner("최신 뉴스를 분석하는 중입니다..."):
                        prompt = f"오늘은 {today_date}입니다. 방금 시스템이 실시간으로 수집한 {display_name}({ticker})의 최신 기사 데이터입니다.\n\n[실시간 시장 동향 데이터]\n{news_context}\n\n위 데이터의 본문 내용을 읽고, 현재 이 기업을 둘러싼 핵심 이슈를 2~3가지 도출해주세요. 뉴스 수가 적거나 이슈가 2개뿐이라면 억지로 3개를 만들지 마세요. 각 이슈가 기업의 향후 실적에 미칠 파급력까지 전문가의 시선으로 분석해주세요.\n\n[지시사항]\n- 정중체 사용. 깔끔한 전문가 톤 유지.\n- 핵심 이슈는 마크다운 헤딩(###)과 숫자로 제목 작성.\n- 핵심 문장은 **굵은 글씨(**)**로 강조.\n- 달러 기호 금지.\n- 출처 표기 절대 금지: 괄호 안에 기사 번호(예: 1, 3, 50)를 작성하거나 인용구를 쓰는 것을 완벽 금지합니다.\n- 뉴스 헤드라인 직접 인용 절대 금지: 기사 제목이나 헤드라인을 따옴표로 그대로 쓰지 마세요."
                        try:
                            response = client.models.generate_content(
                                model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.0}
                            )
                            _html = md_to_html(response.text)
                            st.markdown(f'<div class="ai-result-card">{_html}</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"⚠️ 에러가 발생했습니다. 잠시 후 다시 시도해주세요. ({e})")
                        
                        st.markdown("---")
                        st.markdown("**📌 참고한 실시간 뉴스 원문 (클릭해서 바로 이동)**")
                        if news_list:
                            for item in news_list[:10]:
                                st.markdown(f"• <a href='{item['link']}' target='_blank'>{item['title']}</a>", unsafe_allow_html=True)
                        else:
                            st.write("뉴스 링크를 불러올 수 없습니다.")
          
            with col_news2:
                if st.button("AI 시장 투심 분석 실행"):
                    with st.spinner("시장 참여자들의 투심을 분석하는 중입니다..."):
                        prompt = f"오늘은 {today_date}입니다. 방금 수집된 {display_name}({ticker})의 최신 기사 데이터입니다.\n\n[실시간 시장 동향 데이터]\n{news_context}\n\n이 데이터를 바탕으로 현재 시장 분위기와 투자 심리를 정성적으로 파악하고, 단기 및 중장기 주가 흐름에 미칠 영향을 분석해주세요. 뉴스 25개로 시장 전체를 단정짓지 말고, 현재 보이는 분위기를 균형 있게 서술하세요.\n\n[지시사항]\n- 정중체 사용. 깔끔한 전문가 톤 유지.\n- 단기 및 중장기 분석 시 마크다운 헤딩(###)으로 소제목 작성.\n- 핵심 문장은 **굵은 글씨(**)**로 강조.\n- 달러 기호 금지.\n- 출처 표기 절대 금지: 괄호 안에 기사 번호(예: 1, 3, 50)를 작성하거나 인용구를 쓰는 것을 완벽 금지합니다.\n- 뉴스 헤드라인 직접 인용 절대 금지: 기사 제목이나 헤드라인을 따옴표로 그대로 쓰지 마세요."
                        try:
                            response = client.models.generate_content(
                                model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.0}
                            )
                            _html = md_to_html(response.text)
                            st.markdown(f'<div class="ai-result-card">{_html}</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"⚠️ 에러가 발생했습니다. 잠시 후 다시 시도해주세요. ({e})")

        # --- [탭 4: 종합 리포트 및 투자의견 바] ---
        with tab4:
            st.markdown('<div class="section-header"><span class="section-badge">AI</span> 퀀트 애널리스트 최종 브리핑</div>', unsafe_allow_html=True)

            if "report_cache" not in st.session_state:
                st.session_state.report_cache = {}

            _cache_raw = f"{ticker}|{current_price}|{trailing_pe}|{forward_pe}|{pb}|{debt_str}|{op_margin}|{high_52}|{low_52}"
            _cache_key = hashlib.md5(_cache_raw.encode()).hexdigest()

            _do_generate = st.button("원클릭 종합 분석 리포트 생성")
            if _do_generate:
                st.session_state.report_cache.pop(_cache_key, None)

            if _cache_key in st.session_state.report_cache:
                _c = st.session_state.report_cache[_cache_key]
                st.markdown(f'<div class="ai-result-card">{_c["html"]}</div>', unsafe_allow_html=True)
                if _c.get("bar_html"):
                    st.markdown(_c["bar_html"].replace('\n', ''), unsafe_allow_html=True)
            elif _do_generate:
                with st.spinner('모든 데이터를 종합하여 분석하는 중입니다...'):
                    _category = (info.get('category') or info.get('fundFamily') or '').upper()
                    _name_upper = display_name.upper()
                    _ticker_upper = ticker.upper()

                    _cash_keywords = ['KOFR', 'SOFR', 'LIBOR', 'CD금리', 'T-BILL', 'TBILL',
                                      'MONEY MARKET', 'MMF', '초단기', 'ULTRA SHORT', 'CASH',
                                      '통안채', '단기채']
                    _longbond_keywords = ['TLT', 'EDV', 'ZROZ', '20년', '30년', 'LONG BOND',
                                          'LONG TERM', '장기채', '장기국채']
                    _bond_keywords = ['BOND', 'TREASURY', 'FIXED INCOME', 'AGGREGATE',
                                      'AGG', 'BND', 'IEF', 'SHY', '채권', '국채', '회사채']

                    _is_cash_etf = (
                        any(kw in _name_upper for kw in _cash_keywords) or
                        any(kw in _ticker_upper for kw in _cash_keywords)
                    )
                    _is_longbond_etf = (
                        any(kw in _name_upper for kw in _longbond_keywords) or
                        any(kw in _ticker_upper for kw in _longbond_keywords)
                    )
                    _is_bond_etf = (
                        _is_cash_etf or _is_longbond_etf or
                        any(kw in _name_upper for kw in _bond_keywords) or
                        any(kw in _ticker_upper for kw in _bond_keywords) or
                        any(kw in _category for kw in _bond_keywords)
                    )

                    _lev_keywords = ['TQQQ', 'SQQQ', 'UPRO', 'SPXU', 'UDOW', 'SDOW',
                                     'TECL', 'TECS', 'LABU', 'LABD', 'SOXL', 'SOXS',
                                     'TMF', 'TMV', 'TNA', 'TZA', 'FAS', 'FAZ',
                                     '레버리지', '인버스', '2X', '3X', '곱버스',
                                     'LEVERAGE', 'INVERSE', 'DIREXION', 'PROSHARES']
                    # ULTRA/BULL/BEAR는 일반 주식 종목명에도 포함될 수 있어 ETF일 때만 적용
                    _lev_keywords_etf_only = ['ULTRA', 'BEAR', 'BULL']
                    _is_lev_etf = (
                        any(kw in _name_upper for kw in _lev_keywords) or
                        any(kw in _ticker_upper for kw in _lev_keywords) or
                        (_quote_type == 'ETF' and (
                            any(kw in _name_upper for kw in _lev_keywords_etf_only) or
                            any(kw in _ticker_upper for kw in _lev_keywords_etf_only)
                        ))
                    )

                    _index_keywords = ['S&P', 'NASDAQ', 'KOSPI', 'KOSDAQ', 'INDEX', '인덱스',
                                       'TIGER', 'KODEX', 'ARIRANG', 'KINDEX', 'HANARO',
                                       'SPY', 'QQQ', 'VTI', 'VOO', 'IVV']
                    _is_etf = _quote_type == 'ETF' or any(kw in _name_upper for kw in _index_keywords)

                    if _is_lev_etf:
                        _asset_context = (
                            '[종목 유형 컨텍스트 - 반드시 점수 산정에 반영할 것]\n'
                            '이 종목은 레버리지/인버스 ETF입니다.\n'
                            '- RISK 평가 기준: 기초지수 변동의 2~3배 손익이 발생하는 고위험 상품입니다.\n'
                            '  하락장에서는 일반 ETF 대비 2~3배의 손실이 납니다.\n'
                            '  장기 보유 시 변동성 손실(volatility decay) 효과로 수익이 예상보다 낮아질 수 있습니다.\n'
                            '  RISK는 기초지수 ETF보다 구조적으로 높게 평가하세요.\n'
                            '- RETURN 평가 기준: 기초지수 상승 시 2~3배의 수익이 구조적으로 발생합니다.\n'
                            '  이미 많이 올랐다는 논리는 레버리지 ETF에 동일하게 적용할 수 없습니다.\n'
                            '  기초지수(추종 지수)가 앞으로 상승할 여력이 있다면,\n'
                            '  레버리지 ETF의 RETURN은 기초지수 ETF보다 반드시 높아야 합니다.\n'
                            '  단, 변동성 손실과 횡보장 리스크도 함께 반영하세요.\n'
                            '- 3번 대응 전략 서술 방향: 기술적 타이밍보다 이 ETF가 추종하는 기초지수의 방향성을\n'
                            '  핵심 판단 기준으로 서술하세요. 레버리지 ETF는 장기 보유 시 변동성 손실이 발생하므로,\n'
                            '  현재 보유자에게는 단기 목표 도달 시 청산 원칙과 재진입 조건을 강조하세요.\n'
                        )
                    elif _is_cash_etf:
                        _asset_context = (
                            '[종목 유형 컨텍스트 - 반드시 점수 산정에 반영할 것]\n'
                            '이 종목은 초단기채권/금리형 ETF(현금성 자산)입니다.\n'
                            '- RISK 평가 기준: 주식이 아닌 현금성 자산 기준으로 평가하세요.\n'
                            '  주식시장 전체가 폭락해도 이 상품은 거의 영향받지 않습니다.\n'
                            '  금리 방향성 리스크도 거의 없습니다(단기물이라 듀레이션 극히 짧음).\n'
                            '  현금성 자산 중 가장 안전한 축에 속합니다.\n'
                            '- RETURN 평가 기준: 현재 기준금리 수준의 수익(연 3~5%)만 기대 가능합니다.\n'
                            '  주가 상승 포텐셜은 구조적으로 없으며, 금리 인하 시 수익률이 낮아집니다.\n'
                            '- 3번 대응 전략 서술 방향: 차트 기술적 조건보다 금리 수준 대비 보유 적절성을\n'
                            '  중심으로 서술하세요. 신규 매수 대기자에게는 "언제든 매수 가능하나\n'
                            '  금리 인하 국면에서는 수익률이 낮아지므로 금리 환경을 확인하라"고 안내하세요.\n'
                            '  매도 고려자에게는 더 높은 수익을 줄 수 있는 대체 자산 관점에서 서술하세요.\n'
                        )
                    elif _is_longbond_etf:
                        _asset_context = (
                            '[종목 유형 컨텍스트 - 반드시 점수 산정에 반영할 것]\n'
                            '이 종목은 장기채권 ETF입니다.\n'
                            '- RISK 평가 기준: 채권이지만 듀레이션이 길어 금리 변동에 매우 민감합니다.\n'
                            '  금리 1% 상승 시 가격이 15~20% 급락할 수 있어 일부 주식보다 변동성이 큽니다.\n'
                            '  금리 방향성 리스크를 일반 채권보다 훨씬 높게 반영하세요.\n'
                            '- RETURN 평가 기준: 금리 하락 사이클에서는 큰 자본이득이 가능하나,\n'
                            '  금리 상승 사이클에서는 반대로 큰 손실이 납니다. 현재 금리 방향성을 반드시 고려하세요.\n'
                            '- 3번 대응 전략 서술 방향: 차트 기술적 조건과 함께 금리 방향성(기준금리 추이,\n'
                            '  시장 금리)을 핵심 판단 기준으로 서술하세요. 금리 상승 국면에서는\n'
                            '  보유 비중 축소, 금리 하락 전환 신호 시 비중 확대 전략을 중심으로 안내하세요.\n'
                        )
                    elif _is_bond_etf:
                        _asset_context = (
                            '[종목 유형 컨텍스트 - 반드시 점수 산정에 반영할 것]\n'
                            '이 종목은 채권형 ETF입니다.\n'
                            '- RISK 평가 기준: 주식보다 낮지만, 금리 상승기에는 가격 하락 리스크가 있습니다.\n'
                            '  듀레이션(잔존만기)에 따라 금리 민감도가 다르므로 이를 반영하세요.\n'
                            '  신용등급에 따라 회사채는 디폴트 리스크도 고려해야 합니다.\n'
                            '- RETURN 평가 기준: 이자 수익 + 금리 하락 시 자본이득이 전부입니다.\n'
                            '  주식처럼 폭발적 상승은 없으나, 금리 방향성에 따라 의미 있는 수익도 가능합니다.\n'
                            '- 3번 대응 전략 서술 방향: 차트 기술적 조건과 함께 금리 방향성(기준금리 추이)과\n'
                            '  보유 목적(이자 수익 vs. 금리 하락 차익)을 중심으로 서술하세요.\n'
                            '  대응 전략에서 금리 상승 국면의 리스크와 방어 방법을 반드시 언급하세요.\n'
                        )
                    elif _is_etf:
                        _asset_context = (
                            '[종목 유형 컨텍스트 - 반드시 점수 산정에 반영할 것]\n'
                            '이 종목은 주식형 ETF 또는 인덱스 펀드입니다.\n'
                            '- RISK 평가 기준: 개별 종목보다 분산투자 효과로 RISK가 낮습니다.\n'
                            '  다만 추종 지수/섹터의 시장 리스크는 그대로 반영됩니다.\n'
                            '- RETURN 평가 기준: 추종 지수의 장기 성장성을 반영하세요.\n'
                            '  개별 종목처럼 폭발적 상승은 어렵지만 꾸준한 수익은 가능합니다.\n'
                        )
                    else:
                        _asset_context = ''

                    # 종합 리포트용 차트 CSV 생성 (일봉 60개 + 주봉 26개)
                    # 탭1의 get_formatted_history와 별도로, 탭4 내에서 직접 생성
                    def _build_report_csv(interval_str, ma_windows, n_candles):
                        try:
                            _h = fetch_chart_history(ticker, interval_str)
                            if _h.empty: return ""
                            _h = _h[(_h['Low'] > 0) & (_h['High'] > 0) & (_h['Close'] > 0)].copy()
                            for _w in ma_windows:
                                _h[f'MA_{_w}'] = _h['Close'].rolling(window=_w).mean()
                            _cols = ['Open', 'High', 'Low', 'Close'] + [f'MA_{_w}' for _w in ma_windows]
                            _df = _h[_cols].tail(n_candles).copy()
                            _df.index = _df.index.strftime('%Y-%m-%d')
                            return _df.round(2).to_csv(header=True)
                        except:
                            return ""

                    _report_daily_csv  = _build_report_csv("1d",  [5, 20, 60, 120], 60)
                    _report_weekly_csv = _build_report_csv("1wk", [13, 26, 52],     26)

                    prompt = f"""
                    오늘은 {today_date}입니다. {display_name}({ticker}) 종목을 종합적으로 분석해주세요.
                    이 리포트는 재무 건전성(항목 1) · 기술적 흐름 및 시장 투심(항목 2) · 대응 전략(항목 3) · 가격 제시(항목 4)를 균형 있게 다룹니다. 기술적 개념(OB·FVG 등)은 항목 2의 차트 분석에서만 집중 활용하고, 항목 1은 재무 수치 중심으로 서술하세요.
                    {_asset_context}

                    ─────────────────────────────────────────
                    [기술적 분석 개념 정의 - 항목 2 차트 분석 시 활용]
                    ─────────────────────────────────────────
                    • 유동성 풀(Liquidity Pool): 스윙 고점/저점 직상단·직하단에 쌓인 스탑 주문 군집. 가격이 이 구간을 건드린 뒤 반전하거나 돌파 후 가속하는 경향이 있다.
                    • 오더블록(Order Block, OB): 큰 추세 전환이 시작되기 직전 마지막 상승(매수 OB) 또는 하락(매도 OB) 캔들 구간. 재방문 시 강한 반응이 나타난다. 추정 가능한 경우에만 언급하고 반드시 '추정'임을 명시할 것.
                    • FVG(Fair Value Gap): 연속 3캔들에서 1번 캔들 고가 < 3번 캔들 저가(상승 FVG) 또는 1번 저가 > 3번 고가(하락 FVG)인 미충전 갭. 최근 20캔들 내 유효한 것만 언급.
                    • 피보나치 되돌림: 데이터 내 주요 스윙 고점·저점 기준으로 0.382 / 0.500 / 0.618 구간 산출.
                    • 거짓 돌파(Fake out) / 함정(Trap): 주요 레벨 돌파 후 즉시 회귀하는 세력의 스탑헌팅 패턴.
                    ─────────────────────────────────────────

                    [1. 현재 가격 및 기술적 데이터]
                    - 현재가: {current_price:{price_fmt}} {currency}
                    - 52주 최고/최저: {high_52:{price_fmt}} {currency} / {low_52:{price_fmt}} {currency}
                    - 이동평균선 최근값 (월봉 MA 포함 - 장기 추세 참고용): {ma_context_str}

                    [일봉 차트 데이터 (최근 60캔들 - OB·FVG·피보나치·패턴 분석용)]
                    {_report_daily_csv}

                    [주봉 차트 데이터 (최근 26캔들 - 중기 추세 파악용)]
                    {_report_weekly_csv}
                    
                    [2. 주요 재무 및 펀더멘털 지표]
                    - 시가총액: {format_large_number(market_cap, currency) if market_cap else 'N/A'}, Trailing PER: {fmt_flt(trailing_pe, is_per=True)}, Forward PER: {fmt_flt(forward_pe, is_per=True)}, PBR: {fmt_flt(pb)}, PEG: {fmt_flt(peg)}
                    - ROE: {fmt_pct(roe)}, 영업이익률: {fmt_pct(op_margin)}, 순이익률: {fmt_pct(net_margin)}, 매출 성장률: {fmt_pct(rev_growth)}
                    - 부채비율: {debt_str}, 유동비율: {fmt_flt(current_ratio)}, 이자보상배율: {interest_cov}
                    - 매출액: {v_rev}, 영업이익: {v_op}, 당기순이익: {v_net}, 영업활동현금흐름: {v_cf_op}
                    - 배당 수익률: {fmt_pct(div_yield)}
                    
                    [3. 최신 시장 동향 및 기사 본문 요약]
                    \n{news_context}
                    
                    반드시 다음 4가지 항목을 포함하여 한국어로 명확하게 작성해주세요.
                    
                    1. 재무 상황 종합 평가
                    2. 시장 투심 및 향후 주가 흐름 예상
                    3. 상황별 대응 전략 (현재 보유자 / 신규 매수 대기자 / 매도 고려자)
                    4. 구체적인 가격 제시 (진입 추천가, 1차 목표가, 손절가)
                    
                    [출력 형식 가이드 - 반드시 준수]
                    - 첫 문장은 반드시 아래 문장을 그대로 사용하세요 (수정 금지):
                      "오늘은 {today_date}입니다. {display_name}({ticker}) 종목에 대한 종합 분석입니다."
                    - 각 항목의 제목(1, 2, 3, 4번)은 마크다운 헤딩(## 또는 ###)을 사용하여 작성하세요.
                    - 제목 아래에는 일반 문단으로 줄글을 작성하세요.
                    - 3번 항목(상황별 대응 전략)은 반드시 아래 형식을 그대로 따르세요:
                      ★ 3번에서는 구체적인 가격 수치를 절대 언급하지 마세요. 가격은 4번에서만 제시합니다.
                      ★ 각 대상자가 '어떤 조건·신호가 나타날 때 어떻게 행동할지'를 전략적 관점으로 서술하세요.

                      #### 현재 보유자
                      (추세·지지 유지 여부, 추가 매수 또는 일부 익절 조건, 보유 판단 근거 중심으로 서술)

                      #### 신규 매수 대기자
                      (어떤 기술적 조건이 확인될 때 진입할지, 분할 매수 접근 여부 등 진입 타이밍 전략 중심으로 서술)

                      #### 매도 고려자
                      (어떤 상황에서 비중 축소가 합리적인지, 리스크 관리 관점 중심으로 서술)

                    - 4번 항목(구체적인 가격 제시)은 반드시 아래 형식을 그대로 따르세요. "(설명)" 같은 라벨 절대 금지:
                      #### 진입 추천가: [가격 또는 가격범위]
                      [기술적 근거 1~2문장. 별도 라벨 없이 본문만]

                      #### 1차 목표가: [가격]
                      [기술적 근거 1~2문장]

                      #### 손절가: [가격]
                      (주식·일반 ETF의 경우 손절 기준 가격과 근거 서술)
                      (채권·금리형 ETF의 경우 '손절가' 대신 '비중 축소 조건'으로 서술: 어떤 금리 방향·시장 조건에서 비중을 줄일지)
                      (레버리지 ETF의 경우 높은 변동성을 감안하여 현재가 기준 % 손절 기준으로 서술 가능)

                    - 가격 제시 시 아래 우선순위로 기술적 근거를 활용하세요:
                      [1순위 - 기술적 구조] 지지 오더블록 추정 구간 / 피보나치 0.382·0.500·0.618 / 유동성 풀 / 미충전 FVG 하단 / 주요 수평 지지선
                      [2순위 - 참고 안전망] 52주 최고가({high_52:{price_fmt}} {currency}) / 52주 최저가({low_52:{price_fmt}} {currency}) 는 상한선/하한선 참고용으로만 사용
                      기술적 구조에서 명확한 레벨이 없을 경우에만 현재가 기준 % 범위 사용
                    
                    [분석 지침]
                    - 어조: 정중체 사용. 깔끔한 전문가 톤을 유지하세요. 이모티콘은 절대 사용하지 마세요.
                    - 분량 균형: 1번(재무)·2번(차트+투심)·3번(전략)·4번(가격) 각 항목이 고르게 서술되어야 합니다. 2번 항목에 과도하게 집중하지 마세요.
                    - 항목 2(시장 투심 및 향후 주가 흐름)에서 차트 분석 시: 주봉→일봉 2개 타임프레임 관점(장기 추세는 이동평균선 최근값 참고)에서 유동성 풀, 오더블록(OB), FVG, 주요 차트 패턴(Fake out·Trap·이중천장·이중바닥 등), 피보나치 구간을 종합하여 분석하세요. 이동평균선 숫자 나열에 그치지 말 것.
                    - 핵심 강조: 핵심 문장은 반드시 **굵은 글씨(**)**로 강조하세요. 단순 수치 나열에는 굵은 글씨 쓰지 말 것.
                    - 달러 기호 금지. 금액은 반드시 '{currency}'으로 표기할 것.
                    - 출처 표기 절대 금지: 문장 끝에 (1, 5, 20) 같은 기사 번호를 괄호로 적는 행위를 완벽하게 금지합니다.
                    - 뉴스 헤드라인 직접 인용 절대 금지: 기사 제목이나 헤드라인을 따옴표로 그대로 쓰지 마세요.

                    
                    리포트 본문 작성을 모두 마친 후, 맨 마지막에 아래 형식을 반드시 정확히 작성하세요.
                    아래 블록은 파싱에 사용됩니다. 형식을 절대 바꾸지 마세요.

                    참고 수치:
                    - 현재가의 52주 범위 위치: {round((current_price - low_52) / (high_52 - low_52) * 100) if high_52 != low_52 else 50}% (0%=52주최저, 100%=52주최고)
                    - 시가총액: {format_large_number(market_cap, currency) if market_cap else 'N/A'}

                    **판단근거:**
                    - RISK 근거: [재무안전성·하락여지를 종합하여 한 문장으로. 업종 특성 반영(금융주 고부채=정상, 바이오 적자=감안). 30자 이상 80자 이내]
                    - RETURN 근거: [사업의 구조적·장기적 성장 잠재력과 현재 주가의 반영 정도를 한 문장으로. 상승 잠재력 중심으로 서술하고, 하락 우려는 RISK 근거에서 다루세요. 30자 이상 80자 이내]

                    위 판단을 마친 뒤, 아래 점수를 산출하세요.
                    RISK와 RETURN은 판단근거와 반드시 일치해야 합니다.

                    [점수 기준 앵커 - 먼저 읽고 척도를 잡은 뒤 산출하세요]
                    RISK 스펙트럼 (투자 위험 수준):
                      RISK 10~25 = 초단기 금리형·국채 ETF 등 사실상 원금 보전 자산
                      RISK 40~60 = 글로벌 대형주 인덱스(분산 500종) 또는 대형 우량 개별주 평균 수준
                      RISK 75~90 = 적자 초기 성장주·소형 바이오·레버리지 ETF·고변동성 테마주
                    RETURN 스펙트럼 (기대 수익 잠재력):
                      RETURN 10~25 = 채권·금리형 자산 수준 (연 3~5% 기대)
                      RETURN 40~60 = 시장 평균 성장 수준 (연 8~15% 기대)
                      RETURN 75~90 = 고성장 기술주·구조적 성장 초기 기업·강한 모멘텀 수준

                    생존가능성이 낮거나 하락여지가 크면 RISK는 높아야 합니다.
                    성장천장이 높고 현재 주가에 덜 반영됐을수록 RETURN은 높아야 합니다.
                    단, 전 세계 투자자에게 이미 널리 알려진 초대형 기업은 성장 기대가 주가에 충분히 반영되어 있을 가능성이 높으므로, 추가 성장 배율이 구조적으로 제한됨을 고려하세요.

                    감정이나 보수성을 개입시키지 말고 판단근거에만 근거하여 1단위 정수로 정직하게 산출하세요.

                    아래 두 줄을 반드시 출력하세요. 대괄호·콜론·공백 형식을 그대로 지키고, 숫자 자리에 0~100 사이 실제 분석값을 넣으세요.
                    [RISK: (여기에 숫자)]
                    [RETURN: (여기에 숫자)]
                    """
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.3}
                        )
                        
                        report_text = response.text

                        def _parse_num(text, tag):
                            # re.findall로 모든 매치를 찾고 마지막 값 사용
                            # (AI가 본문에 [RISK: ...] 패턴을 먼저 쓸 경우 오파싱 방지)
                            matches = re.findall(rf'\[{tag}:\s*(\d+)\s*\]', text, re.IGNORECASE)
                            return int(matches[-1]) if matches else None

                        risk_score   = _parse_num(report_text, 'RISK')
                        return_score = _parse_num(report_text, 'RETURN')
                        if risk_score is not None and return_score is not None:
                            final_score = round((return_score - risk_score + 100) / 2)
                            final_score = max(0, min(100, final_score))
                        else:
                            final_score = None

                        _cleaned = report_text.strip()

                        _rationale = ""
                        _rat_s = re.search(r'\*\*판단근거:\*\*', _cleaned)
                        _rat_e = re.search(r'\[RISK:\s*\d+\]', _cleaned)
                        if _rat_s and _rat_e and _rat_s.start() < _rat_e.start():
                            _rat_block = _cleaned[_rat_s.end():_rat_e.start()]
                            def _extract_reason(block, label):
                                # \Z(문자열 절대 끝)로 교체하여 DOTALL+$ 모호성 제거
                                m = re.search(rf'-\s*{label}\s*근거\s*:(.*?)(?=-\s*(?:RISK|RETURN|SCORE)\s*근거|\Z)', block, re.DOTALL)
                                if not m: return ""
                                raw = m.group(1).strip()
                                raw = re.sub(r'\*\*(.+?)\*\*', r'\1', raw)
                                raw = re.sub(r'\*+', '', raw)
                                raw = re.sub(r'#+\s*', '', raw)
                                raw = re.sub(r'\s*\n\s*', ' ', raw)
                                raw = re.sub(r'\s{2,}', ' ', raw).strip()
                                return raw
                            _r_reason   = _extract_reason(_rat_block, 'RISK')
                            _ret_reason = _extract_reason(_rat_block, 'RETURN')
                            parts = []
                            if _r_reason:   parts.append(f'RISK\t{_r_reason}')
                            if _ret_reason: parts.append(f'RETURN\t{_ret_reason}')
                            if risk_score is not None and return_score is not None:
                                _auto_sc = round((return_score - risk_score + 100) / 2)
                                _auto_sc = max(0, min(100, _auto_sc))
                                if   _auto_sc >= 81: _sc_label = "강력 매수"
                                elif _auto_sc >= 61: _sc_label = "매수"
                                elif _auto_sc >= 41: _sc_label = "중립"
                                elif _auto_sc >= 21: _sc_label = "매도"
                                else:                _sc_label = "강력 매도"
                                parts.append(f'SCORE\tRISK {risk_score} · RETURN {return_score} 기준 {_auto_sc}점 → {_sc_label}')
                            _rationale = '\n'.join(parts)

                        # '참고 수치:' 이후 전체 제거 (AI가 판단근거 앞에 배치하도록 지시했으므로)
                        # '**판단근거:**' 이후도 별도 제거 (둘 다 처리해야 어느 순서든 대응 가능)
                        _cleaned = re.sub(r'참고 수치:.*', '', _cleaned, flags=re.DOTALL).strip()
                        _cleaned = re.sub(r'\*\*판단근거:\*\*.*', '', _cleaned, flags=re.DOTALL).strip()
                        _cleaned = re.sub(r"[,'\.\s]+$", "", _cleaned).strip()
                        _html = md_to_html(_cleaned)
                        st.session_state.report_cache[_cache_key] = {"html": _html, "bar_html": None}
                        
                        matrix_html = ""
                        if risk_score is not None and return_score is not None:
                            r_s = max(0, min(100, risk_score))
                            ret_s = max(0, min(100, return_score))
                            matrix_html = (
                                '<div style="margin-top: 40px; padding-top: 20px; border-top: 1px dashed #ddd;">' +
                                '<h4 style="text-align: center; margin-bottom: 25px; color: #333; font-weight: 700;">위험-수익 매트릭스</h4>' +
                                '<div style="position: relative; width: 100%; max-width: 450px; height: 300px; margin: 0 auto; background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); border: 1px solid #dcdcdc; border-radius: 8px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);">' +
                                '<div style="position: absolute; top: 50%; left: 0; width: 100%; height: 1px; background-color: #d0d0d0;"></div>' +
                                '<div style="position: absolute; top: 0; left: 50%; width: 1px; height: 100%; background-color: #d0d0d0;"></div>' +
                                '<div style="position: absolute; top: 10px; left: 10px; font-size: 13px; font-weight: 800; color: #ff6b6b;">저위험 고수익</div>' +
                                '<div style="position: absolute; top: 10px; right: 10px; font-size: 13px; font-weight: 800; color: #ff2d55;">고위험 고수익</div>' +
                                '<div style="position: absolute; bottom: 10px; left: 10px; font-size: 13px; font-weight: 800; color: #555555;">저위험 저수익</div>' +
                                '<div style="position: absolute; bottom: 10px; right: 10px; font-size: 13px; font-weight: 800; color: #007aff;">고위험 저수익</div>' +
                                f'<div style="position: absolute; top: calc({100 - ret_s}% - 12px); left: calc({r_s}% - 12px); width: 24px; height: 24px; background-color: #333; border: 3px solid white; border-radius: 50%; box-shadow: 0 3px 6px rgba(0,0,0,0.3); z-index: 10;"></div>' +
                                '</div>' +
                                (('<div style="margin-top: 16px; padding: 12px 16px; border-top: 1px solid #e8e8e8;">'
                                  '<span style="font-size: 12px; font-weight: 700; color: #444; letter-spacing: 0.3px;">판단근거</span>' +
                                  ''.join(
                                      f'<div style="margin-top: 9px; display: flex; align-items: baseline; gap: 10px;">'
                                      f'<span style="font-size: 10px; font-weight: 800; color: #aaa; letter-spacing: 1px; min-width: 46px; flex-shrink: 0;">{line.split(chr(9))[0]}</span>'
                                      f'<span style="font-size: 12.5px; color: #555; line-height: 1.55;">{line.split(chr(9))[1] if chr(9) in line else ""}</span>'
                                      f'</div>'
                                      for line in _rationale.split(chr(10)) if line.strip()
                                  ) +
                                  '</div>') if _rationale else '') +
                                '</div>'
                            )

                        bar_html = ""
                        if final_score is not None:
                            final_score = max(0, min(100, final_score))
                            if final_score <= 20: opinion_text, text_color = "강력 매도", "#007aff"
                            elif final_score <= 40: opinion_text, text_color = "매도", "#66b2ff"
                            elif final_score <= 60: opinion_text, text_color = "중립", "#555555"
                            elif final_score <= 80: opinion_text, text_color = "매수", "#ff6b6b"
                            else: opinion_text, text_color = "강력 매수", "#ff2d55"
                            arrow = "&#x25BC;"
                            # 화살표 위치: 0% 또는 100%에서 바깥으로 나가지 않도록 2~98% 클램프
                            _arrow_pos = max(2, min(98, final_score))
                            bar_html = (
                                '<div style="margin-top: 30px; margin-bottom: 20px; padding: 25px 20px; border-radius: 12px; background-color: #f8f9fa; border: 1px solid #eaeaea;">' +
                                f'<h4 style="text-align: center; margin-bottom: 30px; color: #333; font-weight: 700;">AI 투자의견: <span style="color: {text_color};">{opinion_text}</span></h4>' +
                                '<div style="position: relative; width: 100%; height: 32px; background: linear-gradient(to right, #007aff 0%, #007aff 20%, #66b2ff 20%, #66b2ff 40%, #e0e0e0 40%, #e0e0e0 60%, #ff8080 60%, #ff8080 80%, #ff2d55 80%, #ff2d55 100%); border-radius: 16px; display: flex; box-shadow: inset 0 2px 4px rgba(0,0,0,0.15);">' +
                                '<div style="width: 20%; line-height: 32px; text-align: center; color: white; font-weight: 800; font-size: 13px; text-shadow: 1px 1px 2px rgba(0,0,0,0.4);">강력 매도</div>' +
                                '<div style="width: 20%; line-height: 32px; text-align: center; color: white; font-weight: 800; font-size: 13px; text-shadow: 1px 1px 2px rgba(0,0,0,0.4);">매도</div>' +
                                '<div style="width: 20%; line-height: 32px; text-align: center; color: #666; font-weight: 800; font-size: 13px;">중립</div>' +
                                '<div style="width: 20%; line-height: 32px; text-align: center; color: white; font-weight: 800; font-size: 13px; text-shadow: 1px 1px 2px rgba(0,0,0,0.4);">매수</div>' +
                                '<div style="width: 20%; line-height: 32px; text-align: center; color: white; font-weight: 800; font-size: 13px; text-shadow: 1px 1px 2px rgba(0,0,0,0.4);">강력 매수</div>' +
                                f'<div style="position: absolute; top: -28px; left: calc({_arrow_pos}% - 12px); font-size: 26px; filter: drop-shadow(0px 3px 3px rgba(0,0,0,0.5));">{arrow}</div>' +
                                '</div>' + matrix_html + '</div>'
                            )

                        combined_html = bar_html if bar_html else (
                            ('<div style="margin-top: 30px; margin-bottom: 20px; padding: 25px 20px; border-radius: 12px; background-color: #f8f9fa; border: 1px solid #eaeaea;">' + matrix_html + '</div>') if matrix_html else ""
                        )
                        if combined_html:
                            st.session_state.report_cache[_cache_key] = {"html": _html, "bar_html": combined_html}
                            st.markdown(f'<div class="ai-result-card">{_html}</div>', unsafe_allow_html=True)
                            st.markdown(combined_html.replace('\n', ''), unsafe_allow_html=True)
                        else:
                            st.session_state.report_cache[_cache_key] = {"html": _html, "bar_html": None}
                            st.markdown(f'<div class="ai-result-card">{_html}</div>', unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.error(f"⚠️ 에러가 발생했습니다. 잠시 후 다시 시도해주세요. ({e})")

    else:
        st.error(f"'{user_input}' 종목을 찾을 수 없습니다. (시도한 티커: {ticker})\n\n정확한 종목명이나 티커 심볼을 입력해 주세요.\n예) 삼성전자, 005930.KS, AAPL, NVDA")

else:
    st.markdown("""
    <div style="margin-top: 50px; font-size: 13px; color: #9ca3af; line-height: 1.8;">
        <strong>업데이트 내용 (2026.03.22)</strong><br>
        • 미국 주식 검색 정확도 대폭 개선 (Yahoo Finance API quoteType 키 버그 수정)<br>
        • AI 차트 분석 대폭 강화: 유동성 풀·오더블록·FVG·피보나치·차트 패턴 등 SMC 기반 심층 분석<br>
        • 종합 리포트 차트 분석도 동일하게 강화, 가격 제시 근거를 기술적 구조 기반으로 개선<br>
        • 재무 건전성 평가 데이터 보강: 재무상태표 세부 항목 추가, 지표 포맷 통일<br>
        • 이자보상배율 계산 오류 수정 (적자 기업 음수 표시)<br>
        • 네이버·Finviz 크롤링 캐시 적용으로 탭 전환 속도 개선<br>
        • 기타 안정성 개선 (현재가 조회 로직, 뉴스 토큰 최적화 등)
    </div>
    """, unsafe_allow_html=True)
