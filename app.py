import streamlit as st
import time
import os
import json
import yfinance as yf
import plotly.graph_objects as go
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from services.market_data import fetch_market_data, generate_market_charts
from services.news import fetch_news
from services.sentiment import analyze_sentiment
from services.report import generate_report
from services.workflow import run_analysis

load_dotenv()

# Configure logging
def setup_logging():
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = f"{log_dir}/financial_report_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

# Set up logging at startup
setup_logging()

st.set_page_config(
    page_title="Financial News Reports",
    page_icon="",
    layout="wide"
)

def load_portfolio(file_path: str):
    try:
        logging.info(f"Loading portfolio from {file_path}")
        with open(file_path, "r") as f:
            portfolio = json.load(f)
            logging.info(f"Portfolio loaded successfully with {sum(len(v) for v in portfolio.values())} total assets")
            return portfolio
    except FileNotFoundError:
        logging.warning(f"Portfolio file not found at {file_path}. Creating new portfolio.")
        return {
            "crypto": [],
            "forex": [],
            "stocks": []
        }

def save_portfolio(file_path: str, portfolio):
    logging.info(f"Saving portfolio to {file_path}")
    with open(file_path, "w") as f:
        json.dump(portfolio, f, indent=4)
    logging.info("Portfolio saved successfully")

