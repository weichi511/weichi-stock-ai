import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import time

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="My AI Stock", layout="centered", page_icon="🚀")

# --- 2. 數據抓取邏輯 ---
@st.cache_data(ttl=600)
def fetch_stock_data(ticker):
    try:
        is_tw = ticker.isdigit() or ".TW" in ticker.upper()
        clean_ticker = ticker.upper().replace(".TW", "")
        
        if is_tw:
            dl = DataLoader()
            # 修改 start_date 確保有歷史數據可以畫圖
            df = dl.taiwan_stock_daily(
                stock_id=clean_ticker,
                start_date='2025-07-01' 
            )
            if df is None or df.empty:
                return None, []
                
            df = df.rename(columns={
                'date': 'Date', 'close': 'Close', 'open': 'Open',
                'max': 'High', 'min': 'Low', 'Trading_Volume': 'Volume'
            })
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
        else:
            stock_yf = yf.Ticker(ticker)
            df = stock_yf.history(period="3mo")
        
        if df is None or df.empty:
            return None, []
            
        return df, [] # 簡化新聞抓取以提高穩定性
    except Exception as e:
        return None, []

# --- 3. 安全驗證 ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    if not st.session_state["authenticated"]:
        st.title("🔒 身份驗證")
        pwd = st.text_input("請輸入密碼", type="password")
        if st.button("登入"):
            if pwd == st.secrets["MY_APP_PWD"]: 
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("密碼錯誤！")
        return False
    return True

# --- 4. 主程式邏輯 ---
if check_password():
    # --- AI 初始化 (簡化版) ---
    try:
        # 使用 strip() 確保不會讀到多餘的換行或空格
        api_key = st.secrets["GEMINI_API_KEY"].strip()
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"AI 配置失敗: {e}")
        st.stop()

    st.title("🚀 私人 AI 股市助理")

    target_stock = st.text_input("輸入代號 (台股如: 2330)", value="2330").upper()
    analyze_btn = st.button("開始分析", use_container_width=True)

    if analyze_btn:
        with st.spinner('數據讀取與 AI 分析中...'):
            df, _ = fetch_stock_data(target_stock)

            if df is None or df.empty:
                st.error(f"⚠️ 無法抓取 '{target_stock}' 的數據。")
            else:
                current_p = df['Close'].iloc[-1]
                prev_p = df['Close'].iloc[-2]
                change = ((current_p - prev_p) / prev_p) * 100
                
                # 顯示數據指標
                st.metric(f"{target_stock} 目前股價", f"{current_p:.2f}", f"{change:.2f}%")
                st.line_chart(df['Close'])

                # AI 分析區
                st.subheader("🤖 AI 訊號分析")
                prompt = f"請分析股票:{target_stock}，目前價格 {current_p:.2f}。請給出投資建議燈號與理由。"
                try:
                    response = model.generate_content(prompt)
                    st.info(response.text)
                except Exception as e:
                    st.error(f"AI 分析失敗，請檢查 API Key 權限。錯誤: {e}")
