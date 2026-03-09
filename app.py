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
import textwrap

# 전체 화면 넓게 쓰기 및 기본 설정
st.set_page_config(layout="wide", page_title="AI 주식 분석 터미널")

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
        padding: 18px 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
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

    /* ===== 불필요한 UI 숨기기 ===== */
    .stDeployButton { display: none !important; }
    [data-testid="stStatusWidget"] * { display: none !important; }
    [data-testid="stStatusWidget"]::after {
        content: "분석 중..."; font-size: 13px; font-weight: 600; color: #6b7280;
        display: flex; align-items: center; padding: 5px 15px;
    }

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
                    if korean_name:
                        return korean_name
            korean_name = ac_data['items'][0][0][1] 
            if korean_name:
                return korean_name
    except:
        pass
    return english_name

@st.cache_data(ttl=3600)
def get_ticker_symbol(search_term):
    search_term = search_term.strip()
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
        "디어유": "376300.KQ"  
    }
    
    if search_clean in custom_mapping:
        return custom_mapping[search_clean]

    if not krx_df.empty:
        df_temp = krx_df.copy()
        df_temp['Name_clean'] = df_temp['Name'].astype(str).str.replace(" ", "").str.upper()
        match = df_temp[df_temp['Name_clean'] == search_clean]
        if not match.empty:
            code = match.iloc[0]['Code']
            market = match.iloc[0]['Market']
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
            
            if '코스피' in market_str: return f"{code}.KS"
            elif '코스닥' in market_str: return f"{code}.KQ"
            else: return f"{code}.KS"
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
      
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(search_term)}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        data = res.json()
        if 'quotes' in data and len(data['quotes']) > 0:
            us_exchanges = ['NYQ', 'NMS', 'NYSE', 'NASDAQ']
            for quote in data['quotes']:
                if quote.get('type') in ['EQUITY', 'ETF'] and quote.get('exchange', '').upper() in us_exchanges:
                    return quote['symbol']
            for quote in data['quotes']:
                if quote.get('type') in ['EQUITY', 'ETF']:
                    return quote['symbol']
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

def augment_korean_fundamentals(ticker, info):
    if not (ticker.endswith('.KS') or ticker.endswith('.KQ')):
        return info
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
        
        if per is not None: info['trailingPE'] = per
        if pbr is not None: info['priceToBook'] = pbr
        if div is not None: 
            info['dividendYield'] = div / 100.0
            info['naver_div_yield'] = div / 100.0 

        table = soup.find('table', {'class': 'tb_type1 tb_num tb_type1_ifrs'})
        if table:
            tbody = table.find('tbody')
            if tbody:
                rows = tbody.find_all('tr')
                for row in rows:
                    th = row.find('th')
                    if not th: continue
                    title = th.text.strip()
                    tds = row.find_all('td')
                    
                    valid_vals = []
                    for td in tds:
                        txt = td.text.strip().replace(',', '')
                        try:
                            valid_vals.append(float(txt))
                        except:
                            pass
                    
                    if not valid_vals: continue
                    recent_val = valid_vals[-1] 
                    
                    if 'ROE' in title:
                        info['returnOnEquity'] = recent_val / 100.0
                    elif '영업이익률' in title:
                        info['operatingMargins'] = recent_val / 100.0
                    elif '순이익률' in title:
                        info['profitMargins'] = recent_val / 100.0
                    elif '부채비율' in title:
                        info['debtToEquity'] = recent_val
                    elif '당좌비율' in title:
                        info['quickRatio'] = recent_val / 100.0
                    elif '유동비율' in title:
                        info['currentRatio'] = recent_val / 100.0
    except:
        pass 
    return info

