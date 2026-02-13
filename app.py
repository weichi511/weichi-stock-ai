import streamlit as st
import google.generativeai as genai
import twstock
import yfinance as yf
import pandas as pd
import time

# 1. 頁面基本設定
st.set_page_config(page_title="My AI Stock", layout="centered", page_icon="🚀")

# --- 數據抓取：整合台股與美股 ---
@st.cache_data(ttl=600)
def fetch_stock_data(ticker):
    try:
        # 判斷是否為台股 (例如 2330.TW 或 2330)
        if ".TW" in ticker.upper() or ticker.isdigit():
            clean_ticker = ticker.upper().replace(".TW", "")
            stock_ts = twstock.Stock(clean_ticker)
            # 抓取最近 31 天數據
            data = stock_ts.fetch_from(2026, 1) # 2026年1月起的數據
            df = pd.DataFrame(stock_ts.data)
            df.set_index('date', inplace=True)
            # 欄位轉換以相容後續邏輯
            df = df.rename(columns={'close': 'Close', 'open': 'Open', 'high': 'High', 'low': 'Low', 'capacity': 'Volume'})
        else:
            # 非台股則維持使用 yfinance
            stock_yf = yf.Ticker(ticker)
            df = stock_yf.history(period="3mo")
        
        if df.empty:
            return None, []
            
        # 獲取新聞 (僅 yfinance 支援)
        news_titles = []
        try:
            yf_news = yf.Ticker(ticker)
            news_titles = [n.get('title', '') for n in yf_news.news[:3]]
        except:
            pass
            
        return df, news_titles
    except Exception as e:
        print(f"Error: {e}")
        return None, []

# 2. 安全驗證
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

# 3. 主程式
if check_password():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"AI 配置失敗: {e}")
        st.stop()

    st.title("🚀 私人 AI 股市助理")

    col1, col2 = st.columns([3, 1])
    with col1:
        target_stock = st.text_input("輸入代號 (台股如: 2330)", value="2330").upper()
    with col2:
        st.write(" ")
        analyze_btn = st.button("分析", use_container_width=True)

    if analyze_btn:
        with st.spinner('數據讀取與 AI 分析中...'):
            df, news_titles = fetch_stock_data(target_stock)

            if df is None or df.empty:
                st.error("⚠️ 數據抓取失敗。請確認代號正確或稍後再試。")
            else:
                current_p = df['Close'].iloc[-1]
                prev_p = df['Close'].iloc[-2]
                change = ((current_p - prev_p) / prev_p) * 100
                avg_5 = df['Close'].tail(5).mean()

                tab1, tab2 = st.tabs(["🤖 AI 訊號分析", "📊 數據指標"])
                
                with tab1:
                    prompt = f"分析股票:{target_stock},現價:{current_p:.2f},漲跌:{change:.2f}%,5日均價:{avg_5:.2f}。請以專業分析師口吻給出【訊號燈】(紅/黃/綠)與理由。"
                    try:
                        response = model.generate_content(prompt)
                        st.info(response.text)
                    except Exception as e:
                        st.error(f"AI 回應失敗：{e}")

                with tab2:
                    st.metric(f"{target_stock} 目前股價", f"{current_p:.2f}", f"{change:.2f}%")
                    st.line_chart(df['Close'])
