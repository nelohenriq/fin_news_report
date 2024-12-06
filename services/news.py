import os
from exa_py.api import Exa
from bs4 import BeautifulSoup
import requests
import html
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

exa_client = Exa(api_key=os.environ.get("EXA_API_KEY"))

def clean_html(content: str) -> str:
    try:
        soup = BeautifulSoup(content, "html.parser")
        clean_text = " ".join(soup.stripped_strings)
        return html.unescape(clean_text)
    except Exception as e:
        print(f"Error cleaning HTML: {str(e)}")
        return content

def scrape_article_content(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return clean_html(response.text)
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return "Unable to scrape content"

def fetch_news(state, category=None):
    tickers = state["tickers"]
    all_news = []

    # Define reliable sources for each category
    reliable_sources = {
        "crypto": ["coindesk.com", "cointelegraph.com", "cryptoslate.com"],
        "stocks": ["marketwatch.com", "bloomberg.com", "reuters.com"],
        "forex": ["forexfactory.com", "fxstreet.com", "investing.com"],
    }

    # Get the list of sources for the category
    sources = reliable_sources.get(category, [])

    for ticker in tickers:
        try:
            # Ensure the ticker format is consistent for news fetching
            if ticker.endswith("-USD"):
                search_ticker = ticker
            else:
                search_ticker = f"{ticker}-USD"  # Append -USD for other tickers

            # Fetch news with source filtering if sources are defined
            if sources:
                response = exa_client.search_and_contents(
                    f"{search_ticker} news from {', '.join(sources)} and market analysis",
                    type="neural",
                    num_results=5,
                    category="news",
                    summary=True,
                )
            else:
                response = exa_client.search_and_contents(
                    f"{search_ticker} news and market analysis",
                    type="neural",
                    num_results=5,
                    category="news",
                    summary=True,
                )

            for result in response.results:
                content = result.summary.strip() if hasattr(result, "summary") else scrape_article_content(result.url)
                all_news.append(content)

        except Exception as e:
            print(f"Error fetching news for {ticker}: {e}")

    logging.info(f"Fetched news articles: {all_news}")
    logging.info("Inspecting contents of all_news:")
    for i, news in enumerate(all_news):
        logging.info(f"Article {i+1}: {news}")
    state["news_content"] = " ".join(all_news)
    return state