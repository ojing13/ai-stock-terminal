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
import math # nan 처리를 위해 추가

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
   
    /* 모바일 환경 폰트 사이즈 조절 (타이틀 한 줄 표시) */
    @media (max-width: 768px) {
        h1 { font-size: 1.5rem !important; word-break: keep-all; }
    }

    /* 탭(항목) 기본 디자인 - 두 줄 방지 */
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
    
    /* 텍스트 입력창 클릭(포커스) 시 테두리 파란색으로 변경 */
    .stTextInput div[data-baseweb="input"]:focus-within {
        border-color: #007bff !important;
        box-shadow: 0 0 0 1px #007bff !important;
    }
   
    /* === Selectbox(차트 주기 등) 타이핑(편집) 방지 및 테두리 파란색 === */
    div[data-baseweb="select"] > div:hover,
    div[data-baseweb="select"] > div:focus-within {
        border-color: #007bff !important;
        box-shadow: 0 0 0 1px #007bff !important;
    }
    div[data-baseweb="select"] input {
        caret-color: transparent !important; /* 깜빡이는 텍스트 커서 숨김 (수정 불가처럼 보임) */
        user-select: none !important;
    }
    
    /* === 슬라이더 전체 파란색 테마 강력 적용 === */
    /* 슬라이더 손잡이(Thumb) */
    div[data-testid="stSlider"] div[role="slider"] {
        background-color: #007bff !important;
        border-color: #007bff !important;
        box-shadow: none !important;
    }
    /* 스트림릿 내부 인라인 빨간색 강제 덮어쓰기 (트랙 구간) */
    div[data-testid="stSlider"] div[style*="background-color: rgb(255, 75, 75)"],
    div[data-testid="stSlider"] div[style*="background-color: #ff4b4b"],
    div[data-testid="stSlider"] div[style*="background: rgb(255, 75, 75)"],
    div[data-testid="stSlider"] div[style*="background: #ff4b4b"] {
        background-color: #007bff !important;
        background: #007bff !important;
    }
   
    /* 슬라이더 날짜 텍스트 파란색 적용 */
    [data-testid="stTickBarMin"],
    [data-testid="stTickBarMax"],
    [data-testid="stThumbValue"] {
        color: #007bff !important;
        font-weight: 700 !important;
    }
    
    /* === 재무제표 표 정렬 및 스타일 === */
    .fin-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; table-layout: fixed; }
    .fin-table th { text-align: left; border-bottom: 1px solid #ddd; padding: 8px; color: #555; }
    .fin-table td { border-bottom: 1px solid #eee; padding: 8px; text-align: right; vertical-align: middle; }
    /* 첫 번째 열(항목명) 너비 고정으로 정렬 맞춤 (칸 앞에 딱 붙도록) */
    .fin-table td:first-child {
        text-align: left;
        font-weight: 600;
        color: #333;
        width: 40%;
        word-break: break-all;
    }
    
    /* === Metric(지표) 텍스트 잘림 방지 === */
    div[data-testid="stMetricValue"] {
        white-space: normal !important;
        word-break: break-all !important;
        font-size: 1.4rem !important; 
        line-height: 1.2 !important;
    }

    /* === 불필요한 UI 완벽 숨기기 === */
    .stDeployButton { display: none !important; }
    [data-testid="stStatusWidget"] * { display: none !important; }
    [data-testid="stStatusWidget"]::after {
        content: "Loading...";
        font-size: 14px;
        font-weight: 600;
        color: #888888;
        display: flex;
        align-items: center;
        padding: 5px 15px;
    }

    /* === AI 답변 텍스트 가독성 최적화 (글자 크기/들여쓰기 통일) === */
    .stMarkdown p, .stMarkdown li {
        line-height: 1.8 !important;
        font-size: 1.05rem !important;
        color: #222222 !important;
    }
    .stMarkdown h3, .stMarkdown h4 {
        color: #111111 !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.8rem !important;
    }
</style>
""", unsafe_allow_html=True)

# API 키를 Streamlit 비밀 금고(Secrets)에서 안전하게 불러오기
try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("🚨 API 키를 찾을 수 없습니다. Streamlit Cloud의 Settings -> Secrets에 'GEMINI_API_KEY'를 등록해주세요.")
    st.stop()
    
client = genai.Client(api_key=MY_API_KEY)

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
        translate_prompt = f"""당신은 세계 최고의 주식 종목 번역 전문가입니다.
다음 한국어 주식 종목명을 정확한 영어 공식명으로 번역해주세요.
답변은 영어 종목명만 한 줄로 출력하세요. 다른 설명 절대 금지.
종목명: {search_term}"""
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

# ==================== 새로운 안전 및 크롤링 함수들 ====================
def format_large_number(num, currency):
    """조/억 단위 대신 다른 항목처럼 숫자로만 콤마 표시"""
    return f"{num:,.0f} {currency}"

def get_52w_high_low(stock, info_high, info_low):
    """52주 최저가 0 나오는 문제 해결"""
    high = info_high
    low = info_low
    if low <= 0 or high <= 0:
        try:
            hist = stock.history(period="2y")
            if not hist.empty:
                high = hist['High'].max()
                low = hist['Low'].min()
        except:
            pass
    return high, low

def safe_info(info, keys, default='N/A'):
    """N/A 너무 많이 나오는 문제 해결 - 여러 키 후보군 시도"""
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

# 기사 본문 스크래핑 함수 (너무 오래 걸리지 않게 방어 로직 추가)
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
    user_input = st.text_input("분석할 종목명 또는 티커 (예: 삼성전자, AAPL)", "")

if user_input:
    ticker = get_ticker_symbol(user_input)
    stock = yf.Ticker(ticker)
    hist_basic = stock.history(period="1d")
  
    if not hist_basic.empty:
        current_price = hist_basic['Close'].iloc[-1]
        
        info = stock.info
        info = augment_korean_fundamentals(ticker, info)
        info = augment_us_fundamentals(ticker, info) 
        
        today_date = datetime.now().strftime("%Y년 %m월 %d일")
       
        # 재무 데이터 로드
        try: fin_df = stock.financials
        except: fin_df = pd.DataFrame()
        try: bs_df = stock.balance_sheet
        except: bs_df = pd.DataFrame()
        try: cf_df = stock.cashflow
        except: cf_df = pd.DataFrame()
       
        # 뉴스 및 기사 본문 추출 (최대 10개로 제한하여 앱 속도 유지)
        news_list = []
        is_korean_stock = ticker.endswith('.KS') or ticker.endswith('.KQ')
        currency = "원" if is_korean_stock else "달러"
        price_fmt = ",.0f" if is_korean_stock else ",.2f"
        
        try:
            if is_korean_stock:
                rss_url = f"https://news.google.com/rss/search?q={user_input}+주식&hl=ko-KR&gl=KR&ceid=KR:ko"
            else:
                rss_url = f"https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en"
            response = requests.get(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
            root = ET.fromstring(response.content)
            for item in root.findall('.//item')[:10]:
                title = item.find('title').text if item.find('title') is not None else "No title"
                link = item.find('link').text if item.find('link') is not None else "#"
                desc = item.find('description').text if item.find('description') is not None else ""
                
                # RSS description에 요약본이 들어있는 경우 추출, 없으면 본문 직접 접근 시도
                content = BeautifulSoup(desc, "html.parser").get_text() if desc else get_article_text(link)
                content = content[:800].replace('\n', ' ')
                news_list.append({"title": title, "link": link, "content": content})
        except:
            pass
          
        if not news_list:
            try:
                raw_news = stock.news
                for n in raw_news[:10]:
                    if isinstance(n, dict) and 'title' in n and 'link' in n:
                        link = n['link']
                        title = n['title']
                        content = n.get('summary', '') 
                        if not content:
                            content = get_article_text(link)
                        news_list.append({"title": title, "link": link, "content": content[:800].replace('\n', ' ')})
            except:
                pass
                
        # 제목과 기사 본문을 합친 강력한 프롬프트 컨텍스트 생성
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
        
        # 재무제표 항목 추출
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
                st.markdown(f"### {user_input} ({ticker}) 현재가: {current_price:{price_fmt}} {currency}")
            
            with col_interval:
                interval_option = st.selectbox("차트 주기", ("일봉", "주봉", "월봉"), index=0)
            
            interval = "1d" if interval_option == "일봉" else "1wk" if interval_option == "주봉" else "1mo"
            history = stock.history(period="max", interval=interval)
            
            # --- [수정된 부분 시작] ---
            # 주기를 변경할 때 슬라이더의 min/max 경계값이 엇갈려 에러가 나는 것을 방지
            raw_min_date = history.index.min().to_pydatetime().date()
            min_date = raw_min_date.replace(day=1)  # 어떤 주기든 항상 해당 월의 1일로 넉넉하게 고정
            max_date = datetime.now().date()        # 최대 날짜는 무조건 오늘로 고정
            
            ideal_start_date = max_date - timedelta(days=365*10)
            default_start = ideal_start_date if ideal_start_date > min_date else min_date
            
            selected_start, selected_end = st.slider(
                "조회 기간 설정",
                min_value=min_date,
                max_value=max_date,
                value=(default_start, max_date),
                format="YYYY-MM-DD",
                label_visibility="collapsed",
                key=f"slider_{ticker}" # 핵심: interval_option을 제거해서 주기가 바뀌어도 키(기억) 유지
            )
            # --- [수정된 부분 끝] ---
            
            mask = (history.index.date >= selected_start) & (history.index.date <= selected_end)
            filtered_history = history.loc[mask].copy()
            
            ma_context_str = "차트 데이터 부족"

            if not filtered_history.empty:
                price_min = filtered_history['Low'].min()
                price_max = filtered_history['High'].max()
                min_idx = filtered_history['Low'].idxmin()
                max_idx = filtered_history['High'].idxmax()
                
                if interval_option == "일봉":
                    ma_settings = [(5, "MA1(5일)", "#00b0ff"), (20, "MA2(20일)", "#ff9100"), (60, "MA3(60일)", "#ff4081"), (120, "MA4(120일)", "#aa00ff")]
                elif interval_option == "주봉":
                    ma_settings = [(13, "MA1(13주)", "#00b0ff"), (26, "MA2(26주)", "#ff9100"), (52, "MA3(52주)", "#ff4081")]
                else:
                    ma_settings = [(9, "MA1(9개월)", "#00b0ff"), (24, "MA2(24개월)", "#ff9100"), (60, "MA3(60개월)", "#ff4081")]
                    
                for w, name, color in ma_settings:
                    history[f'MA_{w}'] = history['Close'].rolling(window=w).mean()

                filtered_history = history.loc[mask].copy()
                
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
                    increasing_line_color='#00ff9d', decreasing_line_color='#ff2d55',
                    name="가격"
                ))

                for w, name, color in ma_settings:
                    fig.add_trace(go.Scatter(
                        x=filtered_history.index, 
                        y=filtered_history[f'MA_{w}'], 
                        name=name,
                        line=dict(color=color, width=1.0)
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
                    title=dict(text=f"{user_input} ({ticker}) - {interval_option}", font=dict(size=22, color="white")),
                    template="plotly_dark",
                    dragmode=False,
                    xaxis=dict(rangeslider=dict(visible=False), type="date", hoverformat="%Y-%m-%d", fixedrange=True),
                    yaxis=dict(range=[min_y, max_y], gridcolor="#333", autorange=False, fixedrange=True),
                    height=520,
                    margin=dict(l=0, r=0, t=40, b=0),
                    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(0,0,0,0.6)", font=dict(color="white")),
                    hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.warning("선택하신 기간에는 표시할 데이터가 없어요. 슬라이더를 조절해 주세요!")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("AI 차트 추세 분석 실행"):
                with st.spinner("순수 기술적 관점에서 차트를 분석 중입니다..."):
                    df_close = filtered_history[['Close']].copy()
                    df_close.index = df_close.index.strftime('%Y-%m-%d')
                    df_close['Close'] = df_close['Close'].round(2)
                    full_data_csv = df_close.to_csv(header=True)
                    
                    prompt = f"""종목 {ticker}의 전체 가격 데이터입니다. (차트 주기: {interval_option})
                    
                    [전체 가격 데이터 내역 (날짜, 종가)]
                    {full_data_csv}
                    
                    위의 '전체 데이터'를 통째로 분석하여 오직 '기술적 분석(Technical Analysis)' 관점에서만 차트 흐름을 브리핑해주세요. 기업의 가치, 성장성 등 기본적 분석(Fundamental)은 100% 배제하세요.
                    
                    [🚨 절대 엄수할 핵심 지시사항 🚨]
                    1. 마크다운 수식 오류 방지: 가격 범위나 기간 표시 시 절대 물결표 및 달러 기호를 사용하지 마세요. (금액은 반드시 '{currency}'로 표기할 것)
                    2. 기계적인 기간 설정 금지: 장기 추세를 분석할 때 스스로 의미 있는 기간을 정의하세요.
                    
                    🚨 [출력 템플릿 및 포맷 규칙 - 절대 엄수]
                    모든 답변은 반드시 아래의 마크다운 구조와 들여쓰기 규격을 100% 동일하게 지켜서 작성하세요. 임의로 폰트 크기(Heading)나 들여쓰기 방식을 변경하지 마세요.
                    
                    ### 1. 단기적인 추세 (Short-term trend)
                    - **[소주제 및 핵심 키워드]**: 핵심 내용 요약
                      - [세부 설명 및 근거] (반드시 스페이스바 2칸 들여쓰기 후 하이픈 '-' 사용)
                      - [세부 설명 및 근거]
                    
                    ### 2. 장기적인 추세 (Long-term trend)
                    - **[소주제 및 핵심 키워드]**: 핵심 내용 요약
                      - [세부 설명 및 근거]
                    """
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                    with st.container(border=True):
                        st.markdown(response.text)
          
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
                    prompt = f"""종목 {ticker}의 상세 재무 데이터 및 최신 동향 텍스트입니다.

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
- [재무 지표 중심의 서술]: 제공된 텍스트 동향은 오직 '재무 지표의 원인과 결과'를 파악하는 데만 조용히 참고하세요. 기술적 차트 이야기나 가십성 이슈는 철저히 배제하고, 철저히 '재무적 관점(수익성, 안정성, 현금흐름, 밸류에이션)'에만 집중해서 평가하세요.
- [뉴스 언급 절대 금지]: "제공된 데이터에 따르면", "수집된 기사/뉴스에서", "최신 동향에서 알 수 있듯" 등의 표현을 완벽하게 금지합니다. '뉴스', '기사', '헤드라인'이라는 단어 자체를 출력문에 쓰지 마세요. 오직 당신이 직접 분석한 팩트인 것처럼 유려하게 서술하세요.
- [입체적 재무 해석]: 부채비율이 높거나 자본잠식 상태일 때, 무조건 '착한 부채'로 포장하지 마세요. 이자보상배율, 현금흐름, 대규모 투자(CapEx) 등의 맥락을 융합하여 실제 시장이 우려하는 재무적 리스크인지 성장을 위한 통과 의례인지 객관적으로 판단하세요.
- [작위적 표현 금지]: "표면적 지표 이면의", "숫자 이면의 진짜 리스크", "숨겨진 리스크" 등 시스템 프롬프트의 지시어 느낌이 나는 단어를 절대 출력하지 마세요.
- 마크다운 렌더링 오류를 막기 위해 절대 물결표(~) 및 달러 기호($)를 사용하지 마세요. (금액은 반드시 '{currency}'으로 표기할 것)

🚨 [출력 템플릿 및 포맷 규칙 - 절대 엄수]
모든 답변은 반드시 아래의 마크다운 구조와 들여쓰기 규격을 100% 동일하게 지켜서 작성하세요. 임의로 폰트 크기(Heading)나 들여쓰기 방식을 변경하지 마세요.

### 1. 기업 가치 평가
- **[소주제 및 핵심 키워드]**: 핵심 내용 요약
  - [세부 설명 및 근거] (반드시 스페이스바 2칸 들여쓰기 후 하이픈 '-' 사용)
  - [세부 설명 및 근거]

### 2. 재무적 안전성 및 리스크
- **[소주제 및 핵심 키워드]**: 핵심 내용 요약
  - [세부 설명 및 근거]

### 3. 수익성 및 미래 성장성
- **[소주제 및 핵심 키워드]**: 핵심 내용 요약
  - [세부 설명 및 근거]
"""
                    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                    with st.container(border=True):
                        st.markdown(response.text)
                    
        # --- [탭 3: 최신 동향] ---
        with tab3:
            st.subheader("실시간 동향 및 투심 분석")
            st.write(f"기준일: **{today_date}**")
          
            col_news1, col_news2 = st.columns(2)
            with col_news1:
                if st.button("AI 최신 동향 브리핑"):
                    with st.spinner("최신 뉴스를 분석하는 중입니다..."):
                        prompt = f"""오늘은 {today_date}입니다. 방금 시스템이 실시간으로 수집한 {ticker}의 최신 핵심 기사 10개의 제목과 본문 데이터입니다.
                        
[실시간 시장 동향 데이터]
{news_context}

위 데이터의 본문 내용까지 꼼꼼하게 읽고, 현재 이 기업을 둘러싼 가장 치명적이고 중요한 핵심 이슈 3가지를 도출해주세요. 각 이슈가 기업의 펀더멘털이나 향후 실적에 미칠 파급력까지 전문가의 시선으로 깊이 있게 브리핑해주세요.

🚨 [지시사항]: 기사의 제목이나 본문 문장을 절대(Never) 따옴표로 묶어 그대로 인용하거나 복사하지 마세요. '기사에 따르면', '뉴스에서' 같은 단어도 절대 쓰지 마세요. 여러 기사의 맥락을 하나로 꿰어내어 완전히 당신만의 언어로 소화해서 작성하세요. 물결표 및 달러 기호 사용 금지.

🚨 [출력 템플릿 및 포맷 규칙 - 절대 엄수]
모든 답변은 반드시 아래의 마크다운 구조와 들여쓰기 규격을 100% 동일하게 지켜서 작성하세요. 임의로 폰트 크기(Heading)나 들여쓰기 방식을 변경하지 마세요.

### 1. [이슈명 1]
- **[소주제 및 파급력]**: 핵심 내용 요약
  - [세부 설명 및 펀더멘털 영향] (반드시 스페이스바 2칸 들여쓰기 후 하이픈 '-' 사용)

### 2. [이슈명 2]
- **[소주제 및 파급력]**: 핵심 내용 요약
  - [세부 설명 및 펀더멘털 영향]

### 3. [이슈명 3]
- **[소주제 및 파급력]**: 핵심 내용 요약
  - [세부 설명 및 펀더멘털 영향]
"""
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                        with st.container(border=True):
                            st.markdown(response.text)
                        
                        st.markdown("---")
                        st.markdown("**📌 참고한 실시간 뉴스 원문 (클릭해서 바로 이동)**")
                        if news_list:
                            for item in news_list:
                                st.markdown(f"• <a href='{item['link']}' target='_blank'>{item['title']}</a>", unsafe_allow_html=True)
                        else:
                            st.write("뉴스 링크를 불러올 수 없습니다.")
          
            with col_news2:
                if st.button("AI 시장 투심 분석 실행"):
                    with st.spinner("시장 참여자들의 투심을 분석하는 중입니다..."):
                        prompt = f"""오늘은 {today_date}입니다. 방금 수집된 {ticker}의 최신 기사 10개의 제목과 본문 데이터입니다.

[실시간 시장 동향 데이터]
{news_context}

이 데이터들을 바탕으로 현재 시장 참여자들의 숨은 투자 심리(Fear & Greed)를 꿰뚫어 보고, 이것이 단기 및 중장기 주가 흐름에 어떤 압력(호재/악재)으로 작용할지 논리적으로 분석해주세요.

🚨 [지시사항]: 기사의 제목이나 본문 문장을 절대 그대로 인용(복사)하지 마세요. '수집된 뉴스에 의하면' 같은 어색한 말도 금지합니다. 거시경제나 산업 전반의 흐름을 엮어서 당신의 지식인 것처럼 꼼꼼하게 해석해주세요. 물결표 및 달러 기호 사용 금지.

🚨 [출력 템플릿 및 포맷 규칙 - 절대 엄수]
모든 답변은 반드시 아래의 마크다운 구조와 들여쓰기 규격을 100% 동일하게 지켜서 작성하세요. 임의로 폰트 크기(Heading)나 들여쓰기 방식을 변경하지 마세요.

### 1. 현재 시장 투심 (Fear & Greed)
- **[핵심 심리 요약]**: 핵심 내용
  - [세부 설명 및 근거] (반드시 스페이스바 2칸 들여쓰기 후 하이픈 '-' 사용)

### 2. 단기 및 중장기 주가 압력
- **[호재/악재 요약]**: 핵심 내용
  - [세부 설명 및 근거]
"""
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                        with st.container(border=True):
                            st.markdown(response.text)

        # --- [탭 4: 종합 리포트] ---
        with tab4:
            st.subheader("AI 퀀트 애널리스트 최종 브리핑")
            if st.button("원클릭 종합 분석 리포트 생성"):
                with st.spinner('모든 데이터를 종합하여 리포트를 작성 중입니다...'):
                    try:
                        prompt = f"""
                        오늘은 {today_date}입니다. {ticker} 종목을 종합적으로 분석해주세요.
                        
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
                        4. 구체적인 가격 제시 (진입 추천가, 1차 목표가, 손절가 - 기술적 지표, 재무, 동향을 융합하여 논리적 근거와 함께 구체적으로 제시할 것)
                        
                        🚨 [최고급 퀀트 애널리스트 수준의 입체적 분석 지침 - 반드시 엄수할 것]
                        - [직접 인용 및 작위적 표현 완벽 금지]: 리포트 내에 '뉴스', '기사', '헤드라인'이라는 단어를 아예 사용하지 마세요. 기사 문장을 절대 복사하지 마세요. 또한 "표면적 지표 이면의", "숨겨진 리스크" 같은 시스템 지시어 느낌의 단어 자체를 쓰지 마세요. 마치 당신이 현업에서 직접 시장을 모니터링하며 얻은 팩트인 것처럼 유려하게 서술하세요.
                        - [배경 지식 총동원]: 제공된 수치와 텍스트에만 갇히지 마세요. 당신이 학습한 해당 기업의 최근 거시경제(금리, 인플레 등) 환경, 산업 트렌드(AI, 반도체 등), 경쟁사 동향, 대규모 투자(CapEx) 현황을 융합하여 인과관계를 설명하세요.
                        - [맹목적 긍정 금지 및 리스크 직시]: 부채비율이 높거나 자본잠식 상태일 때, 무조건 주주환원에 의한 '착한 부채'로 포장하지 마세요. '이자보상배율', '현금흐름', '동향'을 교차 검증하여, 과도한 인프라/M&A 투자로 인한 이자 부담이나 시장이 실제로 우려하는 치명적 리스크라면 아주 냉철하게 경고하세요.
                        - [시장 심리(Fear & Greed) 통찰]: 주가가 크게 하락했거나 변동성이 크다면, 동향의 행간 의미를 파악해 현재 시장 참여자들이 무엇에 공포를 느끼고 있는지 평가에 명확히 반영하세요.
                        - 마크다운 렌더링 오류를 막기 위해 절대 물결표(~) 및 달러 기호($)를 사용하지 마세요. (금액은 반드시 '{currency}'으로 표기할 것)
                        
                        🚨 [출력 템플릿 및 포맷 규칙 - 절대 엄수]
                        모든 답변은 반드시 아래의 마크다운 구조와 들여쓰기 규격을 100% 동일하게 지켜서 작성하세요. 임의로 폰트 크기(Heading)나 들여쓰기 방식을 변경하지 마세요.
                        
                        ### 1. 재무 상황 종합 평가
                        - **[핵심 요약]**: 평가 요약
                          - [상세 분석 및 근거] (반드시 스페이스바 2칸 들여쓰기 후 하이픈 '-' 사용)
                        
                        ### 2. 시장 투심 및 향후 주가 흐름 예상
                        - **[핵심 요약]**: 분석 요약
                          - [상세 분석 및 근거]
                        
                        ### 3. 상황별 대응 전략
                        - **현재 보유자**: 대응 전략
                        - **신규 매수 대기자**: 대응 전략
                        - **매도 고려자**: 대응 전략
                        
                        ### 4. 핵심 프라이싱 (Pricing)
                        - **진입 추천가**: 금액 및 논리적 근거
                        - **1차 목표가**: 금액 및 논리적 근거
                        - **손절가**: 금액 및 논리적 근거
                        """
                        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                        with st.container(border=True):
                            st.markdown(response.text)
                    except Exception as e:
                        st.error(f"오류가 발생했습니다: {e}")
    else:
        st.error(f"'{user_input}'에 대한 데이터를 찾을 수 없어요. 정확한 기업명이나 티커를 입력해 주세요!")
