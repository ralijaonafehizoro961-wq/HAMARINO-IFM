import asyncio
import re
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from .fetcher import fetch_public, extract_article
from .news_db import put_news
from .news_ingest import is_source_link


async def search_express(query, limit=5):
    search_url = (
        "https://www.lexpress.mg/search?"
        + urlencode({"q": query})
    )

    report = {
        "source": "L'Express de Madagascar",
        "query": query,
        "found": 0,
        "indexed": 0,
        "articles": [],
        "errors": [],
    }

    try:
        html = await fetch_public(search_url)
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:
        report["errors"].append(type(exc).__name__)
        return report

    candidates = []
    seen = set()

    for anchor in soup.select("a[href]"):
        url = urljoin(search_url, anchor["href"])
        title = anchor.get_text(" ", strip=True)

        if not is_source_link(url, "Express"):
            continue

        if not re.search(r"/20\d{2}/\d{2}/", url):
            continue

        if url in seen or len(title) < 15:
            continue

        seen.add(url)
        candidates.append((title, url))

    report["found"] = len(candidates)

    required = [
        word.casefold()
        for word in re.findall(r"\w+", query)
        if len(word) >= 5
    ]

    for title, url in candidates[:limit * 3]:
        if report["indexed"] >= limit:
            break

        try:
            article_html = await fetch_public(url)
            actual_title, content = extract_article(
                article_html, url
            )

            if len(content) < 100:
                continue

            searchable = (
                actual_title + " " + content
            ).casefold()

            if required and not any(
                word in searchable for word in required
            ):
                continue

            put_news(
                "Express",
                actual_title,
                url,
                content[:1400],
                content=content[:15000],
                published_at=None,
            )

            report["articles"].append({
                "title": actual_title,
                "url": url,
            })
            report["indexed"] += 1

        except Exception as exc:
            report["errors"].append(
                {
                    "url": url,
                    "error": type(exc).__name__,
                }
            )

    return report
