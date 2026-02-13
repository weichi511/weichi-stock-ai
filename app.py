import streamlit as st
import google.generativeai as genai
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import time

# --- 1. 頁面基本設定 ---
st.set_page_config(page_title="My AI Stock", layout="centered", page_icon="🚀")

# --- 2. 數據抓取：整合 FinMind (台股) 與 yfinance (美股) ---
@st.cache_data(ttl=600)
def fetch_stock_data(ticker):
    try:
        is_tw = ticker.isdigit() or ".TW" in ticker.upper()
        clean_ticker = ticker.upper().replace(".TW", "")
        
        if is_tw:
            dl = DataLoader()
            # 抓取 2026 年最新數據
            df = dl.taiwan_stock_daily(
                stock_id=clean_ticker,
                start_date='2026-01-01' 
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
            
        news_titles = []
        try:
            news_ticker = clean_ticker + ".TW" if is_tw else ticker
            yf_news = yf.Ticker(news_ticker)
            news_titles = [n.get('title', '') for n in yf_news.news[:3]]
        except:
            pass
            
        return df, news_titles
    except Exception as e:
        print(f"Fetch Error: {e}")
        return None, []

# --- 3. 安全驗證 ---
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

# --- 4. 主程式邏輯 ---
if check_password():
    # --- AI 模型配置與初始化 (徹底修正 404 問題) ---
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        
        # 嘗試多種可能的模型名稱格式，增加魯棒性
        model_names = ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-pro']
        model = None
        
        for name in model_names:
            try:
                model = genai.GenerativeModel(name)
                # 測試性呼叫一下（選填，若要更嚴謹可測試）
                break 
            except:
                continue
                
        if model is None:
            st.error("找不到可用的 Gemini 模型，請檢查 API Key 或區域限制。")
            st.stop()
            
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
                st.error(f"⚠️ 無法抓取 '{target_stock}' 的數據。")
            else:
                current_p = df['Close'].iloc[-1]
                prev_p = df['Close'].iloc[-2]
                change = ((current_p - prev_p) / prev_p) * 100
                avg_5 = df['Close'].tail(5).mean()

                tab1, tab2 = st.tabs(["🤖 AI 訊號分析", "📊 數據指標"])
                
                with tab1:
                    # 組合更明確的提示詞
                    news_str = "\n".join(news_titles) if news_titles else "無最新新聞"
                    prompt = f"""
                    請分析股票: {target_stock}
                    最新收盤價: {current_p:.2f}
                    單日漲跌: {change:.2f}%
                    五日均價: {avg_5:.2f}
                    相關新聞: {news_str}
                    
                    請給出【訊號燈】(紅燈/黃燈/綠燈) 以及簡短的專業分析理由。
                    """
                    
                    try:
                        time.sleep(1) # 避免 API 頻率限制
                        response = model.generate_content(prompt)
                        st.info(response.text)
                    except Exception as e:
                        # 中遇到的 404 會在此被捕捉並提供提示
                        st.error(f"AI 回應失敗：{e}")
                        st.write("請確認您的 API Key 是否支援此模型，或嘗試在 Secrets 中更換 Key。")

                with tab2:
                    st.metric(f"{target_stock} 目前股價", f"{current_p:.2f}", f"{change:.2f}%")
                    st.line_chart(df['Close'])
