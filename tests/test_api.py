import io
from PIL import Image
from app import db
from app.fetcher import validate_public_url
from fastapi import HTTPException
import pytest


def test_health_and_sources(client):
    response=client.get('/api/health')
    assert response.status_code==200
    assert response.json()['ok'] is True
    sources=client.get('/api/sources').json()
    assert len(sources['sources'])>=3
    assert sources['documents_count']>=30


def test_unverified_without_sources(client):
    r=client.post('/api/verify/text',json={'text':'Une annonce affirme que le marché de Ville-Exemple est fermé le vendredi.'})
    assert r.status_code==200,r.text
    result=r.json()
    assert result['verdict']=='a_verifier'
    assert result['evidence']==[]
    assert result['claim']
    assert client.get('/api/verifications/'+result['id']).status_code==200
    assert client.get('/api/report/'+result['id']).json()['human_validation_required']
    assert len(client.get('/api/history').json()['items'])==1


def test_admin_protection(client):
    data={'source_id':'meteomadagascar','title':'Un titre suffisamment long',
      'content':'Une longue phrase. '*10,'url':'https://www.meteomadagascar.mg/article-1'}
    assert client.post('/api/corpus/document',json=data).status_code==401
    assert client.post('/api/corpus/document',json=data,headers={'X-Admin-Key':'bad'}).status_code==401
    response=client.post('/api/corpus/document',json=data,headers={'X-Admin-Key':'test-admin-key-1234'})
    assert response.status_code==200,response.text


def test_rag_retrieval_is_not_proof(client):
    db.store_document('meteomadagascar','Exemple de bulletin de pluie','https://www.meteomadagascar.mg/test1',
      ('Les précipitations sont prévues mardi sur la côte orientale de Madagascar. '
       'Une pluie fine pourra toucher certaines régions du versant oriental. ')*2)
    response=client.post('/api/verify/text',json={'text':'Une publication affirme que des précipitations sont prévues mardi sur la côte orientale de Madagascar.'})
    assert response.status_code==200
    data=response.json()
    assert data['verdict']=='a_verifier'
    assert data['evidence']
    assert 'meteomadagascar.mg' in data['evidence'][0]['url']
    assert data['evidence'][0]['passage']


def test_ocr_upload_mock(client,monkeypatch):
    import app.main as api
    monkeypatch.setattr(api,'read_media',lambda data,ctype:('Le marché de Ville-Exemple ouvre le vendredi.','ocr_tesseract'))
    content=io.BytesIO();Image.new('RGB',(240,60),'white').save(content,format='PNG')
    r=client.post('/api/verify/media',files={'file':('capture.png',content.getvalue(),'image/png')})
    assert r.status_code==200,r.text
    assert r.json()['extracted_text'].startswith('Le marché')
    assert r.json()['ocr_method']=='ocr_tesseract'
    assert client.get('/api/verifications/'+r.json()['id']).json()['ocr_method']=='ocr_tesseract'


def test_reject_private_networks():
    for url in ['http://127.0.0.1:5000/','http://10.0.0.1/a','http://localhost/a','ftp://example.com/a']:
        with pytest.raises(HTTPException):validate_public_url(url)


def test_invalid_url_source_domain(client):
    req={'source_id':'meteomadagascar','title':'Titre officiel météo',
      'content':'Analyse de données météorologiques. '*8,'url':'https://example.org/other'}
    r=client.post('/api/corpus/document',json=req,headers={'X-Admin-Key':'test-admin-key-1234'})
    assert r.status_code==400


def test_image_reject_unsupported(client):
    r=client.post('/api/verify/media',files={'file':('x.txt',b'hello world','text/plain')})
    assert r.status_code==415
