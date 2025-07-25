import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from urllib.parse import urljoin, urlparse
import feedparser
import logging
from typing import List, Dict, Optional
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedArticleScraper:
    def __init__(self, max_words=1200, min_words=100, delay=1):
        self.max_words = max_words
        self.min_words = min_words
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def count_words(self, text: str) -> int:
        """Count words in text"""
        return len(re.findall(r'\b\w+\b', text))
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        # Remove common unwanted patterns
        text = re.sub(r'Share\s*\d+\s*Tweet\s*\d+', '', text)
        text = re.sub(r'Read more.*$', '', text, flags=re.IGNORECASE)
        return text
    
    def scrape_with_rss(self, rss_url: str, max_articles: int = 50) -> List[Dict]:
        """Scrape articles using RSS feed - more reliable method"""
        articles = []
        try:
            feed = feedparser.parse(rss_url)
            logger.info(f"Found {len(feed.entries)} entries in RSS feed")
            
            for entry in feed.entries[:max_articles]:
                try:
                    # Get article content from the link
                    article_data = self.scrape_article_from_url(entry.link)
                    if article_data:
                        # Use RSS metadata to enhance the data
                        article_data['rss_title'] = getattr(entry, 'title', '')
                        article_data['published'] = getattr(entry, 'published', '')
                        article_data['rss_summary'] = getattr(entry, 'summary', '')
                        articles.append(article_data)
                        
                except Exception as e:
                    logger.error(f"Error processing RSS entry: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing RSS feed {rss_url}: {str(e)}")
            
        return articles
    
    def scrape_article_from_url(self, url: str) -> Optional[Dict]:
        """Scrape a single article from URL"""
        try:
            time.sleep(self.delay)
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = self.extract_title(soup)
            
            # Extract content using multiple strategies
            content = self.extract_content_advanced(soup)
            
            word_count = self.count_words(content)
            
            if self.min_words <= word_count <= self.max_words:
                return {
                    'title': title,
                    'content': content,
                    'url': url,
                    'word_count': word_count,
                    'source_domain': urlparse(url).netloc
                }
            else:
                logger.info(f"Skipped: {title[:50]}... (words: {word_count})")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            return None
    
    def extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title using multiple strategies"""
        selectors = [
            'h1',
            '.entry-title',
            '.post-title',
            '[property="og:title"]',
            'title'
        ]
        
        for selector in selectors:
            if selector.startswith('['):
                elem = soup.select_one(selector)
                if elem and elem.get('content'):
                    return self.clean_text(elem.get('content'))
            else:
                elem = soup.select_one(selector)
                if elem:
                    return self.clean_text(elem.get_text())
        
        return "No title found"
    
    def extract_content_advanced(self, soup: BeautifulSoup) -> str:
        """Advanced content extraction using multiple strategies"""
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', '.sidebar', '.advertisement', '.ad']):
            element.decompose()
        
        # Try different content selectors in order of preference
        content_selectors = [
            '[property="articleBody"]',
            '.entry-content',
            '.post-content',
            '.article-content',
            '.post-body',
            '.content',
            'main',
            'article'
        ]
        
        for selector in content_selectors:
            elem = soup.select_one(selector)
            if elem:
                content = elem.get_text(separator=' ')
                content = self.clean_text(content)
                if len(content) > 200:  # Ensure we got substantial content
                    return content
        
        # Fallback: get all paragraph text
        paragraphs = soup.find_all('p')
        content = ' '.join([p.get_text() for p in paragraphs])
        return self.clean_text(content)
    
    def scrape_multiple_sources(self, sources: List[Dict], output_file: str = 'articles.csv') -> pd.DataFrame:
        """Scrape from multiple sources (RSS feeds and direct URLs)"""
        all_articles = []
        
        for source in sources:
            source_type = source.get('type', 'url')
            source_url = source['url']
            source_name = source.get('name', urlparse(source_url).netloc)
            
            logger.info(f"Scraping {source_name} ({source_type})")
            
            if source_type == 'rss':
                articles = self.scrape_with_rss(source_url, source.get('max_articles', 20))
            else:
                # For direct URLs, implement sitemap or blog archive scraping
                articles = self.scrape_blog_archive(source_url, source.get('max_articles', 20))
            
            for article in articles:
                article['source_name'] = source_name
                all_articles.append(article)
            
            logger.info(f"Scraped {len(articles)} articles from {source_name}")
        
        # Save to CSV
        if all_articles:
            df = pd.DataFrame(all_articles)
            # Remove duplicates based on title similarity
            df = self.remove_duplicate_articles(df)
            df.to_csv(output_file, index=False, escapechar='\\')
            logger.info(f"Saved {len(df)} unique articles to {output_file}")
            return df
        else:
            logger.warning("No articles were scraped")
            return pd.DataFrame()
    
    def remove_duplicate_articles(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate articles based on title similarity"""
        if len(df) == 0:
            return df
        
        # Simple deduplication based on title similarity
        seen_titles = set()
        indices_to_keep = []
        
        for idx, row in df.iterrows():
            title_words = set(row['title'].lower().split())
            is_duplicate = False
            
            for seen_title in seen_titles:
                seen_words = set(seen_title.split())
                # If more than 70% of words overlap, consider it a duplicate
                if len(title_words & seen_words) / max(len(title_words), len(seen_words)) > 0.7:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_titles.add(row['title'].lower())
                indices_to_keep.append(idx)
        
        return df.loc[indices_to_keep].reset_index(drop=True)
    
    def scrape_blog_archive(self, blog_url: str, max_articles: int = 20) -> List[Dict]:
        """Scrape blog archive page for article links"""
        articles = []
        try:
            response = self.session.get(blog_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find article links
            link_selectors = [
                'a[href*="/blog/"]',
                'a[href*="/post/"]',
                'a[href*="/article/"]',
                '.post-title a',
                '.entry-title a',
                'h2 a',
                'h3 a'
            ]
            
            found_links = set()
            for selector in link_selectors:
                links = soup.select(selector)
                for link in links[:max_articles]:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(blog_url, href)
                        if full_url not in found_links:
                            found_links.add(full_url)
            
            # Scrape each article
            for url in list(found_links)[:max_articles]:
                article = self.scrape_article_from_url(url)
                if article:
                    articles.append(article)
                    
        except Exception as e:
            logger.error(f"Error scraping blog archive {blog_url}: {str(e)}")
            
        return articles

# Better sources for AI/ML content with RSS feeds
ENHANCED_SOURCES = [
    {
        'name': 'Towards Data Science',
        'url': 'https://towardsdatascience.com/feed',
        'type': 'rss',
        'max_articles': 30
    },
    {
        'name': 'Machine Learning Mastery',
        'url': 'https://machinelearningmastery.com/feed/',
        'type': 'rss',
        'max_articles': 25
    },
    {
        'name': 'Google AI Blog',
        'url': 'https://ai.googleblog.com/feeds/posts/default',
        'type': 'rss',
        'max_articles': 20
    },
    {
        'name': 'OpenAI Blog',
        'url': 'https://openai.com/blog/rss.xml',
        'type': 'rss',
        'max_articles': 15
    },
    {
        'name': 'Distill.pub',
        'url': 'https://distill.pub/rss.xml',
        'type': 'rss',
        'max_articles': 10
    },
    {
        'name': 'Analytics Vidhya',
        'url': 'https://www.analyticsvidhya.com/feed/',
        'type': 'rss',
        'max_articles': 25
    },
    {
        'name': 'KDnuggets',
        'url': 'https://www.kdnuggets.com/feed',
        'type': 'rss',
        'max_articles': 20
    }
]

# Usage example
if __name__ == "__main__":
    scraper = EnhancedArticleScraper(max_words=1200, min_words=200, delay=2)
    
    # Scrape from multiple sources
    df = scraper.scrape_multiple_sources(
        sources=ENHANCED_SOURCES[:4],  # Start with first 4 sources
        output_file='enhanced_ai_articles.csv'
    )
    
    print(f"Scraping completed. Total articles: {len(df)}")
    if len(df) > 0:
        print(f"Sources: {df['source_name'].value_counts().to_dict()}")
        print(f"Average word count: {df['word_count'].mean():.1f}")
        print(f"Word count range: {df['word_count'].min()} - {df['word_count'].max()}")
