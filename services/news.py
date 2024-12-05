import os
from exa_py.api import Exa
from bs4 import BeautifulSoup
import requests
import html
from dotenv import load_dotenv

load_dotenv()

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

def fetch_news(state):
    tickers = state["tickers"]
    all_news = []
    
    for ticker in tickers:
        try:
            response = exa_client.search_and_contents(
                f"{ticker} news and market analysis",
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
    
    state["news_content"] = " ".join(all_news)
    return state