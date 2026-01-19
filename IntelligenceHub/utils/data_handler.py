import pandas as pd
import numpy as np
import requests
import random
from datetime import datetime, timedelta

def fetch_stock_data(ticker, api_key):
    """
    Fetches daily time series data for a given ticker using Alpha Vantage API.
    """
    if not api_key:
        return None, "API Key is missing."
    
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={api_key}&datatype=json"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if "Time Series (Daily)" not in data:
            return None, "Error fetching data. Check ticker or API key."
        
        df = pd.DataFrame.from_dict(data["Time Series (Daily)"], orient='index')
        df = df.rename(columns={
            "1. open": "Open",
            "2. high": "High",
            "3. low": "Low",
            "4. close": "Close",
            "5. volume": "Volume"
        })
        df = df.astype(float)
        df.index = pd.to_datetime(df.index)
        return df, None
    except Exception as e:
        return None, str(e)

def generate_mock_competitor_data():
    """
    Generates mock data for competitive analysis with realistic variation.
    """
    competitors = ['Company A', 'Company B', 'Company C', 'MyCompany', 'Company D']
    
    # Generate random market shares that sum to 100, but ensuring they are not uniform
    # Using random integers and normalizing is often more intuitive for "skewed" randoms than dirichlet(1)
    raw_shares = np.random.randint(10, 100, size=5)
    market_share = (raw_shares / raw_shares.sum()) * 100
    
    # Sort for better visual effect (optional, but looks nice in pie charts)
    # Let's just keep them random order relative to names
    
    revenue = np.random.randint(50, 1000, size=5)
    
    df = pd.DataFrame({
        'Competitor': competitors,
        'Market Share (%)': np.round(market_share, 1),
        'Revenue ($M)': revenue
    })
    return df

def generate_mock_news():
    """
    Generates mock news headlines with sentiment.
    """
    headlines = [
        ("Market rally continues as tech stocks soar", "Positive"),
        ("Inflation concerns rise ahead of Fed meeting", "Negative"),
        ("Company X reports record breaking Q4 earnings", "Positive"),
        ("Supply chain disruptions expected to persist", "Negative"),
        ("New regulations introduced for AI sector", "Neutral"),
        ("Startups see funding drop in current quarter", "Negative"),
        ("Global trade volume increases by 5%", "Positive"),
        ("Analyst predicts bearish trend for next month", "Negative")
    ]
    return random.sample(headlines, 5)
