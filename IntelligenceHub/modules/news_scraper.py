import streamlit as st
import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus
from utils.data_handler import generate_mock_news

def fetch_news_rss(topic):
    # Google News RSS is a reliable source for basic headlines without heavy scraping logic
    # q={topic}
    formatted_topic = quote_plus(topic)
    url = f"https://news.google.com/rss/search?q={formatted_topic}&hl=en-US&gl=US&ceid=US:en"
    
    try:
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        
        headlines = []
        # Get top 10 items
        for item in root.findall('./channel/item')[:10]:
            title = item.find('title').text
            if title:
                headlines.append(title)
        
        return headlines
    except Exception as e:
        print(f"RSS Fetch Error: {e}")
        return []

def show():
    st.title("📰 News Monitor")
    st.markdown("---")

    col1, col2 = st.columns([1, 3])

    with col1:
        st.subheader("Settings")
        topic = st.text_input("News Domain / Topic", value="Technology")
        mode = st.radio("Source", ["Live Scrape (RSS)", "Mock Data"])
        
        if st.button("Fetch & Analyze"):
            with st.spinner("Fetching and Categorizing..."):
                headlines = []
                if mode == "Mock Data":
                    # Use existing mock but just titles for the AI flow (or we can categorize the mock ones too)
                    # To be consistent with the AI flow, let's generate mock list, strip sentiment, and letting AI add it back if we want,
                    # OR just use the previous mock function. The prompt specifically asked to "categorizes the news".
                    # Let's simple use the Mock list but re-process it or just pass it trough.
                    # Simplest: Just use standard mock headlines.
                    raw_mock = generate_mock_news() 
                    headlines = [h[0] for h in raw_mock] # Extract just text
                else:
                    headlines = fetch_news_rss(topic)
                
                if not headlines:
                    st.warning("No news found. Using fallback mock data.")
                    headlines = [h[0] for h in generate_mock_news()]

                # AI Processing
                from utils.ai_handler import AIHandler
                ai = AIHandler()
                analyzed_news = ai.categorize_news(headlines)
                st.session_state['analyzed_news'] = analyzed_news

    with col2:
        if 'analyzed_news' in st.session_state:
            st.subheader(f"Latest Updates: {topic.title()}")
            
            for item in st.session_state['analyzed_news']:
                # Item is {headline, category, sentiment}
                sentiment = item.get('sentiment', 'Neutral')
                category = item.get('category', 'General')
                headline = item.get('headline', '')
                
                color = "green" if sentiment == "Positive" else "red" if sentiment == "Negative" else "gray"
                icon = "🔼" if sentiment == "Positive" else "🔽" if sentiment == "Negative" else "➖"
                
                st.markdown(f"""
                <div style="padding: 15px; border-radius: 8px; background-color: #262730; margin-bottom: 12px; border-left: 5px solid {color}; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="display:flex; justify-content:space-between; margin-bottom: 5px;">
                        <span style="font-size: 0.8em; background-color: #444; padding: 2px 8px; border-radius: 4px;">{category}</span>
                        <span style="color: {color}; font-weight: bold;">{icon} {sentiment}</span>
                    </div>
                    <h4 style="margin:5px 0 0 0; font-weight: 500;">{headline}</h4>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Enter a domain and click Fetch to see AI-categorized news.")
