"""Fetch HTML/RSS publicly with strict SSRF checks. Fail closed on redirects."""
import ipaddress
import socket
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from fastapi import HTTPException
import httpx
from .config import settings


def validate_public_url(url: str, resolve: bool=True):
    p = urlparse(url)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:
        raise HTTPException(400,'URL HTTP(S) publique requise.')
    if p.port and p.port not in (80,443):
        raise HTTPException(400,'Port réseau non autorisé.')
    host = p.hostname.lower().rstrip('.')
    if host in ('localhost','localhost.localdomain') or host.endswith(('.local','.internal','.localhost')):
        raise HTTPException(400,'Adresse locale interdite.')
    try:
        parsed_ip=ipaddress.ip_address(host)
        if not parsed_ip.is_global:
            raise HTTPException(400,'Adresse IP non publique interdite.')
    except ValueError:
        pass
    if not resolve:
        return url
    try:
        addr = socket.getaddrinfo(host,None,proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise HTTPException(400,'Nom de domaine introuvable.') from None
    if not addr or any(not ipaddress.ip_address(x[4][0]).is_global for x in addr):
        raise HTTPException(400,'Adresse IP non publique interdite.')
    return url


async def fetch_public(url: str):
    validate_public_url(url)
    headers = {'User-Agent':'HAMARINO-Hackathon/1.0 (source verification; academic prototype)',
               'Accept':'text/html,application/rss+xml,application/xml,text/xml'}
    try:
        async with httpx.AsyncClient(timeout=12,follow_redirects=False,trust_env=False) as client:
            response = await client.get(url,headers=headers)
            if response.status_code in (301,302,303,307,308):
                # No automatic redirect: prevents redirect-based SSRF.
                raise HTTPException(422,'Redirection bloquée. Fournir l’URL finale publique.')
            response.raise_for_status()
            if int(response.headers.get('Content-Length','0') or 0)>settings().max_fetch_bytes:
                raise HTTPException(413,'Contenu trop volumineux.')
            if len(response.content)>settings().max_fetch_bytes:
                raise HTTPException(413,'Contenu trop volumineux.')
            ctype=response.headers.get('content-type','').lower()
            if not any(k in ctype for k in ('html','xml','rss','text/plain')):
                raise HTTPException(422,'La page ne contient pas de texte HTML/XML utilisable.')
            return response.text
    except httpx.HTTPError as e:
        raise HTTPException(422,f'Impossible de charger cette URL : {type(e).__name__}') from e


def extract_article(html: str, url: str):
    soup=BeautifulSoup(html,'html.parser')
    for node in soup(['script','style','nav','header','footer','aside','form','noscript']):
        node.decompose()
    title=(soup.title.get_text(' ',strip=True) if soup.title else url)[:400]
    candidate=soup.find('article') or soup.find('main') or soup.body or soup
    sections=candidate.find_all(['h1','h2','h3','p','li'])
    content='\n'.join(n.get_text(' ',strip=True) for n in sections) if sections else candidate.get_text(' ',strip=True)
    # Do not use nav/ads text as evidence when an article cannot be identified.
    return title,content[:80_000]
