import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd

# 1. 頁面基本設定
st.set_page_config(page_title="My AI Stock", layout="centered")

# --- 核心優化：避開 Yahoo 偵測 ---
@st.cache_data(ttl=900) # 延長快取到 15 分鐘，降低請求頻率
def fetch_stock_data(ticker):
    try:
        # yfinance 內部會自動處理 curl_cffi，前提是環境有安裝
        stock = yf.Ticker(ticker)
        
        # 僅抓取歷史資料 (這是最不容易被擋的部分)
        df = stock.history(period="3mo")
        if df.empty:
            return None, None
        
        # 使用 fast_info 獲取基本資訊，這比 stock.info 快且安全
        try:
            current_price = df['Close'].iloc[-1]
            # 嘗試簡單抓取新聞，若失敗則回傳空清單
            news = stock.news[:3]
            news_titles = [n.get('title', '') for n in news]
        except:
            news_titles = []
            
        return df, news_titles
    except Exception:
        return None, None

# 2. 安全驗證函數
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🔒 身份驗證")
        pwd = st.text_input("請輸入密碼", type="password")
        if st.button("登入"):
            if pwd == st.secrets.get("MY_APP_PWD", "hello2026"): 
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("密碼錯誤！")
        return False
    return True

# 3. 主程式執行
if check_password():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception:
        st.error("❌ Secrets 設定錯誤，請檢查 GEMINI_API_KEY")
        st.stop()

    st.title("🚀 私人 AI 股市助理")

    col1, col2 = st.columns([3, 1])
    with col1:
        target_stock = st.text_input("輸入代號", value="2330.TW").upper()
    with col2:
        analyze_btn = st.button("分析", use_container_width=True)

    if analyze_btn:
        with st.spinner('AI 正在讀取數據...'):
            df, news_titles = fetch_stock_data(target_stock)

            if df is None:
                st.error("⚠️ Yahoo 伺服器封鎖中。請執行 'Reboot App' 或更換 App 名稱重新部署。")
            else:
                current_p = df['Close'].iloc[-1]
                prev_p = df['Close'].iloc[-2]
                change = ((current_p - prev_p) / prev_p) * 100

                tab1, tab2 = st.tabs(["🤖 AI 分析", "📊 趨勢圖"])
                
                with tab1:
                    prompt = f"分析股票:{target_stock},現價:{current_p:.2f},漲跌:{change:.2f}%,5日均價:{df['Close'].tail(5).mean():.2f}。新聞:{news_titles}。請給予短中線建議(繁體中文)。"
                    try:
                        response = model.generate_content(prompt)
                        st.markdown(f"### Gemini 建議\n{response.text}")
                    except Exception as e:
                        st.error("AI 回應失敗，請稍後再試。")

                with tab2:
                    st.metric("目前股價", f"{current_p:.2f}", f"{change:.2f}%")
                    st.line_chart(df['Close'])
