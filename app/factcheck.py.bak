"""API Google Fact Check Tools facultative; aucune vérité déduite d'un simple classement."""
import httpx
from .config import settings


def rating_status(rating: str):
    s=rating.lower()
    if any(k in s for k in ('faux','false','incorrect','misleading','trompeur','pants on fire','intox')):
        return 'contredit'
    if any(k in s for k in ('vrai','true','correct','accurate','exact')):
        return 'corrobore'
    return 'a_verifier'


async def search_factchecks(claim: str):
    key=settings().google_factcheck_api_key
    if not key:return []
    try:
        async with httpx.AsyncClient(timeout=9) as client:
            r=await client.get('https://factchecktools.googleapis.com/v1alpha1/claims:search',
                               params={'query':claim[:350],'key':key,'pageSize':5,'languageCode':'fr'})
            r.raise_for_status()
            rows=[]
            for c in r.json().get('claims',[]):
                for review in c.get('claimReview',[]):
                    if not review.get('url'):continue
                    rating=review.get('textualRating') or 'Note indisponible'
                    rows.append({'claim':c.get('text',''),'publisher':review.get('publisher',{}).get('name',''),
                      'url':review['url'],'rating':rating,'status':rating_status(rating),
                      'review_date':review.get('reviewDate')})
            return rows[:5]
    except (httpx.HTTPError,KeyError,ValueError):
        return []
