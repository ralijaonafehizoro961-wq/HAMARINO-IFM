import asyncio
from urllib.parse import urlencode
from bs4 import BeautifulSoup

from app.fetcher import fetch_public
from app.news_ingest import is_source_link

QUERY = "Andry Rajoelina"

SEARCHES = {
    "2424": "https://www.2424.mg/?" + urlencode({"s": QUERY}),
    "Midi": "https://midi-madagasikara.mg/?" + urlencode({"s": QUERY}),
    "Express": "https://www.lexpress.mg/search?" + urlencode({"q": QUERY}),
}


async def test_search(source, url):
    print(f"\n===== {source} =====")
    print("Recherche :", url)

    try:
        html = await fetch_public(url)
        soup = BeautifulSoup(html, "html.parser")

        print("Page :", soup.title.get_text(" ", strip=True)[:100]
              if soup.title else "Sans titre")

        results = []
        seen = set()

        for a in soup.select("a[href]"):
            href = a.get("href", "")
            title = a.get_text(" ", strip=True)

            if not is_source_link(href, source):
                continue

            if href in seen or len(title) < 20:
                continue

            seen.add(href)
            results.append((title[:100], href))

        print("Liens candidats :", len(results))

        for title, href in results[:5]:
            print("-", title)
            print(" ", href)

    except Exception as exc:
        print("Erreur :", type(exc).__name__)
        print("Détail :", str(exc)[:200])


async def main():
    for source, url in SEARCHES.items():
        await test_search(source, url)


asyncio.run(main())