def save_category_summary(category, reports_info):
    logging.info(f"Generating summary for category: {category}")
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
        logging.info(f"Created reports directory: {reports_dir}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{reports_dir}/{category}_{timestamp}_summary.md"
    
    summary_content = f"""# {category.upper()} Market Analysis Summary
    Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    ## Overview
    Total assets analyzed: {len(reports_info)}

    ## Individual Reports
    """
    
    for ticker, report_file in reports_info:
        summary_content += f"- [{ticker}]({os.path.basename(report_file)})\n"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(summary_content)
    
    logging.info(f"Category summary saved to {filename}")
    return filename

def main():
    logging.info("Starting Financial News Reports application")
    st.title(" Financial News Reports")
    
    # Sidebar
    st.sidebar.header("Portfolio Management")
    
    # Load portfolio
    portfolio = load_portfolio("portfolio.json")
    
    # Add new ticker
    new_ticker = st.sidebar.text_input("Add new ticker:")
    category = st.sidebar.selectbox("Category:", ["Crypto", "Forex", "Stocks"])
    
    if st.sidebar.button("Add"):
        if new_ticker:
            if new_ticker not in portfolio[category.lower()]:
                logging.info(f"Adding new ticker {new_ticker} to category {category}")
                portfolio[category.lower()].append(new_ticker)
                save_portfolio("portfolio.json", portfolio)
                st.sidebar.success(f"Added {new_ticker} to portfolio!")
                logging.info(f"Successfully added {new_ticker} to {category}")
            else:
                logging.warning(f"Ticker {new_ticker} already exists in {category}")
    
    # Analysis section
    logging.info("Preparing analysis section")
    all_tickers = []
    for cat, tickers in portfolio.items():
        all_tickers.extend([(cat, ticker) for ticker in tickers])
    
    analysis_type = st.radio(
        "Choose analysis type:",
        ["Single Ticker", "Full Category Analysis"]
    )
    logging.info(f"Analysis type selected: {analysis_type}")
    
    if analysis_type == "Single Ticker":
        selected_item = st.selectbox(
            "Select ticker to analyze:",
            options=all_tickers,
            format_func=lambda x: x[1]
        )
        
        if selected_item and st.button("Generate Report"):
            selected_ticker = selected_item[1]
            logging.info(f"Generating report for single ticker: {selected_ticker}")
            
            with st.spinner("Analyzing market data and news..."):
                progress_bar = st.progress(0)
                try:
                    state = {
                        "messages": [],
                        "tickers": [selected_ticker],
                        "news_content": "",
                        "sentiment": 0.0,
                        "objectivity": 0.0
                    }
                    
                    # Fetch and analyze data
                    state = fetch_market_data(state)
                    state = fetch_news(state)
                    state = analyze_sentiment(state)
                    
                    # Generate and display market charts
                    market_data = state["market_data"][selected_ticker]
                    if market_data["history"] is not None:
                        fig, trend_analysis = generate_market_charts(selected_ticker, market_data["history"])
                        if fig is not None:
                            st.plotly_chart(fig, use_container_width=True)
                            
                            if trend_analysis:
                                st.subheader("Technical Analysis Summary")
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    trend_icon = "🔼" if trend_analysis['trend'] == 'Strong Uptrend' else "🔽"
                                    rsi_icon = "📉" if trend_analysis['rsi_signal'] == 'Bearish' else "📈"
                                    st.markdown(f"""
                                    Overall Trend: {trend_icon} {trend_analysis['trend']}  
                                    RSI Signal: {rsi_icon} {trend_analysis['rsi_signal']} ({trend_analysis['current_rsi']:.1f})  
                                    5-Day Momentum: {trend_analysis['price_momentum']:.1f}%  
                                    """)
                                
                                with col2:
                                    volume_icon = "📈" if trend_analysis['volume_trend'] == 'Above Average' else "📉"
                                    st.markdown(f"""
                                    Volume Trend: {volume_icon} {trend_analysis['volume_trend']}  
                                    Current Price: ${trend_analysis['current_price']:.2f}  
                                    Trend Strength: {trend_analysis['trend_strength']}/5  
                                    """)
                                
                                # Moving Average Analysis
                                st.markdown("**Moving Average Analysis**")
                                ma_analysis = trend_analysis['ma_analysis']
                                ma_text = [
                                    f"✓ Price > MA20" if ma_analysis['above_ma20'] else "✗ Price < MA20",
                                    f"✓ Price > MA50" if ma_analysis['above_ma50'] else "✗ Price < MA50",
                                    f"✓ Price > MA200" if ma_analysis['above_ma200'] else "✗ Price < MA200",
                                    f"✓ MA20 > MA50" if ma_analysis['ma20_above_ma50'] else "✗ MA20 < MA50",
                                    f"✓ MA50 > MA200" if ma_analysis['ma50_above_ma200'] else "✗ MA50 < MA200"
                                ]
                                st.markdown(" | ".join(ma_text))
                                st.markdown("\n**Legend:**  ")
                                st.markdown("✓ = Price is above the moving average, ✗ = Price is below the moving average")
                                st.markdown("MA20 = 20-day Moving Average, MA50 = 50-day Moving Average, MA200 = 200-day Moving Average")
                    
                    # Display the report
                    report_content = generate_report(state)
                    st.markdown(report_content)
                    logging.info(f"Successfully generated report for {selected_ticker}")
                    
                    # Option to save the report after displaying it
                    save_report = st.checkbox("Save Report")
                    if save_report:
                        report_filename = save_category_summary(selected_ticker, state["messages"])
                        st.success(f"Report saved as: {report_filename}")
                    
                    # Create some space after the charts
                    st.markdown("---")
                    
                except Exception as e:
                    logging.error(f"Error generating report for {selected_ticker}: {str(e)}")
                    st.error(f"Error generating report: {str(e)}")
            
    else:  # Full Category Analysis
        selected_category = st.selectbox(
            "Select category to analyze:",
            options=[cat.capitalize() for cat in portfolio.keys()]
        )
        
        if selected_category and st.button("Generate Category Report"):
            category_key = selected_category.lower()
            tickers = portfolio[category_key]
            logging.info(f"Starting category analysis for {selected_category} with {len(tickers)} tickers")
            
            if not tickers:
                logging.warning(f"No tickers found in {selected_category} category")
                st.warning(f"No tickers found in {selected_category} category.")
            else:
                with st.spinner(f"Analyzing all {selected_category} assets..."):
                    progress_text = st.empty()
                    progress_bar = st.progress(0)
                    reports_info = []
                    
                    total_tickers = len(tickers)
                    for idx, ticker in enumerate(tickers, 1):
                        logging.info(f"Processing {ticker} ({idx}/{total_tickers})")
                        progress_text.text(f"Analyzing {ticker} ({idx}/{total_tickers})")
                        progress_bar.progress(idx/total_tickers)
                        
                        try:
                            state = {
                                "messages": [],
                                "tickers": [ticker],
                                "news_content": "",
                                "sentiment": 0.0,
                                "objectivity": 0.0,
                                "market_data": {}
                            }
                            
                            state = fetch_market_data(state)
                            state = fetch_news(state)
                            state = analyze_sentiment(state)
                            
                            report = generate_report(state, category=selected_category)
                            reports_info.append((ticker, report))
                            st.write(f"Generated report for {ticker}")
                            logging.info(f"Successfully generated report for {ticker}")
                        except Exception as e:
                            logging.error(f"Error processing {ticker}: {str(e)}")
                            st.error(f"Error processing {ticker}: {str(e)}")
                    
                    summary_file = save_category_summary(selected_category, reports_info)
                    
                    progress_text.text("All reports generated!")
                    progress_bar.progress(1.0)
                    success_message = f"""Successfully generated reports for all {selected_category} assets!
                    Category summary saved to: {summary_file}"""
                    st.success(success_message)
                    logging.info(success_message)

if __name__ == "__main__":
    main()