import yfinance as yf
import logging

def fetch_market_data(state):
    tickers = state["tickers"]
    market_data = {}
    
    for ticker in tickers:
        try:
            # Yahoo Finance format for different types of assets
            if ticker.endswith('-USD'):  # Crypto
                yf_ticker = ticker  # Already in correct format (e.g., "BTC-USD")
            elif ticker.endswith('=X'):  # Forex
                yf_ticker = ticker  # Already in correct format (e.g., "EURUSD=X")
            else:  # Stocks
                yf_ticker = ticker  # Regular stock ticker
            
            asset = yf.Ticker(yf_ticker)
            history = asset.history(period="5d")
            
            if history.empty:
                market_data[ticker] = {
                    "last_price": None,
                    "volume": None,
                    "market_cap": None,
                }
                continue
            
            market_data[ticker] = {
                "last_price": history["Close"].iloc[-1] if not history.empty else None,
                "volume": history["Volume"].iloc[-1] if not history.empty else None,
                "market_cap": asset.info.get("marketCap", None),
            }
        except Exception as e:
            logging.error(f"Error fetching data for {ticker}: {e}")
            market_data[ticker] = {
                "last_price": None,
                "volume": None,
                "market_cap": None,
            }
    
    state["market_data"] = market_data
    return state