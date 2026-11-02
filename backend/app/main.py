from contextlib import asynccontextmanager
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, UploadFile, File, Header, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from . import db
from .schemas import TextRequest, LinkRequest, NewSource,DocumentImport,UrlImport
from .fetcher import fetch_public,extract_article,validate_public_url
from .ocr import read_media
from .verification import verify_text

@asynccontextmanager
async def lifespan(app):
    db.init_db()
    yield

app=FastAPI(title='HAMARINO — IFM / FANILO API',version='1.0.0',
    description='OCR + recherche augmentée par des sources + avis de fact-checking. Pas de verdict automatique basé sur une similarité.',
    lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['GET','POST'],
                   allow_headers=['Content-Type','X-Admin-Key'])


def require_admin(x_admin_key: str | None=Header(default=None)):
    key=settings().admin_api_key
    if not key:
        raise HTTPException(503,'Définir ADMIN_API_KEY dans backend/.env pour les opérations administrateur.')
    import hmac
    if not x_admin_key or not hmac.compare_digest(x_admin_key,key):
        raise HTTPException(401,'Clé administrateur absente ou invalide.')

@app.get('/api/health')
def health():
    return {'ok':True,'service':'HAMARINO','sdk':'expo-55',
            'ocr':'Tesseract (sur le serveur)','ai_optional':bool(settings().openai_api_key),
            'factcheck_optional':bool(settings().google_factcheck_api_key)}

@app.post('/api/verify/text')
async def verify_text_endpoint(payload: TextRequest):
    return await verify_text(payload.text)

@app.post('/api/verify/link')
async def verify_link_endpoint(payload: LinkRequest):
    html=await fetch_public(str(payload.url))
    title,text=extract_article(html,str(payload.url))
    if len(text)<30:
        raise HTTPException(422,'Impossible de lire suffisamment de texte sur cette page.')
    return await verify_text(f'{title}. {text[:8000]}',kind='link',input_url=str(payload.url))

@app.post('/api/verify/media')
async def verify_media_endpoint(file: UploadFile=File(...), extra_text: str=Form(default='')):
    ctype=(file.content_type or '').lower().split(';')[0]
    data=await file.read(settings().max_upload_bytes+1)
    if len(data)>settings().max_upload_bytes:
        raise HTTPException(413,'Fichier trop lourd (8 Mo maximum).')
    if not data:raise HTTPException(400,'Fichier vide.')
    extracted,method=read_media(data,ctype)
    content='\n'.join(x for x in (extra_text,extracted) if x)
    result=await verify_text(content,kind='media',extracted_text=extracted)
    result['ocr_method']=method
    # Persist to keep GET/history consistent.
    with db.connection() as con:
        import json
        con.execute('UPDATE verifications SET result_json=? WHERE id=?',
                    (json.dumps(result,ensure_ascii=False),result['id']))
    return result

@app.get('/api/sources')
def sources():
    return {'sources':db.all_sources(),'documents_count':len(db.get_documents())}

@app.post('/api/sources')
def source_create(payload: NewSource, admin=Depends(require_admin)):
    validate_public_url(str(payload.website),resolve=False)
    if payload.rss_url: validate_public_url(str(payload.rss_url),resolve=False)
    sid=db.add_source(payload.name,str(payload.website),str(payload.rss_url) if payload.rss_url else None,
                      payload.category,payload.trusted)
    return {'id':sid,'created':True}

@app.post('/api/corpus/document')
def add_document(payload: DocumentImport,admin=Depends(require_admin)):
    validate_public_url(str(payload.url),resolve=False)
    sources={r['id']:r for r in db.all_sources()}
    if payload.source_id not in sources:raise HTTPException(404,'Source inexistante.')
    if urlparse(str(payload.url)).hostname.removeprefix('www.') != urlparse(sources[payload.source_id]['website']).hostname.removeprefix('www.'):
        raise HTTPException(400,'Le domaine du document doit correspondre à celui de la source.')
    did=db.store_document(payload.source_id,payload.title,str(payload.url),payload.content,
                          payload.published_at,'manuel')
    return {'id':did,'indexed':True}

@app.post('/api/corpus/import-url')
async def import_url(payload:UrlImport,admin=Depends(require_admin)):
    sources={r['id']:r for r in db.all_sources()}
    if payload.source_id not in sources: raise HTTPException(404,'Source inconnue.')
    source=sources[payload.source_id]
    if urlparse(str(payload.url)).hostname.removeprefix('www.') != urlparse(source['website']).hostname.removeprefix('www.'):
        raise HTTPException(400,'Domaine non associé à cette source.')
    html=await fetch_public(str(payload.url))
    title,body=extract_article(html,str(payload.url))
    if len(body)<80:raise HTTPException(422,'Article trop court ou bloqué.')
    did=db.store_document(payload.source_id,title,str(payload.url),body)
    return {'id':did,'title':title,'characters':len(body)}

@app.post('/api/sources/refresh')
async def refresh_sources(admin=Depends(require_admin)):
    import feedparser
    report=[]
    for source in db.all_sources():
        if not source['rss_url']:continue
        try:
            xml=await fetch_public(source['rss_url'])
            feed=feedparser.parse(xml)
            total=0
            for item in feed.entries[:20]:
                link=item.get('link','')
                if not link or not link.startswith(('https://','http://')):continue
                # RSS provides summaries: cite as such, not entire article.
                from bs4 import BeautifulSoup
                raw=' '.join(str(item.get(k,'')) for k in ('title','summary','description'))
                body=BeautifulSoup(raw,'html.parser').get_text(' ',strip=True)
                if len(body)<80: continue
                try:
                    validate_public_url(link)
                except HTTPException: continue
                db.store_document(source['id'],item.get('title','Article RSS'),link,body[:10000],
                    item.get('published'),kind='rss_summary')
                total+=1
            report.append({'source':source['name'],'indexed':total})
        except Exception as e:
            report.append({'source':source['name'],'error':str(e)[:160]})
    return {'refreshed':report}

@app.get('/api/history')
def history(limit:int=20):
    return {'items':db.recent_verifications(max(1,min(limit,100)))}

@app.get('/api/verifications/{verification_id}')
def verification(verification_id:str):
    result=db.get_verification(verification_id)
    if result is None:raise HTTPException(404,'Analyse non trouvée.')
    return result

@app.get('/api/report/{verification_id}')
def report(verification_id:str):
    data=db.get_verification(verification_id)
    if data is None:raise HTTPException(404,'Analyse non trouvée.')
    return {'title':'Rapport de vérification HAMARINO',
      'id':data['id'],'date':data['created_at'],'claim':data['claim'],
      'assessment':data['verdict'],'caution':data['warning'],
      'sources':[{'url':e['url'],'title':e['title'],'passage':e['passage']}
                 for e in data['evidence']],
      'third_party_checks':data['factchecks'],
      'human_validation_required':True}
