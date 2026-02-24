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

# 전체 화면 넓게 쓰기 및 기본 설정
st.set_page_config(layout="wide", page_title="AI 주식 분석기")

# 최고급 세련된 웹 폰트(Pretendard) 적용 및 테두리/밑줄 CSS, UI 커스텀
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
  
    * {
        font-family: 'Pretendard', 'Noto Sans KR', sans-serif !important;
    }
    h1, h2, h3 { font-weight: 700; letter-spacing: -0.5px; }
   
    /* 모바일 환경 폰트 사이즈 조절 */
    @media (max-width: 768px) {
        h1 { font-size: 1.5rem !important; word-break: keep-all; }
    }

    /* 탭(항목) 기본 디자인 */
    .stTabs [data-baseweb="tab-list"] { gap: 30px; border-bottom: 1px solid #e0e0e0; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; font-size: 16px; font-weight: 600; color: #888888;
        border-bottom: 2px solid transparent !important;
    }
   
    /* 선택된 탭 검정색 한 줄로 변경 */
    .stTabs [aria-selected="true"] {
        color: #111111 !important;
        border-bottom: 2px solid #111111 !important;
        box-shadow: none !important;
    }
   
    /* 버튼 디자인 */
    .stButton>button { border-radius: 6px; font-weight: 600; border: 1px solid #cccccc; width: 100%; transition: 0.3s; }
    .stButton>button:hover { border-color: #007bff; color: #007bff; background-color: #f8f8f8; }
    div[data-baseweb="select"] { cursor: pointer; }
    
    /* 텍스트 입력창 포커스 시 파란색 */
    .stTextInput div[data-baseweb="input"]:focus-within {
        border-color: #007bff !important;
        box-shadow: 0 0 0 1px #007bff !important;
    }
   
    /* Selectbox 테두리 파란색 */
    div[data-baseweb="select"] > div:hover,
    div[data-baseweb="select"] > div:focus-within {
        border-color: #007bff !important;
        box-shadow: 0 0 0 1px #007bff !important;
    }
    
    /* 슬라이더 파란색 테마 */
    div[data-testid="stSlider"] div[role="slider"] {
        background-color: #007bff !important;
        border-color: #007bff !important;
        box-shadow: none !important;
    }
    div[data-testid="stSlider"] div[style*="background-color: rgb(255, 75, 75)"],
    div[data-testid="stSlider"] div[style*="background-color: #ff4b4b"],
    div[data-testid="stSlider"] div[style*="background: rgb(255, 75, 75)"],
    div[data-testid="stSlider"] div[style*="background: #ff4b4b"] {
        background-color: #007bff !important;
        background: #007bff !important;
    }
    [data-testid="stTickBarMin"], [data-testid="stTickBarMax"], [data-testid="stThumbValue"] {
        color: #007bff !important;
        font-weight: 700 !important;
    }
    
    /* 재무제표 표 스타일 */
    .fin-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; table-layout: fixed; }
    .fin-table th { text-align: left; border-bottom: 1px solid #ddd; padding: 8px; color: #555; }
    .fin-table td { border-bottom: 1px solid #eee; padding: 8px; text-align: right; vertical-align: middle; }
    .fin-table td:first-child {
        text-align: left; font-weight: 600; color: #333; width: 45%; word-break: break-all;
    }
    
    div[data-testid="stMetricValue"] {
        white-space: normal !important; word-break: break-all !important; font-size: 1.4rem !important; line-height: 1.2 !important;
    }

    /* 불필요 UI 숨기기 */
    .stDeployButton { display: none !important; }
    [data-testid="stStatusWidget"] * { display: none !important; }
    [data-testid="stStatusWidget"]::after {
        content: "Loading..."; font-size: 14px; font-weight: 600; color: #888888; display: flex; align-items: center; padding: 5px 15px;
    }

</style>
""", unsafe_allow_html=True)

try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("🚨 API 키를 찾을 수 없습니다.")
    st.stop()
    
client = genai.Client(api_key=MY_API_KEY)

# ====================== 우측 상단 언어 선택 UI ======================
col_title, col_lang = st.columns([8, 2])
with col_lang:
    # 빈 공간 띄우기 (위치 조정용)
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    lang_opt = st.selectbox(
        "Language", 
        ["🇰🇷 한국어", "🇺🇸 English", "🇯🇵 日本語"], 
        label_visibility="collapsed"
    )

# 국기 이모지 제거하여 내부 로직용 언어 식별자 추출
lang = lang_opt.split(" ")[1]

# ====================== 다국어 UI 사전 ======================
ui_dict = {
    "한국어": {
        "title": "웅이의 AI 주식 분석 터미널",
        "input_label": "분석할 종목명 또는 티커 (예: 삼성전자, AAPL, 7203)",
        "tabs": ["차트 분석", "상세 재무", "최신 동향", "종합 리포트"],
        "btn_chart": "AI 차트 추세 분석 실행", "btn_fin": "AI 재무 건전성 평가 실행",
        "btn_news1": "AI 최신 동향 브리핑", "btn_news2": "AI 시장 투심 분석 실행", "btn_report": "원클릭 종합 분석 리포트 생성",
        "loading": "데이터를 분석하는 중입니다...",
        "error_nodata": "'{}'에 대한 데이터를 찾을 수 없어요. 정확한 기업명이나 티커를 입력해 주세요!",
        "t_price": "가격", "t_high": "최고", "t_low": "최저", "t_intervals": ["일봉", "주봉", "월봉"],
        "f": {
            "v_val": "1. 가치 및 안정성 지표", "v_fin": "2. 재무제표 요약 (최근 결산)",
            "mc": "시가총액", "gm": "매출총이익률", "om": "영업이익률", "nm": "순이익률", "rg": "매출 성장률", "dy": "배당 수익률",
            "de": "부채비율", "cr": "유동비율", "qr": "당좌비율", "ic": "이자보상배율", "52w": "52주 최고/최저",
            "is": "손익계산서", "rev": "매출액", "cogs": "매출원가", "gp": "매출총이익", "sga": "판매관리비", "op": "영업이익", "pre": "법인세차감전이익", "net": "당기순이익", "oci": "기타포괄손익",
            "bs": "재무상태표", "ta": "자산총계", "ca": "유동자산", "cash": "현금성자산", "rec": "매출채권", "inv": "재고자산", "nca": "비유동자산", "ppe": "유형자산", "inta": "무형자산",
            "tl": "부채총계", "cl": "유동부채", "sd": "단기차입금", "ncl": "비유동부채", "ld": "장기차입금", "te": "자본총계", "cs": "자본금", "aps": "자본잉여금", "re": "이익잉여금",
            "cf": "현금흐름표", "beg": "기초현금", "cfo": "영업현금흐름", "cfi": "투자현금흐름", "cff": "재무현금흐름", "div": "배당금 지급", "end": "기말현금"
        }
    },
    "English": {
        "title": "AI Stock Analysis Terminal",
        "input_label": "Enter Stock Name or Ticker (e.g. AAPL, TSLA, 7203)",
        "tabs": ["Chart Analysis", "Financials", "Latest Trends", "Comprehensive Report"],
        "btn_chart": "Run AI Chart Trend Analysis", "btn_fin": "Run AI Financial Health Evaluation",
        "btn_news1": "AI Latest Trend Briefing", "btn_news2": "AI Market Sentiment Analysis", "btn_report": "Generate One-Click Report",
        "loading": "Analyzing data...",
        "error_nodata": "Could not find data for '{}'. Please enter a valid stock name or ticker.",
        "t_price": "Price", "t_high": "High", "t_low": "Low", "t_intervals": ["Daily", "Weekly", "Monthly"],
        "f": {
            "v_val": "1. Valuation & Stability", "v_fin": "2. Financial Statements (Latest)",
            "mc": "Market Cap", "gm": "Gross Margin", "om": "Operating Margin", "nm": "Net Margin", "rg": "Revenue Growth", "dy": "Dividend Yield",
            "de": "Debt to Equity", "cr": "Current Ratio", "qr": "Quick Ratio", "ic": "Interest Coverage", "52w": "52W High/Low",
            "is": "Income Statement", "rev": "Revenue", "cogs": "Cost of Revenue", "gp": "Gross Profit", "sga": "SG&A", "op": "Operating Income", "pre": "Pretax Income", "net": "Net Income", "oci": "Other Comprehensive Income",
            "bs": "Balance Sheet", "ta": "Total Assets", "ca": "Current Assets", "cash": "Cash & Equivalents", "rec": "Receivables", "inv": "Inventory", "nca": "Non-Current Assets", "ppe": "Net PPE", "inta": "Intangible Assets",
            "tl": "Total Liabilities", "cl": "Current Liabilities", "sd": "Short-term Debt", "ncl": "Non-Current Liab", "ld": "Long-term Debt", "te": "Total Equity", "cs": "Capital Stock", "aps": "Paid In Capital", "re": "Retained Earnings",
            "cf": "Cash Flow", "beg": "Beginning Cash", "cfo": "Operating CF", "cfi": "Investing CF", "cff": "Financing CF", "div": "Dividends Paid", "end": "Ending Cash"
        }
    },
    "日本語": {
        "title": "AI株式分析ターミナル",
        "input_label": "銘柄名またはティッカーを入力 (例: トヨタ, AAPL, 7203)",
        "tabs": ["チャート分析", "詳細財務", "最新動向", "総合レポート"],
        "btn_chart": "AIチャートトレンド分析を実行", "btn_fin": "AI財務健全性評価を実行",
        "btn_news1": "AI最新動向ブリーフィング", "btn_news2": "AI市場心理分析を実行", "btn_report": "ワンクリック総合レポート作成",
        "loading": "データを分析しています...",
        "error_nodata": "「{}」のデータが見つかりません。正確な企業名やティッカーを入力してください。",
        "t_price": "価格", "t_high": "高値", "t_low": "安値", "t_intervals": ["日足", "週足", "月足"],
        "f": {
            "v_val": "1. 価値及び安定性指標", "v_fin": "2. 財務諸表要約 (直近)",
            "mc": "時価総額", "gm": "売上総利益率", "om": "営業利益率", "nm": "純利益率", "rg": "売上高成長率", "dy": "配当利回り",
            "de": "負債比率", "cr": "流動比率", "qr": "当座比率", "ic": "ｲﾝﾀﾚｽﾄｶﾊﾞﾚｯｼﾞﾚｼｵ", "52w": "52週高値/安値",
            "is": "損益計算書", "rev": "売上高", "cogs": "売上原価", "gp": "売上総利益", "sga": "販管費", "op": "営業利益", "pre": "税引前当期純利益", "net": "当期純利益", "oci": "その他の包括利益",
            "bs": "貸借対照表", "ta": "総資産", "ca": "流動資産", "cash": "現金及び現金同等物", "rec": "売掛金", "inv": "棚卸資産", "nca": "非流動資産", "ppe": "有形固定資産", "inta": "無形固定資産",
            "tl": "総負債", "cl": "流動負債", "sd": "短期借入金", "ncl": "非流動負債", "ld": "長期借入金", "te": "純資産", "cs": "資本金", "aps": "資本剰余金", "re": "利益剰余金",
            "cf": "キャッシュフロー計算書", "beg": "期首現金残高", "cfo": "営業CF", "cfi": "投資CF", "cff": "財務CF", "div": "配当金支払額", "end": "期末現金残高"
        }
    }
}
ui = ui_dict[lang]
f_t = ui["f"]

with col_title:
    st.title(ui["title"])
st.markdown("---")

user_input = st.text_input(ui["input_label"], "")

@st.cache_data
def load_krx_data():
    return fdr.StockListing('KRX')
krx_df = load_krx_data()

def get_ticker_symbol(search_term):
    search_term = search_term.strip()
    match = krx_df[krx_df['Name'] == search_term]
    if not match.empty:
        code = match.iloc[0]['Code']
        market = match.iloc[0]['Market']
        if market == 'KOSPI': return f"{code}.KS"
        else: return f"{code}.KQ"
    us_dict = {
        "애플": "AAPL", "테슬라": "TSLA", "엔비디아": "NVDA", "마이크로소프트": "MSFT",
        "알파벳": "GOOGL", "구글": "GOOGL", "아마존": "AMZN", "메타": "META",
        "넷플릭스": "NFLX", "마이크론": "MU", "인텔": "INTC", "AMD": "AMD"
    }
    if search_term in us_dict: return us_dict[search_term]
      
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={search_term}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        data = res.json()
        if 'quotes' in data and len(data['quotes']) > 0:
            for quote in data['quotes']:
                if quote.get('type') in ['EQUITY', 'ETF']:
                    return quote['symbol']
            return data['quotes'][0]['symbol']
    except:
        pass
    try:
        translate_prompt = f"""당신은 세계 최고의 주식 종목 식별 전문가입니다. 다음 사용자가 입력한 종목명/코드의 정확한 Yahoo Finance 공식 티커를 찾아주세요.
- 미국 주식: 티커만 (예: AAPL)
- 한국 주식: 티커.KS 또는 .KQ (예: 005930.KS)
- 일본 주식: 숫자 4자리.T (예: 7203.T, 닌텐도 -> 7974.T)
답변은 정확한 티커만 한 줄로 출력하세요.
입력값: {search_term}"""
        trans_response = client.models.generate_content(model='gemini-2.5-flash', contents=translate_prompt)
        eng_name = trans_response.text.strip()
        url_eng = f"https://query2.finance.yahoo.com/v1/finance/search?q={eng_name}"
        res_eng = requests.get(url_eng, headers=headers, timeout=5)
        data_eng = res_eng.json()
        if 'quotes' in data_eng and len(data_eng['quotes']) > 0:
            for quote in data_eng['quotes']:
                if quote.get('type') in ['EQUITY', 'ETF']:
                    return quote['symbol']
            return data_eng['quotes'][0]['symbol']
    except:
        pass
    return search_term.upper()

def safe_get_fin(df, keys, default='N/A'):
    if df is None or df.empty: return default
    for k in keys:
        if k in df.index:
            val = df.loc[k].iloc[0]
            if pd.notna(val): return f"{val:,.0f}"
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
        if v is not None and v != '' and v != 0 and str(v).upper() != 'N/A': return v
    return default

def augment_korean_fundamentals(ticker, info):
    if not (ticker.endswith('.KS') or ticker.endswith('.KQ')): return info
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
                        try: valid_vals.append(float(txt))
                        except: pass
                    
                    if not valid_vals: continue
                    recent_val = valid_vals[-1] 
                    
                    if 'ROE' in title and (info.get('returnOnEquity') in [None, 'N/A', '']): info['returnOnEquity'] = recent_val / 100.0
                    elif '영업이익률' in title and (info.get('operatingMargins') in [None, 'N/A', '']): info['operatingMargins'] = recent_val / 100.0
                    elif '순이익률' in title and (info.get('profitMargins') in [None, 'N/A', '']): info['profitMargins'] = recent_val / 100.0
                    elif '부채비율' in title and (info.get('debtToEquity') in [None, 'N/A', '']): info['debtToEquity'] = recent_val
                    elif '당좌비율' in title and (info.get('quickRatio') in [None, 'N/A', '']): info['quickRatio'] = recent_val / 100.0
                    elif '유동비율' in title and (info.get('currentRatio') in [None, 'N/A', '']): info['currentRatio'] = recent_val / 100.0
    except:
        pass 
    return info

def augment_us_fundamentals(ticker, info):
    if ticker.endswith('.KS') or ticker.endswith('.KQ') or ticker.endswith('.T'): return info
    try:
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
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
                    data_dict[cols[i].text.strip()] = cols[i+1].text.strip()
                    
            def parse_finviz_val(val_str, is_pct=False):
                if val_str == '-' or val_str == '': return None
                val_str = val_str.replace(',', '').replace('%', '')
                try:
                    num = float(val_str)
                    return num / 100.0 if is_pct else num
                except: return None

            if info.get('trailingPE') in [None, 'N/A', 0, '']: info['trailingPE'] = parse_finviz_val(data_dict.get('P/E', '-'))
            if info.get('forwardPE') in [None, 'N/A', 0, '']: info['forwardPE'] = parse_finviz_val(data_dict.get('Forward P/E', '-'))
            if info.get('priceToBook') in [None, 'N/A', 0, '']: info['priceToBook'] = parse_finviz_val(data_dict.get('P/B', '-'))
            if info.get('priceToSalesTrailing12Months') in [None, 'N/A', 0, '']: info['priceToSalesTrailing12Months'] = parse_finviz_val(data_dict.get('P/S', '-'))
            if info.get('pegRatio') in [None, 'N/A', 0, '']: info['pegRatio'] = parse_finviz_val(data_dict.get('PEG', '-'))
            if info.get('returnOnEquity') in [None, 'N/A', 0, '']: info['returnOnEquity'] = parse_finviz_val(data_dict.get('ROE', '-'), True)
            if info.get('returnOnAssets') in [None, 'N/A', 0, '']: info['returnOnAssets'] = parse_finviz_val(data_dict.get('ROA', '-'), True)
            if info.get('returnOnCapitalEmployed') in [None, 'N/A', 0, '']: info['returnOnCapitalEmployed'] = parse_finviz_val(data_dict.get('ROI', '-'), True)
            if info.get('grossMargins') in [None, 'N/A', 0, '']: info['grossMargins'] = parse_finviz_val(data_dict.get('Gross Margin', '-'), True)
            if info.get('operatingMargins') in [None, 'N/A', 0, '']: info['operatingMargins'] = parse_finviz_val(data_dict.get('Oper. Margin', '-'), True)
            if info.get('profitMargins') in [None, 'N/A', 0, '']: info['profitMargins'] = parse_finviz_val(data_dict.get('Profit Margin', '-'), True)
            if info.get('dividendYield') in [None, 'N/A', 0, '']: info['dividendYield'] = parse_finviz_val(data_dict.get('Dividend %', '-'), True)
            if info.get('debtToEquity') in [None, 'N/A', 0, '']: 
                val = parse_finviz_val(data_dict.get('Debt/Eq', '-'))
                if val is not None: info['debtToEquity'] = val * 100
            if info.get('currentRatio') in [None, 'N/A', 0, '']: info['currentRatio'] = parse_finviz_val(data_dict.get('Current Ratio', '-'))
            if info.get('quickRatio') in [None, 'N/A', 0, '']: info['quickRatio'] = parse_finviz_val(data_dict.get('Quick Ratio', '-'))
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

# 메인 프로세스 (검색어 입력 시에만 실행, 에러창도 빈값일 땐 안 띄움)
if user_input:
    ticker = get_ticker_symbol(user_input)
    stock = yf.Ticker(ticker)
    hist_basic = stock.history(period="1d")
  
    if not hist_basic.empty:
        current_price = hist_basic['Close'].iloc[-1]
        info = stock.info
        info = augment_korean_fundamentals(ticker, info)
        info = augment_us_fundamentals(ticker, info) 
        
        today_date = datetime.now().strftime("%Y-%m-%d")
       
        try: fin_df = stock.financials
        except: fin_df = pd.DataFrame()
        try: bs_df = stock.balance_sheet
        except: bs_df = pd.DataFrame()
        try: cf_df = stock.cashflow
        except: cf_df = pd.DataFrame()
       
        news_list = []
        is_korean_stock = ticker.endswith('.KS') or ticker.endswith('.KQ')
        is_japanese_stock = ticker.endswith('.T')
        
        # 언어 및 주식 종류에 따른 통화 설정
        if lang == "한국어":
            if is_korean_stock: currency = "원"
            elif is_japanese_stock: currency = "엔"
            else: currency = "달러"
        elif lang == "English":
            if is_korean_stock: currency = "KRW"
            elif is_japanese_stock: currency = "JPY"
            else: currency = "USD"
        else:
            if is_korean_stock: currency = "ウォン"
            elif is_japanese_stock: currency = "円"
            else: currency = "ドル"
            
        price_fmt = ",.0f" if (is_korean_stock or is_japanese_stock) else ",.2f"
        
        # 뉴스 수집
        try:
            if is_korean_stock: rss_url = f"https://news.google.com/rss/search?q={user_input}+주식&hl=ko-KR&gl=KR&ceid=KR:ko"
            elif is_japanese_stock: rss_url = f"https://news.google.com/rss/search?q={user_input}+株&hl=ja&gl=JP&ceid=JP:ja"
            else: rss_url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
            
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
                for n in stock.news[:100]:
                    if isinstance(n, dict) and 'title' in n and 'link' in n:
                        link = n['link']
                        content = n.get('summary', '') or get_article_text(link)
                        news_list.append({"title": n['title'], "link": link, "content": content[:800].replace('\n', ' ')})
            except: pass
                
        news_context_list = [f"[{i+1}] Title: {x['title']}\nContent: {x.get('content', '')}" for i, x in enumerate(news_list)]
        news_context = "\n\n".join(news_context_list) if news_context_list else "No data."
        
        def fmt_pct(v, is_dividend=False):
            if v == 'N/A' or v is None: return 'N/A'
            try: 
                val = float(v)
                if is_dividend and val >= 1.0: val = val / 100.0
                return f"{val*100:.2f}%"
            except: return 'N/A'
            
        def fmt_flt(v):
            if v is None or pd.isna(v): return 'N/A'
            try: 
                f = float(v)
                return 'N/A' if math.isnan(f) or math.isinf(f) else f"{f:.2f}"
            except: return 'N/A'
            
        market_cap = info.get('marketCap', 0)
        high_52, low_52 = get_52w_high_low(stock, info.get('fiftyTwoWeekHigh', 0), info.get('fiftyTwoWeekLow', 0))
        
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
                op_inc = fin_df.loc['Operating Income'].iloc[0] if 'Operating Income' in fin_df.index else (fin_df.loc['EBIT'].iloc[0] if 'EBIT' in fin_df.index else None)
                tot_assets = bs_df.loc['Total Assets'].iloc[0] if 'Total Assets' in bs_df.index else None
                cur_liab = bs_df.loc['Current Liabilities'].iloc[0] if 'Current Liabilities' in bs_df.index else 0
                
                if pd.notna(op_inc) and pd.notna(tot_assets) and float(tot_assets) > 0:
                    invested_capital = float(tot_assets) - float(cur_liab if pd.notna(cur_liab) else 0)
                    if invested_capital > 0: roic = (float(op_inc) * 0.75) / invested_capital
            except: pass

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
            interest_cov = 'N/A' if pd.isna(op_inc_val) or pd.isna(int_exp_val) or int_exp_val == 0 else fmt_flt(abs(op_inc_val / int_exp_val))
        except: interest_cov = 'N/A'
        
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

        tab1, tab2, tab3, tab4 = st.tabs(ui["tabs"])
        
        # --- [탭 1: 차트 분석] ---
        with tab1:
            col_price, col_interval = st.columns([3, 1])
            with col_price:
                st.markdown(f"### {user_input} ({ticker}) : {current_price:{price_fmt}} {currency}")
            
            with col_interval:
                interval_option = st.selectbox("Interval", ui["t_intervals"], index=0, label_visibility="collapsed")
            
            interval_map = {ui["t_intervals"][0]: "1d", ui["t_intervals"][1]: "1wk", ui["t_intervals"][2]: "1mo"}
            interval = interval_map[interval_option]
            
            history = stock.history(period="max", interval=interval)
            history = history[(history['Low'] > 0) & (history['High'] > 0) & (history['Close'] > 0)]
            
            raw_min_date = history.index.min().to_pydatetime().date()
            min_date = raw_min_date.replace(day=1) 
            max_date = datetime.now().date()       
            ideal_start_date = max_date - timedelta(days=365*10)
            default_start = ideal_start_date if ideal_start_date > min_date else min_date
            
            selected_start, selected_end = st.slider("Date", min_value=min_date, max_value=max_date, value=(default_start, max_date), format="YYYY-MM-DD", label_visibility="collapsed", key=f"slider_{ticker}")
            mask = (history.index.date >= selected_start) & (history.index.date <= selected_end)
            
            if interval == "1d": ma_settings = [(5, "MA1(5)", "#00b0ff"), (20, "MA2(20)", "#ff9100"), (60, "MA3(60)", "#ff4081"), (120, "MA4(120)", "#aa00ff")]
            elif interval == "1wk": ma_settings = [(13, "MA1(13)", "#00b0ff"), (26, "MA2(26)", "#ff9100"), (52, "MA3(52)", "#ff4081")]
            else: ma_settings = [(9, "MA1(9)", "#00b0ff"), (24, "MA2(24)", "#ff9100"), (60, "MA3(60)", "#ff4081")]
                
            for w, name, color in ma_settings:
                history[f'MA_{w}'] = history['Close'].rolling(window=w).mean()

            filtered_history = history.loc[mask].copy()
            ma_context_str = "No Data"

            if not filtered_history.empty:
                price_min = filtered_history['Low'].min()
                price_max = filtered_history['High'].max()
                min_idx = filtered_history['Low'].idxmin()
                max_idx = filtered_history['High'].idxmax()
                
                ma_last_vals_str = []
                for w, name, color in ma_settings:
                    val = filtered_history[f'MA_{w}'].iloc[-1]
                    val_str = f"{val:{price_fmt}} {currency}" if pd.notna(val) else "N/A"
                    ma_last_vals_str.append(f"{name}: {val_str}")
                ma_context_str = " / ".join(ma_last_vals_str)
                
                padding = (price_max - price_min) * 0.1 if price_max != price_min else price_max * 0.1
                
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=filtered_history.index, open=filtered_history['Open'], high=filtered_history['High'],
                    low=filtered_history['Low'], close=filtered_history['Close'],
                    increasing_line_color='#00ff9d', decreasing_line_color='#ff2d55', name=ui["t_price"]
                ))

                for w, name, color in ma_settings:
                    fig.add_trace(go.Scatter(
                        x=filtered_history.index, y=filtered_history[f'MA_{w}'], name=name,
                        line=dict(color=color, width=1.0), hovertemplate=f'%{{y:{price_fmt}}}' 
                    ))
                
                fig.add_annotation(x=max_idx, y=price_max, text=f"{ui['t_high']}: {price_max:{price_fmt}} {currency}", showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#ff2d55", ax=0, ay=-35, font=dict(color="white", size=13, family="Pretendard"), bgcolor="#ff2d55", bordercolor="#ff2d55", borderwidth=1, borderpad=4, opacity=0.9)
                fig.add_annotation(x=min_idx, y=price_min, text=f"{ui['t_low']}: {price_min:{price_fmt}} {currency}", showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#00b0ff", ax=0, ay=35, font=dict(color="white", size=13, family="Pretendard"), bgcolor="#00b0ff", bordercolor="#00b0ff", borderwidth=1, borderpad=4, opacity=0.9)
                
                fig.update_layout(
                    title=dict(text=f"{user_input} ({ticker})", font=dict(size=22, color="white")), template="plotly_dark", dragmode=False, 
                    xaxis=dict(rangeslider=dict(visible=False), type="date", hoverformat="%Y-%m-%d", fixedrange=True),
                    yaxis=dict(range=[price_min - padding, price_max + padding], gridcolor="#333", autorange=False, fixedrange=True, tickformat=price_fmt, hoverformat=price_fmt),
                    height=520, margin=dict(l=0, r=0, t=40, b=0), legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.6)", font=dict(color="white")), hovermode="x unified", clickmode="none", hoverlabel=dict(font_family="Pretendard")
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False, 'showAxisDragHandles': False, 'doubleClick': False})
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(ui["btn_chart"]):
                with st.spinner(ui["loading"]):
                    def get_formatted_history(interval_str, ma_config):
                        temp_hist = stock.history(period="max", interval=interval_str)
                        temp_hist = temp_hist[(temp_hist['Low'] > 0) & (temp_hist['High'] > 0) & (temp_hist['Close'] > 0)].copy()
                        for w, _, _ in ma_config: temp_hist[f'MA_{w}'] = temp_hist['Close'].rolling(window=w).mean()
                        temp_filtered = temp_hist.loc[(temp_hist.index.date >= selected_start) & (temp_hist.index.date <= selected_end)].copy()
                        df_export = temp_filtered[['Open', 'High', 'Low', 'Close'] + [f'MA_{w}' for w, _, _ in ma_config]].copy()
                        df_export.index = df_export.index.strftime('%Y-%m-%d')
                        return df_export.tail(150).round(2).to_csv(header=True)

                    daily_csv = get_formatted_history("1d", [(5, "", ""), (20, "", ""), (60, "", ""), (120, "", "")])
                    weekly_csv = get_formatted_history("1wk", [(13, "", ""), (26, "", ""), (52, "", "")])
                    monthly_csv = get_formatted_history("1mo", [(9, "", ""), (24, "", ""), (60, "", "")])

                    prompt = f"""종목 {ticker}의 일봉, 주봉, 월봉 전체 가격(시가/고가/저가/종가) 및 이동평균선(MA) 데이터와 최신 시장 동향입니다.
[최신 시장 동향 백그라운드 (참고용)]\n{news_context}
[일봉 차트 데이터 내역]\n{daily_csv}
[주봉 차트 데이터 내역]\n{weekly_csv}
[월봉 차트 데이터 내역]\n{monthly_csv}
위 데이터를 바탕으로 실전 트레이더 수준의 깊이 있는 '기술적 분석(Technical Analysis)' 리포트를 작성해주세요. 
[🚨 기술적 분석 핵심 지시사항 🚨]
1. [프라이스 액션 중심 분석]: 시가, 고가, 저가, 종가 데이터를 종합하여 캔들 형태, 돌파 여부 등 실전적인 **'프라이스 액션(Price Action)'** 관점으로 폭넓게 분석하세요.
2. [이동평균선 표기 규칙]: 이동평균선을 언급할 때 기계적인 수치 나열은 금지하며 자연스럽게 작성하세요.
3. 마크다운 수식 오류 방지: 가격 범위나 기간 표시 시 절대 물결표 및 달러 기호를 사용하지 마세요. (금액은 반드시 '{currency}'로 표기할 것)
4. [가독성 철저]: 글머리 기호(-, *, • 등)를 절대 사용하지 마세요. 소제목은 마크다운 헤딩(###)으로 작성하고, 문단 사이에는 빈 줄(Enter 2번)을 넣으세요.
5. [핵심 강조]: 핵심이 되는 문장 및 가격은 반드시 **굵은 글씨(**)**로 강조하세요. 폰트 크기/색상 변경 금지.
6. [어조 설정]: 반드시 '~습니다', '~입니다' 형태의 정중체를 사용하세요.
7. [항목 제한]: 분석 항목은 무조건 '1. 단기적인 추세', '2. 장기적인 추세' 두 가지만 출력하세요.
8. [뉴스 수 언급 금지]: '100개의 기사', '뉴스에 따르면' 등 수집된 기사 자체에 대한 언급을 절대 하지 마세요. 

🚨 [언어 출력 필수 지시사항]
반드시 모든 답변 내용을 **{lang}**로만 번역 및 작성하여 출력하세요!! (제목 포맷 유지: 1. 단기적인 추세 / 2. 장기적인 추세의 번역된 형태)
"""
                    try:
                        st.info(client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.1}).text)
                    except Exception as e: st.error(f"Error: {e}")
          
        # --- [탭 2: 상세 재무] ---
        with tab2:
            st.subheader(f_t["v_val"])
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(f_t["mc"], format_large_number(market_cap, currency))
            c1.metric("Trailing PER", fmt_flt(trailing_pe))
            c1.metric("Forward PER", fmt_flt(forward_pe))
            c1.metric("PBR", fmt_flt(pb))
            c1.metric("PSR", fmt_flt(psr))
            c2.metric("PEG", fmt_flt(peg))
            c2.metric("EV/EBITDA", fmt_flt(ev_ebitda))
            c2.metric("ROE", fmt_pct(roe))
            c2.metric("ROA", fmt_pct(roa))
            c2.metric("ROIC", fmt_pct(roic))
            c3.metric(f_t["gm"], fmt_pct(gross_margin))
            c3.metric(f_t["om"], fmt_pct(op_margin))
            c3.metric(f_t["nm"], fmt_pct(net_margin))
            c3.metric(f_t["rg"], fmt_pct(rev_growth))
            c3.metric(f_t["dy"], fmt_pct(div_yield, is_dividend=True))
            c4.metric(f_t["de"], f"{debt}%" if debt != 'N/A' else 'N/A')
            c4.metric(f_t["cr"], fmt_flt(current_ratio))
            c4.metric(f_t["qr"], fmt_flt(quick_ratio))
            c4.metric(f_t["ic"], interest_cov)
            c4.metric(f_t["52w"], f"{high_52:{price_fmt}} / {low_52:{price_fmt}} {currency}")
            
            st.markdown("---")
            st.subheader(f_t["v_fin"])
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                st.markdown(f"**{f_t['is']}**")
                st.markdown(f"""<table class="fin-table">
                <tr><td>{f_t['rev']}</td><td>{v_rev}</td></tr><tr><td>{f_t['cogs']}</td><td>{v_cogs}</td></tr>
                <tr><td>{f_t['gp']}</td><td>{v_gp}</td></tr><tr><td>{f_t['sga']}</td><td>{v_sga}</td></tr>
                <tr><td>{f_t['op']}</td><td>{v_op}</td></tr><tr><td>{f_t['pre']}</td><td>{v_pretax}</td></tr>
                <tr><td>{f_t['net']}</td><td>{v_net}</td></tr><tr><td>{f_t['oci']}</td><td>{v_oci}</td></tr></table>""", unsafe_allow_html=True)
            with fc2:
                st.markdown(f"**{f_t['bs']}**")
                st.markdown(f"""<table class="fin-table">
                <tr><td>{f_t['ta']}</td><td>{v_tot_assets}</td></tr><tr><td>{f_t['ca']}</td><td>{v_cur_assets}</td></tr>
                <tr><td>{f_t['cash']}</td><td>{v_cash}</td></tr><tr><td>{f_t['rec']}</td><td>{v_receiv}</td></tr>
                <tr><td>{f_t['inv']}</td><td>{v_inv}</td></tr><tr><td>{f_t['nca']}</td><td>{v_ncur_assets}</td></tr>
                <tr><td>{f_t['ppe']}</td><td>{v_tangible}</td></tr><tr><td>{f_t['inta']}</td><td>{v_intangible}</td></tr>
                <tr><td>{f_t['tl']}</td><td>{v_tot_liab}</td></tr><tr><td>{f_t['cl']}</td><td>{v_cur_liab}</td></tr>
                <tr><td>{f_t['sd']}</td><td>{v_s_debt}</td></tr><tr><td>{f_t['ncl']}</td><td>{v_ncur_liab}</td></tr>
                <tr><td>{f_t['ld']}</td><td>{v_l_debt}</td></tr><tr><td>{f_t['te']}</td><td>{v_tot_eq}</td></tr>
                <tr><td>{f_t['cs']}</td><td>{v_cap_stock}</td></tr><tr><td>{f_t['aps']}</td><td>{v_cap_surplus}</td></tr>
                <tr><td>{f_t['re']}</td><td>{v_retained}</td></tr></table>""", unsafe_allow_html=True)
            with fc3:
                st.markdown(f"**{f_t['cf']}**")
                st.markdown(f"""<table class="fin-table">
                <tr><td>{f_t['beg']}</td><td>{v_cf_beg}</td></tr><tr><td>{f_t['cfo']}</td><td>{v_cf_op}</td></tr>
                <tr><td>{f_t['cfi']}</td><td>{v_cf_inv}</td></tr><tr><td>{f_t['cff']}</td><td>{v_cf_fin}</td></tr>
                <tr><td>{f_t['div']}</td><td>{v_dividend}</td></tr><tr><td>{f_t['end']}</td><td>{v_cf_end}</td></tr></table>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(ui["btn_fin"]):
                with st.spinner(ui["loading"]):
                    prompt = f"""종목 {ticker}의 상세 재무 데이터 및 최신 동향 텍스트입니다.
[최신 동향 데이터]\n{news_context}
(재무 지표 수치는 화면에 표시된 표를 기준으로 종합 평가 진행)

1. 현재 기업 가치의 고평가 또는 저평가 여부
2. 기업의 재무적 안전성 및 리스크 판단
3. 기업의 수익성 및 미래 성장 가능성

🚨 [분석 지침]
- [어조 설정]: 반드시 '~습니다', '~입니다' 형태의 정중체를 사용하세요.
- [가독성 철저]: 글머리 기호(-, *, • 등)를 절대 사용하지 마세요! 각 항목은 마크다운 헤딩(###)으로 달고 빈 줄(Enter 2번)로 단락을 나누세요.
- [핵심 강조]: 중요한 단어나 문장은 반드시 **굵은 글씨(**)**로 강조하세요.
- [뉴스 및 기사 수 언급 절대 금지]: "제공된 데이터에 따르면", "수집된 기사/뉴스에서", "100개의 기사를 분석했습니다" 등의 표현 금지.
- 마크다운 렌더링 오류를 막기 위해 절대 물결표 및 달러 기호를 사용하지 마세요. (금액은 반드시 '{currency}'으로 표기할 것)

🚨 [언어 출력 필수 지시사항]
반드시 모든 답변 내용을 **{lang}**로만 번역 및 작성하여 출력하세요!!
"""
                    try:
                        st.info(client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.1}).text)
                    except Exception as e: st.error(f"Error: {e}")
                    
        # --- [탭 3: 최신 동향] ---
        with tab3:
            col_news1, col_news2 = st.columns(2)
            with col_news1:
                if st.button(ui["btn_news1"]):
                    with st.spinner(ui["loading"]):
                        prompt = f"오늘은 {today_date}입니다. 방금 수집한 {ticker}의 최신 기사 데이터입니다.\n[데이터]\n{news_context}\n\n핵심 이슈 3가지를 도출해주세요.\n\n🚨 [지시사항]: \n- [어조]: 정중체(~습니다, ~입니다) 사용.\n- [가독성]: 글머리 기호 금지. 3가지 이슈는 마크다운 헤딩(###)과 숫자로 제목을 달고 빈 줄로 띄어 작성.\n- [핵심 강조]: 중요 단어는 **굵은 글씨** 강조.\n- 기사 직접 인용 금지, 기사 수(100개 등) 언급 금지.\n- 물결표 및 달러 기호 사용 금지.\n\n🚨 [언어 출력 필수 지시사항]\n반드시 모든 답변을 **{lang}**로만 번역하여 출력하세요!!"
                        try: st.info(client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.1}).text)
                        except Exception as e: st.error(f"Error: {e}")
                        st.markdown("---")
                        if news_list:
                            for item in news_list[:10]: st.markdown(f"• <a href='{item['link']}' target='_blank'>{item['title']}</a>", unsafe_allow_html=True)
            with col_news2:
                if st.button(ui["btn_news2"]):
                    with st.spinner(ui["loading"]):
                        prompt = f"오늘은 {today_date}입니다. 방금 수집된 {ticker} 기사 데이터입니다.\n[데이터]\n{news_context}\n\n시장 참여자들의 숨은 투자 심리(Fear & Greed)를 꿰뚫어 보고 단기 및 중장기 주가 흐름 분석.\n\n🚨 [지시사항]: \n- [어조]: 정중체.\n- [가독성]: 글머리 기호 금지, 마크다운 헤딩(###) 사용.\n- [강조]: 결론이나 중요 투심은 **굵은 글씨**.\n- 기사 직접 인용 및 수량 언급 금지. 물결표/달러 금지.\n\n🚨 [언어 출력 필수 지시사항]\n반드시 모든 답변을 **{lang}**로만 번역하여 출력하세요!!"
                        try: st.info(client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.1}).text)
                        except Exception as e: st.error(f"Error: {e}")

        # --- [탭 4: 종합 리포트] ---
        with tab4:
            if st.button(ui["btn_report"]):
                with st.spinner(ui["loading"]):
                    prompt = f"""오늘은 {today_date}입니다. {ticker} 종목 종합 분석.
[데이터 요약] 현재가: {current_price:{price_fmt}} {currency}, 시총: {market_cap}, PER: {trailing_pe}, PBR: {pb}
[최신 뉴스]\n{news_context}

다음 4가지 항목을 포함하여 최고급 애널리스트처럼 작성하세요.
1. 재무 상황 종합 평가
2. 시장 투심 및 향후 주가 흐름 예상
3. 상황별 대응 전략 (현재 보유자 / 신규 매수 대기자 / 매도 고려자)
4. 구체적인 가격 제시 (진입 추천가, 1차 목표가, 손절가)

[형식]
- 글머리 기호(-, *, • 등) 절대 금지.
- 항목 제목은 마크다운 헤딩(###) 사용. 빈 줄(Enter 2번)로 단락 분리.
- 정중체 사용. 물결표/달러 기호 금지(금액은 {currency} 표기). 뉴스 기사 수 언급 금지.

🚨 [언어 출력 필수 지시사항]
반드시 모든 답변 내용을 **{lang}**로만 번역하여 출력하세요!!
"""
                    try: st.info(client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.1}).text)
                    except Exception as e: st.error(f"Error: {e}")
    else:
        # user_input이 있는데 데이터 조회가 안될 때만 에러 팝업
        st.error(ui["error_nodata"].format(user_input))
