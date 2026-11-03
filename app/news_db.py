import hashlib
from . import db
from .news_seed import ARTICLES

PROVIDERS = {
    '2424':('2424.mg','https://www.2424.mg/','https://www.2424.mg/feed/'),
    'Midi':('Midi Madagasikara','https://midi-madagasikara.mg/','https://midi-madagasikara.mg/feed/'),
    'Express':("L'Express de Madagascar",'https://www.lexpress.mg/','https://www.lexpress.mg/feeds/posts/default?alt=rss')
}

def ident(url):
    return hashlib.sha256(url.encode()).hexdigest()[:20]

def init_news():
    with db.connection() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS news (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            summary TEXT NOT NULL,
            content TEXT NOT NULL,
            image_url TEXT,
            image_kind TEXT NOT NULL DEFAULT 'illustration',
            category TEXT NOT NULL,
            published_at TEXT,
            indexed_at TEXT NOT NULL,
            FOREIGN KEY(source_id) REFERENCES sources(id)
        );
        CREATE INDEX IF NOT EXISTS idx_news_date ON news(published_at DESC);
        CREATE INDEX IF NOT EXISTS idx_news_source ON news(source_id);
        ''')
        for sid,(name,website,rss) in PROVIDERS.items():
            con.execute('''INSERT INTO sources(id,name,website,rss_url,category,trusted,created_at)
                VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,
                website=excluded.website,rss_url=excluded.rss_url''',
                (sid,name,website,rss,'media',0,db.utcnow()))
        for sid,title,url,date,category,summary,image in ARTICLES:
            nid=ident(url)
            con.execute('''INSERT OR IGNORE INTO news(id,source_id,title,url,summary,content,image_url,image_kind,category,published_at,indexed_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                (nid,sid,title,url,summary,title+'. '+summary,image or '/api/news/'+nid+'/cover',
                'editorial' if image else 'illustration',category,date,db.utcnow()))
            con.execute('''INSERT INTO documents(id,source_id,title,url,content,published_at,fetched_at,kind)
                VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(url) DO NOTHING''',
                ('n'+nid,sid,title,url,title+'. '+summary,date,db.utcnow(),'seed_excerpt'))

def put_news(source_id,title,url,summary,content='',image_url=None,category='Actualité',published_at=None):
    if source_id not in PROVIDERS: raise ValueError('Source inconnue')
    nid=ident(url)
    with db.connection() as con:
        con.execute('''INSERT INTO news(id,source_id,title,url,summary,content,image_url,image_kind,category,published_at,indexed_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(url) DO UPDATE SET
        title=excluded.title,summary=CASE WHEN length(excluded.summary)>length(news.summary)
        THEN excluded.summary ELSE news.summary END,
        content=CASE WHEN length(excluded.content)>length(news.content) THEN excluded.content ELSE news.content END,
        image_url=CASE WHEN excluded.image_kind='editorial' THEN excluded.image_url ELSE news.image_url END,
        image_kind=CASE WHEN excluded.image_kind='editorial' THEN 'editorial' ELSE news.image_kind END,
        published_at=COALESCE(excluded.published_at,news.published_at),indexed_at=excluded.indexed_at''',
        (nid,source_id,title[:350],url,summary[:1600],content[:15000] or summary[:1600],image_url or '/api/news/'+nid+'/cover',
        'editorial' if image_url else 'illustration',category,published_at,db.utcnow()))
    db.store_document(source_id,title,url,content or title+'. '+summary,published_at,'rss_summary' if not content else 'article')
    return nid

def list_news(source=None,q='',limit=30,offset=0):
    where=['1=1'];args=[]
    if source and source in PROVIDERS:where.append('n.source_id=?');args.append(source)
    if q:
        where.append('(n.title LIKE ? OR n.summary LIKE ?)');args.extend(['%'+q+'%']*2)
    sql='''SELECT n.*,s.name AS source_name FROM news n JOIN sources s ON n.source_id=s.id WHERE '''+' AND '.join(where)+''' ORDER BY n.published_at DESC,n.indexed_at DESC,n.id LIMIT ? OFFSET ?'''
    with db.connection() as con:
        items=[dict(x) for x in con.execute(sql,(*args,limit,offset))]
        total=con.execute('SELECT COUNT(*) FROM news n WHERE '+' AND '.join(where),args).fetchone()[0]
    return items,total

def get_news(nid):
    with db.connection() as con:
        row=con.execute('SELECT n.*,s.name AS source_name FROM news n JOIN sources s ON s.id=n.source_id WHERE n.id=?',(nid,)).fetchone()
    return dict(row) if row else None

def stats():
    with db.connection() as con:
        total=con.execute('SELECT COUNT(*) FROM news').fetchone()[0]
        by_source={x['source_id']:x['cnt'] for x in con.execute('SELECT source_id,COUNT(*) cnt FROM news GROUP BY source_id')}
        analyses=con.execute('SELECT COUNT(*) FROM verifications').fetchone()[0]
        last=con.execute('SELECT MAX(indexed_at) FROM news').fetchone()[0]
    return {'articles':total,'analyses':analyses,'sources':len(PROVIDERS),'par_source':by_source,'last_indexed_at':last}
