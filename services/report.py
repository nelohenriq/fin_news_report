import os
from openai import OpenAI
from datetime import datetime

llm = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY"),
)


def format_market_data(value, format_type):
    if value is None:
        return "N/A"

    if format_type == "price":
        # For extremely small values (like SHIB), show scientific notation or more decimals
        if abs(value) < 0.0001:  # Super small values
            formatted = f"{value:.12f}".rstrip(
                "0"
            )  # Use 12 decimal places for super small values
        elif abs(value) < 0.01:
            formatted = f"{value:.10f}".rstrip(
                "0"
            )  # Use 10 decimal places for very small values
        elif abs(value) < 1:
            formatted = f"{value:.8f}".rstrip(
                "0"
            )  # Use 8 decimal places for small values
        else:
            formatted = f"{value:.4f}".rstrip(
                "0"
            )  # Use 4 decimal places for regular values
        # Remove trailing decimal point if it exists
        formatted = formatted.rstrip(".")
        return f"${formatted}"
    elif format_type == "volume":
        return f"{value:,.0f}"
    elif format_type == "market_cap":
        if value >= 1_000_000_000:  # Billions
            formatted = f"{value/1_000_000_000:.4f}".rstrip("0").rstrip(".")
            return f"${formatted}B"
        elif value >= 1_000_000:  # Millions
            formatted = f"{value/1_000_000:.4f}".rstrip("0").rstrip(".")
            return f"${formatted}M"
        else:
            return f"${value:,.0f}"
    return str(value)


def save_report_to_file(ticker, report_content):
    # Create reports directory if it doesn't exist
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{reports_dir}/{ticker}_{timestamp}_report.md"

    # Save report to file
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report_content)

    return filename


def save_category_summary(category, reports_info):
    # Create reports directory if it doesn't exist
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{reports_dir}/{category}_{timestamp}_summary.md"

    # Create summary content
    summary_content = f"""# {category.upper()} Market Analysis Summary
    Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    ## Overview
    Total assets analyzed: {len(reports_info)}

    ## Individual Reports
    """

    # Add links to individual reports
    for ticker, report_file in reports_info:
        summary_content += f"- [{ticker}]({os.path.basename(report_file)})\n"

    # Save summary to file
    with open(filename, "w", encoding="utf-8") as f:
        f.write(summary_content)

    return filename


