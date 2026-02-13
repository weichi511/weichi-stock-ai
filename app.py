import streamlit as st
from google import genai
import yfinance as yf
import pandas as pd
import time

# 1. 頁面基本設定
st.set_page_config(page_title="My AI Stock", layout="centered", page_icon="🚀")

# --- 數據抓取：優化抗封鎖機制 ---
@st.cache_data(ttl=600)
def fetch_stock_data(ticker):
    try:
        # 使用 yf.Ticker
        stock = yf.Ticker(ticker)
        
        # 嘗試抓取歷史數據
        # 如果頻繁被擋，可以嘗試縮短 period
        df = stock.history(period="3mo")
        
        if df is None or df.empty:
            # 備案：如果 history() 失敗，嘗試抓取基礎數據看是否連線正常
            return None, None
        
        # 獲取新聞，加入安全處理
        news_titles = []
        try:
            news = stock.news
            if news:
                news_titles = [n.get('title', '') for n in news[:3]]
        except:
            pass # 新聞抓取失敗不影響主流程
            
        return df, news_titles
    except Exception as e:
        # 將錯誤印在後台日誌方便除錯
        print(f"Error fetching {ticker}: {e}")
        return None, None

# 2. 安全驗證
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if not st.session_state["authenticated"]:
        st.title("🔒 身份驗證")
        # 建議從 secrets 讀取，若無則用預設
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

# 3. 主程式
if check_password():
    # AI 配置
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
        target_stock = st.text_input("輸入代號 (如: 2330.TW)", value="2330.TW").upper()
    with col2:
        # 增加一個空位讓按鈕與輸入框對齊
        st.write(" ") 
        analyze_btn = st.button("分析", use_container_width=True)

    if analyze_btn:
        with st.spinner('正在獲取最新市場數據...'):
            df, news_titles = fetch_stock_data(target_stock)

            if df is None or df.empty:
                st.error("⚠️ 數據抓取失敗。")
                st.warning("原因可能是 Yahoo Finance 暫時封鎖了連線。請嘗試：\n1. 稍後再試\n2. 點擊右側選單的 'Reboot App'\n3. 檢查代號是否正確 (如台股需加 .TW)")
            else:
                # 確保有足夠數據計算漲跌
                if len(df) < 2:
                    st.warning("數據量不足，無法分析。")
                else:
                    current_p = df['Close'].iloc[-1]
                    prev_p = df['Close'].iloc[-2]
                    change = ((current_p - prev_p) / prev_p) * 100
                    avg_5 = df['Close'].tail(5).mean()

                    tab1, tab2 = st.tabs(["🤖 AI 訊號分析", "📊 數據指標"])
                    
                    with tab1:
                        # 組合新聞資訊給 AI
                        news_context = "\n".join([f"- {t}" for t in news_titles]) if news_titles else "暫無相關新聞"
                        
                        prompt = f"""
                        你是專業分析師。請分析股票: {target_stock}
                        現價: {current_p:.2f}
                        當日漲跌: {change:.2f}%
                        5日均價: {avg_5:.2f}
                        近期新聞:
                        {news_context}

                        請嚴格按照以下格式回覆(繁體中文)：
                        【訊號燈】：(紅燈-買入 / 黃燈-觀望 / 綠燈-減碼)
                        【分析理由】：(請結合技術面與新聞簡短分析)
                        """
                        
                        try:
                            # 增加延遲避免 API 過快
                            time.sleep(0.5)
                            response = model.generate_content(prompt)
                            res_text = response.text
                            
                            # 視覺化呈現
                            if "紅燈" in res_text:
                                st.success("🔴 強力訊號：建議買入")
                            elif "綠燈" in res_text:
                                st.error("🟢 警示訊號：建議減碼")
                            else:
                                st.warning("🟡 中性訊號：建議觀望")
                                
                            st.info(res_text)
                        except Exception as e:
                            st.error(f"AI 分析過程中出錯：{e}")

                    with tab2:
                        st.metric("目前股價", f"{current_p:.2f}", f"{change:.2f}%")
                        st.line_chart(df['Close'])
                        with st.expander("查看原始數據"):
                            st.dataframe(df.tail(10))

