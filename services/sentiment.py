from textblob import TextBlob

def analyze_sentiment(state):
    news_content = state["news_content"]
    analysis = TextBlob(news_content)
    
    state["sentiment"] = analysis.sentiment.polarity
    state["objectivity"] = 1 - analysis.sentiment.subjectivity
    
    return state