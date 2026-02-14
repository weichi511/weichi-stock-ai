import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader

# --- 1. 頁面設定 ---
st.set_page_config(page_title="My AI Stock", layout="centered", page_icon="🚀")

# --- 2. 抓股價 ---
@st.cache_data(ttl=600)
def fetch_stock_data(ticker):
    try:
        is_tw = ticker.isdigit() or ".TW" in ticker.upper()
        clean_ticker = ticker.upper().replace(".TW", "")

        if is_tw:
            dl = DataLoader()
            df = dl.taiwan_stock_daily(
                stock_id=clean_ticker,
                start_date='2024-01-01'
            )

            if df is None or df.empty:
                return None

            df = df.rename(columns={
                'date': 'Date',
                'close': 'Close',
                'open': 'Open',
                'max': 'High',
                'min': 'Low',
                'Trading_Volume': 'Volume'
            })

            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)

        else:
            stock_yf = yf.Ticker(ticker)
            df = stock_yf.history(period="3mo")

        if df is None or df.empty:
            return None

        return df

    except Exception:
        return None


# --- 3. 密碼驗證 ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔒 身份驗證")
        pwd = st.text_input("請輸入密碼", type="password")

        if st.button("登入"):
            real_pwd = st.secrets.get("MY_APP_PWD", "")
            if pwd == real_pwd:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("密碼錯誤！")

        return False
    return True


# --- 4. 主程式 ---
if check_password():

    # --- AI 初始化 ---
    api_key = st.secrets.get("GEMINI_API_KEY", "")

    if not api_key:
        st.error("❌ 找不到 GEMINI_API_KEY，請確認 secrets 設定")
        st.stop()

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-pro")  # ✅ 改成穩定版本
    except Exception as e:
        st.error(f"❌ AI 初始化失敗: {e}")
        st.stop()

    st.title("🚀 私人 AI 股市助理")

    target_stock = st.text_input("輸入代號 (台股如: 2330)", value="2330").upper()
    analyze_btn = st.button("開始分析", use_container_width=True)

    if analyze_btn:

        with st.spinner("數據讀取與 AI 分析中..."):

            df = fetch_stock_data(target_stock)

            if df is None or len(df) < 2:
                st.error(f"⚠️ 無法抓取 '{target_stock}' 的數據")
                st.stop()

            current_p = df['Close'].iloc[-1]
            prev_p = df['Close'].iloc[-2]
            change = ((current_p - prev_p) / prev_p) * 100

            # 顯示股價
            st.metric(
                f"{target_stock} 目前股價",
                f"{current_p:.2f}",
                f"{change:.2f}%"
            )

            st.line_chart(df['Close'])

            # --- AI 分析 ---
            st.subheader("🤖 AI 訊號分析")

            prompt = f"""
你是一個台股專業量化分析師。

股票代號: {target_stock}
目前價格: {current_p:.2f}

請提供：
1. 趨勢判斷（多頭 / 空頭 / 震盪）
2. 操作建議（進場 / 續抱 / 減碼 / 觀望）
3. 風險提醒

請用繁體中文回答。
"""

            try:
                response = model.generate_content(prompt)
                result = response.text if hasattr(response, "text") else "AI 無回應"
                st.success(result)

            except Exception as e:
                st.error("❌ AI 分析失敗")
                st.code(str(e))
