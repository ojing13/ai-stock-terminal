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

# --- [1. 세션 상태 및 완벽한 URL 파라미터 클릭 감지 로직] ---
# 클릭 한 번으로 검색/삭제를 에러 없이 완벽하게 수행하기 위한 무적의 HTML 링크 방식입니다.
if 'search_history' not in st.session_state:
    st.session_state['search_history'] = []

default_search = ""
# URL에 search 파라미터가 있으면 검색창 기본값으로 넣고 파라미터 날리기
if "search" in st.query_params:
    default_search = st.query_params["search"]
    st.query_params.clear()

# URL에 delete 파라미터가 있으면 기록에서 지우고 파라미터 날리기
if "delete" in st.query_params:
    del_val = st.query_params["delete"]
    if del_val in st.session_state["search_history"]:
        st.session_state["search_history"].remove(del_val)
    st.query_params.clear()

# 전체 화면 넓게 쓰기 및 기본 설정
st.set_page_config(layout="wide", page_title="AI 주식 분석기")

# 최고급 웹 폰트 및 UI CSS 세팅
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
  
    * {
        font-family: 'Pretendard', 'Noto Sans KR', sans-serif !important;
    }
    h1, h2, h3 { font-weight: 700; letter-spacing: -0.5px; }
   
    @media (max-width: 768px) {
        h1 { font-size: 1.5rem !important; word-break: keep-all; }
    }

    .stTabs [data-baseweb="tab-list"] { gap: 30px; border-bottom: 1px solid #e0e0e0; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; font-size: 16px; font-weight: 600; color: #888888;
        border-bottom: 2px solid transparent !important;
    }
    .stTabs [aria-selected="true"] {
        color: #111111 !important;
        border-bottom: 2px solid #111111 !important;
        box-shadow: none !important;
    }
   
    .stButton>button { border-radius: 6px; font-weight: 600; border: 1px solid #cccccc; width: 100%; transition: 0.3s; }
    .stButton>button:hover { border-color: #007bff; color: #007bff; background-color: #f8f8f8; }
    div[data-baseweb="select"] { cursor: pointer; }
    
    .stTextInput div[data-baseweb="input"]:focus-within,
    div[data-baseweb="select"] > div:hover,
    div[data-baseweb="select"] > div:focus-within {
        border-color: #007bff !important;
        box-shadow: 0 0 0 1px #007bff !important;
    }
    div[data-baseweb="select"] input { caret-color: transparent !important; user-select: none !important; }
    
    /* === 💥 완벽 교정: 슬라이더 바 & 동그란 손잡이 모두 빨간색으로 통일 === */
    div[data-testid="stSlider"] div[role="slider"] {
        background-color: #ff4b4b !important;
        border-color: #ff4b4b !important;
        box-shadow: none !important;
    }
    div[data-testid="stSlider"] div[role="slider"]:hover,
    div[data-testid="stSlider"] div[role="slider"]:focus {
        box-shadow: 0 0 0 0.2rem rgba(255, 75, 75, 0.25) !important;
    }
    div[data-testid="stSlider"] div[style*="background-color: rgb(255, 75, 75)"],
    div[data-testid="stSlider"] div[style*="background-color: #007bff"],
    div[data-testid="stSlider"] div[style*="background: #007bff"],
    div[data-testid="stSlider"] div[style*="background-color: #ff4b4b"] {
        background-color: #ff4b4b !important;
        background: #ff4b4b !important;
    }
    [data-testid="stTickBarMin"], [data-testid="stTickBarMax"], [data-testid="stThumbValue"] {
        color: #ff4b4b !important;
        font-weight: 700 !important;
    }
    
    .fin-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; table-layout: fixed; }
    .fin-table th { text-align: left; border-bottom: 1px solid #ddd; padding: 8px; color: #555; }
    .fin-table td { border-bottom: 1px solid #eee; padding: 8px; text-align: right; vertical-align: middle; }
    .fin-table td:first-child { text-align: left; font-weight: 600; color: #333; width: 40%; word-break: break-all; }
    div[data-testid="stMetricValue"] { white-space: normal !important; word-break: break-all !important; font-size: 1.4rem !important; line-height: 1.2 !important; }

    /* 불필요한 UI 완벽 숨기기 */
    .stDeployButton { display: none !important; }
    [data-testid="stStatusWidget"] * { display: none !important; }
    [data-testid="stStatusWidget"]::after { content: "Loading..."; font-size: 14px; font-weight: 600; color: #888888; display: flex; align-items: center; padding: 5px 15px; }
</style>
""", unsafe_allow_html=True)

try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("🚨 API 키를 찾을 수 없습니다. Streamlit Cloud의 Settings -> Secrets에 'GEMINI_API_KEY'를 등록해주세요.")
    st.stop()
    
client = genai.Client(api_key=MY_API_KEY)

# 💥 철통 방어 패치: KRX 서버가 죽어도 절대 앱이 터지지 않도록 무조건 에러를 삼킵니다.
@st.cache_data
def load_krx_data():
    try:
        df = fdr.StockListing('KRX')
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
    # 실패 시 빈 깡통 프레임을 던져서 앱 다운을 완벽 방지!
    return pd.DataFrame(columns=['Code', 'Name', 'Market'])

krx_df = load_krx_data()

# 환각 완벽 차단! 검색어 정제 함수
@st.cache_data(show_spinner=False)
def get_ticker_and_korean_name(search_term):
    search_term = search_term.strip()
    search_upper = search_term.upper()
    
    if not krx_df.empty:
        match_name = krx_df[krx_df['Name'] == search_term]
        if not match_name.empty:
            code = match_name.iloc[0]['Code']
            market = match_name.iloc[0]['Market']
            ticker = f"{code}.KS" if market in ['KOSPI', 'STK'] else f"{code}.KQ"
            return ticker, search_term
        match_code = krx_df[krx_df['Code'] == search_upper]
        if not match_code.empty:
            code = match_code.iloc[0]['Code']
            market = match_code.iloc[0]['Market']
            ticker = f"{code}.KS" if market in ['KOSPI', 'STK'] else f"{code}.KQ"
            return ticker, match_code.iloc[0]['Name']
            
    quick_map = {
        "애플": ("AAPL", "애플"), "APPLE": ("AAPL", "애플"), "AAPL": ("AAPL", "애플"),
        "테슬라": ("TSLA", "테슬라"), "TESLA": ("TSLA", "테슬라"), "TSLA": ("TSLA", "테슬라"),
        "엔비디아": ("NVDA", "엔비디아"), "NVIDIA": ("NVDA", "엔비디아"), "NVDA": ("NVDA", "엔비디아"),
        "마이크로소프트": ("MSFT", "마이크로소프트"), "MICROSOFT": ("MSFT", "마이크로소프트"), "MSFT": ("MSFT", "마이크로소프트"), "마소": ("MSFT", "마이크로소프트"),
        "알파벳": ("GOOGL", "구글(Alphabet)"), "구글": ("GOOGL", "구글(Alphabet)"), "GOOGL": ("GOOGL", "구글(Alphabet)"), "GOOG": ("GOOG", "구글(Alphabet)"),
        "아마존": ("AMZN", "아마존"), "AMAZON": ("AMZN", "아마존"), "AMZN": ("AMZN", "아마존"),
        "메타": ("META", "메타"), "META": ("META", "메타"), "페이스북": ("META", "메타"),
        "넷플릭스": ("NFLX", "넷플릭스"), "NETFLIX": ("NFLX", "넷플릭스"), "NFLX": ("NFLX", "넷플릭스"),
        "TSMC": ("TSM", "TSMC"), "TSM": ("TSM", "TSMC"), "대만반도체": ("TSM", "TSMC"),
        "ASML": ("ASML", "ASML"), "ARM": ("ARM", "ARM"), "AMD": ("AMD", "AMD"),
        "TQQQ": ("TQQQ", "TQQQ (나스닥 100 3배 ETF)"),
        "SQQQ": ("SQQQ", "SQQQ (나스닥 인버스 3배 ETF)"),
        "SOXL": ("SOXL", "SOXL (반도체 3배 ETF)"),
        "SOXS": ("SOXS", "SOXS (반도체 인버스 3배 ETF)"),
        "QQQ": ("QQQ", "QQQ (나스닥 100 ETF)"),
        "SPY": ("SPY", "SPY (S&P 500 ETF)"),
        "VOO": ("VOO", "VOO (S&P 500 ETF)"),
        "IVV": ("IVV", "IVV (S&P 500 ETF)"),
        "SCHD": ("SCHD", "SCHD (미국 배당 다우존스 ETF)"),
        "JEPI": ("JEPI", "JEPI (JP모건 커버드콜 ETF)"),
        "오라클": ("ORCL", "오라클"), "ORACLE": ("ORCL", "오라클"), "ORCL": ("ORCL", "오라클"),
        "팔란티어": ("PLTR", "팔란티어"), "PLTR": ("PLTR", "팔란티어"),
        "KORU": ("KORU", "KORU (한국 MSCI 3배 ETF)"), "코루": ("KORU", "KORU (한국 MSCI 3배 ETF)"),
        "BULZ": ("BULZ", "BULZ (빅테크 3배 ETN)"), "FNGU": ("FNGU", "FNGU (빅테크 3배 ETN)"),
        "UPRO": ("UPRO", "UPRO (S&P 500 3배 ETF)"), "UDOW": ("UDOW", "UDOW (다우존스 3배 ETF)")
    }
    
    if search_term in quick_map: return quick_map[search_term]
    elif search_upper in quick_map: return quick_map[search_upper]
        
    if "(" in search_term:
        possible_ticker = search_term.split("(")[0].strip().upper()
        if possible_ticker in quick_map:
            return quick_map[possible_ticker]

    is_pure_english_short = bool(re.match(r'^[A-Za-z]{1,5}$', search_term))
    if is_pure_english_short:
        return search_upper, search_upper
            
    try:
        prompt = f"""당신은 주식/ETF 종목 식별 전문가입니다.
사용자의 검색어: "{search_term}"

[🚨 절대 규칙]
1. 사용자가 한글(예: 삼셩전자, 오랴클)이나 긴 영문 기업명(예: palantir, microsoft)으로 검색한 경우에만 올바른 주식 티커로 변환하세요.
2. 기업명/종목명은 한국어로 자연스럽게 번역하되, 잘 모르는 중소형 주식은 영문명 그대로 두세요.
3. ETF의 경우 '티커명 (테마 간략 설명)' 형태로 작성하세요.

출력 형식은 무조건 "티커|표시할종목명" 이어야 합니다. (다른 설명 절대 금지)
예시 1: "마소" 입력 시 -> MSFT|마이크로소프트
예시 2: "palantir" 입력 시 -> PLTR|팔란티어
"""
        trans_response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=prompt,
            config={"temperature": 0.0} 
        )
        result = trans_response.text.strip()
        if "|" in result:
            t, k = result.split("|")
            return t.strip().upper(), k.strip()
    except:
        pass
        
    return search_upper, search_upper

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
    high = info_high
    low = info_low
    if low <= 0 or high <= 0:
        try:
            hist = stock.history(period="2y")
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
        
        if per and (info.get('trailingPE') in [None, 'N/A', 0, '']): info['trailingPE'] = per
        if pbr and (info.get('priceToBook') in [None, 'N/A', 0, '']): info['priceToBook'] = pbr
        if div and (info.get('dividendYield') in [None, 'N/A', 0, '']): info['dividendYield'] = div / 100.0

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
                    
                    if 'ROE' in title and (info.get('returnOnEquity') in [None, 'N/A', '']):
                        info['returnOnEquity'] = recent_val / 100.0
                    elif '영업이익률' in title and (info.get('operatingMargins') in [None, 'N/A', '']):
                        info['operatingMargins'] = recent_val / 100.0
                    elif '순이익률' in title and (info.get('profitMargins') in [None, 'N/A', '']):
                        info['profitMargins'] = recent_val / 100.0
                    elif '부채비율' in title and (info.get('debtToEquity') in [None, 'N/A', '']):
                        info['debtToEquity'] = recent_val
                    elif '당좌비율' in title and (info.get('quickRatio') in [None, 'N/A', '']):
                        info['quickRatio'] = recent_val / 100.0
                    elif '유동비율' in title and (info.get('currentRatio') in [None, 'N/A', '']):
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://finviz.com/'
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

            if info.get('trailingPE') in [None, 'N/A', 0, '']:
                info['trailingPE'] = parse_finviz_val(data_dict.get('P/E', '-'))
            if info.get('forwardPE') in [None, 'N/A', 0, '']:
                info['forwardPE'] = parse_finviz_val(data_dict.get('Forward P/E', '-'))
            if info.get('priceToBook') in [None, 'N/A', 0, '']:
                info['priceToBook'] = parse_finviz_val(data_dict.get('P/B', '-'))
            if info.get('priceToSalesTrailing12Months') in [None, 'N/A', 0, '']:
                info['priceToSalesTrailing12Months'] = parse_finviz_val(data_dict.get('P/S', '-'))
            if info.get('pegRatio') in [None, 'N/A', 0, '']:
                info['pegRatio'] = parse_finviz_val(data_dict.get('PEG', '-'))
            if info.get('returnOnEquity') in [None, 'N/A', 0, '']:
                info['returnOnEquity'] = parse_finviz_val(data_dict.get('ROE', '-'), True)
            if info.get('returnOnAssets') in [None, 'N/A', 0, '']:
                info['returnOnAssets'] = parse_finviz_val(data_dict.get('ROA', '-'), True)
            if info.get('returnOnCapitalEmployed') in [None, 'N/A', 0, '']:
                info['returnOnCapitalEmployed'] = parse_finviz_val(data_dict.get('ROI', '-'), True)
            if info.get('grossMargins') in [None, 'N/A', 0, '']:
                info['grossMargins'] = parse_finviz_val(data_dict.get('Gross Margin', '-'), True)
            if info.get('operatingMargins') in [None, 'N/A', 0, '']:
                info['operatingMargins'] = parse_finviz_val(data_dict.get('Oper. Margin', '-'), True)
            if info.get('profitMargins') in [None, 'N/A', 0, '']:
                info['profitMargins'] = parse_finviz_val(data_dict.get('Profit Margin', '-'), True)
            if info.get('dividendYield') in [None, 'N/A', 0, '']:
                info['dividendYield'] = parse_finviz_val(data_dict.get('Dividend %', '-'), True)
            if info.get('debtToEquity') in [None, 'N/A', 0, '']:
                val = parse_finviz_val(data_dict.get('Debt/Eq', '-'))
                if val is not None: info['debtToEquity'] = val * 100
            if info.get('currentRatio') in [None, 'N/A', 0, '']:
                info['currentRatio'] = parse_finviz_val(data_dict.get('Current Ratio', '-'))
            if info.get('quickRatio') in [None, 'N/A', 0, '']:
                info['quickRatio'] = parse_finviz_val(data_dict.get('Quick Ratio', '-'))
    except:
        pass
    return info

def get_article_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=2, allow_redirects=True)
        soup = BeautifulSoup(res.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text().strip() for p in paragraphs if p.get_text()])
        return text[:800] if text else ""
    except:
        return ""

# ====================== 메인 ======================
st.title("웅이의 AI 주식 분석 터미널")
st.markdown("---")

col_search, _ = st.columns([1, 2])
with col_search:
    user_input = st.text_input("분석할 종목명 또는 티커 (예: 삼성전자, AAPL, KORU)", value=default_search)

ticker = None
display_name = ""
info = {}
hist_basic = pd.DataFrame()

# 1. 입력 처리 및 검색어 정제
if user_input:
    ticker, display_name = get_ticker_and_korean_name(user_input)
    is_korean_stock = ticker.endswith('.KS') or ticker.endswith('.KQ')
    
    stock = yf.Ticker(ticker)
    
    # 💥 주말 검색 먹통 방지: 한국 주식이어도 최근 5일치로 무조건 최신 가격 가져오기!
    try:
        hist_basic = stock.history(period="5d")
    except Exception:
        pass

    if not hist_basic.empty:
        try:
            info = stock.info
        except Exception:
            pass
        
        # 영문 티커를 입력해 AI를 패스한 경우 야후 파이낸스의 실제 기업명으로 덮어쓰기
        if display_name.upper() == ticker.upper() and info:
            display_name = info.get('shortName', info.get('longName', ticker))
            
        company_name = display_name
            
        # 🕒 완벽하게 정제된 진짜 이름으로 검색 기록 업데이트!
        if display_name in st.session_state['search_history']:
            st.session_state['search_history'].remove(display_name)
        st.session_state['search_history'].insert(0, display_name)
        st.session_state['search_history'] = st.session_state['search_history'][:5]

# 2. 💥 완벽한 순수 HTML/CSS 검색기록 알약(Pill) UI 렌더링
# Streamlit의 컬럼이 깨지는 현상을 100% 원천 차단하기 위해 순수 웹 기술로만 그립니다.
if st.session_state['search_history']:
    st.markdown("<div style='font-size: 13px; font-weight: 600; color: #888; margin-top: -10px; margin-bottom: 5px;'>🕒 최근 검색 기록</div>", unsafe_allow_html=True)
    
    # 여기서부터 하나의 박스 안의 버튼이 가로로 예쁘게 정렬 및 자동 줄바꿈 됩니다.
    html_str = '<div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 15px;">'
    for term in st.session_state['search_history']:
        # HTML 태그 하나하나가 모바일에서 절대 깨지지 않는 완벽한 둥근 박스를 만듭니다.
        html_str += f"""
        <div style="display: flex; align-items: center; background-color: #f8f9fa; border: 1px solid #d1d5db; border-radius: 16px; overflow: hidden; height: 30px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
            <a href="?search={term}" target="_self" style="padding: 0 6px 0 14px; color: #212529; text-decoration: none; font-size: 13px; font-weight: 600; line-height: 30px; display: block; transition: background 0.2s;" onmouseover="this.style.backgroundColor='#e9ecef'" onmouseout="this.style.backgroundColor='transparent'">{term}</a>
            <a href="?delete={term}" target="_self" style="padding: 0 12px 0 6px; color: #adb5bd; text-decoration: none; font-size: 10px; line-height: 30px; display: block; border-left: 1px solid #e9ecef; transition: color 0.2s, background 0.2s;" onmouseover="this.style.backgroundColor='#ffe3e3'; this.style.color='#ff4b4b'; this.style.fontWeight='900'" onmouseout="this.style.backgroundColor='transparent'; this.style.color='#adb5bd'; this.style.fontWeight='normal'">✖</a>
        </div>
        """
    html_str += '</div>'
    st.markdown(html_str, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 3. 메인 주식 분석 로직 렌더링
if user_input:
    if not hist_basic.empty:
        # 최근 5일치 중 가장 마지막 날짜(최신) 종가를 가져옵니다.
        current_price = hist_basic['Close'].iloc[-1]
            
        info = augment_korean_fundamentals(ticker, info)
        info = augment_us_fundamentals(ticker, info) 
            
        today_date = datetime.now().strftime("%Y년 %m월 %d일")
        
        try: fin_df = stock.financials
        except: fin_df = pd.DataFrame()
        try: bs_df = stock.balance_sheet
        except: bs_df = pd.DataFrame()
        try: cf_df = stock.cashflow
        except: cf_df = pd.DataFrame()
        
        news_list = []
        currency = "원" if is_korean_stock else "달러"
        price_fmt = ",.0f" if is_korean_stock else ",.2f"
        
        try:
            if is_korean_stock:
                rss_url = f"https://news.google.com/rss/search?q={display_name}+주식&hl=ko-KR&gl=KR&ceid=KR:ko"
            else:
                rss_url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
            response = requests.get(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
            root = ET.fromstring(response.content)
            for item in root.findall('.//item')[:100]:
                title = item.find('title').text if item.find('title') is not None else "No title"
                link = item.find('link').text if item.find('link') is not None else "#"
                desc = item.find('description').text if item.find('description') is not None else ""
                
                content = BeautifulSoup(desc, "html.parser").get_text() if desc else get_article_text(link)
                content = content[:800].replace('\n', ' ')
                news_list.append({"title": title, "link": link, "content": content})
        except:
            pass
          
        if not news_list:
            try:
                raw_news = stock.news
                for n in raw_news[:100]:
                    if isinstance(n, dict) and 'title' in n and 'link' in n:
                        link = n['link']
                        title = n['title']
                        content = n.get('summary', '') 
                        if not content:
                            content = get_article_text(link)
                        news_list.append({"title": title, "link": link, "content": content[:800].replace('\n', ' ')})
            except:
                pass
                
        news_context_list = []
        for idx, item in enumerate(news_list):
            news_context_list.append(f"[{idx+1}] 제목: {item['title']}\n본문: {item.get('content', '본문 없음')}")
        news_context = "\n\n".join(news_context_list) if news_context_list else "수집된 실시간 데이터가 없습니다."
        
        def fmt_pct(v, is_dividend=False):
            if v == 'N/A' or v is None: return 'N/A'
            try: 
                val = float(v)
                if is_dividend and val >= 1.0:
                    val = val / 100.0
                return f"{val*100:.2f}%"
            except: return 'N/A'
            
        def fmt_flt(v):
            if v is None or pd.isna(v): return 'N/A'
            try: 
                f = float(v)
                if math.isnan(f) or math.isinf(f): return 'N/A'
                return f"{f:.2f}"
            except: return 'N/A'
            
        market_cap = info.get('marketCap', 0)
        high_52 = info.get('fiftyTwoWeekHigh', 0)
        low_52 = info.get('fiftyTwoWeekLow', 0)
        
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
                    if 'Operating Income' in fin_df.index:
                        op_inc = fin_df.loc['Operating Income'].iloc[0]
                    elif 'EBIT' in fin_df.index:
                        op_inc = fin_df.loc['EBIT'].iloc[0]
                
                tot_assets = None
                cur_liab = 0
                if not bs_df.empty:
                    if 'Total Assets' in bs_df.index:
                        tot_assets = bs_df.loc['Total Assets'].iloc[0]
                    if 'Current Liabilities' in bs_df.index:
                        cur_liab = bs_df.loc['Current Liabilities'].iloc[0]
                
                if pd.notna(op_inc) and pd.notna(tot_assets) and float(tot_assets) > 0:
                    nopat = float(op_inc) * 0.75
                    invested_capital = float(tot_assets) - float(cur_liab if pd.notna(cur_liab) else 0)
                    
                    if invested_capital > 0:
                        roic = nopat / invested_capital
            except:
                pass

        gross_margin = safe_info(info, ['grossMargins', 'grossMargin'])
        net_margin = safe_info(info, ['profitMargins', 'netMargin'])
        op_margin = safe_info(info, ['operatingMargins', 'operatingMargin'])
        rev_growth = safe_info(info, ['revenueGrowth'])
        div_yield = safe_info(info, ['dividendYield'])
        
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
            col_price, col_interval = st.columns([3, 1])
            with col_price:
                st.markdown(f"### {company_name} ({ticker}) 현재가: {current_price:{price_fmt}} {currency}")
            
            with col_interval:
                interval_option = st.selectbox("차트 주기", ("일봉", "주봉", "월봉"), index=0)
            
            interval = "1d" if interval_option == "일봉" else "1wk" if interval_option == "주봉" else "1mo"
            
            history = stock.history(period="max", interval=interval)
            
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
                    
                    # 💥 한국식 차트 색상 완벽 패치: 양봉(상승) 빨간색, 음봉(하락) 파란색
                    fig.add_trace(go.Candlestick(
                        x=filtered_history.index, open=filtered_history['Open'], high=filtered_history['High'],
                        low=filtered_history['Low'], close=filtered_history['Close'],
                        increasing_line_color='#ff4b4b', increasing_fillcolor='#ff4b4b',
                        decreasing_line_color='#00b0ff', decreasing_fillcolor='#00b0ff',
                        name="가격"
                    ))

                    for w, name, color in ma_settings:
                        fig.add_trace(go.Scatter(
                            x=filtered_history.index, 
                            y=filtered_history[f'MA_{w}'], 
                            name=name,
                            line=dict(color=color, width=1.0),
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
                        title=dict(text=f"{company_name} ({ticker}) - {interval_option}", font=dict(size=22, color="white")),
                        template="plotly_dark",
                        dragmode=False, 
                        xaxis=dict(rangeslider=dict(visible=False), type="date", hoverformat="%Y-%m-%d", fixedrange=True),
                        yaxis=dict(range=[min_y, max_y], gridcolor="#333", autorange=False, fixedrange=True, tickformat=price_fmt, hoverformat=price_fmt),
                        height=520,
                        margin=dict(l=0, r=0, t=40, b=0),
                        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.6)", font=dict(color="white")),
                        hovermode="x unified",
                        clickmode="none",
                        hoverlabel=dict(font_family="Pretendard")
                    )
                    
                    st.plotly_chart(fig, use_container_width=True, config={
                        'displayModeBar': False,
                        'scrollZoom': False,
                        'showAxisDragHandles': False,
                        'doubleClick': False
                    })
                else:
                    st.warning("선택하신 기간에는 표시할 데이터가 없어요. 슬라이더를 조절해 주세요!")
            else:
                ma_context_str = "차트 데이터 부족"
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("AI 차트 추세 분석 실행"):
                with st.spinner("순수 기술적 관점에서 차트를 분석하는 중입니다..."):
                    
                    def get_formatted_history(interval_str, ma_config):
                        try:
                            temp_hist = stock.history(period="max", interval=interval_str)
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
                        except Exception:
                            return ""

                    daily_csv = get_formatted_history("1d", [(5, "", ""), (20, "", ""), (60, "", ""), (120, "", "")])
                    weekly_csv = get_formatted_history("1wk", [(13, "", ""), (26, "", ""), (52, "", "")])
                    monthly_csv = get_formatted_history("1mo", [(9, "", ""), (24, "", ""), (60, "", "")])

                    prompt = f"""종목 {company_name}({ticker})의 일봉, 주봉, 월봉 전체 가격(시가/고가/저가/종가) 및 이동평균선(MA) 데이터와 최신 시장 동향입니다.
                    
                    [최신 시장 동향 백그라운드 (참고용)]
                    {news_context}
                    
                    [일봉 차트 데이터 내역 (Open, High, Low, Close, MAs)]
                    {daily_csv}
                    
                    [주봉 차트 데이터 내역]
                    {weekly_csv}
                    
                    [월봉 차트 데이터 내역]
                    {monthly_csv}
                    
                    위 데이터를 바탕으로 실전 트레이더 수준의 깊이 있는 '기술적 분석(Technical Analysis)' 리포트를 작성해주세요. 
                    
                    [🚨 기술적 분석 핵심 지시사항 🚨]
                    1. [프라이스 액션 중심 분석]: 이동평균선(MA) 수치만 기계적으로 나열하지 마세요!! 제공된 시가(Open), 고가(High), 저가(Low), 종가(Close) 데이터를 종합하여 캔들의 형태, 고점/저점의 돌파 여부, 심리적 지지와 저항선, 변동성 등 실전적인 **'프라이스 액션(Price Action)'** 관점으로 폭넓게 분석하세요.
                    2. [정보 필터링]: 일봉, 주봉, 월봉을 모두 확인하되, 추세 설명에 꼭 필요한 유의미한 기술적 단서(특정 가격대, 매물대, 주요 돌파 지점 등)만 선별해서 자연스럽게 제시하세요.
                    3. [이동평균선 표기 규칙]: 이동평균선을 언급할 때 '13-주 이동평균선'처럼 숫자와 단위 사이에 하이픈(-)을 절대 넣지 마세요. 반드시 '13주 이동평균선', '20일 이동평균선'과 같이 올바른 한국어로 작성하세요.
                    4. 마크다운 수식 오류 방지: 가격 범위나 기간 표시 시 절대 물결표 및 달러 기호를 사용하지 마세요. (금액은 반드시 '{currency}'로 표기할 것)
                    5. [가독성 철저]: 글머리 기호(-, *, • 등 땡땡 표시)를 절대 사용하지 마세요. 소제목은 마크다운 헤딩(###)으로 작성하고, 문단과 문단 사이에는 빈 줄(Enter 2번)을 넣어 완벽하게 분리하세요.
                    6. [핵심 강조]: 분석 내용 중 핵심이 되는 중요한 단어나 문장 및 주요 지지/저항 가격은 반드시 **굵은 글씨(**)**로 강조해서 한눈에 들어오게 하세요. 단, 폰트 크기나 색상은 절대 변경하지 마세요.
                    7. [어조 설정]: 반드시 '~습니다', '~입니다' 형태의 정중체를 사용하세요.
                    8. [항목 제한]: 분석 항목은 무조건 '1. 단기적인 추세', '2. 장기적인 추세' 딱 두 가지만 출력하세요.
                    9. [뉴스 및 기사 수 언급 절대 금지]: 당신은 100개의 최신 시장 동향 기사를 배경지식으로 제공받았지만, 출력물에 '100개의 기사를 분석했습니다', '뉴스에 따르면' 등의 언급을 절대 하지 마세요. 오직 차트와 가격 움직임을 바탕으로 하되, 배경지식을 활용해 틀린 분석(환각)을 하지 않는 용도로만 조용히 참고하세요.

                    [출력 형식 가이드]
                    ### 1. 단기적인 추세 (Short-term trend)

                    단기적인 가격 흐름과 매수/매도 모멘텀을 분석합니다. 유의미할 경우에 한해 프라이스 액션(캔들 흐름), 주요 지지/저항 가격, 단기 이평선 등을 근거로 자연스럽게 제시하세요. 글머리 기호 없이 일반 문단으로 작성하세요.

                    ### 2. 장기적인 추세 (Long-term trend)

                    일/주/월봉을 아우르는 큰 흐름에서의 추세와 차트 구조를 분석합니다. 유의미할 경우에 한해 중장기 추세선, 거시적 가격대 돌파 여부 등을 언급하세요. 글머리 기호 없이 일반 문단으로 작성하세요.
                    """
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash', 
                            contents=prompt,
                            config={"temperature": 0.1}
                        )
                        st.info(response.text)
                    except Exception as e:
                        st.error(f"⚠️ 현재 구글 AI 서버에 사용자가 몰려 연결이 지연되고 있어요(503 에러). 잠시 후 다시 버튼을 눌러주세요! (자세한 에러: {e})")
          
        # --- [탭 2: 상세 재무] ---
        with tab2:
            st.subheader("1. 가치 및 안정성 지표")
            c1, c2, c3, c4 = st.columns(4)
            
            c1.metric("시가총액", format_large_number(market_cap, currency))
            c1.metric("Trailing PER", fmt_flt(trailing_pe))
            c1.metric("Forward PER", fmt_flt(forward_pe))
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
            c3.metric("배당 수익률", fmt_pct(div_yield, is_dividend=True))
            
            c4.metric("부채비율", f"{debt}%" if debt != 'N/A' else 'N/A')
            c4.metric("유동비율", fmt_flt(current_ratio))
            c4.metric("당좌비율", fmt_flt(quick_ratio))
            c4.metric("이자보상배율", interest_cov)
            c4.metric("52주 최고/최저", f"{high_52:{price_fmt}} {currency} / {low_52:{price_fmt}} {currency}")
            
            st.markdown("---")
            st.subheader("2. 재무제표 요약 (최근 결산)")
            fc1, fc2, fc3 = st.columns(3)
            
            with fc1:
                st.markdown("**손익계산서**")
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
                st.markdown("**재무상태표**")
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
                st.markdown("**현금흐름표**")
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
                    prompt = f"""종목 {company_name}({ticker})의 상세 재무 데이터 및 최신 동향 텍스트입니다.

[최신 동향 데이터]
{news_context}

[가치 및 수익성 지표]
시가총액: {format_large_number(market_cap, currency)}, Trailing PER: {trailing_pe}, Forward PER: {forward_pe}, PBR: {pb}, PSR: {fmt_flt(psr)}, PEG: {fmt_flt(peg)}, EV/EBITDA: {fmt_flt(ev_ebitda)}
ROE: {fmt_pct(roe)}, ROA: {fmt_pct(roa)}, ROIC: {fmt_pct(roic)}, 매출 성장률: {fmt_pct(rev_growth)}, 배당 수익률: {fmt_pct(div_yield, is_dividend=True)}
매출총이익률: {fmt_pct(gross_margin)}, 영업이익률: {fmt_pct(op_margin)}, 순이익률: {fmt_pct(net_margin)}
[안정성 지표]
부채비율: {debt}%, 유동비율: {fmt_flt(current_ratio)}, 당좌비율: {fmt_flt(quick_ratio)}, 이자보상배율: {interest_cov}
[손익계산서]
매출액: {v_rev}, 매출원가: {v_cogs}, 매출총이익: {v_gp}, 판매관리비: {v_sga}, 영업이익: {v_op}, 법인세차감전순이익: {v_pretax}, 당기순이익: {v_net}, 기타포괄손익: {v_oci}
[재무상태표]
자산총계: {v_tot_assets} (유동자산: {v_cur_assets} [현금성자산: {v_cash}, 매출채권: {v_receiv}, 재고자산: {v_inv}], 비유동자산: {v_ncur_assets} [유형자산: {v_tangible}, 무형자산: {v_intangible}])
부채총계: {v_tot_liab} (유동부채: {v_cur_liab} [단기차입금: {v_s_debt}], 비유동부채: {v_ncur_liab} [장기차입금: {v_l_debt}])
자본총계: {v_tot_eq} (자본금: {v_cap_stock}, 자본잉여금: {v_cap_surplus}, 이익잉여금: {v_retained})
[현금흐름표]
기초현금: {v_cf_beg}, 영업활동현금흐름: {v_cf_op}, 투자활동현금흐름: {v_cf_inv}, 재무활동현금흐름: {v_cf_fin}, 배당금지급: {v_dividend}, 기말현금: {v_cf_end}

이 모든 세부 재무 수치들을 종합적으로 분석하여 다음을 객관적으로 평가해주세요:
1. 현재 기업 가치의 고평가 또는 저평가 여부
2. 기업의 재무적 안전성 및 리스크 판단
3. 기업의 수익성 및 미래 성장 가능성

🚨 [최고급 애널리스트 수준의 입체적 분석 지침 - 반드시 엄수할 것]
- [어조 설정]: 반드시 '~습니다', '~입니다' 형태의 정중체를 사용하세요. 반말은 절대 금지하며, 지나치게 깍듯한 극존칭은 피하고 깔끔한 전문가 톤을 유지하세요.
- [가독성 철저]: 글머리 기호(-, *, • 등 땡땡 표시)를 절대 사용하지 마세요! 1, 2, 3번 각 평가 항목은 마크다운 헤딩(###)으로 크고 명확하게 달고, 세부 분석은 빈 줄(Enter 2번)로 단락을 나누어 시원시원한 일반 문단으로 작성하세요.
- [핵심 강조]: 분석 내용 중 핵심이 되는 중요한 단어나 문장은 반드시 **굵은 글씨(**)**로 강조해서 한눈에 들어오게 하세요. 단, 폰트 크기나 색상은 절대 임의로 변경하지 마세요.
- [재무 지표 중심의 서술]: 제공된 텍스트 동향은 오직 '재무 지표의 원인과 결과' 파악에만 조용히 참고하세요. 기술적 차트 이야기나 가십성 이슈는 배제하고, 철저히 '재무적 관점'에만 집중해서 평가하세요.
- [뉴스 및 기사 수 언급 절대 금지]: "제공된 데이터에 따르면", "수집된 기사에서" 등의 표현을 완벽하게 금지합니다.
- [입체적 재무 해석]: 부채비율이 높을 때 무조건 '착한 부채'로 포장하지 마세요. 이자보상배율, 현금흐름 등을 융합하여 객관적으로 판단하세요.
- 마크다운 렌더링 오류를 막기 위해 절대 물결표 및 달러 기호를 사용하지 마세요. (금액은 반드시 '{currency}'으로 표기할 것)
"""
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash', 
                            contents=prompt,
                            config={"temperature": 0.1}
                        )
                        st.info(response.text)
                    except Exception as e:
                        st.error(f"⚠️ 현재 구글 AI 서버에 사용자가 몰려 연결이 지연되고 있어요(503 에러). 잠시 후 다시 버튼을 눌러주세요! (자세한 에러: {e})")
                    
        # --- [탭 3: 최신 동향] ---
        with tab3:
            st.subheader("실시간 동향 및 투심 분석")
            st.write(f"기준일: **{today_date}**")
          
            col_news1, col_news2 = st.columns(2)
            with col_news1:
                if st.button("AI 최신 동향 브리핑"):
                    with st.spinner("최신 뉴스를 분석하는 중입니다..."):
                        prompt = f"오늘은 {today_date}입니다. 방금 시스템이 실시간으로 수집한 {company_name}({ticker})의 최신 기사 데이터입니다.\n\n[실시간 시장 동향 데이터]\n{news_context}\n\n위 데이터의 본문 내용까지 꼼꼼하게 읽고, 현재 이 기업을 둘러싼 가장 치명적이고 중요한 핵심 이슈 3가지를 도출해주세요. 각 이슈가 기업의 펀더멘털이나 향후 실적에 미칠 파급력까지 전문가의 시선으로 깊이 있게 브리핑해주세요.\n\n🚨 [지시사항]: \n- [종목 혼동 완벽 차단]: 현재 분석 타겟은 무조건 '{company_name} ({ticker})'입니다. 수집된 기사 중 티커 철자나 이름이 비슷해서 섞여 들어온 전혀 다른 기업이나 ETF의 정보가 있다면 철저하게 무시하고 버리세요. 절대 두 개 이상의 기업을 섞어서 설명하지 마세요.\n- [어조 설정]: 반드시 '~습니다', '~입니다' 형태의 정중체를 사용하세요. 반말은 절대 금지하며, 지나치게 깍듯한 극존칭은 피하고 깔끔한 전문가 톤을 유지하세요.\n- [가독성 철저]: 글머리 기호(-, *, • 등 땡땡 표시)를 절대 사용하지 마세요! 3가지 핵심 이슈는 마크다운 헤딩(###)과 숫자로 큼직하게 제목을 달고, 그 아래에 빈 줄(Enter 2번)을 띄운 뒤 일반 문단으로 길게 설명하세요.\n- [핵심 강조]: 분석 내용 중 핵심이 되는 중요한 단어나 문장은 반드시 **굵은 글씨(**)**로 강조하세요. 단, 폰트 크기나 색상은 절대 임의로 변경하지 마세요.\n- 기사의 제목이나 본문 문장을 절대(Never) 따옴표로 묶어 그대로 인용하거나 복사하지 마세요. '기사에 따르면', '뉴스에서' 같은 단어도 절대 쓰지 마세요. 여러 기사의 맥락을 하나로 꿰어내어 완전히 당신만의 언어로 소화해서 작성하세요. 물결표 및 달러 기호 사용 금지.\n- [기사 수 언급 절대 금지]: '100개의 기사를 분석했습니다' 등의 언급 금지."
                        try:
                            response = client.models.generate_content(
                                model='gemini-2.5-flash', 
                                contents=prompt,
                                config={"temperature": 0.1}
                            )
                            st.info(response.text)
                        except Exception as e:
                            st.error(f"⚠️ 현재 구글 AI 서버에 사용자가 몰려 연결이 지연되고 있어요(503 에러). 잠시 후 다시 버튼을 눌러주세요! (자세한 에러: {e})")
                        
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
                        prompt = f"오늘은 {today_date}입니다. 방금 수집된 {company_name}({ticker})의 최신 기사 데이터입니다.\n\n[실시간 시장 동향 데이터]\n{news_context}\n\n이 데이터들을 바탕으로 현재 시장 참여자들의 숨은 투자 심리(Fear & Greed)를 꿰뚫어 보고, 이것이 단기 및 중장기 주가 흐름에 어떤 압력(호재/악재)으로 작용할지 논리적으로 분석해주세요.\n\n🚨 [지시사항]: \n- [종목 혼동 완벽 차단]: 현재 분석 타겟은 무조건 '{company_name} ({ticker})'입니다. 수집된 기사 중 티커 철자나 이름이 비슷해서 섞여 들어온 전혀 다른 기업/ETF의 정보가 있다면 완전히 배제하세요.\n- [어조 설정]: 반드시 '~습니다', '~입니다' 형태의 정중체를 사용하세요. 반말은 절대 금지하며, 지나치게 깍듯한 극존칭은 피하고 깔끔한 전문가 톤을 유지하세요.\n- [가독성 철저]: 글머리 기호(-, *, • 등 땡땡 표시)를 절대 사용하지 마세요! 단기 및 중장기 분석 시 마크다운 헤딩(###)으로 소제목을 달고, 그 아래에 빈 줄을 띄워 일반 문단으로 시원하게 작성하세요.\n- [핵심 강조]: 분석 내용 중 핵심이 되는 중요한 투심이나 결론은 반드시 **굵은 글씨(**)**로 강조해서 가독성을 높이세요. 폰트 크기/색상은 절대 변경 금지.\n- 기사의 제목이나 본문 문장을 절대 그대로 인용(복사)하지 마세요. 거시경제나 산업 전반의 흐름을 엮어서 당신의 지식인 것처럼 꼼꼼하게 해석해주세요. 물결표 및 달러 기호 사용 금지.\n- [기사 수 언급 절대 금지]: '100개의 기사를 분석했습니다' 등의 직접적 언급 금지."
                        try:
                            response = client.models.generate_content(
                                model='gemini-2.5-flash', 
                                contents=prompt,
                                config={"temperature": 0.1}
                            )
                            st.info(response.text)
                        except Exception as e:
                            st.error(f"⚠️ 현재 구글 AI 서버에 사용자가 몰려 연결이 지연되고 있어요(503 에러). 잠시 후 다시 버튼을 눌러주세요! (자세한 에러: {e})")

        # --- [탭 4: 종합 리포트] ---
        with tab4:
            st.subheader("AI 퀀트 애널리스트 최종 브리핑")
            if st.button("원클릭 종합 분석 리포트 생성"):
                with st.spinner('모든 데이터를 종합하여 분석하는 중입니다...'):
                    prompt = f"""
                    오늘은 {today_date}입니다. {company_name} ({ticker}) 종목을 종합적으로 분석해주세요.
                    
                    [1. 현재 가격 및 기술적 지표]
                    - 현재가: {current_price:{price_fmt}} {currency}
                    - 52주 최고/최저: {high_52:{price_fmt}} {currency} / {low_52:{price_fmt}} {currency}
                    - 이동평균선 최근값: {ma_context_str}
                    
                    [2. 주요 재무 및 펀더멘털 지표]
                    - 시가총액: {format_large_number(market_cap, currency)}, Trailing PER: {trailing_pe}, Forward PER: {forward_pe}, PBR: {pb}, PEG: {fmt_flt(peg)}
                    - ROE: {fmt_pct(roe)}, 영업이익률: {fmt_pct(op_margin)}, 순이익률: {fmt_pct(net_margin)}, 부채비율: {debt}%
                    - 매출액: {v_rev}, 영업이익: {v_op}, 당기순이익: {v_net}, 영업활동현금흐름: {v_cf_op}
                    - 배당 수익률: {fmt_pct(div_yield, is_dividend=True)}
                    
                    [3. 최신 시장 동향 및 기사 본문 요약]
                    \n{news_context}
                    
                    반드시 다음 4가지 항목을 포함하여 최고급 애널리스트처럼 한국어로 명확하게 작성해주세요.
                    
                    1. 재무 상황 종합 평가
                    2. 시장 투심 및 향후 주가 흐름 예상
                    3. 상황별 대응 전략 (현재 보유자 / 신규 매수 대기자 / 매도 고려자)
                    4. 구체적인 가격 제시 (진입 추천가, 1차 목표가, 손절가)
                    
                    [출력 형식 가이드]
                    - 글머리 기호(-, *, • 등 땡땡 표시)는 일절 사용하지 마세요.
                    - 각 항목의 제목(1, 2, 3, 4번)은 마크다운 헤딩(## 또는 ###)을 사용하여 크게 작성하세요.
                    - 제목 아래에는 반드시 빈 줄(Enter 2번)을 띄우고 일반 문단으로 줄글을 작성하세요.
                    
                    [4번 항목 작성 예시]
                    ### 4. 구체적인 가격 제시
                    
                    진입 추천가: 000 원
                    
                    논리적 근거: 차트를 분석하여 유의미한 기술적 지표(이평선, 지지/저항선 등)나 재무적 근거가 있을 경우에만 이를 포함하여 논리적으로 작성합니다.
                    
                    1차 목표가: 000 원
                    
                    논리적 근거: ... (필요한 경우에만 특정 기술적/가격적 근거를 자연스럽게 엮어서 설명)
                    
                    🚨 [최고급 퀀트 애널리스트 수준의 입체적 분석 지침 - 반드시 엄수할 것]
                    - [종목 혼동 완벽 차단]: 현재 분석 타겟은 무조건 '{company_name} ({ticker})'입니다. 수집된 기사 중 티커 철자나 이름이 비슷해서 섞여 들어온 전혀 다른 기업(예: 의료기기 회사 등)의 정보가 있다면 철저하게 무시하세요. 분석 대상 기업 하나에만 온전히 집중하세요.
                    - [어조 설정]: 반드시 '~습니다', '~입니다' 형태의 정중체를 사용하세요. 반말은 절대 금지하며, 지나치게 깍듯한 극존칭은 피하고 깔끔한 전문가 톤을 유지하세요.
                    - [가독성 철저]: 위 형식 가이드를 완벽히 지켜서, 땡땡 표시 없이 제목과 문단 구분을 통해 마치 잘 쓰여진 신문 기사나 리포트 본문처럼 보이게 하세요.
                    - [균형 잡힌 차트 분석]: 기술적 지표를 언급할 때 이동평균선에만 집착하지 말고, 큰 틀에서의 가격 흐름(Price Action)과 지지/저항, 추세 등을 다각도로 고려하여 자연스럽게 설명하세요.
                    - [핵심 강조]: 전체 리포트에서 핵심이 되는 주요 단어나 결과 문장은 반드시 **굵은 글씨(**)**로 강조해서 핵심을 짚어주세요. 폰트 변경은 불가합니다.
                    - [직접 인용 및 작위적 표현 완벽 금지]: 리포트 내에 '뉴스', '기사', '헤드라인'이라는 단어를 아예 사용하지 마세요. 기사 문장을 절대 복사하지 마세요.
                    - [배경 지식 총동원]: 제공된 수치와 텍스트에만 갇히지 마세요. 당신이 학습한 해당 기업의 최근 거시경제(금리, 인플레 등) 환경, 산업 트렌드(AI, 반도체 등),경쟁사 동향, 대규모 투자(CapEx) 현황을 융합하여 인과관계를 설명하세요.
                    - 마크다운 렌더링 오류를 막기 위해 절대 물결표 및 달러 기호를 사용하지 마세요. (금액은 반드시 '{currency}'으로 표기할 것)
                    - [기사 수 언급 절대 금지]: '100개의 기사를 분석했습니다' 등의 언급 금지.
                    """
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash', 
                            contents=prompt,
                            config={"temperature": 0.1}
                        )
                        st.info(response.text)
                    except Exception as e:
                        st.error(f"⚠️ 현재 구글 AI 서버에 사용자가 몰려 연결이 지연되고 있어요(503 에러). 잠시 후 다시 버튼을 눌러주세요! (자세한 에러: {e})")
    else:
        st.error(f"'{user_input}'에 대한 데이터를 찾을 수 없어요. 정확한 종목명이나 티커를 입력해 주세요!")
