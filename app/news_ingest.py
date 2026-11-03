import asyncio
import re
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from .fetcher import fetch_public, extract_article, validate_public_url
from .news_db import PROVIDERS,put_news, list_news


def is_source_link(url,source):
    try:
        parsed=urlparse(url)
        expected=urlparse(PROVIDERS[source][1])
        return parsed.scheme=='https' and parsed.hostname and parsed.hostname.removeprefix('www.')==expected.hostname.removeprefix('www.') and parsed.path not in ('','/')
    except Exception:
        return False

def page_image(html,base):
    soup=BeautifulSoup(html,'html.parser')
    for attrs in ({'property':'og:image'},{'name':'twitter:image'}):
        tag=soup.find('meta',attrs=attrs)
        if tag and tag.get('content'):
            candidate=urljoin(base,tag.get('content',''))
            if urlparse(candidate).scheme=='https' and urlparse(candidate).hostname:
                return candidate
    article=soup.find('article') or soup.find('main')
    if article:
        image=article.find('img')
        if image:
            src=image.get('data-src') or image.get('src')
            if src:
                candidate=urljoin(base,src)
                if candidate.startswith('https://'):return candidate
    return None

def rss_image(entry):
    media=entry.get('media_content') or entry.get('media_thumbnail') or []
    for item in media:
        url=item.get('url','')
        if url.startswith('https://'): return url
    for enc in entry.get('enclosures',[]):
        url=enc.get('href','')
        if url.startswith('https://') and str(enc.get('type','')).startswith('image/'):return url
    raw=entry.get('summary','')
    soup=BeautifulSoup(raw,'html.parser')
    image=soup.find('img')
    if image and image.get('src','').startswith('https://'):return image['src']
    return None

def item_time(entry):
    for key in ('published_parsed','updated_parsed'):
        t=entry.get(key)
        if t:
            try:return datetime(*t[:6],tzinfo=timezone.utc).date().isoformat()
            except (ValueError,TypeError):pass
    return None

async def refresh_all():
    import feedparser
    result=[]
    for sid,(_,website,rss) in PROVIDERS.items():
        rows=[];error=None
        try:
            xml=await fetch_public(rss)
            feed=feedparser.parse(xml)
            for item in feed.entries[:35]:
                url=item.get('link','')
                if not is_source_link(url,sid):continue
                title=BeautifulSoup(item.get('title',''),'html.parser').get_text(' ',strip=True)
                summary=BeautifulSoup(item.get('summary',''),'html.parser').get_text(' ',strip=True)
                if len(title)<12:continue
                rows.append((title,url,summary,rss_image(item),item_time(item)))
        except Exception as exc:
            error=str(exc)[:170]
        if sid=='2424' and not rows:
            try:
                html=await fetch_public('https://www.2424.mg/actualites')
                soup=BeautifulSoup(html,'html.parser')
                for a in soup.find_all('a',href=True):
                    url=urljoin(website,a['href'])
                    title=a.get_text(' ',strip=True)
                    if not is_source_link(url,sid) or len(title)<35:continue
                    if any(x in url for x in ['/actualites','/offres','/annuaire','/petites-annonces']):continue
                    rows.append((title[:300],url,title[:350],None,None))
                    if len(rows)>=30:break
                error=None if rows else error
            except Exception as exc:
                error=str(exc)[:170]
        count=0
        seen=set()
        for title,url,summary,image,date in rows:
            if url in seen:continue
            seen.add(url)
            if not image and count<5:
                try:
                    html=await fetch_public(url)
                    actual_title,body=extract_article(html,url)
                    image=page_image(html,url)
                    if len(body)>90:summary=body[:1400]
                    if len(actual_title)>12 and actual_title not in ('Accueil','Home'):title=title
                except Exception:
                    pass
            try:
                put_news(sid,title,url,summary or title,summary or title,image,'Actualité',date)
                count+=1
            except Exception:
                continue
            if count>=18:break
        result.append({'source':PROVIDERS[sid][0],'imported':count,'error':error if count==0 else None})
    await enrich_images()
    return result

async def enrich_images(limit=22):
    from .db import connection
    with connection() as con:
        rows=[dict(x) for x in con.execute("SELECT id,url,source_id FROM news WHERE image_kind='illustration' LIMIT ?",(limit,))]
    done=0
    for item in rows:
        try:
            html=await fetch_public(item['url'])
            img=page_image(html,item['url'])
            if img:
                with connection() as con:
                    con.execute("UPDATE news SET image_url=?,image_kind='editorial' WHERE id=?",(img,item['id']))
                done+=1
        except Exception:
            continue
    return done
