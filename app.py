import streamlit as st
import google.generativeai as genai
import twstock
import yfinance as yf
import pandas as pd
import time

# 1. 頁面基本設定 (必須放在所有 st 語句的最前面)
st.set_page_config(page_title="My AI Stock", layout="centered", page_icon="🚀")

# --- 數據抓取：整合台股與美股，增加快取與穩定性 ---
@st.cache_data(ttl=600)
def fetch_stock_data(ticker):
    try:
        # 判斷是否為台股 (純數字或含 .TW)
        is_tw = ticker.isdigit() or ".TW" in ticker.upper()
        
        if is_tw:
            clean_ticker = ticker.upper().replace(".TW", "")
            stock_ts = twstock.Stock(clean_ticker)
            # 抓取最近 31 天數據 (使用 lxml 解析)
            stock_ts.fetch_31() 
            df = pd.DataFrame(stock_ts.data)
            
            if df.empty:
                return None, []
                
            df.set_index('date', inplace=True)
            # 欄位轉換以與 yfinance 相容
            df = df.rename(columns={'close': 'Close', 'open': 'Open', 'high': 'High', 'low': 'Low', 'capacity': 'Volume'})
        else:
            # 非台股使用 yfinance
            stock_yf = yf.Ticker(ticker)
            df = stock_yf.history(period="3mo")
        
        if df is None or df.empty:
            return None, []
            
        # 獲取新聞 (統一透過 yfinance 獲取，台股代號需補上 .TW)
        news_titles = []
        try:
            news_ticker = clean_ticker + ".TW" if (is_tw and ".TW" not in ticker.upper()) else ticker
            yf_news = yf.Ticker(news_ticker)
            news_titles = [n.get('title', '') for n in yf_news.news[:3]]
        except:
            pass
            
        return df, news_titles
    except Exception as e:
        # 這裡的錯誤會顯示在 Streamlit Cloud 的日誌中
        print(f"Fetch Error: {e}")
        return None, []

# 2. 安全驗證
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.title("🔒 身份驗證")
        correct_password = st.secrets.get("MY_APP_PWD", "hello2026")
        pwd = st.text_input("請輸入密碼", type="password")
        if st.button("登入"):
            if pwd == correct_password:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("密碼錯誤！")
        return False
    return True

# 3. 主程式邏輯
if check_password():
    # 配置 AI 模型
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            st.error("請在 Secrets 中設定 GEMINI_API_KEY")
            st.stop()
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"AI 配置失敗: {e}")
        st.stop()

    st.title("🚀 私人 AI 股市助理")

    col1, col2 = st.columns([3, 1])
    with col1:
        target_stock = st.text_input("輸入代號 (台股輸入 2330)", value="2330").upper()
    with col2:
        st.write(" ") # 對齊用
        analyze_btn = st.button("分析", use_container_width=True)

    if analyze_btn:
        with st.spinner('正在獲取最新市場數據並召喚 AI 分析師...'):
            df, news_titles = fetch_stock_data(target_stock)

            if df is None or df.empty:
                st.error(f"⚠️ 無法抓取 '{target_stock}' 的數據。")
                st.info("請確認：1. 代號是否正確 2. 網路連線是否正常 3. 若為台股可嘗試不加 .TW")
            else:
                # 獲取最新行情
                current_p = df['Close'].iloc[-1]
                prev_p = df['Close'].iloc[-2]
                change = ((current_p - prev_p) / prev_p) * 100
                avg_5 = df['Close'].tail(5).mean()

                tab1, tab2 = st.tabs(["🤖 AI 投資建議", "📊 走勢指標"])
                
                with tab1:
                    # 組合 AI 提示詞
                    news_text = "\n".join([f"- {t}" for t in news_titles]) if news_titles else "暫無新聞"
                    prompt = f"""
                    你是專業分析師。請分析股票: {target_stock}
                    目前價格: {current_p:.2f}
                    漲跌幅: {change:.2f}%
                    5日均價: {avg_5:.2f}
                    相關新聞:
                    {news_text}

                    請以繁體中文提供：
                    1. 【訊號燈】(紅燈建議買入/黃燈建議觀望/綠燈建議減碼)
                    2. 【分析分析理由】
                    """
                    
                    try:
                        response = model.generate_content(prompt)
                        res_content = response.text
                        
                        # 簡單的視覺燈號判斷
                        if "紅燈" in res_content:
                            st.success("🔴 AI 訊號：建議買入")
                        elif "綠燈" in res_content:
                            st.error("🟢 AI 訊號：建議減碼")
                        else:
                            st.warning("🟡 AI 訊號：建議觀望")
                            
                        st.markdown(res_content)
                    except Exception as e:
                        st.error(f"AI 分析出錯: {e}")

                with tab2:
                    st.metric(f"{target_stock} 最新收盤價", f"{current_p:.2f}", f"{change:.2f}%")
                    st.line_chart(df['Close'])
                    with st.expander("檢視歷史數據表"):
                        st.write(df.tail(10))
