import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from .config import settings


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def connection():
    path = Path(settings().database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=30)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA foreign_keys=ON')
    return con


def init_db():
    with connection() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS sources (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, website TEXT NOT NULL,
            rss_url TEXT, category TEXT NOT NULL DEFAULT 'media',
            trusted INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, source_id TEXT, title TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE, content TEXT NOT NULL,
            published_at TEXT, fetched_at TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'article',
            FOREIGN KEY(source_id) REFERENCES sources(id)
        );
        CREATE TABLE IF NOT EXISTS verifications (
            id TEXT PRIMARY KEY, input_type TEXT NOT NULL, original_text TEXT NOT NULL,
            extracted_text TEXT, input_url TEXT, verdict TEXT NOT NULL,
            summary TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL
        );
        ''')
        for id_, name, website, rss, category, trusted in DEFAULT_SOURCES:
            db.execute('''INSERT OR IGNORE INTO sources
                (id,name,website,rss_url,category,trusted,created_at)
                VALUES (?,?,?,?,?,?,?)''', (id_, name, website, rss, category, trusted, utcnow()))

DEFAULT_SOURCES = [
    ('rfi-afrique','RFI Afrique','https://www.rfi.fr/fr/afrique',
     'https://www.rfi.fr/fr/afrique/rss','media',0),
    ('meteomadagascar','Météo Madagascar','https://www.meteomadagascar.mg/',
     None,'institution',1),
    ('afp-factuel','AFP Factuel','https://factuel.afp.com/',None,'factcheck',1),
    ('oms','Organisation mondiale de la Santé','https://www.who.int/fr/',
     None,'institution',1),
]


def all_sources():
    with connection() as db:
        return [dict(r) for r in db.execute('SELECT * FROM sources ORDER BY name')]


def add_source(name, website, rss_url, category, trusted):
    sid = str(uuid4())
    with connection() as db:
        db.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?)',
                   (sid,name,website,rss_url,category,int(trusted),utcnow()))
    return sid


def store_document(source_id, title, url, content, published_at=None, kind='article'):
    did = str(uuid4())
    with connection() as db:
        db.execute('''INSERT INTO documents
            (id,source_id,title,url,content,published_at,fetched_at,kind)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(url) DO UPDATE SET title=excluded.title,
            content=excluded.content, published_at=excluded.published_at,
            fetched_at=excluded.fetched_at,source_id=excluded.source_id''',
            (did,source_id,title,url,content[:80_000],published_at,utcnow(),kind))
        row = db.execute('SELECT id FROM documents WHERE url=?', (url,)).fetchone()
        return row['id']


def get_documents(limit=1000):
    with connection() as db:
        return [dict(r) for r in db.execute('''SELECT d.*, s.name AS source_name,
            COALESCE(s.trusted,0) AS trusted, s.category AS category
            FROM documents d LEFT JOIN sources s ON d.source_id=s.id
            ORDER BY d.fetched_at DESC LIMIT ?''', (limit,))]


def save_verification(payload):
    with connection() as db:
        db.execute('''INSERT INTO verifications VALUES (?,?,?,?,?,?,?,?,?)''',
            (payload['id'],payload['input_type'],payload['original_text'],
             payload.get('extracted_text'),payload.get('input_url'),
             payload['verdict'],payload['summary'],
             json.dumps(payload,ensure_ascii=False),payload['created_at']))


def get_verification(verification_id):
    with connection() as db:
        row = db.execute('SELECT result_json FROM verifications WHERE id=?', (verification_id,)).fetchone()
        return json.loads(row['result_json']) if row else None


def recent_verifications(limit=20):
    with connection() as db:
        return [dict(r) for r in db.execute('''SELECT id,input_type,verdict,summary,
         substr(original_text,1,180) AS excerpt,created_at
         FROM verifications ORDER BY created_at DESC,id DESC LIMIT ?''',(limit,))]
