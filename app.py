import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd
import requests

# 1. 頁面基本設定
st.set_page_config(page_title="My AI Stock", layout="centered")

# --- 核心修正：模擬真人瀏覽器，避免被 Yahoo 封鎖 ---
@st.cache_data(ttl=600)
def fetch_stock_data(ticker):
    session = requests.Session()
    # 模擬普通的 Chrome 瀏覽器，減少被判定為機器人的機率
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    stock = yf.Ticker(ticker, session=session)
    try:
        # 抓取 3 個月歷史資料
        df = stock.history(period="3mo")
        if df.empty:
            return None, None, None
        
        # 安全獲取基本資訊與新聞
        try:
            info = stock.info
        except:
            info = {"longName": ticker}
            
        try:
            # 取得前 3 則新聞標題
            news_list = stock.news[:3]
            news_titles = [n.get('title', '') for n in news_list]
        except:
            news_titles = []
            
        return df, info, news_titles
    except Exception as e:
        return None, None, None

# 2. 安全驗證函數
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.title("🔒 身份驗證")
        pwd = st.text_input("請輸入您的存取密碼", type="password")
        if st.button("登入"):
            # 優先讀取 Secrets，備用密碼為 hello2026
            correct_pwd = st.secrets.get("MY_APP_PWD", "hello2026")
            if pwd == correct_pwd: 
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("密碼錯誤！")
        return False
    return True

# 3. 主程式執行邏輯
if check_password():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception:
        st.error("❌ 找不到 API 金鑰。請在 Secrets 加入：GEMINI_API_KEY")
        st.stop()

    st.title("🚀 私人 AI 股市助理")

    col1, col2 = st.columns([3, 1])
    with col1:
        target_stock = st.text_input("輸入代號 (如: 2330.TW)", value="2330.TW").upper()
    with col2:
        analyze_btn = st.button("分析", use_container_width=True)

    if analyze_btn:
        with st.spinner('數據讀取與 AI 分析中...'):
            df, info, news_titles = fetch_stock_data(target_stock)

            if df is None or df.empty:
                st.error("⚠️ 目前無法取得數據。請重啟 App 或稍後再試。")
            else:
                tab1, tab2 = st.tabs(["🤖 AI 分析", "📊 數據指標"])

                current_p = df['Close'].iloc[-1]
                prev_p = df['Close'].iloc[-2]
                price_change = ((current_p - prev_p) / prev_p) * 100

                with tab1:
                    prompt = f"""
                    你是專業股票分析師。
                    股票: {info.get('longName', target_stock)}
                    現價: {current_p:.2f}
                    漲跌: {price_change:.2f}%
                    5日均價: {df['Close'].tail(5).mean():.2f}
                    近期新聞: {", ".join(news_titles) if news_titles else "無"}
                    
                    請給予 1.技術分析總結 2.結合新聞的短中線建議。(繁體中文回答)
                    """
                    try:
                        response = model.generate_content(prompt)
                        st.markdown(f"### Gemini 觀點\n{response.text}")
                    except Exception as e:
                        st.error(f"AI 呼叫失敗: {e}")

                with tab2:
                    st.metric("目前股價", f"{current_p:.2f}", f"{price_change:.2f}%")
                    st.subheader("走勢圖表")
                    st.line_chart(df['Close'])
                    st.write("近期成交數據")
                    st.dataframe(df.tail(5))

    with st.sidebar:
        st.write(f"當前使用者：已授權")
        if st.button("登出"):
            st.session_state["authenticated"] = False
            st.rerun()
