from app.precision_search import terms, queries, relevance_gate

def test_query_not_hardcoded():
    assert 'riz' in queries('Le prix du riz augmente fortement')[0]
    assert 'russie' in queries('Le président voyage en Russie')[0]

def test_wrong_person_and_purpose():
    assert not relevance_gate(
        'Le président de Madagascar est allé en Russie pour le développement durable',
        "Le président de l'Assemblée nationale s'est rendu en Russie pour la coopération interparlementaire"
    )

def test_relevant_passage():
    assert relevance_gate(
        'Air Madagascar reprend son nom historique',
        'Air Madagascar annonce reprendre son nom historique après la réforme.'
    )