def generate_report(state, category=None):
    try:
        ticker = state["tickers"][0]
        market_data = state["market_data"][ticker]
        sentiment = state["sentiment"]
        objectivity = state["objectivity"]
        news_content = state["news_content"]

        # Get crypto analysis if available
        crypto_analysis = state.get("crypto_analysis", {}).get(ticker, {})

        # Create report content with proper markdown formatting
        report_content = f"""# Financial Report for {ticker}
        Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        ## Market Data
        - Last Price: {format_market_data(market_data['last_price'], 'price')}
        - Volume: {format_market_data(market_data['volume'], 'volume')}
        - Market Cap: {format_market_data(market_data['market_cap'], 'market_cap')}
        """

        # Add crypto-specific analysis if available
        if crypto_analysis and ticker.endswith('-USD'):
            tech_indicators = crypto_analysis.get('technical_indicators', {})
            predictions = crypto_analysis.get('predictions', {})
            risk_metrics = crypto_analysis.get('risk_metrics', {})

            report_content += f"""
        ## Technical Analysis
        ### Price Indicators
        - SMA (20-day): {format_market_data(tech_indicators.get('sma'), 'price')}
        - EMA (20-day): {format_market_data(tech_indicators.get('ema'), 'price')}
        - RSI: {tech_indicators.get('rsi', 'N/A'):.2f}
        - MACD: {tech_indicators.get('macd', 'N/A'):.4f}
        - Bollinger Bands:
          - Upper: {format_market_data(tech_indicators.get('bb_upper'), 'price')}
          - Lower: {format_market_data(tech_indicators.get('bb_lower'), 'price')}

        ### Trading Signals
        """
            # Add trading signals
            signals = tech_indicators.get('signals', {})
            for signal, value in signals.items():
                report_content += f"- {signal.replace('_', ' ').title()}: {'Yes' if value else 'No'}\n"

            report_content += f"""
        ### Risk Metrics
        - Volatility (Annualized): {risk_metrics.get('volatility', 'N/A'):.2%}
        - Maximum Drawdown: {risk_metrics.get('max_drawdown', 'N/A'):.2%}
        - Sharpe Ratio: {risk_metrics.get('sharpe_ratio', 'N/A'):.2f}
        """

            # Add price predictions if available
            if predictions.get('predicted_prices'):
                report_content += "\n### Price Predictions\n"
                for date, price in zip(predictions['prediction_dates'], predictions['predicted_prices']):
                    report_content += f"- {date}: {format_market_data(price, 'price')}\n"

        report_content += f"""
        ## Sentiment Analysis
        - Sentiment Score: {sentiment:.2f}
        - Objectivity Score: {objectivity:.2f}

        ## Recent News and Analysis
        {news_content if news_content.strip() else "No recent news available for this asset."}
        """

        # Generate AI analysis with enhanced prompt for crypto
        prompt = f"""
        Based on the following information about {ticker}:

        Market Data:
        - Last Price: {format_market_data(market_data['last_price'], 'price')}
        - Volume: {format_market_data(market_data['volume'], 'volume')}
        - Market Cap: {format_market_data(market_data['market_cap'], 'market_cap')}
        """

        if crypto_analysis and ticker.endswith('-USD'):
            prompt += f"""
        Technical Analysis:
        - RSI: {tech_indicators.get('rsi', 'N/A'):.2f}
        - MACD: {tech_indicators.get('macd', 'N/A'):.4f}
        - Current Price vs SMA: {"Above" if signals.get('price_above_sma') else "Below"}

        Risk Metrics:
        - Volatility: {risk_metrics.get('volatility', 'N/A'):.2%}
        - Maximum Drawdown: {risk_metrics.get('max_drawdown', 'N/A'):.2%}
        - Sharpe Ratio: {risk_metrics.get('sharpe_ratio', 'N/A'):.2f}

        Trading Signals:
        """
            for signal, value in signals.items():
                prompt += f"- {signal.replace('_', ' ').title()}: {'Yes' if value else 'No'}\n"

            if predictions.get('predicted_prices'):
                prompt += "\nPrice Predictions:\n"
                for date, price in zip(predictions['prediction_dates'][:3], predictions['predicted_prices'][:3]):
                    prompt += f"- {date}: {format_market_data(price, 'price')}\n"

        prompt += f"""
        Sentiment Analysis:
        - Sentiment Score: {sentiment:.2f}
        - Objectivity Score: {objectivity:.2f}

        News Content:
        {news_content[:1000] if news_content.strip() else "No recent news available."}

        Please provide a comprehensive analysis of the cryptocurrency's current state and potential outlook.
        Focus on the following aspects:
        1. Technical Analysis: Interpret the indicators and what they suggest about market momentum
        2. Risk Assessment: Evaluate the risk metrics and what they indicate about the investment
        3. Price Predictions: Analyze the predicted price trajectory and potential factors influencing it
        4. Market Sentiment: Combine news sentiment with technical indicators for a holistic view
        5. Trading Recommendation: Based on all available data, suggest a clear trading strategy (buy, sell, or hold)

        Be concise but thorough. If certain data is missing, focus on the available metrics.
        """

        response = llm.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000,
        )

        ai_analysis = response.choices[0].message.content

        # Add AI analysis to report with proper markdown formatting
        report_content += f"\n## AI Analysis\n{ai_analysis}"

        # Save report to file
        report_file = save_report_to_file(ticker, report_content)

        return f"Report generated and saved to: {report_file}\n\n{report_content}"

    except Exception as e:
        return f"Error generating report: {str(e)}"
