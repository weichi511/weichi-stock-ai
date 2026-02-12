import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd

# 1. 頁面基本設定
st.set_page_config(page_title="My AI Stock", layout="centered")

# --- 數據抓取優化 ---
@st.cache_data(ttl=900)
def fetch_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="3mo")
        if df.empty:
            return None, None
        
        # 獲取新聞，若失敗則傳回空列表
        try:
            news_titles = [n.get('title', '') for n in stock.news[:3]]
        except:
            news_titles = []
            
        return df, news_titles
    except:
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
        # 從 Secrets 讀取金鑰
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 嘗試使用最新穩定版模型
        model = genai.GenerativeModel('gemini-1.5-flash')
    except:
        st.error("❌ API 金鑰設定錯誤")
        st.stop()

    st.title("🚀 私人 AI 股市助理")

    col1, col2 = st.columns([3, 1])
    with col1:
        target_stock = st.text_input("輸入代號 (如: 2330.TW)", value="2330.TW").upper()
    with col2:
        analyze_btn = st.button("分析", use_container_width=True)

    if analyze_btn:
        with st.spinner('AI 正在判斷燈號...'):
            df, news_titles = fetch_stock_data(target_stock)

            if df is None:
                st.error("⚠️ 數據抓取失敗，請重啟 App。")
            else:
                current_p = df['Close'].iloc[-1]
                prev_p = df['Close'].iloc[-2]
                change = ((current_p - prev_p) / prev_p) * 100

                # 建立 Tabs 分隔功能
                tab1, tab2 = st.tabs(["🤖 AI 訊號分析", "📊 數據指標"])
                
                with tab1:
                    # 強制 AI 回覆特定格式以便生成燈號
                    prompt = f"""
                    分析股票:{target_stock},現價:{current_p:.2f},漲跌:{change:.2f}%,5日均價:{df['Close'].tail(5).mean():.2f}。
                    新聞:{news_titles}。
                    請依照此格式回覆：
                    【訊號】：(紅燈-強力買入 / 黃燈-觀望 / 綠燈-減碼)
                    【理由】：(簡短分析)
                    """
                    try:
                        response = model.generate_content(prompt)
                        res_text = response.text
                        
                        # --- 視覺化燈號 ---
                        if "紅燈" in res_text:
                            st.error("🔴 強力建議：買入訊號") # 紅色在股市通常代表漲
                        elif "綠燈" in res_text:
                            st.success("🟢 警示訊號：減碼/賣出") # 綠色代表跌
                        else:
                            st.warning("🟡 中性訊號：暫時觀望")
                            
                        st.markdown(f"### Gemini 觀點\n{res_text}")
                    except Exception as e:
                        if "429" in str(e):
                            st.error("⚠️ 請求太快了！請等 60 秒後再試。")
                        else:
                            st.error(f"AI 呼叫失敗，請更換 API 金鑰或確認模型名稱。")

                with tab2:
                    st.metric("目前股價", f"{current_p:.2f}", f"{change:.2f}%")
                    st.line_chart(df['Close'])
