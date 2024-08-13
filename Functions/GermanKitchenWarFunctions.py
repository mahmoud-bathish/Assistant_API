import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

news_api_key = os.environ.get("NEWS_API_KEY")

def get_news(topic):
    url = (f"https://newsapi.org/v2/everything?q={topic}&apiKey={news_api_key}&pageSize=5")
    try:
        response = requests.get(url)
        if response.status_code == 200:
            news = json.dumps(response.json(), indent=4)
            news_json = json.loads(news)
            data = news_json

            status = data["status"]
            total_results = data["totalResults"]
            articles = data["articles"]
            if total_results == 0:
                return "No news found for this topic"
            else:
                final_news = []
                for article in articles:
                    source_name = article["source"]["name"]
                    author = article["author"]
                    title = article["title"]
                    description = article["description"]
                    url = article["url"]
                    content = article["content"]
                    title_description = f"""
                    Title: {title},
                    Author: {author},
                    Source: {source_name},
                    Description: {description},
                    URL: {url}
                    """
                    final_news.append(title_description)
            return final_news
        else:
            return []
    except requests.exceptions.RequestException as e:
        print("Error occured during API Request", e)

