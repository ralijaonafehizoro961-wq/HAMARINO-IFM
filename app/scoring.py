def comparison(evidence):
    if not evidence:
        return {'score':0,'label':'Aucune concordance détectée','level':'insufficient','source_count':0,
                'matched_articles':0,'method':'TF-IDF mots et caractères, diversité des rédactions',
                'explanation':'Aucun passage comparable dans le corpus actuel. Ce résultat ne signifie pas que l’affirmation est fausse.',
                'sources':[]}
    ordered=sorted(evidence,key=lambda e:e['relevance'],reverse=True)
    distinct={e['source_name'] for e in ordered}
    best=ordered[0]['relevance']
    avg=sum(x['relevance'] for x in ordered[:3])/min(len(ordered),3)
    score=round(min(95,(best*65+avg*25)*1.28 +8*max(0,len(distinct)-1)))
    level='strong' if score>=67 and len(distinct)>=2 else 'moderate' if score>=35 else 'weak'
    labels={'strong':'Forte concordance des contenus','moderate':'Concordance partielle','weak':'Rapprochement faible'}
    return {'score':score,'label':labels[level],'level':level,'source_count':len(distinct),
        'matched_articles':len(ordered),'method':'TF-IDF lexical (mots 65 %, caractères 35 %) + diversité des sources',
        'explanation':'Score de rapprochement éditorial, non probabilité que l’information soit vraie. Les médias peuvent reprendre la même dépêche.',
        'sources':[{'source':e['source_name'],'score':round(e['relevance']*100),'title':e['title'],'url':e['url']}
                  for e in ordered]}