def augment_us_fundamentals(ticker, info):
    if ticker.endswith('.KS') or ticker.endswith('.KQ'):
        return info
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
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                for i in range(0, len(cols), 2):
                    key = cols[i].text.strip()
                    val = cols[i+1].text.strip()
                    data_dict[key] = val
                    
            def parse_finviz_val(val_str, is_pct=False):
                if val_str == '-' or val_str == '': return None
                val_str = val_str.replace(',', '').replace('%', '')
                try:
                    num = float(val_str)
                    return num / 100.0 if is_pct else num
                except:
                    return None

            if (v := parse_finviz_val(data_dict.get('P/E', '-'))) is not None: info['trailingPE'] = v
            if (v := parse_finviz_val(data_dict.get('Forward P/E', '-'))) is not None: info['forwardPE'] = v
            if (v := parse_finviz_val(data_dict.get('P/B', '-'))) is not None: info['priceToBook'] = v
            if (v := parse_finviz_val(data_dict.get('P/S', '-'))) is not None: info['priceToSalesTrailing12Months'] = v
            if (v := parse_finviz_val(data_dict.get('PEG', '-'))) is not None: info['pegRatio'] = v
            if (v := parse_finviz_val(data_dict.get('ROE', '-'), True)) is not None: info['returnOnEquity'] = v
            if (v := parse_finviz_val(data_dict.get('ROA', '-'), True)) is not None: info['returnOnAssets'] = v
            if (v := parse_finviz_val(data_dict.get('ROI', '-'), True)) is not None: info['returnOnCapitalEmployed'] = v
            if (v := parse_finviz_val(data_dict.get('Gross Margin', '-'), True)) is not None: info['grossMargins'] = v
            if (v := parse_finviz_val(data_dict.get('Oper. Margin', '-'), True)) is not None: info['operatingMargins'] = v
            if (v := parse_finviz_val(data_dict.get('Profit Margin', '-'), True)) is not None: info['profitMargins'] = v
            if (v := parse_finviz_val(data_dict.get('Dividend %', '-'), True)) is not None: 
                info['dividendYield'] = v
                info['finviz_div_yield'] = v 
            if (v_debt := parse_finviz_val(data_dict.get('Debt/Eq', '-'))) is not None: info['debtToEquity'] = v_debt * 100
            if (v := parse_finviz_val(data_dict.get('Current Ratio', '-'))) is not None: info['currentRatio'] = v
            if (v := parse_finviz_val(data_dict.get('Quick Ratio', '-'))) is not None: info['quickRatio'] = v
    except:
        pass
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
    try: hist_basic = stock.history(period="1d")
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
                if isinstance(n, dict) and 'title' in n and 'link' in n:
                    content = n.get('summary', '') or get_article_text(n['link'])
                    news_list.append({"title": n['title'], "link": n['link'], "content": content[:800].replace('\n', ' ')})
        except: pass
    return news_list

# ====================== 메인 ======================
st.markdown("""
<div style="margin-bottom: 6px;">
    <span style="font-size: 10px; font-weight: 700; letter-spacing: 2.5px; color: #9ca3af; text-transform: uppercase; background:#eef0f4; padding:3px 10px; border-radius:20px;">AI Stock Analysis Terminal</span>
</div>
""", unsafe_allow_html=True)
st.markdown("""
<div style="font-size: 1.75rem; font-weight: 900; color: #1a1a2e; letter-spacing: -0.8px; line-height: 1.2; margin-bottom: 6px;">
    웅이의 AI 주식 분석 터미널
</div>
<div style="color: #9ca3af; font-size: 13.5px; font-weight: 400; margin-bottom: 22px; letter-spacing: 0.1px;">
    종목명 또는 티커를 입력하면 AI가 차트 · 재무 · 뉴스를 종합 분석해드립니다.
</div>
""", unsafe_allow_html=True)

