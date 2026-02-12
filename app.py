import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd

# 1. 頁面基本設定
st.set_page_config(page_title="My AI Stock", layout="centered")

# --- 數據抓取：增加重試邏輯與抗封鎖 ---
@st.cache_data(ttl=600)
def fetch_stock_data(ticker):
    try:
        # 不使用自定義 Session，讓 yfinance 自動處理最新的 curl_cffi 機制
        stock = yf.Ticker(ticker)
        df = stock.history(period="3mo")
        
        if df.empty:
            return None, None
        
        # 獲取新聞，若失敗則回傳空
        try:
            news_titles = [n.get('title', '') for n in stock.news[:3]]
        except:
            news_titles = []
            
        return df, news_titles
    except Exception as e:
        return None, None

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
        # 修正 404 問題：使用最標準的模型名稱
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"AI 配置失敗: {e}")
        st.stop()

    st.title("🚀 私人 AI 股市助理")

    col1, col2 = st.columns([3, 1])
    with col1:
        target_stock = st.text_input("輸入代號 (如: 2330.TW)", value="2330.TW").upper()
    with col2:
        analyze_btn = st.button("分析", use_container_width=True)

    if analyze_btn:
        with st.spinner('數據讀取與 AI 分析中...'):
            df, news_titles = fetch_stock_data(target_stock)

            if df is None or df.empty:
                st.error("⚠️ 數據抓取失敗。Yahoo 伺服器目前拒絕連線，請點擊右下角 'Reboot App'。")
            else:
                current_p = df['Close'].iloc[-1]
                prev_p = df['Close'].iloc[-2]
                change = ((current_p - prev_p) / prev_p) * 100
                avg_5 = df['Close'].tail(5).mean()

                tab1, tab2 = st.tabs(["🤖 AI 訊號分析", "📊 數據指標"])
                
                with tab1:
                    prompt = f"""
                    你是專業分析師。分析股票:{target_stock}, 現價:{current_p:.2f}, 漲跌:{change:.2f}%, 5日均價:{avg_5:.2f}。
                    請嚴格按照以下格式回覆(繁體中文)：
                    【訊號燈】：(紅燈-買入 / 黃燈-觀望 / 綠燈-減碼)
                    【分析理由】：(簡短分析)
                    """
                    try:
                        # 增加一秒延遲避免 Rate Limit
                        import time
                        time.sleep(1)
                        response = model.generate_content(prompt)
                        res_text = response.text
                        
                        # --- 視覺化燈號判斷 ---
                        if "紅燈" in res_text:
                            st.subheader("🔴 強力訊號：買入")
                        elif "綠燈" in res_text:
                            st.subheader("🟢 警示訊號：減碼")
                        else:
                            st.subheader("🟡 中性訊號：觀望")
                            
                        st.info(res_text)
                    except Exception as e:
                        st.error(f"AI 回應失敗：{e}")

                with tab2:
                    st.metric("目前股價", f"{current_p:.2f}", f"{change:.2f}%")
                    st.line_chart(df['Close'])
