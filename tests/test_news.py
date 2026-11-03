def test_news_seed_and_sources(client):
    r=client.get('/api/news')
    assert r.status_code==200
    data=r.json()
    assert data['total']==30
    assert len(data['items'])==30
    assert {x['source_id'] for x in data['items']}=={'2424','Midi','Express'}
    assert len({x['url'] for x in data['items']})==30
    assert all(x['url'].startswith('https://') for x in data['items'])

def test_news_images_and_detail(client):
    data=client.get('/api/news?source=2424').json()
    assert data['total']==10
    assert all(x['image_url'] for x in data['items'])
    news=data['items'][0]
    assert client.get('/api/news/'+news['id']).status_code==200
    cover=client.get('/api/news/'+news['id']+'/cover')
    assert cover.status_code==200
    assert cover.headers['content-type']=='image/png'
    assert cover.content[:8]==b'\x89PNG\r\n\x1a\n'

def test_news_search_and_stats(client):
    r=client.get('/api/news?q=Behoririka').json()
    assert r['total']>=3
    s=client.get('/api/news/stats').json()
    assert s['articles']==30
    assert s['par_source']=={'2424':10,'Express':10,'Midi':10}

def test_news_refresh_admin_required(client):
    assert client.post('/api/news/refresh').status_code==401
    assert client.post('/api/news/enrich-images').status_code==401

def test_comparison_no_fiction(client):
    v=client.post('/api/verify/text',json={'text':'Air Madagascar reprend son nom officiel.'})
    assert v.status_code==200
    data=v.json()
    assert 0<=data['comparison']['score']<=100
    assert data['comparison']['source_count']>=1
    assert 'non probabilité' in data['comparison']['explanation']
