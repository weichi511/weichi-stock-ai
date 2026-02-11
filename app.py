import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd

# 1. 頁面基本設定
st.set_page_config(page_title="My AI Stock", layout="centered")

# 2. 安全驗證 (簡單密碼鎖)
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.title("🔒 身份驗證")
        pwd = st.text_input("請輸入您的存取密碼", type="password")
        if st.button("登入"):
            # 您可以在 Secrets 設定一個自訂密碼，例如 MY_APP_PWD
            if pwd == st.secrets.get("MY_APP_PWD", "hello2026"): 
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("密碼錯誤！")
        return False
    return True

# 確保這兩行前面完全「沒有」任何空格，必須靠左對齊
if check_password():
# 3. 初始化 Gemini
   
    genai.configure(api_key="AIzaSyCZgPL5WNTL1uLOqLROY6qAsY8f-2Sr3gk")
    # 這裡使用「最原始」的宣告方式，能避開 SDK 的路徑錯誤

    model = genai.GenerativeModel('gemini-1.5-flash')
    # 這裡開始才是 App 的主內容，縮排必須與上面的 genai 一致
    st.title("🚀 私人 AI 股市助理")

    # 4. 輸入區 (置頂)
    col1, col2 = st.columns([3, 1])
    with col1:
        target_stock = st.text_input("輸入代號", value="2330.TW").upper()
    with col2:
        analyze_btn = st.button("分析", use_container_width=True)

    if analyze_btn:
        with st.spinner('數據讀取中...'):
            try:
                # 抓取數據
                stock = yf.Ticker(target_stock)
                df = stock.history(period="3mo") # 抓三個月數據
                info = stock.info

                if df.empty:
                    st.error("找不到該股票數據，請檢查代號是否正確。")
                else:
                    # 分頁顯示 (適合手機切換)
                    tab1, tab2 = st.tabs(["🤖 AI 分析", "📊 數據指標"])

                    with tab1:
                        # 準備給 Gemini 的資料包
                        current_p = df['Close'].iloc[-1]
                        price_change = ((current_p - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
                        
                        prompt = f"""
                        你是專業分析師。數據如下：
                        股票: {info.get('longName', target_stock)}
                        現價: {current_p:.2f}
                        今日漲跌: {price_change:.2f}%
                        5日均價: {df['Close'].tail(5).mean():.2f}
                        近期新聞摘要: {stock.news[:3] if stock.news else '無'}
                        請提供：1.技術面簡評 2.投資建議(短/中線)。(繁體中文)
                        """
                        
                        response = model.generate_content(prompt)
                        st.markdown(f"### Gemini 觀點\n{response.text}")

                    with tab2:
                        st.metric("目前股價", f"{current_p:.2f}", f"{price_change:.2f}%")
                        st.subheader("三個月走勢")
                        st.line_chart(df['Close'])
                        st.write("近期成交量")
                        st.bar_chart(df['Volume'].tail(20))
            
            except Exception as e:
                st.error(f"發生錯誤: {e}")

    # 5. 側邊欄：登出與資訊
    with st.sidebar:
        st.write(f"當前使用者：已授權")
        if st.button("登出"):
            st.session_state["authenticated"] = False
            st.rerun()












