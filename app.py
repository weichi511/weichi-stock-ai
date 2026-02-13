@st.cache_data(ttl=600)
def fetch_stock_data(ticker):
    try:
        # 判斷是否為台股
        if ".TW" in ticker.upper() or ticker.isdigit():
            clean_ticker = ticker.upper().replace(".TW", "")
            stock_ts = twstock.Stock(clean_ticker)
            
            # 改成抓取最近 31 天的數據 (更穩定)
            stock_ts.fetch_31() 
            df = pd.DataFrame(stock_ts.data)
            
            if df.empty:
                return None, []
                
            df.set_index('date', inplace=True)
            # 欄位轉換以相容後續邏輯
            df = df.rename(columns={'close': 'Close', 'open': 'Open', 'high': 'High', 'low': 'Low', 'capacity': 'Volume'})
        else:
            # 非台股維持使用 yfinance
            stock_yf = yf.Ticker(ticker)
            df = stock_yf.history(period="3mo")
        
        # 獲取新聞 (維持原樣)
        news_titles = []
        try:
            yf_news = yf.Ticker(ticker if ".TW" in ticker.upper() else ticker)
            news_titles = [n.get('title', '') for n in yf_news.news[:3]]
        except:
            pass
            
        return df, news_titles
    except Exception as e:
        print(f"Error: {e}")
        return None, []
