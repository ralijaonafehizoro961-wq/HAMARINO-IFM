import asyncio
import time

import feedparser
import httpx
from bs4 import BeautifulSoup

from .news_db import PROVIDERS, put_news
from .news_ingest import is_source_link


_last_attempt = 0.0
_last_report = []
_last_state = None
_lock = asyncio.Lock()


async def fetch_feed(client, source_id, provider):
    name, website, rss_url = provider

    try:
        response = await client.get(rss_url)
        response.raise_for_status()

        feed = feedparser.parse(response.content)
        imported = 0

        for entry in feed.entries[:15]:
            url = entry.get("link", "")

            if not is_source_link(url, source_id):
                continue

            title = BeautifulSoup(
                entry.get("title", ""),
                "html.parser",
            ).get_text(" ", strip=True)

            summary = BeautifulSoup(
                entry.get("summary", ""),
                "html.parser",
            ).get_text(" ", strip=True)

            if len(title) < 12:
                continue

            put_news(
                source_id,
                title,
                url,
                summary or title,
                published_at=None,
            )

            imported += 1

        return {
            "source": name,
            "imported": imported,
            "error": None,
        }

    except Exception as exc:
        return {
            "source": name,
            "imported": 0,
            "error": type(exc).__name__,
        }


async def refresh_feeds_fast():
    async with httpx.AsyncClient(
        timeout=7.0,
        follow_redirects=True,
    ) as client:
        tasks = [
            fetch_feed(client, sid, provider)
            for sid, provider in PROVIDERS.items()
        ]

        return await asyncio.gather(*tasks)


async def refresh_recent_if_needed(claim, evidence):
    global _last_attempt, _last_report, _last_state

    if len(evidence) >= 2:
        return {
            "state": "local_sufficient",
            "searched_online": False,
            "feeds": [],
        }

    async with _lock:
        now = time.monotonic()

        interval = 900 if _last_state in (
            "refreshed", "partial"
        ) else 90

        if _last_attempt and now - _last_attempt < interval:
            return {
                "state": "cached",
                "searched_online": False,
                "previous_state": _last_state,
                "feeds": _last_report,
            }

        _last_attempt = now

        try:
            report = await asyncio.wait_for(
                refresh_feeds_fast(),
                timeout=18,
            )

            imported = sum(
                item["imported"] for item in report
            )

            has_error = any(
                item["error"] for item in report
            )

            if imported and has_error:
                state = "partial"
            elif imported:
                state = "refreshed"
            elif has_error:
                state = "error"
            else:
                state = "no_articles"

            _last_report = report
            _last_state = state

            return {
                "state": state,
                "searched_online": True,
                "imported": imported,
                "feeds": report,
            }

        except TimeoutError:
            _last_report = []
            _last_state = "timeout"

            return {
                "state": "timeout",
                "searched_online": True,
                "feeds": [],
                "error": "Délai global de 18 secondes dépassé",
            }
