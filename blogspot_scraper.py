"""
Blogspot AI/ML/Data Science Blog Scraper
========================================

This script scrapes articles from a list of Blogspot blogs focused on
machine learning, artificial intelligence and data science. Each article
is extracted with its title and main content. Only articles containing
1200 words or fewer are included in the output dataset.

The resulting data is saved in a CSV file with two columns: ``title`` and
``content``. The script is designed to be extensible: additional Blogspot
domains can be added to the ``BLOG_URLS`` list, and the scraping logic
attempts to handle common Blogspot templates by searching for typical
article containers such as ``post-body`` or ``entry-content``. Posts are
collected from the blog's landing page; if an "Older Posts" link is
present, the script will follow it to gather more posts.

Usage:
    python blogspot_scraper.py

Dependencies:
    - requests
    - beautifulsoup4

This file can be imported as a module or executed as a script. When run
as a script it writes the scraped data to ``blogspot_ai_ml_scraped_data.csv``
in the current working directory.
"""

import csv
import re
import sys
from dataclasses import dataclass
from typing import Iterable, List, Optional, Set

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/111.0 Safari/537.36"
)


@dataclass
class Article:
    title: str
    content: str
    url: str


def fetch_page(url: str) -> Optional[str]:
    """Fetches a URL and returns its text content.

    A custom user agent is provided to reduce the likelihood of being blocked
    by the server. If the request fails (network error or non-200 status),
    the function returns None.

    Args:
        url: The URL to fetch.

    Returns:
        The response text if successful, otherwise None.
    """
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        # Print error for debugging but continue execution
        print(f"Error fetching {url}: {exc}", file=sys.stderr)
    return None


def extract_post_links(html: str, base_domain: str) -> List[str]:
    """Extracts likely blog post URLs from a Blogspot page.

    Blogspot blogs typically embed links to individual posts on the main
    landing page. This function searches for anchor tags whose hrefs contain
    the blog's domain and a date pattern (``YYYY/``) which is common in
    Blogspot permalinks. Links to labels, searches or feeds are ignored.

    Args:
        html: The HTML content of a Blogspot page.
        base_domain: The base domain of the blog (e.g. ``aimotion.blogspot.com``).

    Returns:
        A list of unique post URLs found on the page.
    """
    soup = BeautifulSoup(html, "html.parser")
    links: Set[str] = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # Normalise relative links
        if href.startswith("/"):
            href = f"https://{base_domain.rstrip('/')}{href}"
        # Only keep links that contain the base domain
        if base_domain not in href:
            continue
        # Ignore blogspot-specific navigation links
        if any(part in href for part in ["/search/", "/label/", "/feed", "#", "?", "/archive"]):
            continue
        # Blogspot posts usually contain a year/month in the path (YYYY/MM)
        if re.search(r"/\d{4}/\d{2}/", href):
            links.add(href)
    return sorted(links)


def find_older_post_link(html: str, base_domain: str) -> Optional[str]:
    """Finds the URL for the "Older Posts" link on a Blogspot page.

    Args:
        html: The HTML content of a Blogspot page.
        base_domain: The base domain of the blog.

    Returns:
        The full URL to the older posts page if found, otherwise None.
    """
    soup = BeautifulSoup(html, "html.parser")
    # The "Older Posts" link often contains the text "Older Posts" or has the class 'blog-pager-older-link'
    link = soup.find("a", string=re.compile("Older Posts", re.IGNORECASE))
    if not link:
        # Try class-based search
        link = soup.find("a", class_=re.compile("blog-pager-older-link", re.IGNORECASE))
    if link and link.get("href"):
        href = link["href"]
        if href.startswith("/"):
            return f"https://{base_domain.rstrip('/')}{href}"
        return href
    return None


