import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd

# 1. 頁面基本設定
st.set_page_config(page_title="My AI Stock", layout="centered")

# --- 快取數據函數 ---
@st.cache_data(ttl=600)
def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    df = stock.history(period="3mo")
    info = stock.info
    news = stock.news[:3] if stock.news else []
    return df, info, news

# 2. 安全驗證函數
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.title("🔒 身份驗證")
        pwd = st.text_input("請輸入您的存取密碼", type="password")
        if st.button("登入"):
            # 從 Secrets 讀取密碼
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
    # --- 從 Secrets 讀取 Gemini API Key ---
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error("找不到 API 金鑰，請檢查 Secrets 設定。")
        st.stop()

    st.title("🚀 私人 AI 股市助理")

    # 4. 輸入區
    col1, col2 = st.columns([3, 1])
    with col1:
        target_stock = st.text_input("輸入代號", value="2330.TW").upper()
    with col2:
        analyze_btn = st.button("分析", use_container_width=True)

    if analyze_btn:
        with st.spinner('數據讀取與 AI 分析中...'):
            try:
                df, info, news = fetch_stock_data(target_stock)

                if df.empty:
                    st.error("找不到該股票數據。")
                else:
                    tab1, tab2 = st.tabs(["🤖 AI 分析", "📊 數據指標"])

                    current_p = df['Close'].iloc[-1]
                    prev_p = df['Close'].iloc[-2]
                    price_change = ((current_p - prev_p) / prev_p) * 100

                    with tab1:
                        prompt = f"你是分析師。股票:{info.get('longName', target_stock)},現價:{current_p:.2f},漲跌:{price_change:.2f}%,5日均價:{df['Close'].tail(5).mean():.2f}。請給予短中線分析。(繁體中文)"
                        response = model.generate_content(prompt)
                        st.markdown(f"### Gemini 觀點\n{response.text}")

                    with tab2:
                        st.metric("目前股價", f"{current_p:.2f}", f"{price_change:.2f}%")
                        st.line_chart(df['Close'])
            
            except Exception as e:
                st.error(f"發生錯誤: {e}")

    # 5. 側邊欄
    with st.sidebar:
        st.write(f"當前使用者：已授權")
        if st.button("登出"):
            st.session_state["authenticated"] = False
            st.rerun()
