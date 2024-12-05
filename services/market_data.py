import yfinance as yf
import logging
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

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
            # Get 6 months of historical data for better visualization
            history = asset.history(period="6mo")
            
            if history.empty:
                market_data[ticker] = {
                    "last_price": None,
                    "volume": None,
                    "market_cap": None,
                    "history": None
                }
                continue
            
            market_data[ticker] = {
                "last_price": history["Close"].iloc[-1] if not history.empty else None,
                "volume": history["Volume"].iloc[-1] if not history.empty else None,
                "market_cap": asset.info.get("marketCap", None),
                "history": history  # Store the historical data
            }
        except Exception as e:
            logging.error(f"Error fetching data for {ticker}: {e}")
            market_data[ticker] = {
                "last_price": None,
                "volume": None,
                "market_cap": None,
                "history": None
            }
    
    state["market_data"] = market_data
    return state

def calculate_rsi(data, periods=14):
    """Calculate RSI indicator."""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def analyze_trend(history, ma20, ma50, ma200, rsi):
    """Analyze market trends using technical indicators."""
    try:
        current_price = history['Close'].iloc[-1]
        current_ma20 = ma20.iloc[-1]
        current_ma50 = ma50.iloc[-1]
        current_ma200 = ma200.iloc[-1]
        current_rsi = rsi.iloc[-1]
        
        # Price momentum (last 5 days)
        price_momentum = (current_price - history['Close'].iloc[-5]) / history['Close'].iloc[-5] * 100
        
        # Volume trend (comparing current volume to 20-day average)
        avg_volume = history['Volume'].rolling(window=20).mean().iloc[-1]
        current_volume = history['Volume'].iloc[-1]
        volume_trend = current_volume > avg_volume

        # Analyze moving average relationships
        ma_trend = {
            'above_ma20': current_price > current_ma20,
            'above_ma50': current_price > current_ma50,
            'above_ma200': current_price > current_ma200,
            'ma20_above_ma50': current_ma20 > current_ma50,
            'ma50_above_ma200': current_ma50 > current_ma200
        }

        # Determine overall trend
        trend_strength = sum([
            current_price > current_ma20,
            current_price > current_ma50,
            current_price > current_ma200,
            current_ma20 > current_ma50,
            current_ma50 > current_ma200
        ])

        if trend_strength >= 4:
            trend = "Strong Uptrend"
        elif trend_strength >= 3:
            trend = "Moderate Uptrend"
        elif trend_strength == 2:
            trend = "Neutral"
        elif trend_strength >= 1:
            trend = "Moderate Downtrend"
        else:
            trend = "Strong Downtrend"

        # RSI analysis
        rsi_signal = "Neutral"
        if current_rsi > 70:
            rsi_signal = "Overbought"
        elif current_rsi < 30:
            rsi_signal = "Oversold"
        elif current_rsi > 50:
            rsi_signal = "Bullish"
        elif current_rsi < 50:
            rsi_signal = "Bearish"

        analysis = {
            'trend': trend,
            'rsi_signal': rsi_signal,
            'price_momentum': price_momentum,
            'volume_trend': 'Above Average' if volume_trend else 'Below Average',
            'ma_analysis': ma_trend,
            'trend_strength': trend_strength,
            'current_price': current_price,
            'current_rsi': current_rsi
        }

        return analysis

    except Exception as e:
        logging.error(f"Error analyzing trend: {e}")
        return None

def generate_market_charts(ticker, history):
    """Generate interactive Plotly charts for market analysis."""
    try:
        # Create figure with three rows for price, RSI, and volume
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('', 'RSI (14)', 'Volume'),  # Remove price title, will add as main title
            row_heights=[0.5, 0.25, 0.25],
            vertical_spacing=0.05,
            shared_xaxes=True
        )

        # Add candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=history.index,
                open=history['Open'],
                high=history['High'],
                low=history['Low'],
                close=history['Close'],
                name='OHLC'
            ),
            row=1, col=1
        )

        # Add moving averages to price chart
        ma20 = history['Close'].rolling(window=20).mean()
        ma50 = history['Close'].rolling(window=50).mean()
        ma200 = history['Close'].rolling(window=200).mean()

        fig.add_trace(
            go.Scatter(
                x=history.index,
                y=ma20,
                name='20 Day MA',
                line=dict(color='orange', width=1)
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=history.index,
                y=ma50,
                name='50 Day MA',
                line=dict(color='blue', width=1)
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=history.index,
                y=ma200,
                name='200 Day MA',
                line=dict(color='green', width=1)
            ),
            row=1, col=1
        )

        # Calculate and add RSI
        rsi = calculate_rsi(history['Close'])
        fig.add_trace(
            go.Scatter(
                x=history.index,
                y=rsi,
                name='RSI (14)',
                line=dict(color='purple', width=1)
            ),
            row=2, col=1
        )

        # Analyze trend
        trend_analysis = analyze_trend(history, ma20, ma50, ma200, rsi)
        if trend_analysis:
            # Add trend information as annotations at the top
            trend_text = f"{ticker} Price | {trend_analysis['trend']} | RSI: {trend_analysis['rsi_signal']} ({trend_analysis['current_rsi']:.1f})"
            momentum_text = f"5-Day Momentum: {trend_analysis['price_momentum']:.1f}% | Volume: {trend_analysis['volume_trend']}"
            
            # Add title with trend information
            fig.update_layout(
                title=dict(
                    text=trend_text + "<br>" + momentum_text,
                    x=0.5,
                    xanchor='center',
                    y=0.95,
                    yanchor='top',
                    font=dict(size=14)
                )
            )

        # Add RSI levels at 70 and 30
        fig.add_hline(y=70, line_width=1, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_width=1, line_dash="dash", line_color="green", row=2, col=1)
        fig.add_hline(y=50, line_width=1, line_dash="dash", line_color="gray", row=2, col=1)

        # Calculate colors for volume bars based on price movement
        colors = ['red' if close < open else 'green' 
                 for close, open in zip(history['Close'], history['Open'])]

        # Add volume chart
        fig.add_trace(
            go.Bar(
                x=history.index,
                y=history['Volume'],
                name='Volume',
                marker_color=colors,
                showlegend=False
            ),
            row=3, col=1
        )

        # Update layout
        fig.update_layout(
            showlegend=True,
            height=800,  # Increased height to accommodate RSI
            width=None,  # Let Streamlit handle the width
            xaxis_rangeslider_visible=False,
            margin=dict(l=50, r=50, t=100, b=50),  # Increased top margin for title
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )

        # Update axes labels and format
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(
            title_text="RSI", 
            row=2, col=1,
            range=[0, 100]  # Fix RSI range
        )
        fig.update_yaxes(
            title_text="Volume", 
            row=3, col=1,
            tickformat=",.0f"  # Format volume numbers with commas
        )

        # Update x-axes
        fig.update_xaxes(title_text="Date", row=3, col=1)  # Only show date on bottom chart

        # Ensure the charts are properly sized
        fig.update_layout(bargap=0.2)

        return fig, trend_analysis

    except Exception as e:
        logging.error(f"Error generating charts for {ticker}: {e}")
        return None, None