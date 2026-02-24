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
import re # 숫자 코드 정규식을 위해 추가

# 전체 화면 넓게 쓰기 및 기본 설정
st.set_page_config(layout="wide", page_title="AI Stock Terminal")

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
        /* 모바일에서 언어 선택기 간격 띄우기 */
        .mobile-lang-spacer { margin-top: 10px; }
    }

    /* 탭(항목) 기본 디자인 */
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
   
    /* 버튼 디자인 */
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
    
    /* 슬라이더 파란색 테마 */
    div[data-testid="stSlider"] div[role="slider"] { background-color: #007bff !important; border-color: #007bff !important; box-shadow: none !important; }
    div[data-testid="stSlider"] div[style*="background-color: rgb(255, 75, 75)"],
    div[data-testid="stSlider"] div[style*="background-color: #ff4b4b"],
    div[data-testid="stSlider"] div[style*="background: rgb(255, 75, 75)"],
    div[data-testid="stSlider"] div[style*="background: #ff4b4b"] { background-color: #007bff !important; background: #007bff !important; }
    [data-testid="stTickBarMin"], [data-testid="stTickBarMax"], [data-testid="stThumbValue"] { color: #007bff !important; font-weight: 700 !important; }
    
    /* 재무제표 표 스타일 */
    .fin-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; table-layout: fixed; }
    .fin-table th { text-align: left; border-bottom: 1px solid #ddd; padding: 8px; color: #555; }
    .fin-table td { border-bottom: 1px solid #eee; padding: 8px; text-align: right; vertical-align: middle; }
    .fin-table td:first-child { text-align: left; font-weight: 600; color: #333; width: 40%; word-break: break-all; }
    
    div[data-testid="stMetricValue"] { white-space: normal !important; word-break: break-all !important; font-size: 1.4rem !important; line-height: 1.2 !important; }

    .stDeployButton { display: none !important; }
    [data-testid="stStatusWidget"] * { display: none !important; }
    [data-testid="stStatusWidget"]::after { content: "Loading..."; font-size: 14px; font-weight: 600; color: #888888; display: flex; align-items: center; padding: 5px 15px; }

</style>
""", unsafe_allow_html=True)

# 다국어 지원 사전 (Dictionary)
lang_dict = {
    "한국어": {
        "title": "웅이의 AI 주식 분석 터미널",
        "search_label": "종목명 또는 티커 (한국/미국/일본 4자리 코드)",
        "tabs": ["차트 분석", "상세 재무", "최신 동향", "종합 리포트"],
        "cur_price_label": "현재가",
        "chart_interval": "차트 주기",
        "intervals": ["일봉", "주봉", "월봉"],
        "date_range": "조회 기간 설정",
        "btn_chart": "AI 차트 추세 분석 실행",
        "btn_fin": "AI 재무 건전성 평가 실행",
        "btn_news1": "AI 최신 동향 브리핑",
        "btn_news2": "AI 시장 투심 분석 실행",
        "btn_report": "원클릭 종합 분석 리포트 생성",
        "loading_chart": "순수 기술적 관점에서 차트를 분석하는 중입니다...",
        "loading_fin": "재무 데이터를 분석하는 중입니다...",
        "loading_news": "최신 뉴스를 분석하는 중입니다...",
        "loading_sentiment": "시장 참여자들의 투심을 분석하는 중입니다...",
        "loading_report": "모든 데이터를 종합하여 분석하는 중입니다...",
        "err_503": "⚠️ 현재 구글 AI 서버에 사용자가 몰려 연결이 지연되고 있어요(503 에러). 잠시 후 다시 버튼을 눌러주세요!",
        "err_notfound": "'{}'에 대한 데이터를 찾을 수 없어요. 정확한 기업명이나 코드를 입력해 주세요!",
        "tone_prompt": "반드시 '~습니다', '~입니다' 형태의 정중한 한국어로 작성하세요.",
        "lang_prompt": "한국어",
        "sub_fin1": "1. 가치 및 안정성 지표",
        "sub_fin2": "2. 재무제표 요약 (최근 결산)",
        "sub_news": "실시간 동향 및 투심 분석",
        "sub_report": "AI 퀀트 애널리스트 최종 브리핑",
        "date_base": "기준일",
        "news_ref": "**📌 참고한 실시간 뉴스 원문 (클릭해서 바로 이동)**",
        "no_news_link": "뉴스 링크를 불러올 수 없습니다.",
        "currency_kr": "원", "currency_us": "달러", "currency_jp": "엔",
        "metrics": ["시가총액", "Trailing PER", "Forward PER", "PBR", "PSR", "PEG", "EV/EBITDA", "ROE", "ROA", "ROIC", "매출총이익률", "영업이익률", "순이익률", "매출 성장률", "배당 수익률", "부채비율", "유동비율", "당좌비율", "이자보상배율", "52주 최고/최저"],
        "tables": ["손익계산서", "매출액", "매출원가", "매출총이익", "판매관리비", "영업이익", "법인세차감전순이익", "당기순이익", "기타포괄손익", "재무상태표", "자산총계", "유동자산", "현금및현금성자산", "매출채권", "재고자산", "비유동자산", "유형자산", "무형자산", "부채총계", "유동부채", "단기차입금", "비유동부채", "장기차입금", "자본총계", "자본금", "자본잉여금", "이익잉여금", "현금흐름표", "기초현금", "영업활동현금흐름", "투자활동현금흐름", "재무활동현금흐름", "배당금 지급", "기말현금"]
    },
    "English": {
        "title": "AI Stock Analysis Terminal",
        "search_label": "Enter Stock Name or Ticker (US/KR/JP code)",
        "tabs": ["Chart Analysis", "Financials", "Latest Trends", "Comprehensive Report"],
        "cur_price_label": "Current Price",
        "chart_interval": "Chart Interval",
        "intervals": ["Daily", "Weekly", "Monthly"],
        "date_range": "Select Date Range",
        "btn_chart": "Run AI Chart Analysis",
        "btn_fin": "Run AI Financial Evaluation",
        "btn_news1": "AI Latest Trends Briefing",
        "btn_news2": "Run AI Market Sentiment Analysis",
        "btn_report": "Generate Comprehensive Report",
        "loading_chart": "Analyzing the chart from a purely technical perspective...",
        "loading_fin": "Analyzing financial data...",
        "loading_news": "Analyzing latest news...",
        "loading_sentiment": "Analyzing market sentiment...",
        "loading_report": "Analyzing all data comprehensively...",
        "err_503": "⚠️ Google AI servers are currently experiencing high traffic (503 Error). Please try again in a moment!",
        "err_notfound": "Could not find data for '{}'. Please enter a valid company name or ticker!",
        "tone_prompt": "Please write in professional, formal, and analytical English.",
        "lang_prompt": "English",
        "sub_fin1": "1. Value & Stability Metrics",
        "sub_fin2": "2. Financial Statement Summary (Latest)",
        "sub_news": "Real-time Trends & Sentiment Analysis",
        "sub_report": "AI Quant Analyst Final Briefing",
        "date_base": "As of",
        "news_ref": "**📌 Referenced Real-time News Articles (Click to open)**",
        "no_news_link": "Could not load news links.",
        "currency_kr": "KRW", "currency_us": "USD", "currency_jp": "JPY",
        "metrics": ["Market Cap", "Trailing PE", "Forward PE", "PBR", "PSR", "PEG", "EV/EBITDA", "ROE", "ROA", "ROIC", "Gross Margin", "Operating Margin", "Net Margin", "Revenue Growth", "Dividend Yield", "Debt to Equity", "Current Ratio", "Quick Ratio", "Int. Coverage", "52W High/Low"],
        "tables": ["Income Statement", "Total Revenue", "Cost Of Revenue", "Gross Profit", "SG&A", "Operating Income", "Pretax Income", "Net Income", "Other Comp. Income", "Balance Sheet", "Total Assets", "Current Assets", "Cash & Equivalents", "Receivables", "Inventory", "Non-Current Assets", "PPE", "Intangible Assets", "Total Liab.", "Current Liab.", "Short-Term Debt", "Non-Current Liab.", "Long-Term Debt", "Total Equity", "Capital Stock", "Capital Surplus", "Retained Earnings", "Cash Flow", "Beginning Cash", "Operating CF", "Investing CF", "Financing CF", "Dividends Paid", "Ending Cash"]
    },
    "日本語": {
        "title": "AI株式分析ターミナル",
        "search_label": "銘柄名またはティッカー (日/米/韓コード)",
        "tabs": ["チャート分析", "詳細財務", "最新動向", "総合レポート"],
        "cur_price_label": "現在値",
        "chart_interval": "チャート周期",
        "intervals": ["日足", "週足", "月足"],
        "date_range": "照会期間設定",
        "btn_chart": "AIチャートトレンド分析を実行",
        "btn_fin": "AI財務健全性評価を実行",
        "btn_news1": "AI最新動向ブリーフィング",
        "btn_news2": "AI市場センチメント分析を実行",
        "btn_report": "ワンクリック総合分析レポート作成",
        "loading_chart": "純粋なテクニカル観点からチャートを分析中...",
        "loading_fin": "財務データを分析中...",
        "loading_news": "最新ニュースを分析中...",
        "loading_sentiment": "市場のセンチメントを分析中...",
        "loading_report": "すべてのデータを統合して分析中...",
        "err_503": "⚠️ 現在、Google AIサーバーにアクセスが集中しています（503エラー）。しばらくしてからもう一度お試しください！",
        "err_notfound": "'{}' のデータが見つかりません。正確な企業名やティッカーを入力してください！",
        "tone_prompt": "必ず「です・ます」調の丁寧で専門的なアナリストの文体で作成してください。",
        "lang_prompt": "日本語",
        "sub_fin1": "1. 価値および安定性指標",
        "sub_fin2": "2. 財務諸表要約 (直近決算)",
        "sub_news": "リアルタイム動向およびセンチメント分析",
        "sub_report": "AIクオンツアナリスト最終ブリーフィング",
        "date_base": "基準日",
        "news_ref": "**📌 参考にした最新ニュース記事 (クリックして移動)**",
        "no_news_link": "ニュースリンクを読み込めませんでした。",
        "currency_kr": "ウォン", "currency_us": "ドル", "currency_jp": "円",
        "metrics": ["時価総額", "実績PER", "予想PER", "PBR", "PSR", "PEG", "EV/EBITDA", "ROE", "ROA", "ROIC", "売上総利益率", "営業利益率", "純利益率", "売上成長率", "配当利回り", "負債比率", "流動比率", "当座比率", "インタレスト・カバレッジ", "52週高値/安値"],
        "tables": ["損益計算書", "売上高", "売上原価", "売上総利益", "販売管理費", "営業利益", "税引前当期純利益", "当期純利益", "その他の包括利益", "財務状態表", "資産合計", "流動資産", "現金及び現金同等物", "売掛金", "棚卸資産", "非流動資産", "有形固定資産", "無形資産", "負債合計", "流動負債", "短期借入金", "非流動負債", "長期借入金", "資本合計", "資本金", "資本剰余金", "利益剰余金", "キャッシュフロー表", "期首残高", "営業CF", "投資CF", "財務CF", "配当金支払", "期末残高"]
    }
}

# Session State로 언어 저장
if 'lang' not in st.session_state:
    st.session_state['lang'] = "한국어"

# --- 화면 최상단 UI: 타이틀과 언어 선택 드롭다운을 깔끔하게 배치 ---
col_title, col_lang = st.columns([7, 3])
with col_title:
    st.title(lang_dict[st.session_state['lang']]["title"])
with col_lang:
    st.markdown("<div class='mobile-lang-spacer'></div>", unsafe_allow_html=True)
    selected_lang = st.selectbox("Language", ["한국어", "English", "日本語"], index=["한국어", "English", "日本語"].index(st.session_state['lang']), label_visibility="collapsed")
    if selected_lang != st.session_state['lang']:
        st.session_state['lang'] = selected_lang
        st.rerun()

t = lang_dict[st.session_state['lang']]
st.markdown("---")

try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("🚨 API Key not found.")
    st.stop()
    
client = genai.Client(api_key=MY_API_KEY)

@st.cache_data
def load_krx_data():
    return fdr.StockListing('KRX')
krx_df = load_krx_data()

def get_ticker_symbol(search_term):
    search_term = search_term.strip()
    
    # 1. 일본 주식 4자리 숫자 코드 입력 처리 (예: 7203 -> 7203.T)
    if re.match(r'^\d{4}$', search_term):
        return f"{search_term}.T"
        
    # 2. 한국 주식 6자리 숫자 코드 입력 처리 (예: 005930 -> 005930.KS)
    if re.match(r'^\d{6}$', search_term):
        match = krx_df[krx_df['Code'] == search_term]
        if not match.empty:
            market = match.iloc[0]['Market']
            return f"{search_term}.KS" if market == 'KOSPI' else f"{search_term}.KQ"
        return f"{search_term}.KS" # 기본값 KOSPI
   
    # 3. 한국어 종목명 검색
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
        
    # 4. 한/미/일 범용 AI 번역기
    try:
        translate_prompt = f"""
        Find the official Yahoo Finance ticker symbol for the following company name.
        - US companies: standard ticker (e.g., AAPL).
        - Japanese companies: 4-digit code + '.T' (e.g., Toyota -> 7203.T, 任天堂 -> 7974.T).
        - Korean companies: 6-digit code + '.KS' or '.KQ' (e.g., Samsung -> 005930.KS).
        Output ONLY the ticker symbol. No markdown, no extra text.
        Name: {search_term}
        """
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
    if ticker.endswith('.KS') or ticker.endswith('.KQ') or ticker.endswith('.T'):
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

# 메인 검색창
col_search, _ = st.columns([1, 2])
with col_search:
    user_input = st.text_input(t["search_label"], "")

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
        
        if is_korean_stock:
            currency = t["currency_kr"]
            price_fmt = ",.0f"
        elif is_japanese_stock:
            currency = t["currency_jp"]
            price_fmt = ",.0f" # 엔화도 소수점 생략
        else:
            currency = t["currency_us"]
            price_fmt = ",.2f"
        
        # 국가별 맞춤 뉴스 기사 100개 수집
        try:
            if is_korean_stock:
                rss_url = f"https://news.google.com/rss/search?q={user_input}+주식&hl=ko-KR&gl=KR&ceid=KR:ko"
            elif is_japanese_stock:
                rss_url = f"https://news.google.com/rss/search?q={user_input}+株&hl=ja&gl=JP&ceid=JP:ja"
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
                        if not content: content = get_article_text(link)
                        news_list.append({"title": title, "link": link, "content": content[:800].replace('\n', ' ')})
            except:
                pass
                
        news_context_list = []
        for idx, item in enumerate(news_list):
            news_context_list.append(f"[{idx+1}] Title: {item['title']}\nContent: {item.get('content', '')}")
        news_context = "\n\n".join(news_context_list) if news_context_list else "No recent data available."
        
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
                if math.isnan(f) or math.isinf(f): return 'N/A'
                return f"{f:.2f}"
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
            if pd.isna(op_inc_val) or pd.isna(int_exp_val) or int_exp_val == 0: interest_cov = 'N/A'
            else: interest_cov = fmt_flt(abs(op_inc_val / int_exp_val))
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

        tab1, tab2, tab3, tab4 = st.tabs(t["tabs"])
        
        # --- [탭 1: 차트 분석] ---
        with tab1:
            col_price, col_interval = st.columns([3, 1])
            with col_price:
                st.markdown(f"### {user_input} ({ticker}) {t['cur_price_label']}: {current_price:{price_fmt}} {currency}")
            
            with col_interval:
                interval_option = st.selectbox(t["chart_interval"], t["intervals"], index=0)
            
            interval = "1d" if interval_option == t["intervals"][0] else "1wk" if interval_option == t["intervals"][1] else "1mo"
            history = stock.history(period="max", interval=interval)
            history = history[(history['Low'] > 0) & (history['High'] > 0) & (history['Close'] > 0)]
            
            raw_min_date = history.index.min().to_pydatetime().date()
            min_date = raw_min_date.replace(day=1) 
            max_date = datetime.now().date()       
            
            ideal_start_date = max_date - timedelta(days=365*10)
            default_start = ideal_start_date if ideal_start_date > min_date else min_date
            
            selected_start, selected_end = st.slider(
                t["date_range"], min_value=min_date, max_value=max_date,
                value=(default_start, max_date), format="YYYY-MM-DD", label_visibility="collapsed", key=f"slider_{ticker}" 
            )
            
            mask = (history.index.date >= selected_start) & (history.index.date <= selected_end)
            
            if interval_option == t["intervals"][0]: ma_settings = [(5, f"MA({5})", "#00b0ff"), (20, f"MA({20})", "#ff9100"), (60, f"MA({60})", "#ff4081"), (120, f"MA({120})", "#aa00ff")]
            elif interval_option == t["intervals"][1]: ma_settings = [(13, f"MA({13})", "#00b0ff"), (26, f"MA({26})", "#ff9100"), (52, f"MA({52})", "#ff4081")]
            else: ma_settings = [(9, f"MA({9})", "#00b0ff"), (24, f"MA({24})", "#ff9100"), (60, f"MA({60})", "#ff4081")]
                
            for w, name, color in ma_settings: history[f'MA_{w}'] = history['Close'].rolling(window=w).mean()

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
                fig.add_trace(go.Candlestick(x=filtered_history.index, open=filtered_history['Open'], high=filtered_history['High'], low=filtered_history['Low'], close=filtered_history['Close'], increasing_line_color='#00ff9d', decreasing_line_color='#ff2d55', name="Price"))
                for w, name, color in ma_settings: fig.add_trace(go.Scatter(x=filtered_history.index, y=filtered_history[f'MA_{w}'], name=name, line=dict(color=color, width=1.0), hovertemplate=f'%{{y:{price_fmt}}}'))
                
                fig.add_annotation(x=max_idx, y=price_max, text=f"Max: {price_max:{price_fmt}}", showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#ff2d55", ax=0, ay=-35, font=dict(color="white", size=13), bgcolor="#ff2d55", borderwidth=1, borderpad=4, opacity=0.9)
                fig.add_annotation(x=min_idx, y=price_min, text=f"Min: {price_min:{price_fmt}}", showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#00b0ff", ax=0, ay=35, font=dict(color="white", size=13), bgcolor="#00b0ff", borderwidth=1, borderpad=4, opacity=0.9)
                
                fig.update_layout(
                    title=dict(text=f"{user_input} ({ticker}) - {interval_option}", font=dict(size=22, color="white")),
                    template="plotly_dark", dragmode=False,
                    xaxis=dict(rangeslider=dict(visible=False), type="date", hoverformat="%Y-%m-%d", fixedrange=True),
                    yaxis=dict(range=[price_min - padding, price_max + padding], gridcolor="#333", autorange=False, fixedrange=True, tickformat=price_fmt, hoverformat=price_fmt),
                    height=520, margin=dict(l=0, r=0, t=40, b=0),
                    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.6)", font=dict(color="white")),
                    hovermode="x unified", clickmode="none", hoverlabel=dict(font_family="Pretendard")
                )
                
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False, 'showAxisDragHandles': False, 'doubleClick': False})
            else:
                st.warning(t["err_notfound"].format(user_input))
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button(t["btn_chart"]):
                with st.spinner(t["loading_chart"]):
                    def get_formatted_history(interval_str, ma_config):
                        temp_hist = stock.history(period="max", interval=interval_str)
                        temp_hist = temp_hist[(temp_hist['Low'] > 0) & (temp_hist['High'] > 0) & (temp_hist['Close'] > 0)].copy()
                        for w, _, _ in ma_config: temp_hist[f'MA_{w}'] = temp_hist['Close'].rolling(window=w).mean()
                        temp_mask = (temp_hist.index.date >= selected_start) & (temp_hist.index.date <= selected_end)
                        temp_filtered = temp_hist.loc[temp_mask].copy()
                        cols_to_export = ['Open', 'High', 'Low', 'Close'] + [f'MA_{w}' for w, _, _ in ma_config]
                        df_export = temp_filtered[cols_to_export].copy()
                        df_export.index = df_export.index.strftime('%Y-%m-%d')
                        return df_export.tail(150).round(2).to_csv(header=True)

                    daily_csv = get_formatted_history("1d", [(5, "", ""), (20, "", ""), (60, "", ""), (120, "", "")])
                    weekly_csv = get_formatted_history("1wk", [(13, "", ""), (26, "", ""), (52, "", "")])
                    monthly_csv = get_formatted_history("1mo", [(9, "", ""), (24, "", ""), (60, "", "")])

                    prompt = f"""
                    [Background Market News (Context Only)]
                    {news_context}
                    
                    [Daily Chart Data]
                    {daily_csv}
                    
                    [Weekly Chart Data]
                    {weekly_csv}
                    
                    [Monthly Chart Data]
                    {monthly_csv}
                    
                    [Instructions]
                    1. Focus on 'Price Action' using Open, High, Low, Close. Do not just list MAs. Analyze support/resistance, breakouts, and trends.
                    2. DO NOT mention that you analyzed "100 articles" or "news data". Use the news strictly as background knowledge to avoid hallucinations.
                    3. Write ONLY in {t['lang_prompt']} using the following tone: {t['tone_prompt']}.
                    4. Output format must have exactly two sections separated by empty lines, without bullet points, and highlight key prices in **bold**.
                    
                    ### 1. Short-term trend
                    (Analysis here...)
                    
                    ### 2. Long-term trend
                    (Analysis here...)
                    """
                    try:
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.1})
                        st.info(response.text)
                    except Exception as e:
                        st.error(t["err_503"])
          
        # --- [탭 2: 상세 재무] ---
        with tab2:
            st.subheader(t["sub_fin1"])
            c1, c2, c3, c4 = st.columns(4)
            tm = t["metrics"]
            
            c1.metric(tm[0], format_large_number(market_cap, currency))
            c1.metric(tm[1], fmt_flt(trailing_pe))
            c1.metric(tm[2], fmt_flt(forward_pe))
            c1.metric(tm[3], fmt_flt(pb))
            c1.metric(tm[4], fmt_flt(psr))
            
            c2.metric(tm[5], fmt_flt(peg))
            c2.metric(tm[6], fmt_flt(ev_ebitda))
            c2.metric(tm[7], fmt_pct(roe))
            c2.metric(tm[8], fmt_pct(roa))
            c2.metric(tm[9], fmt_pct(roic))
            
            c3.metric(tm[10], fmt_pct(gross_margin))
            c3.metric(tm[11], fmt_pct(op_margin))
            c3.metric(tm[12], fmt_pct(net_margin))
            c3.metric(tm[13], fmt_pct(rev_growth))
            c3.metric(tm[14], fmt_pct(div_yield, is_dividend=True))
            
            c4.metric(tm[15], f"{debt}%" if debt != 'N/A' else 'N/A')
            c4.metric(tm[16], fmt_flt(current_ratio))
            c4.metric(tm[17], fmt_flt(quick_ratio))
            c4.metric(tm[18], interest_cov)
            c4.metric(tm[19], f"{high_52:{price_fmt}} / {low_52:{price_fmt}}")
            
            st.markdown("---")
            st.subheader(t["sub_fin2"])
            fc1, fc2, fc3 = st.columns(3)
            tt = t["tables"]
            
            with fc1:
                st.markdown(f"**{tt[0]}**")
                st.markdown(f"""
                <table class="fin-table">
                    <tr><td>{tt[1]}</td><td>{v_rev}</td></tr>
                    <tr><td>{tt[2]}</td><td>{v_cogs}</td></tr>
                    <tr><td>{tt[3]}</td><td>{v_gp}</td></tr>
                    <tr><td>{tt[4]}</td><td>{v_sga}</td></tr>
                    <tr><td>{tt[5]}</td><td>{v_op}</td></tr>
                    <tr><td>{tt[6]}</td><td>{v_pretax}</td></tr>
                    <tr><td>{tt[7]}</td><td>{v_net}</td></tr>
                    <tr><td>{tt[8]}</td><td>{v_oci}</td></tr>
                </table>
                """, unsafe_allow_html=True)
                
            with fc2:
                st.markdown(f"**{tt[9]}**")
                st.markdown(f"""
                <table class="fin-table">
                    <tr><td>{tt[10]}</td><td>{v_tot_assets}</td></tr>
                    <tr><td>{tt[11]}</td><td>{v_cur_assets}</td></tr>
                    <tr><td>{tt[12]}</td><td>{v_cash}</td></tr>
                    <tr><td>{tt[13]}</td><td>{v_receiv}</td></tr>
                    <tr><td>{tt[14]}</td><td>{v_inv}</td></tr>
                    <tr><td>{tt[15]}</td><td>{v_ncur_assets}</td></tr>
                    <tr><td>{tt[16]}</td><td>{v_tangible}</td></tr>
                    <tr><td>{tt[17]}</td><td>{v_intangible}</td></tr>
                    <tr><td>{tt[18]}</td><td>{v_tot_liab}</td></tr>
                    <tr><td>{tt[19]}</td><td>{v_cur_liab}</td></tr>
                    <tr><td>{tt[20]}</td><td>{v_s_debt}</td></tr>
                    <tr><td>{tt[21]}</td><td>{v_ncur_liab}</td></tr>
                    <tr><td>{tt[22]}</td><td>{v_l_debt}</td></tr>
                    <tr><td>{tt[23]}</td><td>{v_tot_eq}</td></tr>
                    <tr><td>{tt[24]}</td><td>{v_cap_stock}</td></tr>
                    <tr><td>{tt[25]}</td><td>{v_cap_surplus}</td></tr>
                    <tr><td>{tt[26]}</td><td>{v_retained}</td></tr>
                </table>
                """, unsafe_allow_html=True)
            with fc3:
                st.markdown(f"**{tt[27]}**")
                st.markdown(f"""
                <table class="fin-table">
                    <tr><td>{tt[28]}</td><td>{v_cf_beg}</td></tr>
                    <tr><td>{tt[29]}</td><td>{v_cf_op}</td></tr>
                    <tr><td>{tt[30]}</td><td>{v_cf_inv}</td></tr>
                    <tr><td>{tt[31]}</td><td>{v_cf_fin}</td></tr>
                    <tr><td>{tt[32]}</td><td>{v_dividend}</td></tr>
                    <tr><td>{tt[33]}</td><td>{v_cf_end}</td></tr>
                </table>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(t["btn_fin"]):
                with st.spinner(t["loading_fin"]):
                    prompt = f"""
                    [Latest News (Context Only)]
                    {news_context}
                    
                    [Financial Data for {ticker}]
                    Market Cap: {market_cap}, PE: {trailing_pe}, PB: {pb}, ROE: {roe}, Debt Ratio: {debt}%, Op Margin: {op_margin}
                    Assets: {v_tot_assets}, Liabilities: {v_tot_liab}, Equity: {v_tot_eq}
                    Op CF: {v_cf_op}, Inv CF: {v_cf_inv}, Fin CF: {v_cf_fin}
                    
                    [Instructions]
                    Analyze 1. Valuation, 2. Financial Stability, 3. Profitability & Growth.
                    Write ONLY in {t['lang_prompt']}. Tone: {t['tone_prompt']}.
                    DO NOT mention "based on the 100 articles" or "news says". Use the news context silently to prevent hallucinations.
                    """
                    try:
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.1})
                        st.info(response.text)
                    except Exception as e:
                        st.error(t["err_503"])
                    
        # --- [탭 3: 최신 동향] ---
        with tab3:
            st.subheader(t["sub_news"])
            st.write(f"{t['date_base']}: **{today_date}**")
          
            col_news1, col_news2 = st.columns(2)
            with col_news1:
                if st.button(t["btn_news1"]):
                    with st.spinner(t["loading_news"]):
                        prompt = f"""
                        [Data]
                        {news_context}
                        
                        [Instructions]
                        Extract 3 most critical news issues affecting {ticker}.
                        Write ONLY in {t['lang_prompt']}. Tone: {t['tone_prompt']}.
                        Format with ### headings and normal paragraphs. Highlight key terms in **bold**.
                        CRITICAL: DO NOT explicitly state the number of articles analyzed (e.g., do not say "I analyzed 100 articles").
                        """
                        try:
                            response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.1})
                            st.info(response.text)
                        except Exception as e:
                            st.error(t["err_503"])
                        
                        st.markdown("---")
                        st.markdown(t["news_ref"])
                        if news_list:
                            for item in news_list[:10]: # 화면에는 상위 10개만
                                st.markdown(f"• <a href='{item['link']}' target='_blank'>{item['title']}</a>", unsafe_allow_html=True)
                        else:
                            st.write(t["no_news_link"])
          
            with col_news2:
                if st.button(t["btn_news2"]):
                    with st.spinner(t["loading_sentiment"]):
                        prompt = f"""
                        [Data]
                        {news_context}
                        
                        [Instructions]
                        Analyze the market sentiment (Fear & Greed) for {ticker} and predict its pressure on the stock.
                        Write ONLY in {t['lang_prompt']}. Tone: {t['tone_prompt']}.
                        CRITICAL: DO NOT explicitly state the number of articles analyzed.
                        """
                        try:
                            response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.1})
                            st.info(response.text)
                        except Exception as e:
                            st.error(t["err_503"])

        # --- [탭 4: 종합 리포트] ---
        with tab4:
            st.subheader(t["sub_report"])
            if st.button(t["btn_report"]):
                with st.spinner(t["loading_report"]):
                    prompt = f"""
                    Provide a final Quant Analyst Briefing for {ticker} as of {today_date}.
                    
                    [Context]
                    Price: {current_price}, 52W: {high_52}/{low_52}, MAs: {ma_context_str}
                    Fin: PE {trailing_pe}, PBR {pb}, ROE {roe}, Debt {debt}%
                    News Context: {news_context}
                    
                    [Sections Required]
                    1. Financial Evaluation
                    2. Market Sentiment & Future Flow
                    3. Strategy (Hold / Buy / Sell)
                    4. Specific Prices (Entry, Target, Stop-loss)
                    
                    [Instructions]
                    - Write ONLY in {t['lang_prompt']}.
                    - Tone: {t['tone_prompt']}
                    - NO bullet points. Use ### for headings, followed by empty line, then paragraph.
                    - Highlight key info in **bold**.
                    - CRITICAL: DO NOT explicitly mention the number of news articles provided. Use them silently for accuracy.
                    """
                    try:
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config={"temperature": 0.1})
                        st.info(response.text)
                    except Exception as e:
                        st.error(t["err_503"])
    else:
        st.error(t["err_notfound"].format(user_input))
