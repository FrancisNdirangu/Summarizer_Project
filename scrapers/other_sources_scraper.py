"""
Scraper for AI/ML/Data‑Science articles from non‑Blogspot sources
===============================================================

This module provides a simple, best‑effort scraper that collects articles
from a handful of popular machine‑learning and data‑science websites that
are **not** hosted on Blogspot/Blogger.  It uses only the standard
`requests` and `BeautifulSoup` packages (no additional third‑party
dependencies) and thus should run in most Python environments without
extra installation steps.

The scraper is intentionally conservative: it looks for links on each
site’s start page that point back to the same domain and that contain
a four‑digit year segment (``/20``) in the path.  This heuristic tends
to find article pages on WordPress‑ and static‑site blogs, while
ignoring navigation links.  For each candidate link the scraper fetches
the page, extracts all paragraph text from within an ``<article>``
element if present (otherwise from the entire body), and discards
articles longer than 1,200 words.  The results are saved to a CSV file
named ``other_sources_ai_ml_scraped_data.csv`` with columns
``title``, ``content`` and ``url``.

Because websites change their markup frequently and may impose access
restrictions, this script is best treated as a starting point rather
than a production‑ready crawler.  Feel free to customise the
``START_URLS`` mapping or the extraction logic to better suit the
structure of your target sites.  When run in an environment with
internet access, the script should retrieve multiple articles from each
domain, but if a site returns HTTP errors (403/404/etc.) the script
will skip it.

Example usage::

    python other_sources_scraper.py

"""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


@dataclass
class Article:
    """Simple representation of a scraped article."""
    title: str
    content: str
    url: str


def get_links_from_page(url: str, domain: str) -> Iterable[str]:
    """Extract candidate article links from a listing page.

    The function fetches the given URL, parses all anchor tags and
    yields fully‑qualified links that:

    * reside on the same domain (including subdomains)
    * contain a four‑digit year segment (e.g. '/2024/', '/2025/') in
      their path—this is a common characteristic of blog article URLs

    Parameters
    ----------
    url:
        The page to scan for article links.
    domain:
        The domain against which links will be filtered.  Links whose
        ``netloc`` does not end with this domain are ignored.

    Yields
    ------
    str
        A fully qualified URL that appears to be an article page.
    """
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except Exception:
        return
    soup = BeautifulSoup(resp.content, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Build absolute URL
        link = urljoin(url, href)
        parsed = urlparse(link)
        # Filter to same domain
        if not parsed.netloc.endswith(domain):
            continue
        # Simple heuristic: look for year in the path (e.g. /2024/)
        if "/20" not in parsed.path:
            continue
        yield link


def extract_article(url: str, max_words: int = 1200) -> Optional[Article]:
    """Fetch and extract text from an article page.

    The function retrieves the page at ``url`` and attempts to find an
    ``<article>`` element.  If found, all paragraph texts from within
    that element are concatenated; otherwise all ``<p>`` tags in the
    document are used.  Articles with more than ``max_words`` words are
    skipped.  On success an :class:`Article` is returned.

    Parameters
    ----------
    url:
        The article URL.
    max_words:
        Maximum number of words allowed in the article body.

    Returns
    -------
    Optional[Article]
        The extracted article or ``None`` if extraction fails or the
        article is too long.
    """
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except Exception:
        return None
    soup = BeautifulSoup(resp.content, "html.parser")
    # Title: prefer <title>, fall back to <h1>
    title_tag = soup.find("title") or soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""
    # Locate article body
    article_tag = soup.find("article")
    if article_tag:
        paras = article_tag.find_all("p")
    else:
        paras = soup.find_all("p")
    content = "\n".join(p.get_text(strip=True) for p in paras)
    # Skip if no content or too long
    if not content:
        return None
    if len(content.split()) > max_words:
        return None
    return Article(title=title, content=content, url=url)


def scrape_site(domain: str, start_urls: Iterable[str], max_articles: int = 100) -> List[Article]:
    """Scrape a single domain starting from one or more pages.

    This function orchestrates link discovery and article extraction.
    It keeps track of visited URLs to avoid duplicates and stops once
    ``max_articles`` have been collected.

    Parameters
    ----------
    domain:
        The domain to which scraped links must belong.
    start_urls:
        One or more pages (listing pages or even direct article pages)
        from which to begin scraping.
    max_articles:
        Maximum number of articles to collect per domain.

    Returns
    -------
    List[Article]
        A list of successfully extracted articles.
    """
    articles: List[Article] = []
    visited: set[str] = set()
    candidate_links: List[str] = []
    # Seed candidate links from start pages
    for start in start_urls:
        # If the start URL itself looks like an article (contains /20XX/)
        # add it directly; otherwise scan for links on the page.
        if "/20" in urlparse(start).path:
            candidate_links.append(start)
        else:
            candidate_links.extend(get_links_from_page(start, domain))
    # Iterate through discovered links
    for link in candidate_links:
        if len(articles) >= max_articles:
            break
        if link in visited:
            continue
        visited.add(link)
        article = extract_article(link)
        if article:
            articles.append(article)
        # Be polite to servers
        time.sleep(1)
    return articles


def main() -> None:
    # Mapping of domains to one or more starting URLs.  You can add
    # additional sites here.  If a start URL points directly to an
    # article, it will be scraped; otherwise the scraper will look for
    # article links on that page.
    START_URLS: Dict[str, List[str]] = {
        # KDnuggets machine‑learning category page
        "kdnuggets.com": [
            "https://www.kdnuggets.com/category/machine-learning",
            # Add a specific article as a fallback
            "https://www.kdnuggets.com/5-machine-learning-papers-to-read-in-2024",
        ],
        # DeepAI machine learning glossary entry
        "deepai.org": [
            "https://deepai.org/machine-learning-glossary-and-terms/machine-learning",
        ],
        # GeeksforGeeks article comparing ML and AI
        "geeksforgeeks.org": [
            "https://www.geeksforgeeks.org/difference-between-machine-learning-and-artificial-intelligence/",
        ],
        # Hugging Face blog article on video LMM benchmarks
        "huggingface.co": [
            "https://huggingface.co/blog/timescope-video-lmm-benchmark",
        ],
        # Open Data Science (ODSC) article on random forest
        "opendatascience.com": [
            "https://opendatascience.com/how-does-the-random-forest-algorithm-work-in-machine-learning/",
        ],
        # Data Science Central article on employee retention
        "datasciencecentral.com": [
            "https://www.datasciencecentral.com/utilize-machine-learning-to-improve-employee-retention-rates/",
        ],
        # Coursera article comparing deep learning and machine learning
        "coursera.org": [
            "https://www.coursera.org/articles/deep-learning-vs-machine-learning",
        ],
        # Google Developers introduction to machine learning course overview
        "developers.google.com": [
            "https://developers.google.com/machine-learning/overview",
        ],
    }

    all_articles: List[Article] = []
    for domain, urls in START_URLS.items():
        print(f"Scraping {domain}...")
        articles = scrape_site(domain, urls)
        print(f"  collected {len(articles)} articles from {domain}")
        all_articles.extend(articles)

    # Write results to CSV
    if all_articles:
        out_path = "other_sources_ai_ml_scraped_data.csv"
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["title", "content", "url"])
            writer.writeheader()
            for art in all_articles:
                writer.writerow({
                    "title": art.title,
                    "content": art.content,
                    "url": art.url,
                })
        print(f"Saved {len(all_articles)} articles to {out_path}")
    else:
        print("No articles were scraped.")


if __name__ == "__main__":
    main()