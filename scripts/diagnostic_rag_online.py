import asyncio
import json
import sys
import time
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from app.db import get_documents
from app.rag import retrieve
from app.precision_search import search_for_claim, filter_evidence
from app.fetcher import fetch_public
from app.news_db import PROVIDERS
from app.news_ingest import is_source_link


CLAIM = " ".join(sys.argv[1:]) or (
    "Le président de Madagascar s'est rendu en Russie "
    "pour le développement durable"
)


def section(name):
    print("\n" + "=" * 72, flush=True)
    print(name, flush=True)
    print("=" * 72, flush=True)


def show_evidence(items):
    for i, item in enumerate(items[:5], 1):
        print(f"\n[{i}] {item.get('title')}")
        print("SOURCE :", item.get("source_name"))
        print("DATE :", item.get("published_at"))
        print("SIMILARITÉ :", item.get("relevance"))
        print("URL :", item.get("url"))
        print("PASSAGE :", str(item.get("passage", ""))[:280])


async def check_feed(source_id, provider):
    name, website, rss = provider
    try:
        xml = await asyncio.wait_for(fetch_public(rss), timeout=16)
        return {
            "source": name,
            "status": "accessible",
            "bytes": len(xml),
        }
    except Exception as exc:
        return {
            "source": name,
            "status": "erreur",
            "detail": str(exc)[:180],
        }


async def check_express_search():
    url = "https://www.lexpress.mg/search?" + urlencode({
        "q": "Russie Madagascar"
    })

    try:
        html = await asyncio.wait_for(fetch_public(url), timeout=16)
        soup = BeautifulSoup(html, "html.parser")
        found = []
        seen = set()

        for anchor in soup.select("a[href]"):
            link = urljoin(url, anchor.get("href", ""))
            title = anchor.get_text(" ", strip=True)

            if not is_source_link(link, "Express"):
                continue
            if "/20" not in link or len(title) < 15:
                continue
            if link in seen:
                continue

            seen.add(link)
            found.append({"title": title[:100], "url": link})

        return {
            "status": "accessible",
            "candidate_count": len(found),
            "examples": found[:5],
        }
    except Exception as exc:
        return {"status": "erreur", "detail": str(exc)[:180]}


async def main():
    start = time.monotonic()

    section("1. AFFIRMATION À VÉRIFIER")
    print(CLAIM)

    section("2. BASE LOCALE AVANT RECHERCHE")
    before = get_documents()
    print("Documents :", len(before))

    local = retrieve(CLAIM, limit=10)
    selected = filter_evidence(CLAIM, local)

    print("Passages RAG bruts :", len(local))
    print("Passages acceptés par le filtre :", len(selected))
    print("Passages rejetés :", len(local) - len(selected))
    show_evidence(local)

    section("3. ACCÈS AUX TROIS FLUX RSS")
    feed_results = await asyncio.gather(*[
        check_feed(sid, provider)
        for sid, provider in PROVIDERS.items()
    ])

    print(json.dumps(feed_results, ensure_ascii=False, indent=2))

    section("4. RECHERCHE DIRECTE DANS L'EXPRESS")
    discovery = await check_express_search()
    print(json.dumps(discovery, ensure_ascii=False, indent=2))

    section("5. MOTEUR AUTOMATIQUE DE HAMARINO")
    try:
        report = await asyncio.wait_for(
            search_for_claim(CLAIM),
            timeout=65
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except Exception as exc:
        print("ERREUR RECHERCHE :", type(exc).__name__, str(exc)[:300])
        report = None

    section("6. BASE LOCALE APRÈS RECHERCHE")
    after = get_documents()

    before_urls = {x["url"] for x in before}
    new_docs = [
        x for x in after
        if x["url"] not in before_urls
    ]

    print("Documents avant :", len(before))
    print("Documents après :", len(after))
    print("Nouvelles URL :", len(new_docs))

    for doc in new_docs[:6]:
        print("-", doc.get("title"))
        print(" ", doc.get("url"))

    section("7. RAG APRÈS RECHERCHE EN LIGNE")
    raw = retrieve(CLAIM, limit=10)
    filtered = filter_evidence(CLAIM, raw)

    print("Passages bruts :", len(raw))
    print("Passages filtrés :", len(filtered))
    print("Passages rejetés :", len(raw) - len(filtered))
    show_evidence(raw)

    section("8. DIAGNOSTIC PROVISOIRE")

    if not any(r["status"] == "accessible" for r in feed_results):
        print("ALERTE : les flux RSS sont inaccessibles.")
    if discovery.get("status") == "erreur":
        print("ALERTE : la recherche directe Express échoue.")

    if isinstance(report, dict):
        candidates = report.get("candidates", 0)
        indexed = report.get("indexed", 0)

        if candidates and not indexed:
            print(
                "POINT SUSPECT : articles candidats découverts, "
                "mais aucun retenu par la recherche."
            )

    if raw and not filtered:
        print(
            "POINT SUSPECT : le RAG retrouve des passages, "
            "mais le filtre les rejette tous."
        )

    if not raw:
        print(
            "POINT SUSPECT : le RAG ne retrouve aucun passage "
            "dans les documents disponibles."
        )

    print("Durée totale :", round(time.monotonic() - start, 1), "s")


asyncio.run(main())
