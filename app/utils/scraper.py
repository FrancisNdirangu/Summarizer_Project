# utils/scraper.py

import requests
from bs4 import BeautifulSoup

class URLScraper:
    def __init__(self, url: str):
        self.url = url

    def get_content(self):
        try:
            response = requests.get(self.url)
            soup = BeautifulSoup(response.text, 'html.parser')
            return ' '.join([p.text for p in soup.find_all('p')])
        except Exception as e:
            return f"Error: {str(e)}"
