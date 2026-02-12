import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd

# 1. 頁面基本設定
st.set_page_config(page_title="My AI Stock", layout="centered")

# --- 核心修正：針對 Yahoo API 的封鎖進行優化 ---
@st.cache_data(ttl=600)
def fetch_stock_data(ticker):
    try:
        # 建立 Ticker 物件
        stock = yf.Ticker(ticker)
        
        # 修正：直接抓取歷史資料，不透過自定義 session (因為 yfinance 內部已更新對抗機制)
        # 如果還是失敗，yfinance 會嘗試使用替代方案
        df = stock.history(period="3mo")
        
        if df.empty:
            return None, None, None
        
        # 安全獲取基本資訊
        try:
            # 雲端環境下 stock.info 極易報錯，若失敗則回傳基本資訊
            info = stock.fast_info
            display_name = ticker
        except:
            info = {"last_price": df['Close'].iloc[-1]}
            display_name = ticker
            
        try:
            # 獲取新聞
            news_list = stock.news[:3]
            news_titles = [n.get('title', '') for n in news_list]
        except:
            news_titles = []
            
        return df, info, news_titles
    except Exception as e:
        st.error(f"數據抓取發生異常: {e}")
        return None, None, None

# 2. 安全驗證函數
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.title("🔒 身份驗證")
        pwd = st.text_input("請輸入您的存取密碼", type="password")
        if st.button("登入"):
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
        st.error("❌ 找不到 API 金鑰。請檢查 Secrets 設定。")
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
                st.error("⚠️ Yahoo 伺服器目前拒絕連線。請嘗試重新 Reboot App 或稍後再試。")
            else:
                tab1, tab2 = st.tabs(["🤖 AI 分析", "📊 數據指標"])

                current_p = df['Close'].iloc[-1]
                prev_p = df['Close'].iloc[-2]
                price_change = ((current_p - prev_p) / prev_p) * 100

                with tab1:
                    prompt = f"""
                    你是專業股票分析師。
                    股票代號: {target_stock}
                    現價: {current_p:.2f}
                    漲跌幅: {price_change:.2f}%
                    5日均價: {df['Close'].tail(5).mean():.2f}
                    近期新聞: {", ".join(news_titles) if news_titles else "無"}
                    
                    請給予：1.技術分析總結 2.結合新聞的建議。(繁體中文)
                    """
                    try:
                        response = model.generate_content(prompt)
                        st.markdown(f"### Gemini 觀點\n{response.text}")
                    except Exception as e:
                        st.error(f"AI 呼叫失敗: {e}")

                with tab2:
                    st.metric("目前股價", f"{current_p:.2f}", f"{price_change:.2f}%")
                    st.line_chart(df['Close'])
                    st.dataframe(df.tail(5))

    with st.sidebar:
        st.write(f"當前使用者：已授權")
        if st.button("登出"):
            st.session_state["authenticated"] = False
            st.rerun()
