from FinMind.data import DataLoader

@st.cache_data(ttl=600)
def fetch_stock_data(ticker):
    try:
        # 判斷是否為台股 (純數字或含 .TW)
        is_tw = ticker.isdigit() or ".TW" in ticker.upper()
        
        if is_tw:
            clean_ticker = ticker.upper().replace(".TW", "")
            dl = DataLoader()
            # 抓取最近 30 天的台股日成交資料
            df = dl.taiwan_stock_daily(
                stock_id=clean_ticker,
                start_date='2026-01-01' # 確保抓取到 2026 年最新數據
            )
            
            if df.empty:
                return None, []
                
            # 轉換 FinMind 格式以符合原程式邏輯
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
            # 非台股繼續使用 yfinance
            stock_yf = yf.Ticker(ticker)
            df = stock_yf.history(period="3mo")
        
        if df is None or df.empty:
            return None, []
            
        # 獲取新聞 (維持原樣)
        news_titles = []
        try:
            news_ticker = clean_ticker + ".TW" if (is_tw and ".TW" not in ticker.upper()) else ticker
            yf_news = yf.Ticker(news_ticker)
            news_titles = [n.get('title', '') for n in yf_news.news[:3]]
        except:
            pass
            
        return df, news_titles
    except Exception as e:
        print(f"Fetch Error: {e}")
        return None, []
