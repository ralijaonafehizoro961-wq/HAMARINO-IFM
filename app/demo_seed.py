"""Données 100% fictives pour démonstration hors connexion. Jamais des faits réels."""
from . import db


def seed():
    db.init_db()
    sources={s['id']:s for s in db.all_sources()}
    if 'demo' not in sources:
        with db.connection() as conn:
            conn.execute('''INSERT INTO sources(id,name,website,rss_url,category,trusted,created_at)
              VALUES (?,?,?,?,?,?,?)''',('demo','DEMO — contenu entièrement fictif',
                      'https://example.org/',None,'other',0,db.utcnow()))
    docs=[
      ('Communiqué fictif : horaires du marché de Ville-Exemple',
       'https://example.org/demo/marche',
       'EXEMPLE FICTIF, NE CORRESPONDANT A AUCUN EVENEMENT REEL. '
       'Le marché de Ville-Exemple ouvre le vendredi à 8 heures et ferme à 16 heures. '
       'Ce programme ne concerne aucune ville existante et sert uniquement à tester la recherche de documents.'),
      ('Bulletin fictif : réunion du centre de démonstration',
       'https://example.org/demo/reunion',
       'EXEMPLE FICTIF. Une réunion du centre de démonstration a été annoncée le samedi à dix heures. '
       'Les participants sont fictifs et ce document ne doit jamais être utilisé comme source réelle.')
    ]
    for title,url,text in docs:
        db.store_document('demo',title,url,text,kind='demo')
    print(f'{len(docs)} documents fictifs chargés. Ne jamais les présenter comme preuves réelles.')

if __name__=='__main__':seed()