col_search, _ = st.columns([1, 2])
with col_search:
    user_input = st.text_input("분석할 종목명 또는 티커", placeholder="예: 삼성전자, AAPL, NVDA")

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
            english_name = info.get('shortName', ticker)
            display_name = get_korean_display_name(ticker, english_name)
        
        info = augment_korean_fundamentals(ticker, info)
        info = augment_us_fundamentals(ticker, info) 
        
        today_date = datetime.now().strftime("%Y년 %m월 %d일")
        
        is_korean_stock = ticker.endswith('.KS') or ticker.endswith('.KQ')
        is_japanese_stock = ticker.endswith('.T')
        
        if is_korean_stock: currency, price_fmt = "원", ",.0f"
        elif is_japanese_stock: currency, price_fmt = "엔", ",.0f"
        else: currency, price_fmt = "달러", ",.2f"
        
        search_korean_news = is_korean_stock or is_japanese_stock
        news_list = fetch_news_data(ticker, display_name, search_korean_news)
                
        news_context_list = []
        for idx, item in enumerate(news_list):
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
                interest_cov = fmt_flt(abs(op_inc_val / int_exp_val))
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

        tab1, tab2, tab3, tab4 = st.tabs(["차트 분석", "상세 재무", "최신 동향", "종합 리포트"])
        
        # --- [탭 1: 차트 분석] ---
        with tab1:
            # 종목명 + 현재가 헤더 카드
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
                ma_context_str = "차트 데이터 부족"

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
                    ma_context_str = " / ".join(ma_last_vals_str)
                    
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
                        title=dict(text=f"{display_name} ({ticker}) - {interval_option}", font=dict(size=20, color="#1a1a2e", family="Pretendard")),
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
                ma_context_str = "차트 데이터 부족"
            
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
                            
                            cols_to_export = ['Open', 'High', 'Low', 'Close'] + [f'MA_{w}' for w, _, _ in ma_config]
                            df_export = temp_filtered[cols_to_export].copy()
                            df_export.index = df_export.index.strftime('%Y-%m-%d')
                            return df_export.tail(150).round(2).to_csv(header=True)
                        except: return ""

                    daily_csv = get_formatted_history("1d", [(5, "", ""), (20, "", ""), (60, "", ""), (120, "", "")])
                    weekly_csv = get_formatted_history("1wk", [(13, "", ""), (26, "", ""), (52, "", "")])
                    monthly_csv = get_formatted_history("1mo", [(9, "", ""), (24, "", ""), (60, "", "")])

                    prompt = f"""종목 {display_name}({ticker})의 일봉, 주봉, 월봉 전체 가격(시가/고가/저가/종가) 및 이동평균선(MA) 데이터와 최신 시장 동향입니다.
                    
                    [최신 시장 동향 백그라운드 (참고용)]
                    {news_context}
                    
                    [일봉 차트 데이터 내역 (Open, High, Low, Close, MAs)]
                    {daily_csv}
                    
                    [주봉 차트 데이터 내역]
                    {weekly_csv}
                    
                    [월봉 차트 데이터 내역]
                    {monthly_csv}
                    
                    위 데이터를 바탕으로 실전 트레이더 수준의 깊이 있는 기술적 분석 리포트를 작성해주세요. 
                    
                    [분석 핵심 지시사항]
                    1. 프라이스 액션 중심 분석: 이동평균선 수치만 나열하지 말고, 캔들의 형태, 주요 지지와 저항선, 변동성 등 실전적인 관점으로 폭넓게 분석하세요.
                    2. 정보 필터링: 유의미한 기술적 단서만 선별해서 자연스럽게 제시하세요.
                    3. 이동평균선 표기 규칙: 올바른 한국어로 작성하세요.
                    4. 달러 기호 사용 금지. (금액은 반드시 '{currency}'로 표기할 것)
                    5. 가독성 철저: 소제목은 마크다운 헤딩(###)으로 작성하고, 일반 문단으로 작성하세요.
                    6. 핵심 강조: 단순히 가격이나 숫자(예: 80 달러)에만 굵은 글씨를 쓰지 마세요!! 추세 전환의 신호, 지지/저항의 핵심적인 의미, 매수/매도 세력의 동향 등 **분석에서 가장 중요하고 유의미한 문장 전체나 키워드**를 **굵은 글씨(**)**로 강조하세요.
                    7. 어조 설정: 정중체 사용. 깔끔한 전문가 톤 유지.
                    8. 항목 제한: 분석 항목은 무조건 '1. 단기적인 추세', '2. 장기적인 추세' 두 가지만 출력.
                    9. 출처 표기 절대 금지: 괄호 안에 기사 번호(예: 1, 2)를 적거나 출처를 언급하는 행위 완벽 금지.
                    """
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.0}
                        )
                        st.markdown('<div class="ai-result-card">', unsafe_allow_html=True)
                        st.markdown(response.text)
                        st.markdown('</div>', unsafe_allow_html=True)
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
                    prompt = f"""종목 {display_name}({ticker})의 상세 재무 데이터 및 최신 동향 텍스트입니다.

[최신 동향 데이터]
{news_context}

[가치 및 수익성 지표]
시가총액: {format_large_number(market_cap, currency) if market_cap else 'N/A'}, Trailing PER: {trailing_pe}, Forward PER: {forward_pe}, PBR: {pb}, PSR: {fmt_flt(psr)}, PEG: {fmt_flt(peg)}, EV/EBITDA: {fmt_flt(ev_ebitda)}
ROE: {fmt_pct(roe)}, ROA: {fmt_pct(roa)}, ROIC: {fmt_pct(roic)}, 매출 성장률: {fmt_pct(rev_growth)}, 배당 수익률: {fmt_pct(div_yield)}
매출총이익률: {fmt_pct(gross_margin)}, 영업이익률: {fmt_pct(op_margin)}, 순이익률: {fmt_pct(net_margin)}
[안정성 지표]
부채비율: {debt_str}, 유동비율: {fmt_flt(current_ratio)}, 당좌비율: {fmt_flt(quick_ratio)}, 이자보상배율: {interest_cov}
[손익계산서]
매출액: {v_rev}, 매출원가: {v_cogs}, 매출총이익: {v_gp}, 판매관리비: {v_sga}, 영업이익: {v_op}, 법인세차감전순이익: {v_pretax}, 당기순이익: {v_net}, 기타포괄손익: {v_oci}
[재무상태표]
자산총계: {v_tot_assets} 
부채총계: {v_tot_liab} 
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
- 뉴스 데이터는 재무 관련 정보 파악에만 참고.
- [기사 번호 괄호 표기 절대 금지]: (예: 1, 12, 50), (60) 등 문장 끝이나 중간에 기사 번호를 괄호로 넣는 짓을 절대 하지 마세요. 출처 번호는 완전히 생략하고 자연스러운 문장으로만 작성하세요.
- 달러 기호 금지. (금액은 '{currency}'으로 표기할 것).
"""
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.0}
                        )
                        st.markdown('<div class="ai-result-card">', unsafe_allow_html=True)
                        st.markdown(response.text)
                        st.markdown('</div>', unsafe_allow_html=True)
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
                        prompt = f"오늘은 {today_date}입니다. 방금 시스템이 실시간으로 수집한 {display_name}({ticker})의 최신 기사 데이터입니다.\n\n[실시간 시장 동향 데이터]\n{news_context}\n\n위 데이터의 본문 내용을 읽고, 현재 이 기업을 둘러싼 중요한 핵심 이슈 3가지를 도출해주세요. 각 이슈가 기업의 향후 실적에 미칠 파급력까지 전문가의 시선으로 분석해주세요.\n\n[지시사항]\n- 정중체 사용. 깔끔한 전문가 톤 유지.\n- 3가지 핵심 이슈는 마크다운 헤딩(###)과 숫자로 제목 작성.\n- 핵심 문장은 **굵은 글씨(**)**로 강조.\n- 달러 기호 금지.\n- 출처 표기 절대 금지: 괄호 안에 기사 번호(예: 1, 3, 50)를 작성하거나 인용구를 쓰는 것을 완벽 금지합니다."
                        try:
                            response = client.models.generate_content(
                                model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.0}
                            )
                            st.markdown('<div class="ai-result-card">', unsafe_allow_html=True)
                            st.markdown(response.text)
                            st.markdown('</div>', unsafe_allow_html=True)
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
                        prompt = f"오늘은 {today_date}입니다. 방금 수집된 {display_name}({ticker})의 최신 기사 데이터입니다.\n\n[실시간 시장 동향 데이터]\n{news_context}\n\n이 데이터를 바탕으로 현재 시장 참여자들의 숨은 투자 심리(Fear & Greed)를 파악하고, 단기 및 중장기 주가 흐름에 미칠 영향을 분석해주세요.\n\n[지시사항]\n- 정중체 사용. 깔끔한 전문가 톤 유지.\n- 단기 및 중장기 분석 시 마크다운 헤딩(###)으로 소제목 작성.\n- 핵심 문장은 **굵은 글씨(**)**로 강조.\n- 달러 기호 금지.\n- 출처 표기 절대 금지: 괄호 안에 기사 번호(예: 1, 3, 50)를 작성하거나 인용구를 쓰는 것을 완벽 금지합니다."
                        try:
                            response = client.models.generate_content(
                                model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.0}
                            )
                            st.markdown('<div class="ai-result-card">', unsafe_allow_html=True)
                            st.markdown(response.text)
                            st.markdown('</div>', unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"⚠️ 에러가 발생했습니다. 잠시 후 다시 시도해주세요. ({e})")

        # --- [탭 4: 종합 리포트 및 투자의견 바] ---
        with tab4:
            st.markdown('<div class="section-header"><span class="section-badge">AI</span> 퀀트 애널리스트 최종 브리핑</div>', unsafe_allow_html=True)
            if st.button("원클릭 종합 분석 리포트 생성"):
                with st.spinner('모든 데이터를 종합하여 분석하는 중입니다...'):
                    prompt = f"""
                    오늘은 {today_date}입니다. {display_name}({ticker}) 종목을 종합적으로 분석해주세요.
                    
                    [1. 현재 가격 및 기술적 지표]
                    - 현재가: {current_price:{price_fmt}} {currency}
                    - 52주 최고/최저: {high_52:{price_fmt}} {currency} / {low_52:{price_fmt}} {currency}
                    - 이동평균선 최근값: {ma_context_str}
                    
                    [2. 주요 재무 및 펀더멘털 지표]
                    - 시가총액: {format_large_number(market_cap, currency) if market_cap else 'N/A'}, Trailing PER: {trailing_pe}, Forward PER: {forward_pe}, PBR: {pb}, PEG: {fmt_flt(peg)}
                    - ROE: {fmt_pct(roe)}, 영업이익률: {fmt_pct(op_margin)}, 순이익률: {fmt_pct(net_margin)}, 부채비율: {debt_str}
                    - 매출액: {v_rev}, 영업이익: {v_op}, 당기순이익: {v_net}, 영업활동현금흐름: {v_cf_op}
                    - 배당 수익률: {fmt_pct(div_yield)}
                    
                    [3. 최신 시장 동향 및 기사 본문 요약]
                    \n{news_context}
                    
                    반드시 다음 4가지 항목을 포함하여 한국어로 명확하게 작성해주세요.
                    
                    1. 재무 상황 종합 평가
                    2. 시장 투심 및 향후 주가 흐름 예상
                    3. 상황별 대응 전략 (현재 보유자 / 신규 매수 대기자 / 매도 고려자)
                    4. 구체적인 가격 제시 (진입 추천가, 1차 목표가, 손절가)
                    
                    [출력 형식 가이드]
                    - 각 항목의 제목(1, 2, 3, 4번)은 마크다운 헤딩(## 또는 ###)을 사용하여 작성하세요.
                    - 제목 아래에는 일반 문단으로 줄글을 작성하세요.
                    
                    [분석 지침]
                    - 어조: 정중체 사용. 깔끔한 전문가 톤을 유지하세요. 이모티콘은 절대 사용하지 마세요.
                    - 균형 잡힌 차트 분석: 큰 틀에서의 가격 흐름(Price Action)과 지지/저항, 추세 등을 다각도로 고려하여 설명.
                    - 핵심 강조: 핵심 문장은 반드시 **굵은 글씨(**)**로 강조하세요. 
                    - 달러 기호 금지. 금액은 반드시 '{currency}'으로 표기할 것.
                    - 출처 표기 절대 금지: 문장 끝에 (1, 5, 20) 같은 기사 번호를 괄호로 적는 행위를 완벽하게 금지합니다.
                    
                    🚨 [최종 스코어 산출 지시사항 - 매우 중요]
                    리포트 작성을 모두 마친 후, 맨 마지막 줄에 반드시 다음 세 가지 점수를 `[SCORE: 점수]`, `[RISK: 점수]`, `[RETURN: 점수]` 형태로 적어주세요.
                    **주의: 동일한 재무 데이터, 주가 위치, 최신 동향이 주어지면 항상 동일한 점수를 도출하도록 감정을 철저히 배제하고 객관적 수치 기반으로 기계적이고 일관된 평가를 진행하세요.**

                    1. [SCORE: 0~100] (AI 투자의견)
                    - 철저한 트레이더 관점에서 현재 주가 자리의 '손익비(Risk/Reward)'와 '최신 시장 동향(호재/악재)'을 종합적으로 가장 중요하게 반영합니다.
                    - 상승 여력과 하락 리스크, 뉴스의 파급력을 계산하여 객관적인 점수를 부여하세요.
                    
                    2. [RISK: 0~100] (리스크 지수)
                    - 주식의 변동성, 재무 불안정성, 고평가 여부, 악재 등 현재 투자 시 감당해야 할 위험도를 평가합니다.
                    - 0에 가까울수록 매우 안전(저위험), 100에 가까울수록 매우 위험(고위험)을 뜻합니다.

                    3. [RETURN: 0~100] (기대수익 지수)
                    - 주식의 상승 잠재력, 미래 성장성, 저평가 매력도, 호재 등을 평가합니다.
                    - 0에 가까울수록 수익 기대감이 낮음(저수익), 100에 가까울수록 엄청난 상승 잠재력(고수익)을 뜻합니다.
                    """
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.0}
                        )
                        
                        report_text = response.text
                        
                        score_match = re.search(r'\[SCORE:\s*(\d+)\s*\]', report_text)
                        risk_match = re.search(r'\[RISK:\s*(\d+)\s*\]', report_text)
                        return_match = re.search(r'\[RETURN:\s*(\d+)\s*\]', report_text)
                        
                        final_score = None
                        risk_score = None
                        return_score = None
                        
                        if score_match:
                            final_score = int(score_match.group(1))
                            report_text = report_text.replace(score_match.group(0), "")
                        
                        if risk_match:
                            risk_score = int(risk_match.group(1))
                            report_text = report_text.replace(risk_match.group(0), "")
                            
                        if return_match:
                            return_score = int(return_match.group(1))
                            report_text = report_text.replace(return_match.group(0), "")
                            
                        st.markdown('<div class="ai-result-card">', unsafe_allow_html=True)
                        st.markdown(report_text.strip())
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        if final_score is not None:
                            final_score = max(0, min(100, final_score)) 
                            
                            if final_score <= 20: opinion_text, text_color = "강력 매도", "#007aff"
                            elif final_score <= 40: opinion_text, text_color = "매도", "#66b2ff"
                            elif final_score <= 60: opinion_text, text_color = "중립", "#555555"
                            elif final_score <= 80: opinion_text, text_color = "매수", "#ff6b6b"
                            else: opinion_text, text_color = "강력 매수", "#ff2d55"
                            
                            matrix_html = ""
                            if risk_score is not None and return_score is not None:
                                r_s = max(0, min(100, risk_score))
                                ret_s = max(0, min(100, return_score))
                                
                                matrix_html = f"""<div style="margin-top: 40px; padding-top: 20px; border-top: 1px dashed #ddd;"><h4 style="text-align: center; margin-bottom: 25px; color: #333; font-weight: 700;">리스크 대비 기대수익 매트릭스</h4><div style="position: relative; width: 100%; max-width: 450px; height: 300px; margin: 0 auto; background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); border: 1px solid #dcdcdc; border-radius: 8px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);"><div style="position: absolute; top: 50%; left: 0; width: 100%; height: 1px; background-color: #d0d0d0;"></div><div style="position: absolute; top: 0; left: 50%; width: 1px; height: 100%; background-color: #d0d0d0;"></div><div style="position: absolute; top: 10px; left: 10px; font-size: 13px; font-weight: 800; color: #ff6b6b;">저위험 고수익</div><div style="position: absolute; top: 10px; right: 10px; font-size: 13px; font-weight: 800; color: #ff2d55;">고위험 고수익</div><div style="position: absolute; bottom: 10px; left: 10px; font-size: 13px; font-weight: 800; color: #555555;">저위험 저수익</div><div style="position: absolute; bottom: 10px; right: 10px; font-size: 13px; font-weight: 800; color: #007aff;">고위험 저수익</div><div style="position: absolute; bottom: calc({ret_s}% - 12px); left: calc({r_s}% - 12px); width: 24px; height: 24px; background-color: #333; border: 3px solid white; border-radius: 50%; box-shadow: 0 3px 6px rgba(0,0,0,0.3); z-index: 10;"></div></div></div>"""
                            
                            bar_html = f"""<div style="margin-top: 30px; margin-bottom: 20px; padding: 25px 20px; border-radius: 12px; background-color: #f8f9fa; border: 1px solid #eaeaea;"><h4 style="text-align: center; margin-bottom: 30px; color: #333; font-weight: 700;">AI 투자의견: <span style="color: {text_color};">{opinion_text}</span></h4><div style="position: relative; width: 100%; height: 32px; background: linear-gradient(to right, #007aff 0%, #007aff 20%, #66b2ff 20%, #66b2ff 40%, #e0e0e0 40%, #e0e0e0 60%, #ff8080 60%, #ff8080 80%, #ff2d55 80%, #ff2d55 100%); border-radius: 16px; display: flex; box-shadow: inset 0 2px 4px rgba(0,0,0,0.15);"><div style="width: 20%; line-height: 32px; text-align: center; color: white; font-weight: 800; font-size: 13px; text-shadow: 1px 1px 2px rgba(0,0,0,0.4);">강력 매도</div><div style="width: 20%; line-height: 32px; text-align: center; color: white; font-weight: 800; font-size: 13px; text-shadow: 1px 1px 2px rgba(0,0,0,0.4);">매도</div><div style="width: 20%; line-height: 32px; text-align: center; color: #666; font-weight: 800; font-size: 13px;">중립</div><div style="width: 20%; line-height: 32px; text-align: center; color: white; font-weight: 800; font-size: 13px; text-shadow: 1px 1px 2px rgba(0,0,0,0.4);">매수</div><div style="width: 20%; line-height: 32px; text-align: center; color: white; font-weight: 800; font-size: 13px; text-shadow: 1px 1px 2px rgba(0,0,0,0.4);">강력 매수</div><div style="position: absolute; top: -28px; left: calc({final_score}% - 12px); font-size: 26px; filter: drop-shadow(0px 3px 3px rgba(0,0,0,0.5));">▼</div></div>{matrix_html}</div>"""
                            
                            clean_html = bar_html.replace('\n', '')
                            st.markdown(clean_html, unsafe_allow_html=True)
                            
                    except Exception as e:
                        st.error(f"⚠️ 에러가 발생했습니다. 잠시 후 다시 시도해주세요. ({e})")
    else:
        st.error(f"'{user_input}'에 대한 데이터를 찾을 수 없어요. 정확한 종목명이나 티커를 입력해 주세요!")