def parse_article(html: str) -> Optional[Article]:
    """Parses an individual Blogspot post and extracts the title and content.

    This function tries multiple strategies to locate the main article content,
    including typical Blogspot containers such as ``post-body`` or
    ``entry-content``. If the extracted text is empty, None is returned.

    Args:
        html: The HTML content of the Blogspot post.

    Returns:
        An ``Article`` instance if the post could be parsed, otherwise None.
    """
    soup = BeautifulSoup(html, "html.parser")
    # Extract title
    title = None
    # Check og:title meta tag
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    if not title:
        # Fallback to title tag
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
    if not title:
        # Fallback to first h1 or h2 tag with a reasonable length
        for tag_name in ["h1", "h2", "h3"]:
            tag = soup.find(tag_name)
            if tag and tag.get_text(strip=True):
                title = tag.get_text(strip=True)
                break
    if not title:
        return None
    # Extract content from typical blogspot containers
    # Common containers: post-body, entry-content, post-content
    content_container = None
    for class_pattern in ["post-body", "entry-content", "post-content", "article-body"]:
        content_container = soup.find("div", class_=re.compile(class_pattern, re.IGNORECASE))
        if content_container:
            break
    # If no specific container found, fall back to article tag or main div
    if not content_container:
        content_container = soup.find("article")
    if not content_container:
        # As a last resort, use the body tag but this may include navigation
        content_container = soup.find("body")
    if not content_container:
        return None
    text = content_container.get_text(separator=" ", strip=True)
    if not text:
        return None
    return Article(title=title, content=text, url="")


def scrape_blog(blog_url: str, max_articles_per_blog: int = 10) -> List[Article]:
    """Scrapes a Blogspot blog and returns a list of articles.

    The function fetches the blog's main page, extracts post links,
    optionally follows the "Older Posts" link to collect additional posts,
    parses each post, and filters articles exceeding 1200 words.

    Args:
        blog_url: The base URL of the Blogspot blog (e.g. ``https://data-space-zone.blogspot.com``).
        max_articles_per_blog: Maximum number of articles to extract per blog.

    Returns:
        A list of ``Article`` instances containing the title, content and URL.
    """
    # Normalize blog URL (remove trailing slash)
    blog_url = blog_url.rstrip("/")
    base_domain = re.sub(r"https?://", "", blog_url)
    collected_articles: List[Article] = []
    visited_posts: Set[str] = set()
    pages_to_visit: List[str] = [blog_url]
    while pages_to_visit and len(collected_articles) < max_articles_per_blog:
        page_url = pages_to_visit.pop(0)
        html = fetch_page(page_url)
        if not html:
            continue
        post_links = extract_post_links(html, base_domain)
        for post_url in post_links:
            if len(collected_articles) >= max_articles_per_blog:
                break
            if post_url in visited_posts:
                continue
            visited_posts.add(post_url)
            post_html = fetch_page(post_url)
            if not post_html:
                continue
            article = parse_article(post_html)
            if not article:
                continue
            # Set the URL on the article object
            article.url = post_url
            # Filter by word count
            word_count = len(article.content.split())
            if word_count <= 1200:
                collected_articles.append(article)
        # Attempt to follow "Older Posts" link to collect more posts
        if len(collected_articles) < max_articles_per_blog:
            older_link = find_older_post_link(html, base_domain)
            if older_link and older_link not in pages_to_visit:
                pages_to_visit.append(older_link)
    return collected_articles


def save_to_csv(articles: Iterable[Article], filename: str) -> None:
    """Saves a list of articles to a CSV file with title and content columns.

    Args:
        articles: Iterable of ``Article`` instances.
        filename: The path to the CSV file to create.
    """
    with open(filename, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "content", "url"])
        for article in articles:
            writer.writerow([article.title, article.content, article.url])


def main() -> None:
    """Entry point when running as a script."""
    # List of Blogspot blogs related to AI/ML/Data Science to scrape
    BLOG_URLS = [
        "https://data-space-zone.blogspot.com",
        "https://abbottanalytics.blogspot.com",
        "https://dominicm73.blogspot.com",
        "https://firsttimeprogrammer.blogspot.com",
        "https://nlpers.blogspot.com",
        "https://practicalcheminformatics.blogspot.com",
        "https://davegiles.blogspot.com",
        "https://muratbuffalo.blogspot.com",
        "https://aimotion.blogspot.com",
        "https://qingkaikong.blogspot.com",
        "https://acm-datascience-blog.blogspot.com",
    ]
    all_articles: List[Article] = []
    for blog_url in BLOG_URLS:
        print(f"Scraping {blog_url}…")
        try:
            articles = scrape_blog(blog_url, max_articles_per_blog=100)
            print(f"  Found {len(articles)} articles from {blog_url}")
            all_articles.extend(articles)
        except Exception as exc:
            print(f"  Error scraping {blog_url}: {exc}", file=sys.stderr)
    if not all_articles:
        print("No articles were scraped.")
        return
    output_file = "blogspot_ai_ml_scraped_data_100_per_blog.csv"
    save_to_csv(all_articles, output_file)
    print(f"Saved {len(all_articles)} articles to {output_file}")


if __name__ == "__main__":
    main()