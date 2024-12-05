from typing import Annotated, Dict, TypedDict
from langgraph.graph import Graph, StateGraph
import logging
from services.market_data import fetch_market_data
from services.news import fetch_news
from services.report import generate_report
from services.sentiment import analyze_sentiment
from services.crypto_analysis import analyze_crypto

class AnalysisState(TypedDict):
    messages: list
    tickers: list
    news_content: str
    sentiment: float
    objectivity: float
    market_data: dict
    crypto_analysis: dict
    category: str | None
    status: str
    error: str | None

def create_analysis_workflow():
    # Create state graph
    workflow = StateGraph(AnalysisState)

    # Define nodes
    def market_data_node(state: AnalysisState) -> AnalysisState:
        try:
            if "market_data" not in state:
                state = fetch_market_data(state)
            state["status"] = "market_data_complete"
        except Exception as e:
            state["error"] = str(e)
            state["status"] = "error"
        return state

    def news_node(state: AnalysisState) -> AnalysisState:
        try:
            state = fetch_news(state)
            state["status"] = "news_complete"
        except Exception as e:
            state["error"] = str(e)
            state["status"] = "error"
        return state

    def sentiment_node(state: AnalysisState) -> AnalysisState:
        try:
            state = analyze_sentiment(state)
            state["status"] = "sentiment_complete"
        except Exception as e:
            state["error"] = str(e)
            state["status"] = "error"
        return state

    def crypto_analysis_node(state: AnalysisState) -> AnalysisState:
        try:
            if "crypto_analysis" not in state:
                state = analyze_crypto(state)
            state["status"] = "crypto_analysis_complete"
        except Exception as e:
            state["error"] = str(e)
            state["status"] = "error"
        return state

    def report_node(state: AnalysisState) -> AnalysisState:
        try:
            report = generate_report(state, state.get("category"))
            state["report"] = report
            state["status"] = "complete"
        except Exception as e:
            state["error"] = str(e)
            state["status"] = "error"
        return state

    # Add nodes to graph
    workflow.add_node("market_data", market_data_node)
    workflow.add_node("news", news_node)
    workflow.add_node("sentiment", sentiment_node)
    workflow.add_node("crypto_analysis", crypto_analysis_node)
    workflow.add_node("report", report_node)

    # Define edges
    workflow.set_entry_point("market_data")
    
    workflow.add_edge("market_data", "news")
    workflow.add_edge("news", "sentiment")
    workflow.add_edge("sentiment", "crypto_analysis")
    workflow.add_edge("crypto_analysis", "report")

    # Conditional logic for error handling
    workflow.add_conditional_edges(
        "market_data",
        lambda x: "error" if x["status"] == "error" else "news"
    )
    workflow.add_conditional_edges(
        "news",
        lambda x: "error" if x["status"] == "error" else "sentiment"
    )
    workflow.add_conditional_edges(
        "sentiment",
        lambda x: "error" if x["status"] == "error" else "crypto_analysis"
    )
    workflow.add_conditional_edges(
        "crypto_analysis",
        lambda x: "error" if x["status"] == "error" else "report"
    )

    # Compile the graph
    app = workflow.compile()
    return app

def run_analysis(tickers: list, category: str | None = None) -> Dict:
    """
    Run the analysis workflow for given tickers
    """
    initial_state: AnalysisState = {
        "messages": [],
        "tickers": tickers,
        "news_content": "",
        "sentiment": 0.0,
        "objectivity": 0.0,
        "market_data": {},
        "crypto_analysis": {},
        "category": category,
        "status": "started",
        "error": None
    }

    app = create_analysis_workflow()
    final_state = app.invoke(initial_state)
    return final_state